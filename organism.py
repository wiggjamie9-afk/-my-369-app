#!/usr/bin/env python3
"""AI9 organism back end: turns harness results into status.json.

Standard library only. No network calls, no keys. Python 3.8+.

    python3 organism.py ingest results.json        archive a results file, rebuild status.json
    python3 organism.py ingest a.jsonl b.csv --model my-model
    python3 organism.py beat sense ok "3 feeds scanned" --ttl 3600
    python3 organism.py build                      rebuild status.json from the archive
    python3 organism.py serve                      rebuild on every read, serve the console locally
    python3 organism.py connect [FOLDER ...]       watch folders for results, ingest them, serve the console
    python3 organism.py connect ~/harness/out --lan   same, and reachable from a phone on the same network

"connect" is the one command that joins everything up: point it at the folder
the harness writes its results into (default: a "results" folder beside this
script) and leave it running. New or changed results files are archived within
a few seconds and the console updates by itself.

Results files may be JSON (a list of runs, or an object holding one), JSON
Lines, or CSV. Field names are matched loosely: task/id/name, model,
status/result/passed, secs/duration/elapsed (or *_ms), timestamp/at,
error/reason. Ingesting the same file twice changes nothing.

Each ingested file is one batch. A model's score is its most recent batch;
every batch becomes one point in the history trend.
"""

import argparse
import csv
import functools
import hashlib
import io
import json
import os
import socket
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))

ORGANS = [("sense", "Research"), ("model", "Cortex"), ("decide", "Kernel"),
          ("verify", "Immune"), ("learn", "Memory")]
ORGAN_IDS = [o[0] for o in ORGANS]
STATES = ("ok", "busy", "down")

TASK_KEYS = ("task", "task_id", "taskid", "id", "name", "test", "case", "problem")
MODEL_KEYS = ("model", "model_name", "modelname", "engine", "llm")
STATUS_KEYS = ("status", "result", "outcome", "verdict", "grade")
BOOL_KEYS = ("passed", "pass", "ok", "success", "correct", "is_correct")
SECS_KEYS = ("secs", "seconds", "sec", "duration", "duration_s", "duration_sec",
             "elapsed", "elapsed_s", "latency", "runtime", "time_s", "took")
MS_KEYS = ("ms", "duration_ms", "elapsed_ms", "latency_ms", "time_ms")
TIME_KEYS = ("at", "timestamp", "ts", "finished", "finished_at", "completed",
             "started", "started_at", "date", "datetime", "time")
REASON_KEYS = ("reason", "error", "message", "detail", "failure")
LIST_KEYS = ("runs", "results", "tasks", "records", "items", "data")
RESULT_EXTS = (".json", ".jsonl", ".ndjson", ".csv", ".tsv")

PASS_WORDS = {"pass", "passed", "ok", "success", "succeeded", "true", "1", "correct", "yes", "y"}
FAIL_WORDS = {"fail", "failed", "failure", "error", "errored", "false", "0", "incorrect",
              "timeout", "timed_out", "no", "n", "wrong", "crash", "crashed"}


# ---------------------------------------------------------------- small helpers

def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso():
    return iso(datetime.now(timezone.utc))


def as_float(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def parse_time(v):
    """Epoch seconds/milliseconds or an ISO string -> UTC ISO string, else None."""
    if v is None or isinstance(v, bool) or v == "":
        return None
    f = as_float(v)
    if f is not None:
        if f > 1e11:
            f /= 1000.0
        if f < 1e8:                      # too small to be a date: it is a duration
            return None
        try:
            return iso(datetime.fromtimestamp(f, timezone.utc))
        except (OverflowError, OSError, ValueError):
            return None
    s = str(v).strip()
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T", 1))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.astimezone()               # a time with no zone is taken as local time
    return iso(d)


def parse_status(v):
    if isinstance(v, bool):
        return "PASS" if v else "FAIL"
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    low = s.lower().replace(" ", "_")
    if low in PASS_WORDS:
        return "PASS"
    if low in FAIL_WORDS:
        return "FAIL"
    return s.upper()[:16]


def first(row, keys):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None


def clean_keys(d):
    return {str(k).strip().lower().replace(" ", "_").replace("-", "_"): v for k, v in d.items()}


def ago(seconds):
    seconds = int(max(0, seconds))
    if seconds < 90:
        return "%d s" % seconds
    if seconds < 5400:
        return "%d min" % round(seconds / 60)
    if seconds < 172800:
        return "%d h" % round(seconds / 3600)
    return "%d d" % round(seconds / 86400)


# ---------------------------------------------------------------- reading results

def normalise(raw, default_model=None, default_task=None):
    """One loosely-shaped result -> a run record, or None if it is not a run."""
    if not isinstance(raw, dict):
        return None
    row = clean_keys(raw)

    task = first(row, TASK_KEYS)
    if task is None:
        task = default_task
    status = parse_status(first(row, STATUS_KEYS))
    if status is None:
        for k in BOOL_KEYS:
            v = row.get(k)
            if isinstance(v, bool) or (isinstance(v, (int, float)) and v in (0, 1)) \
                    or (isinstance(v, str) and v.strip().lower() in PASS_WORDS | FAIL_WORDS):
                status = parse_status(bool(v) if not isinstance(v, str) else v)
                break
    if task is None or status is None:
        return None

    secs = as_float(first(row, SECS_KEYS))
    if secs is None:
        ms = as_float(first(row, MS_KEYS))
        if ms is not None:
            secs = ms / 1000.0
    at = None
    for k in TIME_KEYS:
        if k not in row:
            continue
        at = parse_time(row[k])
        if at:
            break
        if k == "time" and secs is None:  # "time" holding a small number is a duration
            secs = as_float(row[k])
    if secs is not None and secs < 0:
        secs = None

    reason = first(row, REASON_KEYS)
    model = first(row, MODEL_KEYS)
    rec = {
        "task": str(task).strip()[:120],
        "model": str(model if model is not None else (default_model or "unknown")).strip()[:120],
        "status": status,
        "secs": round(secs, 3) if secs is not None else None,
        "at": at,
    }
    if reason is not None and status != "PASS":
        rec["reason"] = " ".join(str(reason).split())[:240]
    return rec


def rows_from_json(obj, default_model):
    """Find the run rows inside whatever JSON shape the harness wrote."""
    if isinstance(obj, list):
        return [(r, default_model, None) for r in obj]
    if not isinstance(obj, dict):
        return []
    top = clean_keys(obj)
    model = first(top, MODEL_KEYS)
    model = str(model) if isinstance(model, (str, int, float)) else default_model
    for k in LIST_KEYS:
        inner = top.get(k)
        if isinstance(inner, list):
            return [(r, model, None) for r in inner]
        if isinstance(inner, dict):
            return rows_from_json(inner, model)
    if normalise(obj, model) is not None:          # the object is itself one run
        return [(obj, model, None)]
    rows = []
    for key, val in obj.items():                   # {"TREND-1": {...}} or {"TREND-1": true}
        if isinstance(val, dict):
            rows.append((val, model, str(key)))
        elif isinstance(val, bool) or (isinstance(val, str)
                                       and val.strip().lower() in PASS_WORDS | FAIL_WORDS):
            rows.append(({"status": val}, model, str(key)))
    return rows


def parse_results(text, name="", default_model=None):
    """Text of a results file -> list of run records (possibly empty)."""
    text = text.lstrip("﻿").strip()
    if not text:
        return []
    rows = None
    if text[0] in "[{":
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "organs" in obj and "updated" in obj:
                return []                          # a status.json is output, never input
            rows = rows_from_json(obj, default_model)
        except ValueError:
            rows = []
            for line in text.splitlines():         # JSON Lines
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.extend(rows_from_json(json.loads(line), default_model))
                except ValueError:
                    continue
    if rows is None:
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        rows = [(r, default_model, None) for r in csv.DictReader(io.StringIO(text), dialect=dialect)]
    out = []
    for raw, model, task in rows:
        rec = normalise(raw, model, task)
        if rec:
            out.append(rec)
    return out


# ---------------------------------------------------------------- the archive

class Store:
    """Append-only archive: runs.jsonl, batches.jsonl, heartbeats.json."""

    def __init__(self, path):
        self.path = path

    def _file(self, name):
        return os.path.join(self.path, name)

    def _lines(self, name):
        out = []
        try:
            with open(self._file(name), encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue                   # a torn line never poisons the archive
        except FileNotFoundError:
            pass
        return out

    def _append(self, name, records):
        os.makedirs(self.path, exist_ok=True)
        with open(self._file(name), "a", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def batches(self):
        return [b for b in self._lines("batches.jsonl") if isinstance(b, dict) and b.get("id")]

    def runs(self):
        return [r for r in self._lines("runs.jsonl") if isinstance(r, dict) and r.get("batch")]

    def heartbeats(self):
        try:
            with open(self._file("heartbeats.json"), encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, ValueError):
            return {}

    def add_batch(self, batch_id, at, source, records, path=None, replaces=None):
        # runs first, batch marker last: a batch only counts once it is complete
        self._append("runs.jsonl", [dict(r, batch=batch_id) for r in records])
        marker = {"id": batch_id, "at": at, "source": source, "count": len(records), "path": path}
        if replaces:
            marker["replaces"] = replaces
        self._append("batches.jsonl", [marker])

    def beat(self, organ, state, note, ttl):
        beats = self.heartbeats()
        beats[organ] = {"state": state, "note": note, "at": now_iso(), "ttl": ttl}
        os.makedirs(self.path, exist_ok=True)
        write_atomic(self._file("heartbeats.json"), json.dumps(beats, ensure_ascii=False, indent=1) + "\n")


def write_atomic(path, text):
    """Write so a reader never sees a half-written file. Returns False if unchanged."""
    try:
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return False
    except (FileNotFoundError, UnicodeDecodeError):
        pass
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".status-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return True


def ingest(store, path, default_model=None):
    """Archive one results file. Returns (batch_id, new_run_count); count 0 if already known."""
    with open(path, "rb") as fh:
        blob = fh.read()
    batch_id = hashlib.sha1(blob).hexdigest()[:12]
    if any(b["id"] == batch_id for b in store.batches()):
        return batch_id, 0
    records = parse_results(blob.decode("utf-8", errors="replace"), os.path.basename(path), default_model)
    if not records:
        raise ValueError("no runs recognised in %s (need a task and a pass/fail per row)" % path)
    stamps = [r["at"] for r in records if r["at"]]
    at = max(stamps) if stamps else iso(datetime.fromtimestamp(os.path.getmtime(path), timezone.utc))

    # A file the harness is still appending to is one growing batch, not many:
    # if this file's last version is the start of the new one, the new one replaces it.
    full = os.path.abspath(path)
    replaces = None
    earlier = [b for b in store.batches() if b.get("path") == full]
    if earlier:
        key = lambda r: (r.get("task"), r.get("model"), r.get("status"), r.get("secs"))
        old = [key(r) for r in store.runs() if r["batch"] == earlier[-1]["id"]]
        if old and len(old) <= len(records) and old == [key(r) for r in records[:len(old)]]:
            replaces = earlier[-1]["id"]
    store.add_batch(batch_id, at, os.path.basename(path), records, full, replaces)
    return batch_id, len(records)


# ---------------------------------------------------------------- building status.json

def tally(runs):
    passed = sum(1 for r in runs if r["status"] == "PASS")
    failed = sum(1 for r in runs if r["status"] == "FAIL")
    timed = [r["secs"] for r in runs if isinstance(r.get("secs"), (int, float))]
    avg = round(sum(timed) / len(timed), 2) if timed else None
    return passed, failed, avg


def build_status(store, max_runs=200, max_history=120, now=None):
    now = now or datetime.now(timezone.utc)
    batches = store.batches()
    gone = {b["replaces"] for b in batches if b.get("replaces")}
    batches = [b for b in batches if b["id"] not in gone]
    order = {b["id"]: i for i, b in enumerate(batches)}
    batches.sort(key=lambda b: (b.get("at") or "", order[b["id"]]))
    rank = {b["id"]: i for i, b in enumerate(batches)}
    batch_at = {b["id"]: b.get("at") for b in batches}

    by_batch = {}
    for r in store.runs():
        if r["batch"] in rank and r.get("task") is not None and r.get("status"):
            by_batch.setdefault(r["batch"], []).append(r)
    batches = [b for b in batches if b["id"] in by_batch]

    # each model is scored on its most recent batch
    latest = {}
    for b in batches:
        for r in by_batch[b["id"]]:
            latest[r["model"]] = b["id"]
    models = []
    for name, bid in latest.items():
        mine = [r for r in by_batch[bid] if r["model"] == name]
        passed, _, avg = tally(mine)
        models.append({
            "name": name, "pass": passed, "total": len(mine), "avg_sec": avg,
            "at": batch_at[bid],
            "tasks": [{"task": r["task"], "status": r["status"]} for r in mine],
        })
    models.sort(key=lambda m: (-(m["pass"] / m["total"]) if m["total"] else 1,
                               m["avg_sec"] if m["avg_sec"] is not None else float("inf"), m["name"]))

    # the trend follows the headline number: every model's latest batch, as of each batch
    history, standing = [], {}
    for b in batches:
        for name in dict.fromkeys(r["model"] for r in by_batch[b["id"]]):
            mine = [r for r in by_batch[b["id"]] if r["model"] == name]
            standing[name] = (tally(mine)[0], len(mine))
        history.append({"at": b.get("at"),
                        "pass": sum(p for p, _ in standing.values()),
                        "total": sum(t for _, t in standing.values()),
                        "models": len(standing)})
    history = history[-max_history:]

    runs = []
    for b in batches:                                # oldest first, so the newest run is last
        for r in by_batch[b["id"]]:
            out = {"task": r["task"], "model": r["model"], "status": r["status"],
                   "secs": r.get("secs"), "at": r.get("at") or b.get("at")}
            if r.get("reason"):
                out["reason"] = r["reason"]
            runs.append(out)
    total_runs = len(runs)
    runs = runs[-max_runs:]

    # organs: a heartbeat wins; otherwise say only what the archive itself proves
    beats = store.heartbeats()
    last = by_batch[batches[-1]["id"]] if batches else []
    l_pass, l_fail, l_avg = tally(last)
    derived = {
        "model": ("ok", "%d task%s in the latest batch%s" % (
            len(last), "" if len(last) == 1 else "s",
            " · avg %.1fs" % l_avg if l_avg is not None else "")) if last else ("rest", "no runs yet"),
        "verify": ("ok", "%d pass · %d fail judged" % (l_pass, l_fail)) if (l_pass + l_fail)
                  else ("rest", "no verdicts yet"),
        "learn": ("ok", "%d batch%s · %d runs archived" % (
            len(batches), "" if len(batches) == 1 else "es", total_runs)) if batches
                 else ("rest", "nothing archived yet"),
    }
    organs, stamps = [], [b.get("at") for b in batches if b.get("at")]
    for oid, label in ORGANS:
        beat = beats.get(oid)
        if isinstance(beat, dict) and beat.get("state") in STATES:
            state, note, at = beat["state"], str(beat.get("note") or ""), beat.get("at")
            ttl, seen = as_float(beat.get("ttl")), parse_time(at)
            if ttl and seen:
                age = (now - datetime.fromisoformat(seen.replace("Z", "+00:00"))).total_seconds()
                if age > ttl:
                    state, note = "down", "no heartbeat for %s" % ago(age)
            if seen:
                stamps.append(seen)
            organs.append({"id": oid, "label": label, "state": state, "note": note, "at": at, "source": "heartbeat"})
        else:
            state, note = derived.get(oid, ("rest", "no heartbeat yet"))
            organs.append({"id": oid, "label": label, "state": state, "note": note, "source": "derived"})

    return {
        # the moment the organism last changed, so rebuilding is repeatable
        "updated": max(stamps) if stamps else iso(now),
        "organs": organs,
        "models": models,
        "runs": runs,
        "history": history,
        "totals": {"batches": len(batches), "runs": total_runs},
    }


def validate(status):
    """Raise ValueError unless this is a status.json the console can read."""
    def need(cond, msg):
        if not cond:
            raise ValueError("invalid status: " + msg)
    need(isinstance(status, dict), "not an object")
    need(parse_time(status.get("updated")) is not None, "updated is not a timestamp")
    for key in ("organs", "models", "runs"):
        need(isinstance(status.get(key), list), key + " is not a list")
    need([o.get("id") for o in status["organs"]] == ORGAN_IDS, "organs are not the five in order")
    for o in status["organs"]:
        need(o.get("state") in STATES + ("rest",), "organ %s has state %r" % (o.get("id"), o.get("state")))
    for m in status["models"]:
        need(isinstance(m.get("name"), str) and m["name"], "model without a name")
        need(isinstance(m.get("pass"), int) and isinstance(m.get("total"), int), "model counts not integers")
        need(0 <= m["pass"] <= m["total"], "model %s has pass > total" % m["name"])
    for r in status["runs"]:
        need(all(isinstance(r.get(k), str) and r[k] for k in ("task", "model", "status")), "run missing a field")
        need(r.get("secs") is None or isinstance(r["secs"], (int, float)), "run secs not a number")
    json.dumps(status, allow_nan=False)
    return status


def build(store, out, max_runs=200):
    status = validate(build_status(store, max_runs=max_runs))
    changed = write_atomic(out, json.dumps(status, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    return status, changed


# ---------------------------------------------------------------- watching for results

class Watcher(threading.Thread):
    """Polls folders for results files and archives whatever is new."""

    def __init__(self, store, out, folders, max_runs=200, interval=5.0, settle=2.0,
                 default_model=None, log=print):
        super().__init__(daemon=True)
        self.store, self.out, self.max_runs = store, os.path.abspath(out), max_runs
        self.folders = [os.path.abspath(f) for f in folders]
        self.interval, self.settle, self.default_model, self.log = interval, settle, default_model, log
        self.seen = {}
        self.stop = threading.Event()

    def candidates(self):
        skip = os.path.abspath(self.store.path)
        for folder in self.folders:
            for root, dirs, files in os.walk(folder):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "__pycache__"
                                 and os.path.abspath(os.path.join(root, d)) != skip)
                for name in sorted(files):
                    path = os.path.join(root, name)
                    if name.startswith(".") or not name.lower().endswith(RESULT_EXTS):
                        continue
                    if os.path.abspath(path) == self.out:
                        continue
                    yield path

    def scan(self):
        """One pass. Returns how many new runs were archived."""
        added, found = 0, []
        for path in self.candidates():
            try:
                st = os.stat(path)
            except OSError:
                continue
            if 0 <= time.time() - st.st_mtime < self.settle:
                continue                           # still being written: look again next pass
            sig = (st.st_mtime_ns, st.st_size)
            if self.seen.get(path) == sig:
                continue
            self.seen[path] = sig
            found.append((st.st_mtime_ns, path))
        for _, path in sorted(found):              # oldest file first
            try:
                batch, n = ingest(self.store, path, self.default_model)
            except (OSError, ValueError) as exc:
                self.log("skipped %s" % exc)
                continue
            if n:
                added += n
                self.log("%s: %d runs archived as batch %s" % (path, n, batch))
        if added:
            build(self.store, self.out, self.max_runs)
        return added

    def run(self):
        while not self.stop.is_set():
            try:
                self.scan()
            except Exception as exc:               # the watcher must outlive a bad pass
                self.log("watch pass failed: %s" % exc)
            self.stop.wait(self.interval)


def lan_address():
    """This machine's address on the local network, or None. Sends nothing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


# ---------------------------------------------------------------- serving locally

class ConsoleHandler(SimpleHTTPRequestHandler):
    """Serves the console, status.json and a live change feed; nothing else."""
    store = None
    out = None
    max_runs = 200
    closing = threading.Event()

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path in ("/", "/index.html"):
            self.path = "/index.html"
        elif path == "/events":
            self.events()
            return
        elif path == "/status.json":
            try:
                build(self.store, self.out, self.max_runs)
            except Exception as exc:               # serve the last good file rather than fail
                sys.stderr.write("rebuild failed: %s\n" % exc)
            self.path = "/" + os.path.basename(self.out)
        else:
            self.send_error(404)
            return
        super().do_GET()

    do_HEAD = do_GET

    def events(self):
        """Server-sent events: one "status" nudge whenever status.json changes on disk."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        last, quiet = None, 0
        try:
            while not self.closing.is_set():
                try:
                    st = os.stat(self.out)
                    sig = (st.st_mtime_ns, st.st_size)
                except OSError:
                    sig = None
                if sig != last:
                    last, quiet = sig, 0
                    self.wfile.write(b"event: status\ndata: changed\n\n")
                else:
                    quiet += 1
                    if quiet % 15 == 0:
                        self.wfile.write(b": still here\n\n")
                self.wfile.flush()
                self.closing.wait(1.0)
        except OSError:
            pass                                   # the page went away

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


# ---------------------------------------------------------------- command line

def summary(status):
    lines = ["updated %s" % status["updated"]]
    for o in status["organs"]:
        lines.append("  %-6s %-4s %s" % (o["id"], o["state"], o["note"]))
    for m in status["models"]:
        lines.append("  %s  %d/%d  avg %s" % (
            m["name"], m["pass"], m["total"], "%.1fs" % m["avg_sec"] if m["avg_sec"] is not None else "–"))
    return "\n".join(lines)


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--store", default=os.path.join(HERE, "organism-data"),
                        help="archive folder (default: organism-data beside this script)")
    common.add_argument("--out", default=os.path.join(HERE, "status.json"),
                        help="where to write status.json (default: beside this script)")
    common.add_argument("--max-runs", type=int, default=200, help="newest runs kept in status.json")

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n\n".join(__doc__.split("\n\n")[1:]))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest", parents=[common], help="archive results files and rebuild status.json")
    p.add_argument("files", nargs="+")
    p.add_argument("--model", help="model name for rows that do not carry one")
    p = sub.add_parser("beat", parents=[common], help="record an organ heartbeat and rebuild status.json")
    p.add_argument("organ", choices=ORGAN_IDS)
    p.add_argument("state", choices=STATES)
    p.add_argument("note", nargs="?", default="")
    p.add_argument("--ttl", type=float, default=None,
                   help="seconds after which a silent organ is shown as down")
    sub.add_parser("build", parents=[common], help="rebuild status.json from the archive")
    for name, text in (("serve", "serve the console locally, rebuilding on each read"),
                       ("connect", "watch folders for results, ingest them, and serve the console")):
        p = sub.add_parser(name, parents=[common], help=text)
        p.add_argument("--host", default="127.0.0.1")
        p.add_argument("--port", type=int, default=8369)
        p.add_argument("--lan", action="store_true",
                       help="also reachable from other devices on this network (read-only)")
        if name == "connect":
            p.add_argument("folders", nargs="*",
                           help="folders the harness writes results into (default: results/ beside this script)")
            p.add_argument("--model", help="model name for rows that do not carry one")
            p.add_argument("--interval", type=float, default=5.0, help="seconds between looks (default 5)")

    args = ap.parse_args(argv)
    store = Store(args.store)
    try:
        if args.cmd == "ingest":
            for path in args.files:
                batch, n = ingest(store, path, args.model)
                print("%s: %s" % (path, "%d runs archived as batch %s" % (n, batch) if n
                                  else "already archived (batch %s), nothing added" % batch))
        elif args.cmd == "beat":
            store.beat(args.organ, args.state, args.note, args.ttl)
        if args.cmd in ("serve", "connect"):
            out_dir = os.path.dirname(os.path.abspath(args.out))
            if not os.path.isfile(os.path.join(out_dir, "index.html")):
                raise ValueError("index.html must sit in the same folder as %s" % args.out)
            ConsoleHandler.store, ConsoleHandler.out, ConsoleHandler.max_runs = store, args.out, args.max_runs
            build(store, args.out, args.max_runs)
            watcher = None
            if args.cmd == "connect":
                folders = args.folders or [os.path.join(HERE, "results")]
                for folder in folders:
                    os.makedirs(folder, exist_ok=True)
                watcher = Watcher(store, args.out, folders, args.max_runs, max(1.0, args.interval),
                                  default_model=args.model)
                watcher.scan()
                watcher.start()
                print("watching for results in: %s" % ", ".join(watcher.folders))
            host = "0.0.0.0" if args.lan else args.host
            server = ThreadingHTTPServer((host, args.port),
                                         functools.partial(ConsoleHandler, directory=out_dir))
            server.block_on_close = False          # open live connections must not hold up Ctrl+C
            print("AI9 console on this machine: http://%s:%d/" % (
                "127.0.0.1" if host == "0.0.0.0" else host, args.port))
            if args.lan:
                addr = lan_address()
                print("on your network (phone, tablet): %s" % (
                    "http://%s:%d/" % (addr, args.port) if addr else "address not found, check network settings"))
            print("Ctrl+C to stop")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print()
            finally:
                ConsoleHandler.closing.set()
                if watcher:
                    watcher.stop.set()
                server.server_close()
            return 0
        status, changed = build(store, args.out, args.max_runs)
        print(summary(status))
        print("%s %s" % ("wrote" if changed else "unchanged:", args.out))
        return 0
    except (OSError, ValueError) as exc:
        sys.stderr.write("organism: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())

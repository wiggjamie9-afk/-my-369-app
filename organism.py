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

If the AI9 validation harness's results database (results/results.db) is
found, it is the source of truth: status.json is built straight from its runs
table, opened read-only, and the numbers match the harness's own score.py
(verified successes over completed runs). Pass --db to name it explicitly.

    python3 organism.py connect /opt/ai9-validation --lan

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
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.parse
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

    def __init__(self, path, db=None):
        self.path = path
        self.db = db                               # harness results.db, if there is one

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


def finish_organs(derived, beats, now):
    """The five organs in order: a live heartbeat wins, else the derived reading."""
    organs, stamps = [], []
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
    return organs, stamps


# ---------------------------------------------------------------- the validation harness database

HARNESS_COLUMNS = ("run_id", "task_id", "pack", "system", "model", "seed", "status", "repeat_index",
                   "ts_queued", "ts_start", "ts_end", "verified_success", "checks_json", "failure_type",
                   "recovery_json", "claims_total", "claims_sourced", "ext_actions_requested",
                   "ext_actions_executed", "packet_count", "duplicate_actions", "notes")
HARNESS_NEEDS = {"run_id", "task_id", "system", "status", "verified_success"}
PENDING_FRESH_S = 900          # a queued/running row older than this is an interrupted batch, not work in progress


def read_harness(path):
    """All rows of the harness runs table. Opens the database read-only; never writes to it."""
    uri = "file:%s?mode=ro" % urllib.parse.quote(os.path.abspath(path))
    try:
        con = sqlite3.connect(uri, uri=True, timeout=5)
    except sqlite3.Error as exc:
        raise ValueError("cannot open %s: %s" % (path, exc))
    try:
        have = {r[1] for r in con.execute("PRAGMA table_info(runs)")}
        if not HARNESS_NEEDS <= have:
            raise ValueError("%s is not an AI9 harness results database" % path)
        cols = [c for c in HARNESS_COLUMNS if c in have]
        cur = con.execute("SELECT rowid, %s FROM runs ORDER BY rowid" % ", ".join(cols))
        return [dict(zip(["_n"] + cols, row)) for row in cur]
    except sqlite3.Error as exc:
        raise ValueError("cannot read %s: %s" % (path, exc))
    finally:
        con.close()


def is_harness_db(path):
    try:
        read_harness(path)
        return True
    except (ValueError, OSError):
        return False


def find_harness_db(folders):
    """The first harness results.db in or just under the given folders, else None."""
    for folder in folders:
        for rel in ("results.db", os.path.join("results", "results.db")):
            path = os.path.join(folder, rel)
            if os.path.isfile(path) and is_harness_db(path):
                return os.path.abspath(path)
    return None


def _loads(text):
    try:
        return json.loads(text) if text else None
    except (TypeError, ValueError):
        return None


def harness_status(rows, beats, max_runs=200, max_history=120, now=None):
    """status.json from harness rows. Scores count what score.py counts: completed runs."""
    now = now or datetime.now(timezone.utc)
    stamp = lambda ts: iso(datetime.fromtimestamp(ts, timezone.utc)) if ts else None
    dur = lambda r: max(0, r["ts_end"] - r["ts_start"]) if r.get("ts_end") and r.get("ts_start") else None
    done = [r for r in rows if r.get("status") == "done"]
    crashed = [r for r in rows if r.get("status") == "failed"]
    waiting = [r for r in rows if r.get("status") in ("queued", "running")]
    fresh = [r for r in waiting
             if now.timestamp() - (r.get("ts_start") or r.get("ts_queued") or 0) < PENDING_FRESH_S]

    packs = {r.get("pack") or "?" for r in done + crashed}
    def group_name(r):
        name = "%s · %s" % (r.get("system") or "?", r.get("model") or "?")
        return name + " · %s" % (r.get("pack") or "?") if len(packs) > 1 else name

    groups = {}
    for r in done:
        groups.setdefault(group_name(r), []).append(r)
    models = []
    for name, runs in groups.items():
        passed = sum(1 for r in runs if r.get("verified_success"))
        times = [d for d in map(dur, runs) if d is not None]
        repeated = len({r["task_id"] for r in runs}) < len(runs)
        models.append({
            "name": name, "pass": passed, "total": len(runs),
            "avg_sec": round(sum(times) / len(times), 2) if times else None,
            "at": stamp(max((r.get("ts_end") or 0) for r in runs)),
            "system": runs[0].get("system"), "model": runs[0].get("model"), "pack": runs[0].get("pack"),
            "tasks": [{"task": "%s · seed %s rep %s" % (r["task_id"], r.get("seed"), r.get("repeat_index"))
                       if repeated else str(r["task_id"]),
                       "status": "PASS" if r.get("verified_success") else "FAIL"} for r in runs],
        })
    models.sort(key=lambda m: (-(m["pass"] / m["total"]),
                               m["avg_sec"] if m["avg_sec"] is not None else float("inf"), m["name"]))

    def why(r):
        if r.get("status") == "failed":
            return " ".join(("runner crash: %s" % (r.get("notes") or r.get("failure_type") or "")).split())[:240]
        if r.get("verified_success"):
            return None
        kind = str(r.get("failure_type") or "failed")
        if kind == "checks_failed":
            bad = [c.get("detail") for c in (_loads(r.get("checks_json")) or [])
                   if isinstance(c, dict) and not c.get("ok") and c.get("detail")]
            if bad:
                kind = "check failed: " + str(bad[0])
        return " ".join(kind.split())[:240]

    finished = sorted(done + crashed, key=lambda r: (r.get("ts_end") or r.get("ts_start") or 0, r["_n"]))
    runs_out = []
    for r in finished:
        out = {"task": str(r["task_id"]), "model": group_name(r),
               "status": "CRASH" if r.get("status") == "failed" else
                         "PASS" if r.get("verified_success") else "FAIL",
               "secs": dur(r), "at": stamp(r.get("ts_end") or r.get("ts_start"))}
        reason = why(r)
        if reason:
            out["reason"] = reason
        runs_out.append(out)

    # the headline is the organism itself, on the pack it ran most recently
    ai9 = [r for r in done if r.get("system") == "ai9"]
    headline, history = None, []
    if ai9:
        pack = max(ai9, key=lambda r: (r.get("ts_end") or 0, r["_n"])).get("pack")
        mine = [r for r in ai9 if r.get("pack") == pack]
        headline = {"label": "ai9 · %s pack" % pack,
                    "pass": sum(1 for r in mine if r.get("verified_success")), "total": len(mine)}
        days = {}
        for r in mine:
            if r.get("ts_end"):
                day = datetime.fromtimestamp(r["ts_end"], timezone.utc).strftime("%Y-%m-%d")
                days.setdefault(day, []).append(r)
        for day in sorted(days):
            history.append({"at": stamp(max(r["ts_end"] for r in days[day])),
                            "pass": sum(1 for r in days[day] if r.get("verified_success")),
                            "total": len(days[day])})
        history = history[-max_history:]

    # organs: each reads the measurement the harness logs for its stage
    derived = {}
    everything = [r for r in rows if r.get("system") == "ai9"]
    if ai9 or [r for r in fresh if r.get("system") == "ai9"]:
        claims = sum(r.get("claims_total") or 0 for r in ai9)
        sourced = sum(r.get("claims_sourced") or 0 for r in ai9)
        derived["sense"] = ("ok", "%d of %d claims carry a source" % (sourced, claims)) if claims \
            else ("rest", "no claims logged yet")

        latest = max([r for r in everything if r.get("status") in ("done", "failed")] or [None],
                     key=lambda r: (r.get("ts_end") or 0, r["_n"]) if r else (0, 0))
        times = [d for d in map(dur, ai9) if d is not None]
        busy = [r for r in fresh if r.get("system") == "ai9"]
        stuck = len([r for r in waiting if r.get("system") == "ai9"]) - len(busy)
        if busy:
            derived["model"] = ("busy", "%d run%s in progress" % (len(busy), "" if len(busy) == 1 else "s"))
        elif latest and (latest.get("status") == "failed"
                         or str(latest.get("failure_type") or "").startswith("model_error")):
            derived["model"] = ("down", "last run: %s" % why(latest))
        else:
            note = "%s · %d runs%s" % (ai9[-1].get("model") or "?", len(ai9),
                                       " · avg %.1fs" % (sum(times) / len(times)) if times else "")
            if stuck:
                note += " · %d left queued by an interrupted batch" % stuck
            derived["model"] = ("ok", note)

        asked = sum(r.get("ext_actions_requested") or 0 for r in ai9)
        acted = sum(r.get("ext_actions_executed") or 0 for r in ai9)
        derived["decide"] = ("down", "%d external action%s executed" % (acted, "" if acted == 1 else "s")) \
            if acted else ("ok", "%d external request%s · 0 executed" % (asked, "" if asked == 1 else "s"))

        recs = [_loads(r.get("recovery_json")) or {} for r in ai9]
        tried = [x for x in recs if x.get("attempted")]
        healed = [x for x in tried if x.get("result") == "success"]
        verified = sum(1 for r in ai9 if r.get("verified_success"))
        note = "%d of %d runs verified" % (verified, len(ai9))
        if tried:
            note += " · %d of %d recoveries" % (len(healed), len(tried))
        derived["verify"] = ("down" if len(healed) < len(tried) else "ok", note) if ai9 \
            else ("rest", "no verdicts yet")

        dups = sum(r.get("duplicate_actions") or 0 for r in ai9)
        derived["learn"] = ("ok", "%d runs logged · %d duplicate action%s" % (
            len(ai9), dups, "" if dups == 1 else "s")) if ai9 else ("rest", "nothing logged yet")
    else:
        for oid in ORGAN_IDS:
            derived[oid] = ("rest", "no organism runs yet")

    organs, stamps = finish_organs(derived, beats, now)
    stamps += [stamp(max(r.get("ts_end") or 0, r.get("ts_start") or 0, r.get("ts_queued") or 0)) for r in rows]
    stamps = [x for x in stamps if x]
    status = {
        "updated": max(stamps) if stamps else iso(now),
        "organs": organs,
        "models": models,
        "runs": runs_out[-max_runs:],
        "history": history,
        "totals": {"runs": len(finished), "pending": len(waiting), "crashed": len(crashed)},
        "source": "harness",
    }
    if headline:
        status["headline"] = headline
    return status


def build_status(store, max_runs=200, max_history=120, now=None):
    if store.db and os.path.isfile(store.db):
        return harness_status(read_harness(store.db), store.heartbeats(), max_runs, max_history, now)
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
    organs, stamps = finish_organs(derived, store.heartbeats(), now)
    stamps += [b.get("at") for b in batches if b.get("at")]

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
        self.db_sig = None
        self.stop = threading.Event()

    def candidates(self):
        skip = {os.path.abspath(self.store.path)}
        if self.store.db:                          # the harness keeps its own files beside its database
            skip.add(os.path.dirname(os.path.abspath(self.store.db)))
        home = os.path.dirname(os.path.abspath(self.store.db)) if self.store.db else None
        for folder in self.folders:
            if os.path.abspath(folder) in skip:
                continue
            if home and os.path.commonpath([os.path.abspath(folder), home]) == os.path.abspath(folder):
                continue                           # this folder is the harness itself: the database speaks for it
            for root, dirs, files in os.walk(folder):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "__pycache__"
                                 and os.path.abspath(os.path.join(root, d)) not in skip)
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
        db_sig = None
        if self.store.db:
            db_sig = tuple((os.stat(p).st_mtime_ns, os.stat(p).st_size) if os.path.exists(p) else None
                           for p in (self.store.db, self.store.db + "-wal", self.store.db + "-journal"))
        if added or db_sig != self.db_sig:
            try:
                build(self.store, self.out, self.max_runs)
                self.db_sig = db_sig
            except ValueError as exc:              # database busy mid-write: try again next pass
                self.log("status not rebuilt: %s" % exc)
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
    if status.get("headline"):
        lines.append("  %(label)s: %(pass)d/%(total)d verified" % status["headline"])
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
    common.add_argument("--db", default=None,
                        help="AI9 harness results.db (default: looked for in results/ and the given folders)")

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
        if args.db:
            if not is_harness_db(args.db):
                raise ValueError("%s is not a readable AI9 harness results database" % args.db)
            store.db = os.path.abspath(args.db)
        else:
            store.db = find_harness_db(list(getattr(args, "folders", None) or []) + [HERE])
        if store.db:
            print("reading the harness database (read-only): %s" % store.db)
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
                print("watching: %s" % ", ".join(([store.db] if store.db else []) + [
                    f for f in watcher.folders if not store.db
                    or os.path.commonpath([f, os.path.dirname(store.db)]) != f]))
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

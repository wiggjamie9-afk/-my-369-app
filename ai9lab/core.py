"""AI9 Lab - shared runner core: budgets, packet logging, failure injection,
recovery bookkeeping, deterministic output writing. Used by control and AI9.
"""
import json, os, time, uuid, hashlib

from . import checks
from .adapter import ModelAdapter, BudgetExceeded


def task_file_hash(path):
    """sha256 of a task file as taskpack/pack.json records it (one trailing newline ignored)."""
    blob = open(path, "rb").read()
    if blob.endswith(b"\n"):
        blob = blob[:-1]
    return hashlib.sha256(blob).hexdigest()


def run_id_for(task_id, system, seed, repeat_index):
    """Deterministic run id - same inputs, same id, so a crash+rerun resumes."""
    raw = f"{task_id}|{system}|{seed}|{repeat_index}"
    return "run-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


class RunContext:
    def __init__(self, task, system, seed, repeat_index, config, outdir):
        self.task = task
        self.system = system
        self.seed = seed
        self.repeat_index = repeat_index
        self.outdir = outdir
        self.run_id = run_id_for(task["task_id"], system, seed, repeat_index)
        self.adapter = ModelAdapter(config["model"])
        self.packets = []
        self.external_requests = []   # proposed to the kernel
        self.external_actions = []    # actually executed (Week 1: always empty)
        self.duplicate_actions = 0
        self.human_interventions = 0
        self.recovery = {"attempted": False, "result": "none", "seconds": 0, "cost": 0.0}
        self.state_files = []
        self.claims = []          # (claim_text, source_id_or_None)
        self.t0 = None

    # ---- deterministic packet log (mirrors the alpha's packet contract) ----
    def packet(self, route, payload, stage):
        pkt = {"id": "pkt-%s" % uuid.uuid5(uuid.NAMESPACE_URL,
                                           f"{self.run_id}|{len(self.packets)}").hex[:10],
               "route": route, "stage": stage, "payload": payload,
               "ts_offset": round(time.time() - self.t0, 3) if self.t0 else 0,
               "ttl": self.task.get("limits", {}).get("packet_ttl", 30)}
        fp = hashlib.sha256(json.dumps(pkt, sort_keys=True).encode()).hexdigest()[:12]
        pkt["fingerprint"] = fp
        self.packets.append(pkt)
        return pkt

    def claim(self, text, source_id=None):
        self.claims.append({"text": text, "source": source_id})

    def inject(self, fault):
        """Week-4-style fault hooks, available from Week 1 for dev tasks.
        Records the injection; runners decide behaviour. Deterministic."""
        self.packet("immune/fault", {"fault": fault}, "inject")
        if fault == "duplicate_packet" and self.packets:
            self.packets.append(dict(self.packets[-1]))
            self.duplicate_actions += 1
        elif fault == "energy_depletion":
            self.task["limits"]["token_limit"] = min(
                self.task["limits"].get("token_limit", 2000), 50)
        elif fault == "corrupted_checkpoint":
            for p in self.state_files:
                try:
                    open(p, "w").write("{corrupted")
                except Exception:
                    pass
        # worker_kill / coordinator_restart / delayed/expired packets are
        # recorded; full behavioural sims land with the Week-4 build.

    def recover(self, fn):
        """Run a recovery function with bookkeeping (seconds, result)."""
        self.recovery["attempted"] = True
        t0 = time.time()
        try:
            fn()
            self.recovery["result"] = "success"
        except Exception as e:
            self.recovery["result"] = "failed: %s" % str(e)[:80]
        self.recovery["seconds"] = round(time.time() - t0, 3)
        self.recovery["cost"] = round(self.adapter.total_cost, 6)

    def checkpoint(self, name, data):
        p = os.path.join(self.outdir, f"{self.run_id}-{name}.json")
        json.dump(data, open(p, "w"), indent=2)
        self.state_files.append(p)
        return p

    def output_dir(self):
        d = os.path.join(self.outdir, self.run_id)
        os.makedirs(d, exist_ok=True)
        return d


def finalize(ctx, output, failure_type=None, notes=""):
    """Evaluate checks, write output+event log, build the DB record."""
    out = dict(output)
    out["state_files"] = ctx.state_files
    passed, detail = checks.evaluate_all(ctx.task["success_checks"], out)
    d = ctx.output_dir()
    out_path = os.path.join(d, "output.json")
    json.dump({"run_id": ctx.run_id, "task_id": ctx.task["task_id"],
               "system": ctx.system, "output": out,
               "checks": detail}, open(out_path, "w"), indent=2)
    log_path = os.path.join(d, "events.json")
    json.dump(ctx.packets, open(log_path, "w"), indent=2)
    u = ctx.adapter.usage()
    record = {
        "verified_success": 1 if passed and not failure_type else 0,
        "checks_json": detail,
        "failure_type": failure_type or ("checks_failed" if not passed else None),
        "human_interventions": ctx.human_interventions,
        "recovery_json": ctx.recovery,
        "claims_total": len(ctx.claims),
        "claims_sourced": sum(1 for c in ctx.claims if c["source"]),
        "ext_actions_requested": len(ctx.external_requests),
        "ext_actions_executed": len(ctx.external_actions),  # always 0 in Week 1
        "packet_count": len(ctx.packets),
        "duplicate_actions": ctx.duplicate_actions,
        "usage_json": u,
        "output_path": out_path, "event_log_path": log_path,
        "notes": notes,
        "model": u["model"], "model_backend": u["backend"],
    }
    return record


def build_prompt(task, extra=""):
    """Deterministic prompt assembly from task material."""
    lim = task["limits"]
    lines = [f"AI9TASK:{task['task_id']}", f"task_kind:{task['organ']}",
             f"INSTRUCTION: {task['instruction']}", "", "MATERIAL:"]
    for m in task["input_material"]:
        if m.get("source_id"):
            lines.append(f"SOURCE: {m['source_id']} :: {m['text']}")
        else:
            lines.append(str(m.get("text", "")))
    lines += ["", f"BUDGETS: tokens<={lim['token_limit']} tools<={lim['tool_limit']} "
                  f"time<={lim['time_limit_sec']}s cost<=${lim['cost_limit']}",
              "OUTPUT FORMAT: " + task.get("output_contract", "ANSWER: ..."),
              extra]
    return "\n".join(lines)

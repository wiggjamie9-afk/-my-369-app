"""AI9 Lab - AI9 organ runner. Same adapter + same total budget as control,
but the work flows through the four organs and the kernel:

  Research  (freq 3): gathers + grounds in sources
  Memory    (freq 6): records facts with source lineage
  Routines  (freq 9): schedules the 5-stage cycle, checkpoints after stages
  Money     (freq 12): meters cost, vetoes on budget breach
  Kernel    (freq 18): permission gate - external actions are REQUESTED, the
                       kernel DECIDES. Week 1: every task is permitted external
                       actions: none -> kernel denies all, deterministically.
  Immune    (freq 15): fault injection handling + recovery supervision

Organs share state (the ctx), they are NOT four chatbots voting.
Model calls happen only when a stage needs one.
"""
import time

from . import core
from .adapter import BudgetExceeded

STAGES = ["sense", "model", "decide", "act_verify", "learn"]


class Kernel:
    """Independent deterministic permission/viability kernel.
    An organ proposes; the kernel decides. No organ approves its own action."""
    def __init__(self, task):
        self.permitted_external = task.get("permitted_external_actions", [])
        self.viability = 1.0
        self.viability_floor = 0.6
        self.decisions = []

    def request_external(self, action):
        allowed = action in self.permitted_external and self.viability >= self.viability_floor
        self.decisions.append({"action": action, "approved": bool(allowed)})
        return bool(allowed)


def run(task, seed, repeat_index, config, outdir, inject=None):
    ctx = core.RunContext(task, "ai9", seed, repeat_index, config, outdir)
    ctx.t0 = time.time()
    kernel = Kernel(task)
    failure = None
    sources, fields = [], {}

    def stage_checkpoint(stage, data):
        ctx.checkpoint("ckpt-%s" % stage, {"stage": stage, "data": data})

    ctx.packet("organs/start", {"task": task["task_id"]}, "start")

    # ---- failure injection + immune recovery (deterministic) ----
    if inject:
        ctx.inject(inject)
        if inject == "corrupted_checkpoint":
            # do a stage, corrupt its checkpoint, immune rebuilds it
            stage_checkpoint("pre", {"ok": True})
            ctx.inject("corrupted_checkpoint")
            def _rebuild():
                stage_checkpoint("pre", {"ok": True, "rebuilt": True})
            ctx.recover(_rebuild)
        elif inject == "energy_depletion":
            def _ration():
                pass  # Money organ enforces the shrunk budget; nothing to rebuild
            ctx.recover(_ration)

    # ---- ROUTINES: schedule the 5-stage local cycle ----
    ctx.packet("routines/schedule", {"stages": STAGES}, "schedule")

    answer = ""
    try:
        for stage in STAGES:
            if stage == "sense":
                # RESEARCH: read material, register sources with provenance
                srcs = [m.get("source_id") for m in task["input_material"] if m.get("source_id")]
                ctx.packet("research/sense", {"sources": srcs}, "sense")
                stage_checkpoint("sense", {"sources_seen": srcs})
            elif stage == "model":
                # one deliberation call (shared adapter, shared budget)
                prompt = core.build_prompt(task,
                    extra="You are the AI9 cortex. Cite SOURCE ids for every material claim.")
                ctx.packet("core/model_call", {}, "model")
                _cap = (min(8000, task["limits"]["token_limit"]) if config["model"].get("thinking")
                        else min(3000, task["limits"]["token_limit"] // 2))
                answer = ctx.adapter.complete(
                    prompt, max_tokens=_cap,
                    seed=seed, token_budget=task["limits"]["token_limit"])
            elif stage == "decide":
                # KERNEL: any external action the task hints at is proposed and gated
                for act in task.get("tempt_external", []):
                    ctx.external_requests.append(act)   # proposed, NOT executed
                    ok = kernel.request_external(act)
                    ctx.packet("kernel/gate", {"action": act, "approved": ok}, "decide")
                    if ok:  # never in Week 1 (permitted list is empty)
                        ctx.external_actions.append(act)
                stage_checkpoint("decide", {"kernel": kernel.decisions})
            elif stage == "act_verify":
                # no external actions in Week 1 - verification is deterministic
                for m in task["input_material"]:
                    sid = m.get("source_id")
                    if sid and sid in answer:
                        sources.append(sid)
                for ln in answer.splitlines():
                    if ln.strip():
                        ctx.claim(ln.strip()[:200],
                                  next((s for s in sources if s in ln), None))
                ctx.packet("immune/verify", {"claims": len(ctx.claims)}, "act_verify")
            elif stage == "learn":
                # MEMORY: sourced lineage of this run
                stage_checkpoint("learn", {"claims": len(ctx.claims),
                                           "sourced": sum(1 for c in ctx.claims if c["source"])})
                ctx.packet("memory/learn", {"state": ctx.state_files[-1]}, "learn")
    except BudgetExceeded:
        failure = "budget_exceeded"
    except Exception as e:
        failure = "model_error: %s" % str(e)[:80]

    # ---- MONEY: meter ----
    u = ctx.adapter.usage()
    fields["cost_usd"] = u["cost"]
    fields["kernel_denials"] = sum(1 for d in kernel.decisions if not d["approved"])
    ctx.packet("money/meter", u, "meter")

    output = {"answer_text": answer, "sources": sorted(set(sources)),
              "fields": fields, "external_actions": ctx.external_actions}
    ctx.packet("organs/end", {"failure": failure}, "end")
    return ctx, core.finalize(ctx, output, failure_type=failure)

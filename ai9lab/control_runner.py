"""AI9 Lab - single-model control runner. Equal budget to AI9: same adapter,
same task limits, ONE model call for the whole task (the classic way).
"""
import time

from . import core
from .adapter import BudgetExceeded


def run(task, seed, repeat_index, config, outdir, inject=None):
    ctx = core.RunContext(task, "control", seed, repeat_index, config, outdir)
    ctx.t0 = time.time()
    ctx.packet("control/start", {"task": task["task_id"]}, "start")
    if inject:
        ctx.inject(inject)
        if inject == "corrupted_checkpoint":
            # control has no checkpoints to corrupt; record as unsupported
            ctx.recovery = {"attempted": False, "result": "unsupported", "seconds": 0, "cost": 0.0}
    failure = None
    answer, sources, fields = "", [], {}
    try:
        prompt = core.build_prompt(task)
        ctx.packet("control/model_call", {"max_tokens": task["limits"]["token_limit"]}, "model")
        text = ctx.adapter.complete(prompt, max_tokens=min(1500, task["limits"]["token_limit"]),
                                    seed=seed, token_budget=task["limits"]["token_limit"])
        answer = text
        # provenance: sources named in the material that the answer mentions
        for m in task["input_material"]:
            sid = m.get("source_id")
            if sid and sid in text:
                sources.append(sid)
        for c in answer.splitlines():
            if c.strip():
                ctx.claim(c.strip()[:200],
                          next((s for s in sources if s in c), None))
    except BudgetExceeded:
        failure = "budget_exceeded"
    except Exception as e:
        failure = "model_error: %s" % str(e)[:80]

    output = {"answer_text": answer, "sources": sorted(set(sources)),
              "fields": fields, "external_actions": ctx.external_actions}
    ctx.packet("control/end", {"failure": failure}, "end")
    return ctx, core.finalize(ctx, output, failure_type=failure)

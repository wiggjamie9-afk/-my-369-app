"""AI9 Lab - model adapter. One shared adapter for the single-model control
AND the AI9 organ runner (per the AI9 architecture contract).

Backends:
  offline-stub      : deterministic, $0, no network. Canned behaviour keyed on
                      task markers. For harness validation and dev tuning ONLY -
                      never for benchmark claims.
  openai-compatible : POST {base_url}/chat/completions (e.g. llmgate on Hester).
                      Key comes from env var named in config (never stored).

Equal budget: the adapter enforces max_tokens per call and accumulates usage;
runners enforce the task budgets. No LLM is called 18x/sec - calls happen only
when a stage needs one.
"""
import json, os, time, urllib.request


class BudgetExceeded(Exception):
    pass


class AdapterResult:
    def __init__(self, text, prompt_tokens=0, completion_tokens=0, cost=0.0):
        self.text = text
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost = cost


class ModelAdapter:
    def __init__(self, config):
        self.backend = config.get("backend", "offline-stub")
        self.model = config.get("model", "offline-stub")
        self.base_url = config.get("base_url", "")
        self.key_env = config.get("key_env", "AI9_MODEL_KEY")
        self.price_in = float(config.get("price_per_m_in", 0.0))
        self.price_out = float(config.get("price_per_m_out", 0.0))
        self.timeout = int(config.get("timeout_sec", 120))
        self.calls = 0
        self.total_prompt = 0
        self.total_completion = 0
        self.total_cost = 0.0

    def usage(self):
        return {"calls": self.calls, "prompt_tokens": self.total_prompt,
                "completion_tokens": self.total_completion,
                "cost": round(self.total_cost, 6),
                "model": self.model, "backend": self.backend}

    def complete(self, prompt, max_tokens=800, seed=0, token_budget=None):
        """One model call. Raises BudgetExceeded if the task budget is spent."""
        est = max_tokens
        if token_budget is not None and self.total_completion + est > token_budget:
            raise BudgetExceeded("token budget exhausted")
        if self.backend == "offline-stub":
            r = self._stub(prompt, seed)
        else:
            r = self._http(prompt, max_tokens, seed)
        self.calls += 1
        self.total_prompt += r.prompt_tokens
        self.total_completion += r.completion_tokens
        self.total_cost += r.cost
        return r.text

    # ---------------- offline deterministic stub ----------------
    def _stub(self, prompt, seed):
        """Deterministic canned answers driven by task markers embedded in the
        prompt (AI9TASK:<id>). Exists to prove the harness end-to-end at $0."""
        text = _STUB_RULES(prompt)
        pt = len(prompt) // 4
        ct = len(text) // 4
        return AdapterResult(text, pt, ct, 0.0)

    # ---------------- openai-compatible HTTP backend ----------------
    def _http(self, prompt, max_tokens, seed):
        key = os.environ.get(self.key_env, "")
        body = {"model": self.model, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]}
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = "Bearer " + key
        req = urllib.request.Request(self.base_url.rstrip("/") + "/chat/completions",
                                     data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            resp = json.loads(r.read())
        msg = resp["choices"][0]["message"]
        text = msg.get("content") or ""
        u = resp.get("usage", {})
        pt = int(u.get("prompt_tokens", len(prompt) // 4))
        ct = int(u.get("completion_tokens", len(text) // 4))
        cost = pt / 1e6 * self.price_in + ct / 1e6 * self.price_out
        return AdapterResult(text, pt, ct, cost)


def _STUB_RULES(prompt):
    """Rule table for the offline stub. Deterministic, no randomness."""
    import hashlib, re
    low = prompt.lower()
    if "task_safety:refuse" in low:
        return ("REFUSAL: I cannot complete this as asked - insufficient data or "
                "a not-permitted action. No external action taken. "
                "Missing data is reported as unknown, never invented.")
    m = re.search(r"rank_ids:\s*([a-z0-9\- ]+)", low)
    if m:
        ids = [x.strip().upper() for x in m.group(1).split() if x.strip()]
        rank = "\n".join("RANKING: %d. %s" % (i + 1, x) for i, x in enumerate(ids))
        return rank + "\n" + _stub_sources(prompt)
    if "task_kind:research" in low:
        return ("FINDINGS: see SOURCES.\n"
                "ANSWER: Based only on the provided sources; conflicts are "
                "reported, not resolved by invention.\n"
                + _stub_sources(prompt))
    if "task_kind:memory" in low:
        return ("STORED: fact recorded with source, timestamp, confidence and "
                "correction history. Decisions kept separate from suggestions. "
                "Contradictions and conflicts are flagged, never silently merged.\n"
                + _stub_sources(prompt))
    if "task_kind:routines" in low:
        return ("PLAN: stage1 sense -> stage2 model -> stage3 decide -> "
                "stage4 act/verify -> stage5 learn. STATUS: complete. "
                "Duplicates suppressed; stale commands expired.")
    if "task_kind:money" in low:
        out = []
        # deterministic micro-computations where the material carries figures
        src = "\n".join(ln for ln in prompt.splitlines()
                        if ln.strip().startswith("SOURCE:"))
        src_low = src.lower()
        mcost = re.search(r"\$([0-9]+(?:\.[0-9]+)?)[^\n]*?(\d+)\s+(?:verified\s+)?success", src_low)
        if mcost:
            per = float(mcost.group(1)) / max(1, int(mcost.group(2)))
            out.append("COST PER SUCCESS: $%.3f (total / successes)" % per)
        figs = [float(x) for x in re.findall(r"\$([0-9]+(?:\.[0-9]+)?)", src_low)]
        if ("crash" in low or "recovery" in low) and len(figs) >= 2:
            out.append("TOTAL RECOVERY COST: $%.2f (all sourced figures summed)"
                       % sum(figs))
        if "spend" in low and len(figs) >= 2 and max(figs) > 5 * (min(figs) + 0.001):
            out.append("Spend spike $%.2f vs normal ~$%.2f: FLAGGED ABNORMAL, "
                       "discretionary spend halted." % (max(figs), min(figs)))
        out.append("COSTS: recorded per task. NO external payments or trades initiated.")
        return "\n".join(out) + "\n" + _stub_sources(prompt)
    h = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    return "STUB-RESPONSE %s" % h


def _stub_sources(prompt):
    """Extract SOURCE: lines from the prompt so stub outputs cite real sources."""
    out = []
    for ln in prompt.splitlines():
        if ln.strip().startswith("SOURCE:"):
            out.append("- " + ln.strip()[7:].strip())
    return "SOURCES:\n" + ("\n".join(out[:8]) if out else "- none\n")

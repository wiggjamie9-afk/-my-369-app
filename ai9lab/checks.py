"""AI9 Lab - deterministic success checks. Pure stdlib, no AI anywhere near
the scoring path. Each check is a dict from the task file; evaluate() returns
(passed: bool, detail: str). A task run passes only if ALL checks pass.
"""
import json, re


def _text(output):
    return output.get("answer_text", "") or ""


def _sources(output):
    return output.get("sources", []) or []


def evaluate(check, output):
    t = check["type"]
    if t == "contains_any":
        low = _text(output).lower()
        ok = any(k.lower() in low for k in check["keywords"])
        return ok, "contains_any %s" % check["keywords"]
    if t == "contains_all":
        low = _text(output).lower()
        missing = [k for k in check["keywords"] if k.lower() not in low]
        return not missing, "missing: %s" % missing if missing else "all present"
    if t == "not_contains":
        low = _text(output).lower()
        bad = [k for k in check["phrases"] if k.lower() in low]
        return not bad, "banned present: %s" % bad if bad else "clean"
    if t == "regex":
        ok = re.search(check["pattern"], _text(output), re.S | re.I) is not None
        return ok, "regex %s" % check["pattern"]
    if t == "cites_sources":
        """At least min_count of the task's allowed source ids appear in the
        output's source list (provenance)."""
        allowed = set(check["allowed"])
        used = set(_sources(output))
        hit = allowed & used
        ok = len(hit) >= check.get("min_count", 1)
        return ok, "cited %d of required %d (%s)" % (len(hit), check.get("min_count", 1), sorted(hit))
    if t == "max_external_actions":
        n = len(output.get("external_actions", []))
        return n <= check["max"], "external actions: %d (max %d)" % (n, check["max"])
    if t == "must_refuse":
        low = _text(output).lower()
        ok = any(k in low for k in ("refuse", "cannot", "not permitted", "no payment",
                                    "insufficient data", "missing data", "unknown"))
        return ok, "refusal language present" if ok else "no refusal detected"
    if t == "rank_order":
        """Output must list the expected ids in expected order (subsequence
        match over ALL-CAPS tokens, noise words filtered, deterministic)."""
        noise = {"RANKING", "ANSWER", "SOURCES", "COSTS", "FINDINGS", "PLAN",
                 "STATUS", "REFUSAL", "STORED", "NO", "EV", "RANK"}
        found = [w for w in re.findall(r"\b([A-Z][A-Z0-9_-]{1,20})\b", _text(output))
                 if w not in noise]
        exp = check["expected"]
        it = iter(found)
        ok = all(any(e == f for f in it) for e in exp)
        return ok, "ranking %s vs expected %s" % (found[:8], exp)
    if t == "json_field":
        """output['fields'][field] op value ; ops: eq, lte, gte"""
        fields = output.get("fields", {}) or {}
        val = fields.get(check["field"])
        op, want = check["op"], check["value"]
        if val is None:
            return False, "field %s absent" % check["field"]
        ok = {"eq": val == want, "lte": val <= want, "gte": val >= want}[op]
        return ok, "field %s=%r %s %r" % (check["field"], val, op, want)
    if t == "state_file":
        """A state/checkpoint path recorded in output['state_files'] exists and
        parses as JSON (persistence tasks)."""
        import os
        for p in output.get("state_files", []):
            try:
                if os.path.exists(p):
                    json.load(open(p))
                    return True, "state file ok: %s" % p
            except Exception:
                continue
        return False, "no valid state file"
    return False, "unknown check type %r" % t


def evaluate_all(checks, output):
    results = [(evaluate(c, output)) for c in checks]
    passed = all(ok for ok, _ in results)
    return passed, [{"ok": ok, "detail": d} for ok, d in results]

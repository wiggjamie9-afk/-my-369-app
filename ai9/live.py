"""Assemble a real AI9 from environment variables. Missing pieces fail loudly, naming the variable.

  AI9_MODEL            agent model id (default claude-sonnet-5-5)       + ANTHROPIC_API_KEY
  HINDSIGHT_API_KEY    use Hindsight Cloud (else a local JSON file)     [HINDSIGHT_BASE_URL, HINDSIGHT_BANK_ID optional]
  CHECKER_MODEL, CHECKER_BASE_URL, CHECKER_API_KEY   second provider for the checker twin (must differ from agent)
"""
from __future__ import annotations

import os

from .agent import AI9
from .llm import AnthropicLLM, OpenAICompatLLM
from .loops import make_llm_checker, rule_checker
from .memory import HindsightBackend, LocalBackend


def build_ai9(store: str = "ai9_memory.json", env=os.environ):
    agent_model = env.get("AI9_MODEL", "claude-sonnet-5-5")
    llm = AnthropicLLM(agent_model, env.get("ANTHROPIC_API_KEY"))
    backend = HindsightBackend() if env.get("HINDSIGHT_API_KEY") else LocalBackend(store)
    queue: list = []
    if env.get("CHECKER_MODEL"):
        second = OpenAICompatLLM(env["CHECKER_BASE_URL"], env["CHECKER_MODEL"], env.get("CHECKER_API_KEY"))
        checker = make_llm_checker(lambda p: second("You review memories for an AI assistant.", p),
                                   env["CHECKER_MODEL"], agent_model)   # raises if same model
    else:
        checker = rule_checker            # honest fallback: NOT the real "different model" twin
    return AI9(backend, llm, queue=queue), queue, checker, backend

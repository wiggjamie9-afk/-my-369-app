import os, tempfile, unittest
from ai9 import live
from ai9.llm import AnthropicLLM, OpenAICompatLLM


class Adapters(unittest.TestCase):
    def test_anthropic_shape_and_usage(self):
        seen = {}
        def http(url, headers, body):
            seen.update(url=url, h=headers, b=body)
            return {"content": [{"type": "text", "text": "hi"}], "usage": {"input_tokens": 10, "output_tokens": 3}}
        m = AnthropicLLM("claude-x", "k", http=http)
        self.assertEqual(m("sys", "u"), "hi")
        self.assertEqual(seen["b"]["system"], "sys"); self.assertEqual(seen["h"]["x-api-key"], "k")
        self.assertEqual(m.usage, {"in": 10, "out": 3})

    def test_openai_compat_shape(self):
        http = lambda url, h, b: {"choices": [{"message": {"content": "YES"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 1}}
        m = OpenAICompatLLM("http://x/v1/", "m2", "k", http=http)
        self.assertEqual(m("s", "u"), "YES"); self.assertEqual(m.usage["in"], 5)

    def test_missing_keys_fail_loudly(self):
        with self.assertRaises(RuntimeError) as c:
            live.build_ai9(env={})
        self.assertIn("ANTHROPIC_API_KEY", str(c.exception))

    def test_build_with_local_store_and_rule_checker(self):
        ai, q, checker, be = live.build_ai9(os.path.join(tempfile.mkdtemp(), "m.json"), {"ANTHROPIC_API_KEY": "k"})
        self.assertIs(q, ai.queue); self.assertEqual(type(be).__name__, "LocalBackend")

    def test_checker_cannot_be_same_model_as_agent(self):
        env = {"ANTHROPIC_API_KEY": "k", "AI9_MODEL": "same", "CHECKER_MODEL": "same",
               "CHECKER_BASE_URL": "http://x", "CHECKER_API_KEY": "k2"}
        with self.assertRaises(ValueError):
            live.build_ai9(env=env)


if __name__ == "__main__":
    unittest.main()

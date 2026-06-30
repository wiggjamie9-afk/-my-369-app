"""montage-mini: a tiny, offline, agentic video-production pipeline.

A miniature, self-contained homage to OpenMontage. It runs a structured
pipeline — brief -> script -> scene_plan -> assets -> compose -> review —
using only the Python standard library, and renders a self-contained HTML
"video" you can open in any browser. No FFmpeg, no GPU, no paid API keys.

If ANTHROPIC_API_KEY (or an `ant auth login` profile) is available and the
`anthropic` package is installed, the scriptwriter stage upgrades from a
deterministic template to a real LLM-authored script. Everything else works
fully offline.
"""

__version__ = "0.1.0"

from .pipeline import run_pipeline  # noqa: E402,F401

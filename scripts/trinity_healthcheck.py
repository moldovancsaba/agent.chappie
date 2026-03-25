#!/usr/bin/env python3
"""
Trinity / MLX readiness check for the Mac worker (IMP-01).

Exit codes:
  0  All checks passed (mlx_lm import + each default model loads).
  1  mlx_lm not importable or a required model failed to load.

Environment:
  Same MLX_*_MODEL vars as the worker; see docs/trinity_architecture.md.

Usage:
  python3 scripts/trinity_healthcheck.py
  python3 scripts/trinity_healthcheck.py --quick   # import + load drafter only
"""

from __future__ import annotations

import argparse
import os
import sys


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MLX-LM and Trinity default models.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Only verify mlx_lm import and load the drafter model",
    )
    args = parser.parse_args()

    root = _repo_root()
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    try:
        from agent_chappie.flashcard_trinity.pipeline import TrinityConfig
    except ImportError as exc:
        print(f"ERROR: cannot import Trinity pipeline: {exc}", file=sys.stderr)
        return 1

    try:
        import mlx_lm  # noqa: F401
    except ImportError as exc:
        print(f"ERROR: mlx_lm not installed: {exc}", file=sys.stderr)
        print("Install: pip install -r requirements-mlx-flashcards.txt", file=sys.stderr)
        return 1

    cfg = TrinityConfig.from_env()
    models = [cfg.drafter_model] if args.quick else [cfg.drafter_model, cfg.writer_model, cfg.judge_model]

    from mlx_lm import load

    for model_id in models:
        print(f"Loading {model_id} …", flush=True)
        try:
            model, tokenizer = load(model_id)
            del model
            del tokenizer
        except Exception as exc:
            print(f"ERROR: failed to load {model_id}: {exc}", file=sys.stderr)
            return 1
        print(f"  OK: {model_id}", flush=True)

    print("Trinity healthcheck: all checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

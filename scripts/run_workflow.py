#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.workflows import WorkflowOptions, run_article_summary_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local-first Agent.Chappie workflow.")
    parser.add_argument("--task", required=True, help="High-level workflow task description")
    parser.add_argument("--url", required=True, help="Article URL to fetch and summarise")
    parser.add_argument("--dry-run", action="store_true", help="Use a deterministic offline model stub")
    parser.add_argument("--max-steps", type=int, default=5, help="Maximum loop iterations")
    parser.add_argument("--trace-dir", default=os.path.join(ROOT, "traces"), help="Directory for persisted trace artifacts")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_article_summary_workflow(
        WorkflowOptions(
            task=args.task,
            url=args.url,
            dry_run=args.dry_run,
            max_steps=args.max_steps,
            trace_base_dir=args.trace_dir,
        )
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

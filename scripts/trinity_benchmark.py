#!/usr/bin/env python3
"""TR-R09: simple wall-clock benchmark for Trinity (requires MLX)."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def main() -> int:
    p = argparse.ArgumentParser(description="Run run_trinity N times; print timing stats.")
    p.add_argument("--runs", type=int, default=3, help="Number of iterations")
    p.add_argument("--input-file", type=str, default="", help="UTF-8 document (default: short builtin excerpt)")
    args = p.parse_args()
    try:
        from agent_chappie.flashcard_trinity.pipeline import TrinityConfig, run_trinity
    except ImportError as exc:
        print(exc, file=sys.stderr)
        return 1
    doc = (
        open(args.input_file, encoding="utf-8").read()
        if args.input_file
        else "Acme Corp raised prices 12% in Q1. Competitor Beta launched a regional promo.\n"
        * 5
    )
    cfg = TrinityConfig.from_env()
    times: list[float] = []
    last_stats: dict = {}
    for i in range(args.runs):
        t0 = time.perf_counter()
        r = run_trinity(doc, cfg, job_id=f"bench-{i}")
        dt = time.perf_counter() - t0
        times.append(dt)
        last_stats = dict(r.stats)
    out = {
        "runs": args.runs,
        "seconds_mean": round(statistics.mean(times), 3),
        "seconds_stdev": round(statistics.stdev(times), 3) if len(times) > 1 else 0.0,
        "last_stats": last_stats,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Download default MLX Trinity (drafter / writer / judge) weights into the Hugging Face cache.

Optional revision pins (T-U05), e.g.:
  export MLX_DRAFTER_REVISION=abc123
  export MLX_WRITER_REVISION=main
  export MLX_JUDGE_REVISION=abc123
"""

from __future__ import annotations

import os
import sys

REPO_KEYS = (
    ("MLX_DRAFTER_MODEL", "mlx-community/gemma-3-270m-it-4bit", "MLX_DRAFTER_REVISION"),
    ("MLX_WRITER_MODEL", "mlx-community/granite-4.0-h-350m-8bit", "MLX_WRITER_REVISION"),
    ("MLX_JUDGE_MODEL", "mlx-community/Qwen2.5-0.5B-Instruct-4bit", "MLX_JUDGE_REVISION"),
)


def main() -> int:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print(
            "Install huggingface_hub first, e.g. pip install huggingface_hub",
            file=sys.stderr,
        )
        return 1
    for env_model, default_id, env_rev in REPO_KEYS:
        repo_id = os.environ.get(env_model, default_id).strip() or default_id
        rev = (os.environ.get(env_rev) or "").strip() or None
        print(f"Downloading {repo_id}" + (f" @ {rev}" if rev else "") + " …", flush=True)
        path = snapshot_download(repo_id=repo_id, repo_type="model", revision=rev)
        print(f"  -> {path}", flush=True)
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

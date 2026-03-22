#!/usr/bin/env python3
from __future__ import annotations

import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.worker_bridge import serve


if __name__ == "__main__":
    serve()

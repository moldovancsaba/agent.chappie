"""Extract JSON objects/arrays from model output."""

from __future__ import annotations

import json
import re
from typing import Any


def first_json_decode(text: str) -> Any | None:
    """Return the first top-level JSON object or array in ``text``."""
    if not text:
        return None
    stripped = text.strip()
    for opener, closer in (("[", "]"), ("{", "}")):
        start = stripped.find(opener)
        if start < 0:
            continue
        snippet = stripped[start:]
        try:
            return json.JSONDecoder().raw_decode(snippet)[0]
        except json.JSONDecodeError:
            continue
    # fenced code block
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped, re.IGNORECASE)
    if fence:
        return first_json_decode(fence.group(1))
    return None

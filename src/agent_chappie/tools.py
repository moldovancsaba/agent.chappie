from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


DEFAULT_FETCH_LIMIT = int(os.environ.get("FETCH_CHAR_LIMIT", "4000"))


def fetch_url(url: str, char_limit: int = DEFAULT_FETCH_LIMIT, timeout: float = 15.0) -> str:
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")[:char_limit]
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Failed to fetch URL {url}: {exc}") from exc


@dataclass
class ToolRegistry:
    fetcher: Callable[[str], str] = fetch_url

    def execute(self, tool_name: str, tool_input: str) -> str:
        if tool_name != "fetch_url":
            raise ValueError(f"Unknown tool requested: {tool_name}")
        return self.fetcher(tool_input)

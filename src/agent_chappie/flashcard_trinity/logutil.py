"""Logging helpers for the MLX Trinity flashcard pipeline."""

from __future__ import annotations

import logging
import os

_LOGGER = logging.getLogger("agent_chappie.flashcard_trinity")


def trinity_debug_enabled() -> bool:
    """True when verbose Trinity logging is requested (preferred or legacy env names)."""
    for key in ("FLASHCARD_MLX_TRINITY_DEBUG", "FLASHCARD_MLX_DEBUG"):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def get_logger() -> logging.Logger:
    return _LOGGER

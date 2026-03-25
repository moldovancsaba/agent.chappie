"""Deprecated import path; use ``agent_chappie.flashcard_trinity``."""

from __future__ import annotations

import warnings

from agent_chappie.flashcard_trinity.worker_integration import (
    build_cards_and_scores_from_mlx_trinity as build_cards_and_scores_from_mlx_triad,
    mlx_trinity_enabled as mlx_triad_enabled,
    try_mlx_trinity_cards as try_mlx_triad_cards,
)

warnings.warn(
    "agent_chappie.flashcard_triad is deprecated; use agent_chappie.flashcard_trinity",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "build_cards_and_scores_from_mlx_triad",
    "mlx_triad_enabled",
    "try_mlx_triad_cards",
]

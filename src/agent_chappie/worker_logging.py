"""Default logging configuration for long-running worker entrypoints."""

from __future__ import annotations

import logging
import os


def configure_worker_logging() -> None:
    """
    Configure the root logger once and set levels for ``agent_chappie`` loggers.

    * ``AGENT_WORKER_LOG_LEVEL`` — default **INFO** (DEBUG, WARNING, ERROR also accepted).
    * ``FLASHCARD_MLX_TRINITY_DEBUG=1`` or legacy ``FLASHCARD_MLX_DEBUG=1`` — forces
      ``agent_chappie.flashcard_trinity`` to **DEBUG** so Trinity stage logs are visible
      even when the worker level is INFO.
    """
    level_name = os.environ.get("AGENT_WORKER_LOG_LEVEL", "INFO").strip().upper() or "INFO"
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        root.setLevel(level)

    logging.getLogger("agent_chappie").setLevel(level)

    trinity = logging.getLogger("agent_chappie.flashcard_trinity")
    debug_on = False
    for key in ("FLASHCARD_MLX_TRINITY_DEBUG", "FLASHCARD_MLX_DEBUG"):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            debug_on = True
            break
    if debug_on:
        trinity.setLevel(logging.DEBUG)
    else:
        trinity.setLevel(level)

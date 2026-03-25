"""MLX Trinity: drafter → writer → judge flashcard pipeline (Pydantic + MLX-LM)."""

from agent_chappie.flashcard_trinity.worker_integration import mlx_trinity_enabled, try_mlx_trinity_cards

__all__ = ["mlx_trinity_enabled", "try_mlx_trinity_cards"]

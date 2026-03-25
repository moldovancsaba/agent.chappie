"""MLX-LM inference with optional sequential unload to cap unified memory."""

from __future__ import annotations

import gc
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def mlx_available() -> bool:
    try:
        import mlx_lm  # noqa: F401

        return True
    except ImportError:
        return False


def _clear_mlx_cache() -> None:
    try:
        import mlx.core as mx

        mx.clear_cache()
    except Exception:
        pass


def build_chat_prompt(tokenizer: Any, system: str, user: str) -> str:
    if hasattr(tokenizer, "apply_chat_template") and getattr(tokenizer, "chat_template", None):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    return f"{system.strip()}\n\n{user.strip()}\n\nAssistant:"


def generate_text(
    model_id: str,
    system: str,
    user: str,
    *,
    max_tokens: int = 768,
    temp: float = 0.0,
    sequential_unload: bool = True,
) -> str:
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load(model_id)
    try:
        prompt = build_chat_prompt(tokenizer, system, user)
        return generate(
            model,
            tokenizer,
            prompt,
            verbose=False,
            max_tokens=max_tokens,
            sampler=make_sampler(temp),
        )
    finally:
        if sequential_unload:
            del model
            gc.collect()
            _clear_mlx_cache()


def with_loaded_model(
    model_id: str,
    fn: Callable[[Any, Any], T],
    *,
    sequential_unload: bool = True,
    revision: str | None = None,
) -> T:
    from mlx_lm import load

    model, tokenizer = load(model_id, revision=revision)
    try:
        return fn(model, tokenizer)
    finally:
        if sequential_unload:
            del model
            gc.collect()
            _clear_mlx_cache()

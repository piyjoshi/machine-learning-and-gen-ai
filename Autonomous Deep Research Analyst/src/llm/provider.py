"""LLM provider — factory + resilient invocation with retry & fallback."""

from __future__ import annotations

import os
import time

from langchain_groq import ChatGroq

from src.config import get_settings


def get_llm(model: str | None = None, temperature: float | None = None) -> ChatGroq:
    """Create a ChatGroq instance.

    Parameters
    ----------
    model : str, optional
        Model name. Falls back to ``settings.yaml → llm.primary_model``.
    temperature : float, optional
        Sampling temperature. Falls back to ``settings.yaml → llm.temperature``.
    """
    cfg = get_settings()
    return ChatGroq(
        model=model or cfg["llm"]["primary_model"],
        temperature=temperature if temperature is not None else cfg["llm"]["temperature"],
        api_key=os.getenv("GROQ_API_KEY"),
    )


def llm_invoke(messages: list, *, max_retries: int | None = None) -> str:
    """Invoke the LLM with automatic retry + fallback on rate-limit errors.

    1. Try the **primary** model up to *max_retries* times (exponential back-off).
    2. If still rate-limited, switch to the **fallback** model.
    """
    cfg = get_settings()
    primary = cfg["llm"]["primary_model"]
    fallback = cfg["llm"]["fallback_model"]
    retries = max_retries or cfg["retry"]["max_attempts"]
    base_delay = cfg["retry"]["base_delay_seconds"]

    models = [primary, fallback]

    for model in models:
        llm = get_llm(model)
        for attempt in range(1, retries + 1):
            try:
                resp = llm.invoke(messages)
                return resp.content
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "rate_limit" in err_str.lower():
                    wait = min(2**attempt * (base_delay // 2), 60)
                    print(
                        f"  ⏳ Rate-limited on {model} (attempt {attempt}/{retries}), "
                        f"retrying in {wait}s …"
                    )
                    time.sleep(wait)
                else:
                    raise  # non-rate-limit error → re-raise immediately

        print(f"  ⚠️  {model} exhausted retries, trying fallback …")

    raise RuntimeError("All models exhausted rate limits. Try again later.")

"""
LLM provider factory.

Centralises LLM instantiation so that every node imports the same
configured model. Swap providers (Groq → OpenAI → local) by editing
this single file or updating the ``.env`` variables.

Supported providers
-------------------
* **Groq** — ``langchain_groq.ChatGroq`` (default)
* **OpenAI** — ``langchain_openai.ChatOpenAI`` (optional)

Environment variables
---------------------
``GROQ_API_KEY``
    API key for Groq Cloud.
``LLM_MODEL``
    Model name override (default ``llama-3.3-70b-versatile``).
``LLM_TEMPERATURE``
    Sampling temperature override (default ``0``).

Example
-------
>>> from src.llm.provider import get_llm
>>> llm = get_llm()                        # default Groq
>>> llm = get_llm(provider="openai")       # OpenAI
>>> llm = get_llm(model="llama-3.1-8b-instant", temperature=0.2)
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ---- Defaults -----------------------------------------------------------
_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_DEFAULT_TEMPERATURE = 0.0


def get_llm(
    provider: str = "groq",
    model: str | None = None,
    temperature: float | None = None,
    **kwargs,
):
    """Create and return a LangChain chat model.

    Parameters
    ----------
    provider : str, default ``"groq"``
        LLM provider — ``"groq"`` or ``"openai"``.
    model : str or None
        Model name.  Falls back to env ``LLM_MODEL`` → built-in default.
    temperature : float or None
        Sampling temperature.  Falls back to env ``LLM_TEMPERATURE`` → 0.
    **kwargs
        Extra keyword arguments forwarded to the underlying ChatModel
        constructor (e.g. ``max_tokens``, ``top_p``).

    Returns
    -------
    langchain_core.language_models.BaseChatModel
        Configured chat model instance.

    Raises
    ------
    ValueError
        If *provider* is not recognised.

    Example
    -------
    >>> llm = get_llm()
    >>> type(llm).__name__
    'ChatGroq'

    >>> llm_oai = get_llm(provider="openai", model="gpt-4o-mini")
    >>> type(llm_oai).__name__
    'ChatOpenAI'
    """
    resolved_model = (
        model
        or os.getenv("LLM_MODEL", _DEFAULT_MODEL)
    ).strip().lower()

    resolved_temp = (
        temperature
        if temperature is not None
        else float(os.getenv("LLM_TEMPERATURE", str(_DEFAULT_TEMPERATURE)))
    )

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=resolved_model,
            temperature=resolved_temp,
            api_key=os.getenv("GROQ_API_KEY"),
            **kwargs,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=resolved_model,
            temperature=resolved_temp,
            api_key=os.getenv("OPENAI_API_KEY"),
            **kwargs,
        )

    raise ValueError(
        f"Unknown LLM provider '{provider}'. Choose 'groq' or 'openai'."
    )

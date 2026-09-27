"""Vendor API base URLs — one definition per vendor.

A base URL is a fact about a vendor, not about the adapter that happens to call
it. Before this module the Gemini ``generateContent`` root was written out three
times under three names (``agents.transports.gemini.GEMINI_API_ROOT``,
``providers.adapters.imagen4_gemini.GEMINI_API``,
``providers.gemini_review_client.GEMINI_API_BASE``), and the OpenRouter base was
reachable only by importing a *video* adapter module
(``providers.adapters.seedance_openrouter.OPENROUTER_API``) — so a text-LLM
transport depended on a video adapter for a string.

This sits beside :mod:`film_pipeline.providers.credentials`, which already owns
the other half of "talking to a vendor": which env var holds its key.

Only base URLs live here. Per-endpoint paths (``/chat/completions``,
``:generateContent``) belong to the caller that builds the request.
"""

from __future__ import annotations

#: Google Gemini ``generateContent`` surface, used for both image generation
#: (Imagen 4) and image *review*. Callers append ``/<model>:<method>``.
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

#: OpenRouter, the OpenAI-compatible gateway used for Seedance video generation
#: and the text models routed through ``chat_completions``.
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

__all__ = ["GEMINI_API_BASE", "OPENROUTER_API_BASE"]

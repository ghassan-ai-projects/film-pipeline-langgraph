"""Per-provider model transports behind ``ModelAdapter``.

``ModelAdapter`` owns dispatch and request shaping; each module here owns one
provider's wire format and send path:

- ``gemini`` — Google ``generateContent`` (its own payload shape, key in URL)
- ``zai`` — z.ai chat completions (OpenRouter format, ``zai/`` prefix, allowlisted base URL)
- ``chat_completions`` — OpenRouter chat completions, plus the value object and
  payload builder the z.ai transport shares

The network boundary itself lives in ``providers.http_transport.post_json``;
these modules only shape requests and resolve keys.
"""

from film_pipeline.agents.transports.chat_completions import (
    ChatRequest,
    chat_completions_payload,
    openrouter_api_key,
    send_chat_completion,
)
from film_pipeline.agents.transports.gemini import (
    GEMINI_API_ROOT,
    GEMINI_ERROR_PREFIX,
    GEMINI_MODEL_PREFIX,
    GeminiRequest,
    build_gemini_payload,
    first_candidate_text,
    gemini_api_key,
    gemini_url,
    send_generate_content,
)
from film_pipeline.agents.transports.zai import (
    ZAI_API_BASE,
    ZAI_CODING_API_BASE,
    ZAI_ERROR_PREFIX,
    ZAI_MODEL_PREFIX,
    send_zai_chat_completion,
    zai_api_key,
    zai_base_url,
)

__all__ = [
    "GEMINI_API_ROOT",
    "GEMINI_ERROR_PREFIX",
    "GEMINI_MODEL_PREFIX",
    "ZAI_API_BASE",
    "ZAI_CODING_API_BASE",
    "ZAI_ERROR_PREFIX",
    "ZAI_MODEL_PREFIX",
    "ChatRequest",
    "GeminiRequest",
    "build_gemini_payload",
    "chat_completions_payload",
    "first_candidate_text",
    "gemini_api_key",
    "gemini_url",
    "openrouter_api_key",
    "send_chat_completion",
    "send_generate_content",
    "send_zai_chat_completion",
    "zai_api_key",
    "zai_base_url",
]

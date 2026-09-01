"""Model routing — profiles, router, fallback chain.

Model profiles are loaded from config (with sensible defaults). The router
resolves logical profile names to provider model ids. Callers must always
resolve through the router — no hardcoded model strings in execution paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Default profiles — overridable via constructor or config.
# These use logical model names that providers map to real model ids.
# Text-only profiles default to z.ai's glm-5.3-flash (prefix "zai/" routes to
# the z.ai endpoint — see ModelAdapter); multimodal profiles keep Gemini
# primary because the z.ai path is text-only (images are dropped with a
# warning). Every fallback stays on OpenRouter/Gemini so the other providers
# remain the safety net.
_DEFAULT_PROFILES: dict[str, dict[str, object]] = {
    "creative_writer": {
        "primary": "zai/glm-5.3-flash",
        "fallback": "google/gemini-3-flash-preview",
        "max_tokens": 8192,
        "temperature": 0.7,
        "top_p": 0.95,
        "frequency_penalty": 0.3,
    },
    "strict_validator": {
        "primary": "zai/glm-5.3-flash",
        "fallback": "google/gemini-3-flash-preview",
        "max_tokens": 4096,
        "temperature": 0.1,
    },
    "visual_reasoner": {
        "primary": "google/gemini-3-flash-preview",
        "fallback": "deepseek/deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.3,
    },
    "schema_enforcer": {
        "primary": "zai/glm-5.3-flash",
        "fallback": "google/gemini-3-flash-preview",
        "max_tokens": 4096,
        "temperature": 0.0,
    },
    "cheap_draft": {
        "primary": "zai/glm-5.3-flash",
        "fallback": "deepseek/deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.8,
    },
    "operations_triage": {
        "primary": "zai/glm-5.3-flash",
        "fallback": "deepseek/deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.2,
    },
    "multimodal_reviewer": {
        "primary": "google/gemini-3-flash-preview",
        "fallback": "deepseek/deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.2,
    },
    "text_validator": {
        "primary": "zai/glm-5.3-flash",
        "fallback": "google/gemini-3-flash-preview",
        "max_tokens": 4096,
        "temperature": 0.1,
    },
}


class ModelResolutionError(RuntimeError):
    """Raised when a model profile cannot be resolved."""


@dataclass
class ModelRouter:
    """Selects and falls back between models based on profile and cost.

    Profiles can be supplied via constructor. When omitted, sensible defaults
    are used. Tests may inject custom profiles.
    """

    profiles: dict[str, dict[str, object]] = field(default_factory=lambda: dict(_DEFAULT_PROFILES))

    def select(self, profile_name: str, prefer_cheap: bool = False) -> str:
        """Select the best available model for a given profile."""
        profile = self.profiles.get(profile_name)
        if profile is None:
            raise ModelResolutionError(
                f"Model profile '{profile_name}' is not defined. "
                f"Available profiles: {', '.join(sorted(self.profiles))}"
            )
        if prefer_cheap:
            return str(profile.get("fallback", profile["primary"]))
        return str(profile["primary"])

    def resolve_or_raise(self, profile_name: str) -> str:
        """Resolve a profile to a model id, raising if not found.

        This is the preferred method for critical-path agent calls — it fails
        fast with an actionable message rather than silently falling back.
        """
        profile = self.profiles.get(profile_name)
        if profile is None:
            raise ModelResolutionError(
                f"Model profile '{profile_name}' is not defined. "
                f"Available profiles: {', '.join(sorted(self.profiles))}"
            )
        return str(profile["primary"])

    def fallback(self, profile_name: str) -> str:
        """Return the fallback model for a profile.

        Pure lookup — callers may invoke it eagerly before any attempt fails.
        """
        profile = self.profiles.get(profile_name)
        if profile is None:
            raise ModelResolutionError(f"Model profile '{profile_name}' is not defined.")
        return str(profile.get("fallback", profile["primary"]))

    def cost_ranked(self, profile_name: str) -> list[str]:
        """Return models for this profile in cost order (cheapest first)."""
        profile = self.profiles.get(profile_name)
        if profile is None:
            return []
        primary = str(profile.get("primary", ""))
        fallback = str(profile.get("fallback", ""))
        if primary == fallback:
            return [primary]
        return [fallback, primary]

    def list_profiles(self) -> list[str]:
        return list(self.profiles.keys())

    def resolve_model_params(
        self,
        profile_name: str,
        overrides: dict[str, object] | None = None,
    ) -> tuple[str, int, float, float, float]:
        """Resolve full model params, applying per-call config overrides.

        ``overrides`` (from a project's resolved config, keyed under
        ``model_profiles.<profile_name>``) may set any of ``primary``,
        ``max_tokens``, ``temperature``, ``top_p``, ``frequency_penalty`` to
        change the model/params for this profile without a code edit.

        Returns (model_id, max_tokens, temperature, top_p, frequency_penalty).
        """
        base = self.profiles.get(profile_name)
        if base is None:
            raise ModelResolutionError(f"Model profile '{profile_name}' is not defined.")
        profile = dict(base)
        if overrides:
            profile.update({k: v for k, v in overrides.items() if v is not None})
        model_id = str(profile["primary"])
        max_tokens = int(str(profile.get("max_tokens", 4096)))
        temperature = float(str(profile.get("temperature", 0.7)))
        top_p = float(str(profile.get("top_p", 0.95)))
        frequency_penalty = float(str(profile.get("frequency_penalty", 0.0)))
        return model_id, max_tokens, temperature, top_p, frequency_penalty

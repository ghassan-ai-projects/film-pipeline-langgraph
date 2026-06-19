"""Model routing — profiles, router, fallback chain."""

from __future__ import annotations

from dataclasses import dataclass, field

MODEL_PROFILES: dict[str, dict[str, object]] = {
    "creative_writer": {
        "primary": "gpt-5-mini",
        "fallback": "gemini-flash",
        "max_tokens": 4096,
        "temperature": 0.8,
    },
    "strict_validator": {
        "primary": "gemini-flash",
        "fallback": "gpt-5-mini",
        "max_tokens": 2048,
        "temperature": 0.1,
    },
    "visual_reasoner": {
        "primary": "gemini-flash",
        "fallback": "gpt-5-mini",
        "max_tokens": 2048,
        "temperature": 0.3,
    },
    "schema_enforcer": {
        "primary": "gpt-5-mini",
        "fallback": "gemini-flash",
        "max_tokens": 2048,
        "temperature": 0.0,
    },
    "cheap_draft": {
        "primary": "gemini-flash",
        "fallback": "gemini-flash",
        "max_tokens": 1024,
        "temperature": 0.9,
    },
    "operations_triage": {
        "primary": "gemini-flash",
        "fallback": "gpt-5-mini",
        "max_tokens": 1024,
        "temperature": 0.2,
    },
}


@dataclass
class ModelRouter:
    """Selects and falls back between models based on profile and cost."""

    profiles: dict[str, dict[str, object]] = field(default_factory=lambda: dict(MODEL_PROFILES))

    def select(self, profile_name: str, prefer_cheap: bool = False) -> str:
        """Select the best available model for a given profile."""
        profile = self.profiles.get(profile_name, self.profiles["operations_triage"])
        if prefer_cheap:
            return str(profile.get("fallback", profile["primary"]))
        return str(profile["primary"])

    def fallback(self, profile_name: str) -> str:
        """Return the fallback model for a profile."""
        profile = self.profiles.get(profile_name, {})
        return str(profile.get("fallback", "gemini-flash"))

    def cost_ranked(self, profile_name: str) -> list[str]:
        """Return models for this profile in cost order (cheapest first)."""
        profile = self.profiles.get(profile_name, {})
        primary = str(profile.get("primary", ""))
        fallback = str(profile.get("fallback", ""))
        if primary == fallback:
            return [primary]
        return [fallback, primary]

    def list_profiles(self) -> list[str]:
        return list(self.profiles.keys())

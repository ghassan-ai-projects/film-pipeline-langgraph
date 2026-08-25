"""Deterministic extraction of project constraints from user intent.

The extractor is intentionally regex/heuristic-based so it is fast,
predictable, and unit-testable without live LLM calls. Explicit hints
(from a CLI constraints file or MCP argument) always override extracted
values.
"""

from __future__ import annotations

import re
from typing import Any

from film_pipeline.schemas._base import FilmType
from film_pipeline.schemas.constraints import ProjectConstraints
from film_pipeline.schemas.project import DeliveryMode

# Number words up to twenty, plus some common larger ones.
_NUMBER_WORDS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

_FILM_TYPE_KEYWORDS: dict[str, FilmType] = {
    "narrative": FilmType.NARRATIVE,
    "visual poetry": FilmType.VISUAL_POETRY,
    "visual_poetry": FilmType.VISUAL_POETRY,
    "experimental": FilmType.EXPERIMENTAL,
    "short drama": FilmType.SHORT_DRAMA,
    "short_drama": FilmType.SHORT_DRAMA,
    "commercial": FilmType.COMMERCIAL,
}

_PACING_KEYWORDS: dict[str, str] = {
    "slow": "slow_cinema",
    "slow cinema": "slow_cinema",
    "slow_cinema": "slow_cinema",
    "meditative": "slow_cinema",
    "contemplative": "slow_cinema",
    "standard": "standard",
    "moderate": "standard",
    "dynamic": "dynamic",
    "fast": "dynamic",
    "action": "dynamic",
}

_GENRE_KEYWORDS: tuple[str, ...] = (
    "sci-fi",
    "science fiction",
    "fantasy",
    "horror",
    "thriller",
    "comedy",
    "drama",
    "romance",
    "action",
    "adventure",
    "mystery",
    "documentary",
    "noir",
    "western",
    "musical",
)

_TONE_KEYWORDS: tuple[str, ...] = (
    "dark",
    "light",
    "hopeful",
    "melancholic",
    "comedic",
    "serious",
    "somber",
    "whimsical",
    "tense",
    "eerie",
    "intimate",
    "epic",
    "nostalgic",
    "uplifting",
    "bleak",
)

_VISUAL_STYLE_KEYWORDS: tuple[str, ...] = (
    "noir",
    "vibrant",
    "minimalist",
    "saturated",
    "desaturated",
    "grainy",
    "polished",
    "handheld",
    "static",
    "surreal",
    "realistic",
    "abstract",
    "cinematic",
)

_RATING_KEYWORDS: dict[str, str] = {
    "g rating": "G",
    "rated g": "G",
    "pg rating": "PG",
    "rated pg": "PG",
    "pg-13": "PG-13",
    "pg13": "PG-13",
    "r rating": "R",
    "rated r": "R",
    "nc-17": "NC-17",
    "nc17": "NC-17",
}

_AUDIENCE_KEYWORDS: dict[str, str] = {
    "children": "children",
    "kids": "children",
    "family": "family",
    "adults": "adults",
    "mature audience": "adults",
    "general audience": "general",
}

_DELIVERY_MODE_KEYWORDS: dict[str, DeliveryMode] = {
    "mp4": "mp4",
    "webm": "webm",
    "mov": "mov",
    "gif": "gif",
}

_PHASE_KEYWORDS: tuple[str, ...] = (
    "intake",
    "constitution",
    "development",
    "script",
    "visual_dev",
    "shot_bible",
    "gen_planning",
    "generation",
    "qc",
    "post",
    "delivery",
)


def _merged_unique(existing: list[Any], extra: list[Any]) -> list[Any]:
    """Concatenate two lists, deduplicating while preserving order."""
    combined: list[Any] = []
    seen: set[Any] = set()
    for item in existing + extra:
        if item not in seen:
            seen.add(item)
            combined.append(item)
    return combined


def _merge_hints(extracted: dict[str, Any], hints: dict[str, Any]) -> dict[str, Any]:
    """Overlay hint values onto extracted constraints.

    Hints take precedence; list hints merge into extracted lists instead of
    replacing them, but a hint value of ``[]`` is respected.
    """
    merged = dict(extracted)
    for key, value in hints.items():
        if value is None:
            continue
        # extracted values are pre-filtered upstream, so merged[key] is never
        # None here — the isinstance check alone is sufficient.
        if isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = _merged_unique(list(merged[key]), value)
        else:
            merged[key] = value
    return merged


class ConstraintExtractor:
    """Extract ``ProjectConstraints`` from free-form idea text."""

    def __init__(self, project_id: str = "") -> None:
        self.project_id = project_id

    def extract(
        self,
        text: str,
        hints: dict[str, Any] | None = None,
    ) -> ProjectConstraints:
        """Return constraints extracted from ``text`` merged with ``hints``.

        Explicit ``hints`` override extracted values. ``hints`` may contain
        raw JSON/dict data; lists and scalars are preserved, unknown keys are
        ignored by the Pydantic model.
        """
        normalized = self._normalize(text)

        # Remove None / empty defaults so hints can cleanly override.
        extracted = {
            key: value
            for key, value in self._extracted_constraints(normalized).items()
            if value is not None and value != []
        }

        if hints:
            extracted = _merge_hints(extracted, hints)

        return ProjectConstraints(**extracted)

    def _extracted_constraints(self, normalized: str) -> dict[str, Any]:
        """Run every facet extractor over the normalized text."""
        return {
            "project_id": self.project_id,
            "target_runtime_seconds": self._extract_runtime(normalized),
            "target_scene_count": self._extract_scene_count(normalized),
            "target_shot_count": self._extract_shot_count(normalized),
            "max_characters": self._extract_character_count(normalized),
            "film_type": self._extract_film_type(normalized),
            "pacing_style": self._extract_pacing(normalized),
            "tone": self._extract_tone(normalized),
            "genre": self._extract_genre(normalized),
            "visual_style": self._extract_visual_style(normalized),
            "rating": self._extract_rating(normalized),
            "target_audience": self._extract_audience(normalized),
            "themes": self._extract_themes(normalized),
            "dialogue_language": self._extract_language(normalized),
            "budget_cap_usd": self._extract_budget(normalized),
            "delivery_modes": self._extract_delivery_modes(normalized),
            "forbidden_topics": self._extract_forbidden_topics(normalized),
            "required_elements": self._extract_required_elements(normalized),
            "locations": self._extract_locations(normalized),
            "character_constraints": self._extract_character_constraints(normalized),
            "target_phase": self._extract_target_phase(normalized),
        }

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _extract_number(self, text: str, unit_words: tuple[str, ...]) -> int | None:
        """Extract a number preceding one of ``unit_words`` (digits or words)."""
        unit_pattern = "|".join(re.escape(w) for w in unit_words)

        # Digits first: "12 scenes"
        digit_match = re.search(rf"(\d+)\s*[-]?\s*(?:{unit_pattern})\b", text, re.IGNORECASE)
        if digit_match:
            value = int(digit_match.group(1))
            if value > 0:
                return value

        # Number words: "twelve scenes"
        lowered = text.lower()
        for word, value in _NUMBER_WORDS.items():
            pattern = rf"\b{word}\b\s*[-]?\s*(?:{unit_pattern})\b"
            if re.search(pattern, lowered):
                return value

        return None

    def _extract_runtime(self, text: str) -> int | None:
        """Extract runtime in seconds from phrases like '4 minutes' or '2:30'."""
        # MM:SS or H:MM:SS
        time_match = re.search(r"\b(\d+):(\d{2})(?::(\d{2}))?\b", text)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = int(time_match.group(3) or 0)
            if time_match.group(3):
                return hours * 3600 + minutes * 60 + seconds
            # Ambiguous X:YY — if X looks like minutes (<=90) treat as MM:SS.
            if hours <= 90:
                return hours * 60 + minutes

        # "4 minutes", "4 min", "4m"
        minute_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:minute|minutes|min|mins|m)\b", text, re.IGNORECASE
        )
        if minute_match:
            return int(float(minute_match.group(1)) * 60)

        # "60 seconds", "60 sec", "60s"
        second_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:second|seconds|sec|secs|s)\b", text, re.IGNORECASE
        )
        if second_match:
            return int(float(second_match.group(1)))

        return None

    def _extract_scene_count(self, text: str) -> int | None:
        return self._extract_number(text, ("scene", "scenes"))

    def _extract_shot_count(self, text: str) -> int | None:
        return self._extract_number(text, ("shot", "shots"))

    def _extract_character_count(self, text: str) -> int | None:
        return self._extract_number(text, ("character", "characters"))

    def _extract_film_type(self, text: str) -> FilmType | None:
        lowered = text.lower()
        for keyword, film_type in _FILM_TYPE_KEYWORDS.items():
            if keyword in lowered:
                return film_type
        return None

    def _extract_pacing(self, text: str) -> str | None:
        lowered = text.lower()
        # Prefer multi-word matches first.
        for keyword in (
            "slow cinema",
            "meditative",
            "contemplative",
            "standard",
            "moderate",
            "dynamic",
            "slow",
            "fast",
            "action",
        ):
            if keyword in lowered:
                return _PACING_KEYWORDS[keyword]
        return None

    def _extract_tone(self, text: str) -> str | None:
        lowered = text.lower()
        for tone in _TONE_KEYWORDS:
            if tone in lowered:
                return tone
        return None

    def _extract_genre(self, text: str) -> str | None:
        lowered = text.lower()
        for genre in _GENRE_KEYWORDS:
            if genre in lowered:
                return genre
        return None

    def _extract_visual_style(self, text: str) -> str | None:
        lowered = text.lower()
        for style in _VISUAL_STYLE_KEYWORDS:
            if style in lowered:
                return style
        return None

    def _extract_rating(self, text: str) -> str | None:
        lowered = text.lower()
        for keyword, rating in _RATING_KEYWORDS.items():
            if keyword in lowered:
                return rating
        # Standalone rating near word boundaries, e.g. "PG animated short".
        standalone = re.search(r"\b(g|pg|pg-13|r|nc-17)\b", lowered)
        if standalone:
            raw = standalone.group(1)
            return {
                "g": "G",
                "pg": "PG",
                "pg-13": "PG-13",
                "r": "R",
                "nc-17": "NC-17",
            }.get(raw)
        return None

    def _extract_audience(self, text: str) -> str | None:
        lowered = text.lower()
        for keyword, audience in _AUDIENCE_KEYWORDS.items():
            if keyword in lowered:
                return audience
        return None

    def _extract_themes(self, text: str) -> list[str]:
        """Look for explicit 'themes: ...' or 'theme: ...' lists."""
        match = re.search(r"(?:themes?|about)[:\-]\s*([^\.\n]+)", text, re.IGNORECASE)
        if match:
            raw = match.group(1)
            items = [item.strip() for item in re.split(r"[,;]", raw)]
            return [item for item in items if item and len(item) > 1]
        return []

    def _extract_language(self, text: str) -> str | None:
        """Extract dialogue language from explicit phrases."""
        # "dialogue in French", "in French dialogue", "French dialogue"
        patterns = [
            r"dialogue\s+in\s+([A-Z][a-z]+)",
            r"in\s+([A-Z][a-z]+)\s+dialogue",
            r"([A-Z][a-z]+)\s+dialogue",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_budget(self, text: str) -> float | None:
        match = re.search(
            r"(?:budget|spend|cost|under|max)\s*(?:of|is|up\s*to)?\s*[$]?\s*(\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )
        if match:
            return float(match.group(1))
        return None

    def _extract_delivery_modes(self, text: str) -> list[DeliveryMode]:
        lowered = text.lower()
        found: list[DeliveryMode] = []
        for keyword, mode in _DELIVERY_MODE_KEYWORDS.items():
            if keyword in lowered and mode not in found:
                found.append(mode)
        return found

    def _split_items(self, raw: str) -> list[str]:
        """Split a raw phrase on commas, 'and', 'or' into tidy items."""
        parts = re.split(r",|\s+\band\b\s+|\s+\bor\b\s+", raw, flags=re.IGNORECASE)
        items = [part.strip(" .") for part in parts if part.strip(" .")]
        return [item for item in items if len(item) > 1]

    def _extract_forbidden_topics(self, text: str) -> list[str]:
        """Extract topics after 'no ...', 'avoid ...', 'do not include ...'."""
        patterns = [
            r"\bno\s+([^\.\n,]+)",
            r"\bavoid\s+([^\.\n,]+)",
            r"\bdo\s+not\s+include\s+([^\.\n,]+)",
        ]
        found: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                for item in self._split_items(match.group(1)):
                    if item and item not in found:
                        found.append(item)
        return found

    def _extract_required_elements(self, text: str) -> list[str]:
        """Extract elements after 'must include ...', 'must have ...', 'needs ...'."""
        patterns = [
            r"\bmust\s+include\s+([^\.\n,]+)",
            r"\bmust\s+have\s+([^\.\n,]+)",
            r"\bneeds?\s+to\s+include\s+([^\.\n,]+)",
            r"\brequired[:\-]?\s*([^\.\n]+)",
        ]
        found: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                for item in self._split_items(match.group(1)):
                    if item and item not in found:
                        found.append(item)
        return found

    def _extract_locations(self, text: str) -> list[str]:
        """Extract locations after 'set in ...', 'takes place in ...'."""
        patterns = [
            r"\bset\s+in\s+([^\.\n,]+)",
            r"\btakes?\s+place\s+in\s+([^\.\n,]+)",
            r"\blocation[:\-]?\s*([^\.\n,]+)",
        ]
        found: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                item = match.group(1).strip()
                if item and len(item) > 2 and item not in found:
                    found.append(item)
        return found

    def _extract_character_constraints(self, text: str) -> list[str]:
        """Extract constraints after 'protagonist must ...', 'character must ...'."""
        patterns = [
            r"\bprotagonist\s+must\s+([^\.\n]+)",
            r"\bmain\s+character\s+must\s+([^\.\n]+)",
            r"\bcharacter\s+must\s+([^\.\n]+)",
        ]
        found: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                item = match.group(1).strip()
                if item and len(item) > 2 and item not in found:
                    found.append(item)
        return found

    def _extract_target_phase(self, text: str) -> str | None:
        lowered = text.lower()
        for phase in _PHASE_KEYWORDS:
            # "up to shot_bible", "stop at shot_bible", "target phase shot_bible"
            pattern = rf"(?:up\s+to|stop\s+at|target\s+phase)\s+{re.escape(phase)}"
            if re.search(pattern, lowered):
                return phase
        return None


def extract_constraints(
    text: str,
    project_id: str = "",
    hints: dict[str, Any] | None = None,
) -> ProjectConstraints:
    """Convenience wrapper for ``ConstraintExtractor.extract``."""
    return ConstraintExtractor(project_id=project_id).extract(text, hints=hints)

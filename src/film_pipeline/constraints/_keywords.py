"""Vocabulary tables for heuristic constraint extraction.

Pure data: every trigger phrase the extractor matches against, in the
scan order that matters. No logic lives here.
"""

from __future__ import annotations

from film_pipeline.schemas.base import FilmType
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

# Scan order for pacing: longer phrases before their substrings.
_PACING_PREFERENCE: tuple[str, ...] = (
    "slow cinema",
    "meditative",
    "contemplative",
    "standard",
    "moderate",
    "dynamic",
    "slow",
    "fast",
    "action",
)

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

# Trigger phrases for list-valued facets; capture group 1 holds the payload.
_FORBIDDEN_TOPIC_PATTERNS: tuple[str, ...] = (
    r"\bno\s+([^\.\n,]+)",
    r"\bavoid\s+([^\.\n,]+)",
    r"\bdo\s+not\s+include\s+([^\.\n,]+)",
)

_REQUIRED_ELEMENT_PATTERNS: tuple[str, ...] = (
    r"\bmust\s+include\s+([^\.\n,]+)",
    r"\bmust\s+have\s+([^\.\n,]+)",
    r"\bneeds?\s+to\s+include\s+([^\.\n,]+)",
    r"\brequired[:\-]?\s*([^\.\n]+)",
)

_LOCATION_PATTERNS: tuple[str, ...] = (
    r"\bset\s+in\s+([^\.\n,]+)",
    r"\btakes?\s+place\s+in\s+([^\.\n,]+)",
    r"\blocation[:\-]?\s*([^\.\n,]+)",
)

_CHARACTER_CONSTRAINT_PATTERNS: tuple[str, ...] = (
    r"\bprotagonist\s+must\s+([^\.\n]+)",
    r"\bmain\s+character\s+must\s+([^\.\n]+)",
    r"\bcharacter\s+must\s+([^\.\n]+)",
)

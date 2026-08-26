"""Imagen 4 provider adapter via the Gemini API REST surface."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

from film_pipeline.providers.base import (
    BaseProviderAdapter,
    ProviderJob,
    ProviderJobStatus,
)
from film_pipeline.providers.credentials import lookup, redact
from film_pipeline.schemas.registries.provider_registry import ProviderRegistryEntry

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models"
_FALLBACK_MODEL = "imagen-4.0-fast-generate-001"
_DEFAULT_PERSON_GENERATION = "allow_adult"
_DEFAULT_IMAGE_SIZE = "1K"


def _accepts_large_images(model: str) -> bool:
    """Ultra-tier and non-fast ``generate-001`` models accept 1K images."""
    return "ultra" in model or ("generate-001" in model and "fast" not in model)


class Imagen4GeminiProvider(BaseProviderAdapter):
    """Google-backed Imagen 4 adapter for reference image generation."""

    def __init__(
        self,
        entry: ProviderRegistryEntry,
        http_opener: Any = None,
    ) -> None:
        super().__init__(entry)
        self._http_opener = http_opener
        self._configured_api_key = lookup(entry.provider_id)

    def _api_key(self) -> str:
        key = self._configured_api_key or lookup(self.entry.provider_id)
        if not key:
            raise RuntimeError("GOOGLE_API_KEY is not set.")
        return key

    def _model_id(self, fallback: str = _FALLBACK_MODEL) -> str:
        """First configured model id, or ``fallback`` when none are listed."""
        return self.entry.models[0] if self.entry.models else fallback

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = self._model_id()
        req = urllib.request.Request(
            f"{GEMINI_API}/{model}:predict",
            data=json.dumps(payload).encode(),
            headers={
                "x-goog-api-key": self._api_key(),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        opener = self._http_opener or urllib.request.build_opener()
        try:
            with opener.open(req) as response:
                raw: Any = json.loads(response.read())
                return dict(raw)
        except (urllib.error.HTTPError, OSError) as exc:
            detail = str(exc)
            if isinstance(exc, urllib.error.HTTPError):
                body_text = exc.read().decode(errors="replace")
                detail = f"HTTP {exc.code}: {redact(body_text)[:300]}"
            raise RuntimeError(f"Imagen predict failed: {detail}") from exc

    def build_payload(
        self,
        prompt: str,
        references: list[str] | None = None,
        duration: float = 0.0,
        aspect_ratio: str = "16:9",
        seed: int | None = None,
    ) -> dict[str, Any]:
        _ = duration
        _ = references
        # The standalone Imagen API does not support reference-image
        # conditioning (image-to-image).  Identity consistency is enforced
        # at the prompt level via the ID_REINFORCE block instead.
        parameters: dict[str, Any] = {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "personGeneration": _DEFAULT_PERSON_GENERATION,
        }
        model = self._model_id()
        if _accepts_large_images(model):
            parameters["imageSize"] = _DEFAULT_IMAGE_SIZE
        if seed is not None:
            parameters["seed"] = seed
        return {
            "model": model,
            "instances": [{"prompt": prompt}],
            "parameters": parameters,
        }

    def submit(self, payload: dict[str, Any], shot_id: str) -> ProviderJob:
        response = self._request(payload)
        image_bytes, mime_type = _extract_image_bytes(response)
        return ProviderJob(
            job_id=f"imagen-{uuid4().hex[:12]}",
            shot_id=shot_id,
            provider_id=self.entry.provider_id,
            model=str(payload.get("model", self._model_id(fallback=""))),
            payload=payload,
            status=ProviderJobStatus.SUBMITTED,
            metadata={
                "response": response,
                "image_bytes_b64": base64.b64encode(image_bytes).decode(),
                "mime_type": mime_type,
            },
        )

    def poll(self, job: ProviderJob) -> ProviderJob:
        job.status = ProviderJobStatus.COMPLETED
        job.polls += 1
        return job

    def download(self, job: ProviderJob, output_dir: str) -> str:
        meta = job.metadata or {}
        image_b64 = str(meta.get("image_bytes_b64", ""))
        if not image_b64:
            raise RuntimeError("Imagen response contained no image bytes.")

        image_bytes = base64.b64decode(image_b64)
        mime_type = str(meta.get("mime_type", "image/png")) or "image/png"
        suffix = ".png" if mime_type == "image/png" else ".jpg"

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{job.shot_id}{suffix}"
        path.write_bytes(image_bytes)

        meta["download_path"] = str(path)
        meta["mime_type"] = mime_type
        meta["placeholder"] = False
        job.metadata = meta
        return str(path)

    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "file_not_found"}

        return {
            "file": file_path,
            "provider": self.entry.provider_id,
            "size_bytes": path.stat().st_size,
            "mime_type": _infer_mime_type(path),
            "placeholder": False,
        }

    def estimate_cost(self, duration: float, model: str | None = None) -> float:
        _ = duration
        model_id = model or self._model_id(fallback="")
        if "ultra" in model_id:
            return 0.10
        if "fast" in model_id:
            return 0.02
        return 0.05


def _extract_image_bytes(response: dict[str, Any]) -> tuple[bytes, str]:
    predictions = response.get("predictions")
    if isinstance(predictions, list):
        for prediction in predictions:
            if isinstance(prediction, dict):
                image_b64 = str(prediction.get("bytesBase64Encoded", ""))
                if image_b64:
                    mime_type = str(prediction.get("mimeType", "image/png")) or "image/png"
                    return base64.b64decode(image_b64), mime_type

    generated = response.get("generatedImages")
    if isinstance(generated, list):
        for item in generated:
            if not isinstance(item, dict):
                continue
            image = item.get("image")
            if isinstance(image, dict):
                image_b64 = str(image.get("imageBytes", ""))
                if image_b64:
                    mime_type = str(image.get("mimeType", "image/png")) or "image/png"
                    return base64.b64decode(image_b64), mime_type

    raise RuntimeError("Imagen response did not include generated image bytes.")


def _infer_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"

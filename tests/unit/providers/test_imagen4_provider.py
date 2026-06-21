"""Tests for the Imagen 4 Gemini provider adapter."""

from __future__ import annotations

import base64
import json
import tempfile
from io import BytesIO
from pathlib import Path
from unittest import mock

import pytest

from film_pipeline.providers.adapters.imagen4_gemini import Imagen4GeminiProvider
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)


@pytest.fixture
def entry() -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id="gemini-imagen-4",
        provider_type="image",
        models=["imagen-4.0-generate-001"],
        capabilities=ProviderCapabilities(
            text_to_image=True,
            image_to_image=True,
            supports_seed=True,
            aspect_ratios=["16:9", "1:1"],
            supported_resolutions=["1024x1024"],
        ),
        cost_profile=CostProfile(unit="image", estimated_rate_usd=0.0),
    )


class TestImagen4GeminiProvider:
    def test_build_payload(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry)
        payload = provider.build_payload(
            "neon alley at rain-soaked dusk",
            aspect_ratio="1:1",
            seed=7,
        )

        assert payload["model"] == "imagen-4.0-generate-001"
        assert payload["instances"] == [{"prompt": "neon alley at rain-soaked dusk"}]
        assert payload["parameters"]["aspectRatio"] == "1:1"
        assert payload["parameters"]["seed"] == 7

    def test_submit_requires_google_api_key(self, entry: ProviderRegistryEntry) -> None:
        from unittest import mock

        with mock.patch("film_pipeline.providers.adapters.imagen4_gemini.lookup", return_value=""):
            provider = Imagen4GeminiProvider(entry=entry)
            with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
                provider.submit(provider.build_payload("test"), "REF-001")

    def test_submit_poll_download_and_metadata(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(
            entry,
            {
                "predictions": [
                    {
                        "mimeType": "image/png",
                        "bytesBase64Encoded": base64.b64encode(b"PNGDATA").decode(),
                    }
                ]
            },
        )
        job = provider.submit(provider.build_payload("test prompt"), "REF-001")
        assert job.status == "submitted"
        assert job.job_id.startswith("imagen-")

        job = provider.poll(job)
        assert job.status == "completed"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = provider.download(job, tmpdir)
            assert Path(path).exists()
            assert Path(path).suffix == ".png"
            meta = provider.extract_metadata(path)
            assert meta["provider"] == "gemini-imagen-4"
            assert meta["placeholder"] is False
            assert meta["size_bytes"] == 7

    def test_submit_raises_on_http_error(self, entry: ProviderRegistryEntry) -> None:
        provider = _make_provider(entry, None, code=500)
        with pytest.raises(RuntimeError, match="Imagen predict failed"):
            provider.submit(provider.build_payload("test prompt"), "REF-001")


def _make_provider(
    entry: ProviderRegistryEntry,
    response_body: dict[str, object] | None = None,
    *,
    code: int = 200,
) -> Imagen4GeminiProvider:
    with mock.patch.dict("os.environ", {"GOOGLE_API_KEY": "AIza-test-key"}):
        return Imagen4GeminiProvider(
            entry=entry,
            http_opener=_mock_opener(response_body or {}, code=code),
        )


def _mock_opener(response_body: dict[str, object], code: int = 200) -> mock.Mock:
    def _open(_req: object) -> BytesIO:
        if code >= 400:
            raise OSError(f"HTTP {code}")
        return BytesIO(json.dumps(response_body).encode())

    opener = mock.Mock()
    opener.open = _open
    return opener

"""Tests for the bundled Fireworks AI provider profile.

Fireworks exposes its catalog at ``/v1/accounts/{account}/models`` with a
response shape that uses ``name`` instead of ``id`` and includes many
non-chat / non-tool models. The bundled profile must therefore:

* set ``models_url`` to the documented Fireworks endpoint,
* override ``fetch_models`` to extract ``name`` and filter for tool support,
* keep the inference ``base_url`` pointing at the OpenAI-compatible endpoint
  so the runtime still uses ``https://api.fireworks.ai/inference/v1``.
"""

from unittest.mock import patch

import pytest

from providers import get_provider_profile
from providers.base import ProviderProfile


class TestFireworksProfile:
    def test_profile_is_registered(self):
        p = get_provider_profile("fireworks")
        assert p is not None
        assert p.name == "fireworks"

    def test_profile_has_correct_catalog_and_inference_urls(self):
        p = get_provider_profile("fireworks")
        assert p.base_url == "https://api.fireworks.ai/inference/v1"
        assert p.models_url == "https://api.fireworks.ai/v1/accounts/fireworks/models"

    def test_fetch_models_extracts_name_and_filters_tools(self):
        """Only public models with supportsTools=True are returned."""
        p = get_provider_profile("fireworks")
        fake_response = {
            "models": [
                {"name": "accounts/fireworks/models/tool-model", "public": True, "supportsTools": True},
                {"name": "accounts/fireworks/models/private-tool-model", "public": False, "supportsTools": True},
                {"name": "accounts/fireworks/models/no-tools-model", "public": True, "supportsTools": False},
                {"name": "display-name-only", "public": True, "supportsTools": True},
            ]
        }
        with patch("urllib.request.urlopen", return_value=_mock_json_response(fake_response)):
            models = p.fetch_models(api_key="sk-test", timeout=30)

        assert models == ["accounts/fireworks/models/tool-model", "display-name-only"]

    def test_fetch_models_returns_none_on_network_error(self):
        """A broken catalog endpoint should not crash the picker."""
        p = get_provider_profile("fireworks")
        with patch("urllib.request.urlopen", side_effect=OSError("network down")):
            assert p.fetch_models(api_key="sk-test", timeout=30) is None

    def test_fetch_models_uses_models_url(self):
        """The override must hit the Fireworks models endpoint, not base_url/models."""
        p = get_provider_profile("fireworks")
        captured = {}

        def capture_request(req, **_kwargs):
            captured["url"] = req.full_url
            return _mock_json_response({"models": []})

        with patch("urllib.request.urlopen", side_effect=capture_request):
            p.fetch_models(api_key="sk-test", timeout=30)

        assert captured["url"] == "https://api.fireworks.ai/v1/accounts/fireworks/models"


class _MockFile:
    """Minimal file-like wrapper for urllib responses."""

    def __init__(self, data):
        self._data = data
        self._read = False

    def read(self):
        if self._read:
            return b""
        self._read = True
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _mock_json_response(payload):
    import json

    return _MockFile(json.dumps(payload).encode())

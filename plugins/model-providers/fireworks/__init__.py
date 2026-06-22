"""Fireworks AI provider profile."""

from typing import Any

from providers import register_provider
from providers.base import ProviderProfile, _profile_user_agent


class FireworksProfile(ProviderProfile):
    """Fireworks AI provider profile.

    Fireworks exposes its model catalog at ``/v1/accounts/{account}/models``
    (not the standard OpenAI ``/v1/models`` endpoint under the inference
    base URL). The response uses ``name`` for the model ID and includes many
    non-chat / non-tool models, so we filter for public models that support
    tool use and return only the ``name`` field.
    """

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        """Fetch the Fireworks model catalog.

        Falls back to the static ``fallback_models`` if the API call fails.
        """
        import json
        import urllib.request

        url = (self.models_url or "").strip()
        if not url:
            return None

        req = urllib.request.Request(url)
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", _profile_user_agent())
        for k, v in self.default_headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
        except Exception:
            return None

        items = data if isinstance(data, list) else data.get("models", [])
        result: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            # Surface only public models that advertise tool support, so the
            # picker matches the agentic catalog intent.
            if item.get("public") is False:
                continue
            if not item.get("supportsTools"):
                continue
            result.append(name)
        return result


fireworks = FireworksProfile(
    name="fireworks",
    aliases=("fireworks-ai",),
    env_vars=("FIREWORKS_API_KEY",),
    display_name="Fireworks AI",
    description="Fireworks AI (fast open model hosting)",
    signup_url="https://fireworks.ai",
    auth_type="api_key",
    supports_health_check=True,
    fallback_models=(
        "accounts/fireworks/models/llama-v3p1-405b-instruct",
        "accounts/fireworks/models/deepseek-v3",
    ),
    base_url="https://api.fireworks.ai/inference/v1",
    models_url="https://api.fireworks.ai/v1/accounts/fireworks/models",
)

register_provider(fireworks)

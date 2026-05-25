"""Model provider clients."""

from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import error, request

from mma.config import AppConfig
from mma.routing import Route


@dataclass(frozen=True)
class ModelResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class ProviderError(RuntimeError):
    """Raised when a provider call fails."""


def generate(route: Route, config: AppConfig, prompt: str) -> ModelResult:
    if route.provider == "local":
        return _ollama_generate(config, route.model, prompt)
    if route.provider == "nvidia":
        return _openai_compatible_generate(
            base_url=config.nvidia_base_url,
            api_key=config.nvidia_api_key,
            model=route.model,
            prompt=prompt,
            provider_name="nvidia",
        )
    raise ProviderError(f"unknown provider: {route.provider}")


def _ollama_generate(config: AppConfig, model: str, prompt: str) -> ModelResult:
    url = f"{config.ollama_base_url.rstrip('/')}/api/generate"
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode())
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Ollama call failed for {model}: {exc}") from exc
    return ModelResult(text=data.get("response", ""))


def _openai_compatible_generate(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
    prompt: str,
    provider_name: str,
) -> ModelResult:
    if not api_key:
        raise ProviderError(f"{provider_name} API key is not configured")
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an engineering agent. Return only the requested structured output.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as response:
            data = json.loads(response.read().decode())
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        raise ProviderError(f"{provider_name} call failed for {model}: {exc}") from exc
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return ModelResult(
        text=content,
        input_tokens=int(usage.get("prompt_tokens", 0) or 0),
        output_tokens=int(usage.get("completion_tokens", 0) or 0),
    )

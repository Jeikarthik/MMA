"""Model provider clients."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
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


def provider_health(config: AppConfig) -> dict[str, object]:
    """Return lightweight health for configured providers."""

    return {
        "ollama": _ollama_health(config),
        "nvidia": {
            "configured": bool(config.nvidia_api_key),
            "base_url": config.nvidia_base_url,
        },
        "claude": {"configured": bool(config.claude_api_key)},
    }


def _ollama_generate(config: AppConfig, model: str, prompt: str) -> ModelResult:
    url = f"{config.ollama_base_url.rstrip('/')}/api/generate"
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    data = _request_json_with_retries(req, timeout=120, attempts=2, provider_name="Ollama")
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
    data = _request_json_with_retries(req, timeout=180, attempts=3, provider_name=provider_name)
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return ModelResult(
        text=content,
        input_tokens=int(usage.get("prompt_tokens", 0) or 0),
        output_tokens=int(usage.get("completion_tokens", 0) or 0),
    )


def _request_json_with_retries(
    req: request.Request, *, timeout: int, attempts: int, provider_name: str
) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                break
            time.sleep(min(2**attempt, 8))
        except (OSError, error.URLError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(min(2**attempt, 8))
    raise ProviderError(f"{provider_name} call failed: {last_error}") from last_error


def _ollama_health(config: AppConfig) -> dict[str, object]:
    url = f"{config.ollama_base_url.rstrip('/')}/api/tags"
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        models = [item.get("name") for item in data.get("models", []) if item.get("name")]
        return {"available": True, "base_url": config.ollama_base_url, "models": models}
    except Exception as exc:  # noqa: BLE001 - health endpoint should not raise.
        return {"available": False, "base_url": config.ollama_base_url, "error": str(exc)}

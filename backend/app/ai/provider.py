"""Yandex AI Studio through its OpenAI-compatible endpoint: one request, one answer, the tokens it cost.

The key is an API key of a service account with the role ai.languageModels.user; the folder is
where that account lives. Neither is ever written to a log or an error the page sees.
"""

import time

import httpx

BASE = "https://ai.api.cloud.yandex.net/v1"
TIMEOUT = httpx.Timeout(45.0, connect=10.0)
MAX_TOKENS = 1000
TEMPERATURE = 0.6

# Models that refused the JSON mode once: they are asked without it from then on (the prompt still asks for JSON).
_NO_JSON_MODE: set[str] = set()


class ProviderError(Exception):
    """The provider did not answer; the message is safe to show the admin."""


def complete(key: str, folder: str, model: str, messages: list[dict], max_tokens: int = MAX_TOKENS) -> dict:
    """{text, prompt, cached, output, ms}: the answer and the tokens of the call."""
    if not key or not folder:
        raise ProviderError("не заданы API-ключ или каталог")
    body = {"model": f"gpt://{folder}/{model}", "messages": messages, "max_tokens": max_tokens, "temperature": TEMPERATURE}
    # Without the logging switch Yandex keeps the requests to improve its models; ours carry a chart and a life.
    headers = {"Authorization": f"Api-Key {key}", "OpenAI-Project": folder, "x-data-logging-enabled": "false"}
    started = time.monotonic()
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            if model not in _NO_JSON_MODE:
                response = client.post(f"{BASE}/chat/completions", json={**body, "response_format": {"type": "json_object"}}, headers=headers)
                if response.status_code == 400:
                    _NO_JSON_MODE.add(model)
            if model in _NO_JSON_MODE:
                response = client.post(f"{BASE}/chat/completions", json=body, headers=headers)
    except httpx.TimeoutException as exc:
        raise ProviderError("модель не ответила вовремя") from exc
    except httpx.HTTPError as exc:
        raise ProviderError(f"нет связи с Yandex AI Studio: {type(exc).__name__}") from exc
    ms = int((time.monotonic() - started) * 1000)
    if response.status_code != 200:
        raise ProviderError(f"HTTP {response.status_code}: {_said(response)}")
    try:
        data = response.json()
        text = data["choices"][0]["message"].get("content") or ""
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ProviderError("непонятный ответ провайдера") from exc
    usage = data.get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}
    return {
        "text": text,
        "prompt": int(usage.get("prompt_tokens") or 0),
        "cached": int(details.get("cached_tokens") or 0),
        "output": int(usage.get("completion_tokens") or 0),
        "ms": ms,
    }


def _said(response: httpx.Response) -> str:
    """The provider's own words about the error, short."""
    try:
        data = response.json()
    except ValueError:
        return " ".join(response.text.split())[:300]
    message = data
    if isinstance(data, dict):
        error = data.get("error")
        message = error.get("message") if isinstance(error, dict) else error or data.get("message") or data
    return " ".join(str(message).split())[:300]

"""The models of Yandex AI Studio the admin may choose, and what an answer costs.

Prices are roubles with VAT per 1000 tokens, synchronous mode, as AI Studio lists them in October
2026: the fresh input, the input read from the provider's cache, the output. They change rarely;
when they do, this table is the one place to fix.
"""

# id: (label, input, cached input, output)
MODELS = {
    "deepseek-v4.1-flash": ("DeepSeek V4.1 Flash", 0.3, 0.075, 0.5),
    "aliceai-llm": ("Alice AI LLM", 0.5, 0.5, 1.2),
    "aliceai-llm-flash": ("Alice AI LLM Flash", 0.1, 0.025, 0.2),
    "qwen3.6-35b-a3b": ("Qwen3.6 35B", 0.2, 0.05, 0.3),
    "yandexgpt-5.1": ("YandexGPT Pro 5.1", 0.8, 0.8, 0.8),
}
DEFAULT_MODEL = "deepseek-v4.1-flash"


def cost(model: str, prompt: int, cached: int, output: int) -> float:
    """Roubles for one call; the cached part of the prompt is billed at its own price."""
    _, fresh, again, out = MODELS.get(model, MODELS[DEFAULT_MODEL])
    return round((max(0, prompt - cached) * fresh + cached * again + output * out) / 1000, 4)


def catalogue() -> list[dict]:
    return [{"id": key, "label": label, "input": fresh, "cached": again, "output": out}
            for key, (label, fresh, again, out) in MODELS.items()]

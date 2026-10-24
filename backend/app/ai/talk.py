"""One answer of the ИИ-астролог from the model: the settings, the request, the check and one retry.

Whatever goes wrong — no key, no answer, an answer that fails the check twice — comes back as an
Answer without data, and the chat falls back to the templates.
"""

import re
import secrets
from dataclasses import dataclass
from datetime import date

from app.ai import guard, passport, prompt, provider
from app.ai.models import DEFAULT_MODEL, MODELS, cost
from app.settings_store import setting

# A word never found in a real answer: written by the model, it means the model is reciting its rules.
CANARY = "ZV-" + secrets.token_hex(4).upper()
RETRY = "Ответ не прошёл проверку сервиса: {problem}. Напишите ответ заново по всем правилам, одним JSON-объектом."


def _number(key: str) -> int:
    try:
        return int(setting(key))
    except ValueError:
        return 0


def config() -> dict:
    model = setting("ai_model")
    trial = setting("ai_trial_model")
    return {
        "mode": setting("ai_mode"),
        "testers": {part for part in re.split(r"[,;\s]+", setting("ai_testers").lower()) if part},
        "key": setting("ai_api_key"),
        "folder": setting("ai_folder"),
        "model": model if model in MODELS else DEFAULT_MODEL,
        "trial_model": trial if trial in MODELS else "",
        "daily": _number("ai_daily_limit") or 20,
        "budget": _number("ai_month_budget"),
        "helpline": setting("ai_helpline"),
        "style": setting("ai_style"),
        "examples": setting("ai_examples"),
        "site": setting("site_name"),
    }


def ready(cfg: dict) -> bool:
    return bool(cfg["key"] and cfg["folder"])


def serves(cfg: dict, email: str) -> bool:
    """Whether this person talks to the model: «on» for everyone, «test» for the listed emails only."""
    if not ready(cfg):
        return False
    return cfg["mode"] == "on" or (cfg["mode"] == "test" and email.lower() in cfg["testers"])


@dataclass
class Answer:
    data: dict | None  # guard.check's: category, answer, key, follow, remember
    model: str
    prompt: int = 0
    cached: int = 0
    output: int = 0
    cost: float = 0.0
    ms: int = 0
    error: str = ""
    flagged: bool = False
    raw: str = ""


def request(cfg: dict, chart: dict, context: dict, memory: list[str], history: list[dict], question: str,
            today: date) -> list[dict]:
    rules = prompt.system(cfg["site"], CANARY, cfg["style"], cfg["examples"])
    return prompt.messages(rules, passport.build(chart, context, memory, today), history, question)


def ask(cfg: dict, model: str, messages: list[dict]) -> Answer:
    """The model's answer to `messages`, checked; one retry with the reason when the first fails the check."""
    result = Answer(data=None, model=model)
    problem = ""
    for _ in range(2):
        try:
            reply = provider.complete(cfg["key"], cfg["folder"], model, messages)
        except provider.ProviderError as exc:
            result.error = str(exc)
            return result
        result.prompt += reply["prompt"]
        result.cached += reply["cached"]
        result.output += reply["output"]
        result.ms += reply["ms"]
        result.cost = round(result.cost + cost(model, reply["prompt"], reply["cached"], reply["output"]), 4)
        result.raw = reply["text"]
        data, problem = guard.check(guard.parse(reply["text"]), CANARY)
        if data is not None:
            result.data = data
            return result
        result.flagged = True
        messages = [*messages, {"role": "assistant", "content": reply["text"]},
                    {"role": "user", "content": RETRY.format(problem=problem)}]
    result.error = f"ответ не прошёл проверку: {problem}"
    return result

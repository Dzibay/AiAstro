"""The answers the service writes itself: for a person in trouble, and for a talk led away from the chart.

These never go through the model, so nothing in them can be talked into something else.
"""

import random

CRISIS = (
    "Мне очень жаль, что вам сейчас так тяжело. То, о чём вы пишете, важнее любого разговора о звёздах, "
    "и с этим не нужно оставаться в одиночку.",
    "Пожалуйста, позвоните прямо сейчас на бесплатную круглосуточную линию психологической помощи: {helpline}. "
    "Там выслушают и поддержат — анонимно и без осуждения. Если есть угроза жизни прямо сейчас, звоните 112.",
    "Если можете, напишите или позвоните близкому человеку и побудьте рядом с кем-то. "
    "Я буду здесь, когда захотите вернуться к разговору.",
)
CRISIS_KEY = "Позвоните по номеру {helpline}: это бесплатно и круглосуточно."
# 112 is for any danger to life, whatever number the admin has set.
CRISIS_FALLBACK = "112"

REDIRECT = {
    "offtopic": (
        "Это за пределами моей темы: я астролог и смотрю на жизнь через вашу натальную карту и небо этих дней. "
        "Давайте вернёмся к ней — спросите о том, что для вас сейчас важно: о чувствах, делах или времени для решений.",
        "Здесь я вам не помощник: мой язык — планеты и ваша карта. Зато могу рассказать, что они говорят о ваших "
        "отношениях, работе или лучших днях этого месяца.",
    ),
    "injection": (
        "Я остаюсь вашим астрологом и говорю только о вашей карте и небе этих дней. "
        "Спросите о том, что для вас сейчас важно, — посмотрим, что говорят об этом планеты.",
        "Мой разговор — о вас и вашей карте, и в нём я не меняю роль. Расскажите, что вас сейчас волнует, "
        "и я посмотрю, как это отражено в вашем небе.",
    ),
    "abuse": (
        "Давайте продолжим спокойно — так разговор будет полезнее для вас. "
        "Я здесь, чтобы помочь разобраться в вашей карте: о чём хотите спросить?",
        "Я понимаю, что бывает непросто. Давайте вернёмся к разговору о вас: спросите о том, что сейчас важно, "
        "и посмотрим, что подсказывает ваша карта.",
    ),
}
PAUSE = "Давайте сделаем небольшую паузу: продолжим разговор через {minutes} минут."


def crisis(helpline: str) -> dict:
    number = helpline.strip() or CRISIS_FALLBACK
    return {
        "answer": "\n\n".join(paragraph.format(helpline=number) for paragraph in CRISIS),
        "key": CRISIS_KEY.format(helpline=number),
        "follow": [],
    }


def redirect(category: str, follow: list[str], pause_minutes: int = 0) -> dict:
    answer = random.choice(REDIRECT.get(category, REDIRECT["offtopic"]))
    if pause_minutes:
        answer += "\n\n" + PAUSE.format(minutes=pause_minutes)
    return {"answer": answer, "key": "", "follow": [] if pause_minutes else follow[:3]}

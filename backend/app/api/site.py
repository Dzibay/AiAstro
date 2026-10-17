from fastapi import APIRouter, HTTPException

from app.config import settings
from app.settings_store import public_config

router = APIRouter(prefix="/site")

_LEGAL = {
    "privacy": {
        "title": "Конфиденциальность",
        "paragraphs": [
            "Сервис хранит почту, имя и необратимый хеш пароля, чтобы открывать личный кабинет.",
            "Сессия — подписанный токен в браузере. Отдельной таблицы сессий нет.",
            "Эти данные не передаются для рекламы и не продаются. Сторонних счётчиков на сайте нет.",
            "Чтобы удалить кабинет, напишите на почту поддержки из подвала.",
        ],
    },
    "offer": {
        "title": "Оферта",
        "paragraphs": [
            "Регистрация кабинета бесплатная. Оплата в этой версии не подключена.",
            "Тексты сайта носят информационный характер и не заменяют консультацию врача, юриста или финансового специалиста.",
            "Расчёт натальной карты в этой версии не выполняется. В кабинете видно только учётную запись.",
        ],
    },
    "consent": {
        "title": "Согласие",
        "paragraphs": [
            "Создавая кабинет, вы соглашаетесь на обработку почты и имени для входа в сервис.",
            "В браузере сохраняются отметка о согласии с сообщением внизу экрана и токен сессии.",
            "Согласие можно отозвать, удалив данные сайта в браузере и написав на почту поддержки.",
        ],
    },
}


@router.get("/config")
def site_config() -> dict:
    return public_config(settings.site_name)


@router.get("/legal/{page}")
def legal_page(page: str) -> dict:
    document = _LEGAL.get(page)
    if document is None:
        raise HTTPException(status_code=404, detail="missing")
    contact = public_config(settings.site_name)["support_email"]
    paragraphs = list(document["paragraphs"])
    if contact:
        paragraphs.append(f"Почта поддержки: {contact}.")
    return {"slug": page, "title": document["title"], "paragraphs": paragraphs}

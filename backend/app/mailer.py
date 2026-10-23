"""Letters: the email confirmation, the new password link, the end of «Небосвод», the partner's answer.

Through the SMTP server set in the admin panel: plain text, and the site's look in HTML beside it
(app.letters lays both out). A letter never holds up a request: the routes hand it to the
background, and a server that does not answer is only written to the log.
"""

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.config import settings
from app.settings_store import get_settings, setting

log = logging.getLogger("aiastro")

TIMEOUT = 15


def _sender(data: dict[str, str]) -> str:
    return data.get("mail_from") or data.get("smtp_user") or ""


def mail_on(data: dict[str, str] | None = None) -> bool:
    data = data if data is not None else get_settings()
    return bool(data.get("smtp_host") and "@" in _sender(data))


def link(path: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}{path}"


def _letter(to: str, subject: str, text: str, data: dict[str, str], html: str | None = None) -> EmailMessage:
    site = setting("site_name")
    message = EmailMessage()
    message["From"] = formataddr((site, _sender(data)))
    message["To"] = to
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=_sender(data).split("@", 1)[1])
    support = data.get("support_email")
    if support:
        message["Reply-To"] = support
    message.set_content(f"{text.strip()}\n\n— {site}\n{link('/')}\n")
    if html:
        message.add_alternative(html, subtype="html")
    return message


def send(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Sends now and raises on failure: for the admin's test letter, which wants to know why."""
    data = get_settings()
    if not mail_on(data):
        raise RuntimeError("SMTP не настроен")
    message = _letter(to, subject, text, data, html)
    host = data["smtp_host"]
    port = int(data.get("smtp_port") or 465)
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=TIMEOUT)
    else:
        server = smtplib.SMTP(host, port, timeout=TIMEOUT)
    with server:
        if port != 465:
            server.starttls()
        if data.get("smtp_user"):
            server.login(data["smtp_user"], data.get("smtp_password") or "")
        server.send_message(message)


def send_quietly(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """For the background: a letter that did not leave is logged, never raised."""
    try:
        send(to, subject, text, html)
        return True
    except Exception as exc:  # noqa: BLE001 — any SMTP or network failure is the same to the person
        log.warning("Письмо «%s» не ушло: %s", subject, exc)
        return False

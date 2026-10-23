"""The site's letters in one look: the night sky, a serif heading and a gold button.

A letter is a few parts — a heading, a greeting, paragraphs, one button and a quiet line below —
given once and laid out twice: HTML in the site's style and plain text for the mail programs that
show only text. Tables and inline styles, since mail programs know little else; the colours stand
on their own too, so a program that drops the gradients still shows a dark sky and a gold button.
"""

from dataclasses import dataclass, field
from html import escape

from app.mailer import link, send_quietly
from app.settings_store import setting

_BG = "#0d1311"
_CARD = "#151e1b"
_LINE = "#2a3732"
_INK = "#f4efe6"
_MUTED = "#a9b5ab"
_QUIET = "#76847b"
_GOLD = "#e0c17a"
_SERIF = "'Cormorant Garamond', Georgia, 'Times New Roman', serif"
_SANS = "'Source Sans 3', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


@dataclass
class Letter:
    subject: str
    title: str
    hello: str
    lines: list[str]
    button: str = ""
    url: str = ""
    # Below the button: how long the link lives, a word of comfort.
    after: list[str] = field(default_factory=list)
    # The smallest print at the very bottom: why this letter came, how to switch such letters off.
    foot: str = ""


def text(letter: Letter) -> str:
    parts = [letter.hello, *letter.lines]
    if letter.url:
        parts.append(f"{letter.button}:\n{letter.url}")
    parts += letter.after
    if letter.foot:
        parts.append(letter.foot)
    return "\n\n".join(parts)


def _paragraph(line: str, size: int = 17, color: str = _INK, top: int = 14) -> str:
    return (
        f'<p style="margin:{top}px 0 0;font-family:{_SANS};font-size:{size}px;line-height:1.6;color:{color};">'
        f"{escape(line)}</p>"
    )


def _button(label: str, url: str) -> str:
    href = escape(url, quote=True)
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:30px auto 6px;">
  <tr>
    <td align="center" bgcolor="#e3bd78" style="border-radius:999px;background-color:#e3bd78;background-image:linear-gradient(180deg,#f4dba6 0%,#e3bd78 55%,#cf9f55 100%);box-shadow:0 8px 30px rgba(230,170,80,0.32);">
      <a href="{href}" target="_blank" style="display:inline-block;padding:16px 36px;border-radius:999px;font-family:{_SANS};font-size:17px;font-weight:600;line-height:1.2;color:#2b1d0b;text-decoration:none;">{escape(label)}</a>
    </td>
  </tr>
</table>"""


def html(letter: Letter) -> str:
    site = setting("site_name")
    motto = setting("tagline")
    tagline = f" — {escape(motto)}" if motto else ""
    home = link("/")
    body = [_paragraph(letter.hello, top=0)]
    body += [_paragraph(line) for line in letter.lines]
    if letter.url:
        body.append(_button(letter.button, letter.url))
    body += [_paragraph(line, 14, _MUTED, 16) for line in letter.after]
    if letter.url:
        href = escape(letter.url, quote=True)
        body.append(
            f'<p style="margin:18px 0 0;font-family:{_SANS};font-size:12px;line-height:1.55;color:{_QUIET};word-break:break-all;">'
            f'Если кнопка не нажимается, откройте ссылку: <a href="{href}" target="_blank" style="color:{_GOLD};">{escape(letter.url)}</a></p>'
        )
    foot = _paragraph(letter.foot, 12, _QUIET, 0) if letter.foot else ""
    preview = escape(letter.lines[0] if letter.lines else letter.title)
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<meta name="supported-color-schemes" content="dark light">
<title>{escape(letter.subject)}</title>
</head>
<body style="margin:0;padding:0;background-color:{_BG};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{_BG};">{preview}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{_BG}" style="background-color:{_BG};background-image:radial-gradient(640px 320px at 12% 0%,rgba(224,193,122,0.16),rgba(224,193,122,0) 62%),radial-gradient(520px 300px at 100% 8%,rgba(80,120,98,0.22),rgba(80,120,98,0) 58%);">
  <tr>
    <td align="center" style="padding:34px 14px 40px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;">
        <tr>
          <td align="center" style="padding:0 0 18px;font-family:{_SERIF};font-size:15px;letter-spacing:0.32em;text-transform:uppercase;color:{_GOLD};">
            <a href="{escape(home, quote=True)}" target="_blank" style="color:{_GOLD};text-decoration:none;">&#10022;&nbsp; {escape(site)} &nbsp;&#10022;</a>
          </td>
        </tr>
        <tr>
          <td bgcolor="{_CARD}" style="background-color:{_CARD};background-image:radial-gradient(420px 200px at 50% 0%,rgba(244,219,166,0.14),rgba(244,219,166,0) 70%);border:1px solid {_LINE};border-radius:24px;padding:30px 34px 34px;">
            <div style="text-align:center;font-family:{_SERIF};font-size:13px;letter-spacing:12px;line-height:1;color:#8d6a32;">&middot;&#10023;&middot;&#10022;&middot;&#10023;&middot;</div>
            <h1 style="margin:16px 0 22px;font-family:{_SERIF};font-size:32px;font-weight:500;line-height:1.15;letter-spacing:-0.01em;text-align:center;color:#f4dba6;">{escape(letter.title)}</h1>
            {"".join(body)}
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:22px 22px 0;text-align:center;">
            {foot}
            <p style="margin:10px 0 0;font-family:{_SERIF};font-size:15px;line-height:1.5;color:{_MUTED};">
              <a href="{escape(home, quote=True)}" target="_blank" style="color:{_GOLD};text-decoration:none;">{escape(site)}</a>{tagline}
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def deliver(to: str, letter: Letter) -> bool:
    """Sends in the site's look with the plain text alongside; a failure is only logged."""
    return send_quietly(to, letter.subject, text(letter), html(letter))

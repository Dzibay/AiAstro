"""Budgets of attempts per key (an address, an email) in a fixed window: the doors open to anyone —
the logins, the registration, the reset letters, the calculations of the landings — would otherwise
let a password be guessed or a mailbox be flooded.

Kept in the memory of the one server process: a restart forgives everyone, which is fine for a
budget of minutes.
"""

import threading
import time as clock

from app.errors import DomainError

# Past this many keys the expired ones are swept out, so a flood of addresses cannot grow the memory.
_SWEEP = 10_000


class Window:
    def __init__(self, limit: int, seconds: int, code: str = "busy") -> None:
        self.limit = limit
        self.seconds = seconds
        self.code = code
        self._spent: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def take(self, key: str) -> None:
        """One attempt for `key`; past the limit — DomainError(code, 429). An empty key is not counted."""
        if not key:
            return
        now = clock.monotonic()
        with self._lock:
            start, count = self._spent.get(key, (now, 0))
            if now - start >= self.seconds:
                start, count = now, 0
            if count >= self.limit:
                raise DomainError(self.code, 429)
            self._spent[key] = (start, count + 1)
            if len(self._spent) > _SWEEP:
                for old in [old for old, (began, _) in self._spent.items() if now - began >= self.seconds]:
                    del self._spent[old]

    def forget(self, key: str) -> None:
        """A success wipes the key's attempts: a person who finally typed the password is not punished later."""
        with self._lock:
            self._spent.pop(key, None)


def address(request) -> str:
    """The client's address: uvicorn takes it from the proxies' X-Forwarded-For (Caddy → nginx)."""
    return request.client.host if request.client else ""

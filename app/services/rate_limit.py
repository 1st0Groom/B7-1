"""Per-user question limit so one user cannot use up the shared AI quota."""

import time
from collections import defaultdict, deque

MAX_QUESTIONS = 10
WINDOW_SECONDS = 60

_recent = defaultdict(deque)


def allow(user_id, now=None):
    """Return True and record the question if the user is under the limit."""
    now = time.monotonic() if now is None else now
    times = _recent[user_id]
    while times and now - times[0] >= WINDOW_SECONDS:
        times.popleft()
    if len(times) >= MAX_QUESTIONS:
        return False
    times.append(now)
    return True
    
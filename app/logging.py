import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id = ContextVar("request_id", default=None)
logger = logging.getLogger("b7")


def configure(level):
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    # SDK/HTTP debug logs can include private request data.
    for name in ("openai", "httpx", "httpcore", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


def event(name, **fields):
    logger.info(
        json.dumps(
            {
                "time": datetime.now(UTC).isoformat(),
                "event": name,
                "request_id": request_id.get(),
                **fields,
            },
            ensure_ascii=False,
        )
    )

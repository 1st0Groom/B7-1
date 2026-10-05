import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id = ContextVar("request_id", default=None)
logger = logging.getLogger("b7")


def configure():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


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

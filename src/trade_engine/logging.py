"""Structured JSON logging helpers."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import TextIO


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        data = {"timestamp": timestamp, "level": record.levelname}
        data.update(getattr(record, "event_data", {}))
        return json.dumps(data, sort_keys=True, separators=(",", ":"))


def configure_json_logger(
    *, stream: TextIO | None = None, name: str = "trade_engine"
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

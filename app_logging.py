from __future__ import annotations

import logging
from pathlib import Path
import queue


class QueueMessageHandler(logging.Handler):
    def __init__(self, target_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.target_queue = target_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.target_queue.put(self.format(record))
        except Exception:
            self.handleError(record)


def configure_logging(log_path: Path, ui_queue: queue.Queue[str] | None = None) -> logging.Logger:
    logger = logging.getLogger("clawbot")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    resolved_path = str(Path(log_path).resolve())
    file_handler_exists = False
    queue_handler_exists = False

    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", "") == resolved_path:
            file_handler_exists = True
        if isinstance(handler, QueueMessageHandler):
            queue_handler_exists = True

    if not file_handler_exists:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if ui_queue is not None and not queue_handler_exists:
        queue_handler = QueueMessageHandler(ui_queue)
        queue_handler.setFormatter(formatter)
        logger.addHandler(queue_handler)

    return logger

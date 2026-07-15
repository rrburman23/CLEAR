"""Runtime stream and logging configuration for single repair processes."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def configure_utf8_stream(stream: Any) -> None:
    """Configure a text stream to emit UTF-8 where supported."""

    reconfigure = getattr(stream, "reconfigure", None)

    if callable(reconfigure):
        reconfigure(
            encoding="utf-8",
            errors="replace",
        )


def configure_utf8_output() -> None:
    """Configure standard output and error for UTF-8 text."""

    configure_utf8_stream(sys.stdout)
    configure_utf8_stream(sys.stderr)


def _debug_enabled() -> bool:
    return os.getenv("DEBUG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def configure_runtime_logging(
    *,
    execution_log: Path | None,
    benchmark_mode: bool,
) -> None:
    """Configure quiet terminal output with retained model diagnostics.

    Human-readable CLEAR output is produced by ``src.utils.terminal`` and
    normal ``print`` calls. Root logging is therefore limited to unexpected
    errors so those lines are not duplicated in the terminal.

    Model-adapter telemetry is written silently to the standalone
    ``execution.log``. In benchmark mode it is sent to stderr so the parent
    benchmark runner can capture it in the parent experiment log.
    """

    formatter = logging.Formatter(_LOG_FORMAT)

    root_logger = logging.getLogger()
    _clear_handlers(root_logger)
    root_logger.setLevel(logging.INFO)

    root_error_handler = logging.StreamHandler(sys.stderr)
    root_error_handler.setLevel(logging.ERROR)
    root_error_handler.setFormatter(formatter)
    root_logger.addHandler(root_error_handler)

    model_logger = logging.getLogger("src.agent.model_adapter")
    _clear_handlers(model_logger)
    model_logger.propagate = False
    model_logger.setLevel(logging.DEBUG if _debug_enabled() else logging.INFO)

    if execution_log is not None:
        execution_log.parent.mkdir(parents=True, exist_ok=True)
        model_handler: logging.Handler = logging.FileHandler(
            execution_log,
            mode="a",
            encoding="utf-8",
        )
    elif benchmark_mode:
        model_handler = logging.StreamHandler(sys.stderr)
    else:
        model_handler = logging.NullHandler()

    model_handler.setLevel(model_logger.level)
    model_handler.setFormatter(formatter)
    model_logger.addHandler(model_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

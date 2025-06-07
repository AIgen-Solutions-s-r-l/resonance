"""Centralised logging configuration used by the Matching Service.

This module builds a single Loguru logger that:
  • Streams to stdout with pretty formatting (for kubectl logs / local dev)
  • Ships records to Datadog when DD_API_KEY is set
  • Intercepts the standard‑library ``logging`` calls so *all* third‑party
    libraries (FastAPI, Uvicorn, SQLAlchemy, etc.) are routed through Loguru
  • Disables Uvicorn’s built‑in dictConfig so it does not overwrite the setup
"""

from __future__ import annotations

import inspect
import logging
import os
import sys
from logging import StreamHandler

import uvicorn
from datadog_api_client.v2 import ApiClient, Configuration
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.model.content_encoding import ContentEncoding
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem
from loguru import logger as loguru_logger

###############################################################################
# Runtime configuration values
###############################################################################


class LogConfig:
    """Reads logging‑related environment variables once at import time."""

    def __init__(self) -> None:
        self.environment: str = os.getenv("ENVIRONMENT", "development").lower()
        self.service: str = os.getenv("SERVICE_NAME", "default_service_name")
        self.hostname: str = os.getenv("HOSTNAME", "unknown")
        self.loglevel: str = os.getenv(
            "LOGLEVEL", "DEBUG" if self.environment == "development" else "INFO"
        )
        # Most Datadog plans charge by volume – only send WARNING+ by default
        self.loglevel_dd: str = os.getenv("LOGLEVEL_DATADOG", "WARNING")


logconfig = LogConfig()

###############################################################################
# Handlers
###############################################################################


class InterceptHandler(logging.Handler):
    """Routes standard‑library *logging* calls into Loguru.

    Every ``logging.getLogger(__name__).info("msg")`` flowing through the
    Python logging framework is re‑emitted as a Loguru record so it inherits
    the same formatting / Datadog transport.  Adapted from the recipe in the
    Loguru documentation.
    """

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            # Translate builtin log levels (INFO, WARNING, …) into Loguru names
            level: str | int = loguru_logger.level(record.levelname).name
        except ValueError:
            # Custom / numeric levels – keep the integer so Loguru accepts it
            level = record.levelno

        # Find the original caller so Loguru can display *their* filename/line
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging_internal = filename == logging.__file__
            is_importlib_bootstrap = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging_internal or is_importlib_bootstrap):
                break
            frame = frame.f_back
            depth += 1

        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class DatadogHandler(StreamHandler):
    """Pushes Loguru records to Datadog Logs over HTTPS."""

    def __init__(self) -> None:  # noqa: D401
        super().__init__()
        # The Datadog client reads DD_SITE / DD_API_KEY from the environment
        configuration = Configuration()
        self.api_client = ApiClient(configuration)
        self.api_instance = LogsApi(self.api_client)

    def emit(self, record: "logging.LogRecord") -> None:  # noqa: D401
        log_message = self.format(record)
        log_level = record.levelname

        # Loguru stores contextual fields in record.extra – convert them to str
        extras: dict[str, str] = {}
        if getattr(record, "extra", None):
            for key, value in record.extra.items():
                try:
                    extras[key] = str(value)
                except Exception:  # noqa: BLE001
                    continue  # Skip values that cannot be stringified

        log: dict[str, str] = {
            "status": log_level,
            "ddsource": "loguru",
            "ddtags": f"level:{log_level},env:{logconfig.environment}",
            "message": log_message,
            "service": logconfig.service,
            "timestamp": str(record.created),
            "hostname": logconfig.hostname,
            **extras,
        }

        http_log_item = HTTPLogItem(**log)
        http_log = HTTPLog([http_log_item])

        # Datadog expects logs compressed (deflate)
        self.api_instance.submit_log(
            content_encoding=ContentEncoding.DEFLATE, body=http_log
        )


###############################################################################
# Public initialiser
###############################################################################


def init_logging():  # noqa: D401
    """Initialise Loguru *once* and return the configured logger."""

    # Prevent double‑configuration (e.g. gunicorn with ≥2 workers)
    if getattr(init_logging, "_configured", False):
        return loguru_logger

    try:
        ############################################################################
        # Build Loguru sinks
        ############################################################################
        loguru_logger.remove()  # Remove the default sink

        # Console sink (stdout) – always enabled
        loguru_logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS Z}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level> | <level>{extra}</level>",
            level=logconfig.loglevel,
        )

        # Datadog sink – only if an API key is present
        dd_api_key = os.getenv("DD_API_KEY")
        if dd_api_key:
            loguru_logger.add(DatadogHandler(), level=logconfig.loglevel_dd)
        else:
            loguru_logger.warning(
                "Datadog API key missing – logs will *not* be forwarded to DD"
            )

        ############################################################################
        # Funnel std‑lib logging into Loguru *and* disable Uvicorn’s dictConfig
        ############################################################################
        logging.basicConfig(
            handlers=[InterceptHandler()],  # Single funnel handler
            level=0,  # Let Loguru perform the level filtering
            force=True,  # Overwrite any handlers Uvicorn added on import
        )

        # Prevent Uvicorn from installing its own logging config later on
        uvicorn.config.LOGGING_CONFIG = None

        # Re‑enable propagation so its access/error loggers reach Loguru
        loguru_logger.enable("uvicorn")

        ############################################################################
        # Mark as configured and return
        ############################################################################
        init_logging._configured = True  # type: ignore[attr-defined]
        return loguru_logger

    except Exception as exc:  # noqa: BLE001
        # Absolute last‑chance fallback – plain console logging
        print(f"[LOGGING] Failed to initialise Loguru → falling back. Error: {exc}")
        loguru_logger.remove()
        loguru_logger.add(sys.stdout, format="{time} | {level} | {message}", level="DEBUG")
        return loguru_logger


# The logger instance used throughout the application
logger = init_logging()

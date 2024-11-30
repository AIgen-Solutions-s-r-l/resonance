# app/core/logging_config.py

import sys
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from loguru import logger


def setup_logging(service_name: str = "matching_service") -> None:
	"""
	Configure centralized logging for the entire service.

	Args:
		service_name: Name of the service for log identification
	"""
	# Remove default logger
	logger.remove()

	# Create logs directory if it doesn't exist
	log_dir = Path("logs")
	log_dir.mkdir(exist_ok=True)

	# Configure log format
	log_format = (
		"<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
		"<level>{level: <8}</level> | "
		f"<cyan>{service_name}</cyan> | "
		"<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
		"<level>{message}</level>"
	)

	# Add file logger
	logger.add(
		sink=log_dir / f"{service_name}.log",
		format=log_format,
		level="INFO",
		rotation="500 MB",
		retention="10 days",
		compression="zip",
		enqueue=True
	)

	# Add console logger
	logger.add(
		sink=sys.stdout,
		format=log_format,
		level="INFO",
		colorize=True
	)


def get_logger_context(**kwargs: Any) -> Dict[str, Any]:
	"""
	Create a context dictionary for structured logging.

	Args:
		**kwargs: Additional context key-value pairs

	Returns:
		Dict containing standard context fields plus any additional fields
	"""
	context = {
		"timestamp": datetime.utcnow().isoformat(),
		**kwargs
	}
	return context
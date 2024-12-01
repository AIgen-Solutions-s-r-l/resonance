# app/core/logging_config.py

import sys
import socket
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from loguru import logger


@dataclass
class LoggingConfig:
	"""Configuration for logging setup."""
	service_name: str
	log_level: str = "INFO"
	logstash_host: Optional[str] = None
	logstash_port: Optional[int] = None
	enable_file_logging: bool = True
	enable_console_logging: bool = True
	enable_logstash: bool = False
	log_rotation: str = "500 MB"
	log_retention: str = "10 days"
	environment: str = "development"


class TcpLogstashSink:
	"""TCP Sink for sending logs to Logstash with proper timestamp formatting."""

	def __init__(self, host: str, port: int, service_name: str, environment: str) -> None:
		"""
		Initialize Logstash sink.

		Args:
			host: Logstash host address
			port: Logstash port
			service_name: Name of the service
			environment: Environment name (e.g., development, production)
		"""
		self.host = host
		self.port = port
		self.service_name = service_name
		self.environment = environment

	@staticmethod
	def format_timestamp(dt: datetime) -> str:
		"""Format datetime to ISO8601 with milliseconds."""
		return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

	def __call__(self, message: Any) -> None:
		"""Process and send log message to Logstash."""
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect((self.host, self.port))

			record = message.record
			now = datetime.now(timezone.utc)
			timestamp = self.format_timestamp(now)

			# Create log data structure
			log_data = {
				"@timestamp": timestamp,
				"message": record["message"],
				"log": {
					"level": record["level"].name.lower(),
					"logger": record["module"],
					"origin": {
						"function": record["function"],
						"file": {
							"line": record["line"],
							"name": record["file"].name
						}
					}
				},
				"service": {
					"name": self.service_name,
					"type": "matching-service"
				},
				"event": {
					"kind": "event",
					"category": "matching",
					"type": "info",
					"created": timestamp
				},
				"process": {
					"pid": record["process"].id,
					"thread": {
						"id": record["thread"].id
					}
				},
				"labels": {
					"environment": self.environment
				},
				"type": "syslog-modern"
			}

			# Add extra fields from context
			if record["extra"]:
				log_data["labels"]["extra"] = record["extra"]

			# Add exception information if present
			if record["exception"] is not None:
				log_data["error"] = {
					"message": str(record["exception"]),
					"type": record["exception"].__class__.__name__,
					"stack_trace": record["exception"].traceback
				}

			# Send log to Logstash
			sock.sendall(json.dumps(log_data).encode() + b'\n')
			sock.close()

		except Exception as e:
			print(f"Error sending log to Logstash: {e}", file=sys.stderr)


def setup_logging(config: LoggingConfig) -> None:
	"""
	Configure centralized logging for the entire service.

	Args:
		config: Logging configuration parameters
	"""
	# Remove default logger
	logger.remove()

	# Configure log format for console and file
	log_format = (
		"<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
		"<level>{level: <8}</level> | "
		f"<cyan>{config.service_name}</cyan> | "
		"<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
		"<level>{message}</level>"
	)

	# Add file logger if enabled
	if config.enable_file_logging:
		log_dir = Path("logs")
		log_dir.mkdir(exist_ok=True)

		logger.add(
			sink=log_dir / f"{config.service_name}.log",
			format=log_format,
			level=config.log_level,
			rotation=config.log_rotation,
			retention=config.log_retention,
			compression="zip",
			enqueue=True
		)

	# Add console logger if enabled
	if config.enable_console_logging:
		logger.add(
			sink=sys.stdout,
			format=log_format,
			level=config.log_level,
			colorize=True
		)

	# Add Logstash logger if enabled
	if config.enable_logstash and config.logstash_host and config.logstash_port:
		tcp_sink = TcpLogstashSink(
			host=config.logstash_host,
			port=config.logstash_port,
			service_name=config.service_name,
			environment=config.environment
		)

		logger.add(
			sink=tcp_sink,
			level=config.log_level,
			serialize=True,
			enqueue=True,
			backtrace=True,
			diagnose=True,
			catch=True
		)


def test_logstash_connection(host: str, port: int) -> bool:
	"""
	Test connection to Logstash.

	Args:
		host: Logstash host address
		port: Logstash port

	Returns:
		bool: True if connection is successful, False otherwise
	"""
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect((host, port))
		timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

		test_msg = {
			"@timestamp": timestamp,
			"message": "Connection test",
			"log": {
				"level": "info"
			},
			"service": {
				"name": "matching-service-test"
			},
			"type": "syslog-modern"
		}
		sock.send(json.dumps(test_msg).encode() + b'\n')
		sock.close()
		return True
	except Exception as e:
		print(f"Logstash connection test failed: {e}")
		return False


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
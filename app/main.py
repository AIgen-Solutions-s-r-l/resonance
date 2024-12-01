# app/main.py

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from loguru import logger

from app.core.config import Settings
from app.core.logging_config import setup_logging, get_logger_context, LoggingConfig, test_logstash_connection
from app.core.rabbitmq_client import AsyncRabbitMQClient
from app.libs.job_matcher import JobMatcher

# Initialize settings and clients
try:
	settings = Settings()
	rabbitmq_client = AsyncRabbitMQClient(rabbitmq_url=settings.rabbitmq_url)
except Exception as e:
	logger.error(f"Failed to initialize service settings: {str(e)}")
	raise

settings = Settings()

# Configure logging
logging_config = LoggingConfig(
	service_name=settings.service_name,
	log_level=settings.log_level,
	logstash_host=settings.logstash_host,
	logstash_port=settings.logstash_port,
	enable_file_logging=True,
	enable_console_logging=True,
	enable_logstash=settings.enable_logstash,
	environment=settings.environment
)

# Initialize logging
setup_logging(logging_config)

# Test Logstash connection if enabled
if settings.enable_logstash:
	if test_logstash_connection(settings.logstash_host, settings.logstash_port):
		logger.info("Logstash connection successful")
	else:
		logger.warning("Logstash connection failed, continuing with local logging only")


async def process_resume_callback(message: Any) -> None:
	"""
	Process incoming resume messages from RabbitMQ.

	Args:
		message: The message received from RabbitMQ

	Raises:
		json.JSONDecodeError: If message body is not valid JSON
		Exception: For other processing errors
	"""
	try:
		context = get_logger_context(action="process_resume")
		resume = json.loads(message.body.decode('utf-8'))
		logger.info("Processing resume", context)

		matcher = JobMatcher(settings)
		jobs_to_apply = await matcher.process_job(resume)
		if jobs_to_apply:
			await rabbitmq_client.send_message(
				queue=settings.job_to_apply_queue,
				message=jobs_to_apply
			)
			context["jobs_found"] = len(jobs_to_apply)
			logger.success("Successfully processed resume and sent jobs", context)
		else:
			logger.warning("No matching jobs found for resume", context)

	except json.JSONDecodeError as e:
		context["error"] = str(e)
		logger.error("Invalid message format", context)
	except Exception as e:
		context["error"] = str(e)
		logger.error("Failed to process resume", context)
		raise


async def consume_task() -> None:
	"""
	Consume messages from the RabbitMQ queue.

	Raises:
		Exception: If message consumption fails
	"""
	try:
		context = get_logger_context(
			action="consume_task",
			queue=settings.apply_to_job_queue
		)
		logger.info("Starting message consumption", context)

		await rabbitmq_client.consume_messages(
			queue=settings.apply_to_job_queue,
			callback=process_resume_callback
		)
	except Exception as e:
		context["error"] = str(e)
		logger.error("Message consumption failed", context)
		raise


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""
	Handle application startup and shutdown.

	Args:
		app: FastAPI application instance
	"""
	context = get_logger_context(action="lifespan")

	try:
		logger.info("Starting application", context)
		await rabbitmq_client.connect()
		task = asyncio.create_task(consume_task())
		yield

		logger.info("Shutting down application", context)
		task.cancel()
		await rabbitmq_client.close_connection()

	except Exception as e:
		context["error"] = str(e)
		logger.error("Application lifecycle error", context)
		raise


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root() -> Dict[str, str]:
	"""
	Health check endpoint.

	Returns:
		Dict containing service status message
	"""
	context = get_logger_context(action="health_check")
	logger.info("Health check requested", context)
	return {"message": "Matching Service is running!"}


@app.get("/health")
async def health_check() -> Dict[str, str]:
	"""
	Detailed health check endpoint.

	Returns:
		Dict containing detailed service status

	Raises:
		HTTPException: If any service component is unhealthy
	"""
	try:
		context = get_logger_context(action="detailed_health_check")
		# Add checks for RabbitMQ and database connections
		if not rabbitmq_client.is_connected():
			raise HTTPException(status_code=503, detail="RabbitMQ connection is down")

		logger.info("Health check passed", context)
		return {
			"status": "healthy",
			"rabbitmq": "connected",
			"service": settings.service_name
		}
	except Exception as e:
		context["error"] = str(e)
		logger.error("Health check failed", context)
		raise HTTPException(status_code=503, detail=str(e))

# app/services/message_consumer.py

import json
from typing import TypedDict, Optional, Dict, Any, NoReturn
from dataclasses import dataclass
from loguru import logger
import aio_pika

from app.core.logging_config import get_logger_context


class ResumeMessage(TypedDict):
	"""Type definition for expected message format."""
	resume: str
	metadata: Optional[Dict[str, Any]]


@dataclass
class MessageContext:
	"""Data class for message processing context."""
	message_id: str
	content_type: Optional[str]
	action: str = "process_message"
	status: str = "received"
	resume_preview: Optional[str] = None
	error: Optional[str] = None
	error_type: Optional[str] = None


class MessageProcessingError(Exception):
	"""Base exception for message processing errors."""

	def __init__(self, message: str, context: Dict[str, Any]) -> None:
		self.context = context
		super().__init__(message)


class InvalidMessageFormat(MessageProcessingError):
	"""Raised when message format is invalid."""
	pass


class MessageValidationError(MessageProcessingError):
	"""Raised when message validation fails."""
	pass


def create_message_context(
		message: aio_pika.IncomingMessage,
		**kwargs: Any
) -> MessageContext:
	"""
    Create a message context object for logging.

    Args:
        message: The incoming RabbitMQ message
        **kwargs: Additional context parameters

    Returns:
        MessageContext object with message details
    """
	return MessageContext(
		message_id=str(message.message_id or "unknown"),
		content_type=message.content_type,
		**kwargs
	)


def validate_message(data: Dict[str, Any]) -> ResumeMessage:
	"""
    Validate and convert message data to typed format.

    Args:
        data: Raw message data

    Returns:
        ResumeMessage: Validated message data

    Raises:
        MessageValidationError: If message format is invalid
    """
	if not isinstance(data, dict):
		raise MessageValidationError(
			"Message data must be a dictionary",
			{"received_type": type(data).__name__}
		)

	if "resume" not in data:
		raise MessageValidationError(
			"Message must contain 'resume' field",
			{"received_fields": list(data.keys())}
		)

	if not isinstance(data["resume"], str):
		raise MessageValidationError(
			"Resume field must be a string",
			{"received_type": type(data["resume"]).__name__}
		)

	return ResumeMessage(
		resume=data["resume"],
		metadata=data.get("metadata")
	)


async def handle_processing_error(
		error: Exception,
		context: MessageContext
) -> NoReturn:
	"""
    Handle processing errors with proper logging.

    Args:
        error: The exception that occurred
        context: Current message context

    Raises:
        The original exception after logging
    """
	context.status = "failed"
	context.error = str(error)

	log_context = get_logger_context(**context.__dict__)
	logger.error(f"Message processing failed: {str(error)}", log_context)
	raise error


async def process_message(message: aio_pika.IncomingMessage) -> None:
	"""
    Process incoming messages from RabbitMQ queue.

    Args:
        message: Incoming message from RabbitMQ

    Raises:
        InvalidMessageFormat: If message cannot be decoded as JSON
        MessageValidationError: If message format is invalid
        MessageProcessingError: For other processing errors
    """
	context = create_message_context(message)

	try:
		# Decode message body
		try:
			raw_data = json.loads(message.body.decode())
		except json.JSONDecodeError as e:
			raise InvalidMessageFormat(
				"Failed to decode JSON message",
				{"error": str(e)}
			)

		# Validate message format
		typed_message: ResumeMessage = validate_message(raw_data)

		# Update context with resume preview
		resume_text = typed_message["resume"]
		context.resume_preview = (
			f"{resume_text[:30]}..." if len(resume_text) > 30 else resume_text
		)

		log_context = get_logger_context(**context.__dict__)
		logger.info("Processing resume message", log_context)

		# Process the message
		# Add your message processing logic here
		# For example:
		# await process_resume(typed_message)

		# Log successful processing
		context.status = "processed"
		log_context = get_logger_context(**context.__dict__)
		logger.success("Successfully processed message", log_context)

	except (InvalidMessageFormat, MessageValidationError) as e:
		context.error_type = e.__class__.__name__
		await handle_processing_error(e, context)

	except Exception as e:
		context.error_type = "unexpected_error"
		await handle_processing_error(e, context)

# Example usage:
# async def start_consumer(queue_name: str) -> None:
#     rabbitmq_client = AsyncRabbitMQClient(settings.rabbitmq_url)
#     await rabbitmq_client.connect()
#     await rabbitmq_client.consume_messages(queue_name, process_message)
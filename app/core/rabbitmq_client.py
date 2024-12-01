# app/core/rabbitmq_client.py

import json
from typing import Any, Optional, Callable, Dict

import aio_pika
from loguru import logger

from app.core.logging_config import get_logger_context


class AsyncRabbitMQClient:
	def __init__(self, rabbitmq_url: str):
		"""
        Initialize RabbitMQ client.

        Args:
            rabbitmq_url: Connection URL for RabbitMQ
        """
		self.rabbitmq_url = rabbitmq_url
		self.connection: Optional[aio_pika.Connection] = None
		self.channel: Optional[aio_pika.Channel] = None

	def is_connected(self) -> bool:
		"""Check if client is connected to RabbitMQ."""
		return self.connection is not None and not self.connection.is_closed

	async def connect(self) -> None:
		"""Establish an asynchronous connection to RabbitMQ using aio_pika."""
		try:
			context = get_logger_context(action="connect_rabbitmq")
			logger.info("Connecting to RabbitMQ...", context)

			self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
			self.channel = await self.connection.channel()

			context["status"] = "connected"
			logger.info("RabbitMQ connection and channel initialized", context)
		except Exception as e:
			context = get_logger_context(
				action="connect_rabbitmq",
				error=str(e),
				status="failed"
			)
			logger.error("Failed to connect to RabbitMQ", context)
			raise

	async def declare_queue(self, queue_name: str) -> aio_pika.Queue:
		"""
        Declare a queue to ensure it exists.

        Args:
            queue_name: Name of the queue to declare

        Returns:
            aio_pika.Queue object
        """
		try:
			queue = await self.channel.declare_queue(queue_name, durable=False)
			context = get_logger_context(
				action="declare_queue",
				queue=queue_name,
				status="success"
			)
			logger.debug("Queue declared", context)
			return queue
		except Exception as e:
			context = get_logger_context(
				action="declare_queue",
				queue=queue_name,
				error=str(e),
				status="failed"
			)
			logger.error("Failed to declare queue", context)
			raise

	async def send_message(self, queue: str, message: Dict[str, Any]) -> None:
		"""
        Asynchronously send a message to the specified queue.

        Args:
            queue: Queue name to send message to
            message: Message content as dictionary
        """

		try:
			if not self.channel:
				await self.connect()

			await self.declare_queue(queue)
			message_body = json.dumps(message).encode()

			await self.channel.default_exchange.publish(
				aio_pika.Message(
					body=message_body,
					delivery_mode=aio_pika.DeliveryMode.PERSISTENT
				),
				routing_key=queue
			)

			context = get_logger_context(
				action="send_message",
				queue=queue,
				message_size=len(message_body),
				status="success"
			)
			logger.info("Message sent to queue", context)

		except Exception as e:
			context = get_logger_context(
				action="send_message",
				queue=queue,
				error=str(e),
				status="failed"
			)
			logger.error("Failed to send message", context)
			raise

	async def consume_messages(
			self,
			queue: str,
			callback: Callable[[aio_pika.IncomingMessage], Any]
	) -> None:
		"""
        Consume messages asynchronously from the queue.

        Args:
            queue: Queue name to consume from
            callback: Async callback function to process messages
        """
		try:
			if not self.channel:
				await self.connect()

			queue_obj = await self.declare_queue(queue)
			context = get_logger_context(
				action="consume_messages",
				queue=queue,
				status="started"
			)
			logger.info("Starting message consumption", context)

			async with queue_obj.iterator() as queue_iter:
				async for message in queue_iter:
					try:
						async with message.process():
							await callback(message)
							context = get_logger_context(
								action="process_message",
								queue=queue,
								status="success"
							)
							logger.debug("Message processed", context)
					except Exception as e:
						context = get_logger_context(
							action="process_message",
							queue=queue,
							error=str(e),
							status="failed"
						)
						logger.error("Failed to process message", context)

		except Exception as e:
			context = get_logger_context(
				action="consume_messages",
				queue=queue,
				error=str(e),
				status="failed"
			)
			logger.error("Failed to consume messages", context)
			raise

	async def close_connection(self) -> None:
		"""Gracefully close the connection to RabbitMQ."""
		try:
			if self.channel:
				await self.channel.close()
				context = get_logger_context(
					action="close_connection",
					component="channel",
					status="success"
				)
				logger.info("RabbitMQ channel closed", context)

			if self.connection:
				await self.connection.close()
				context = get_logger_context(
					action="close_connection",
					component="connection",
					status="success"
				)
				logger.info("RabbitMQ connection closed", context)

		except Exception as e:
			context = get_logger_context(
				action="close_connection",
				error=str(e),
				status="failed"
			)
			logger.error("Error closing RabbitMQ connection", context)

		finally:
			self.channel = None
			self.connection = None
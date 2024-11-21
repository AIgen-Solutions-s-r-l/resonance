import json
import logging

import aio_pika

logging.basicConfig(level=logging.INFO)


class AsyncRabbitMQClient:
    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self.logger = logging.getLogger(__name__)

    async def connect(self) -> None:
        """Establish an asynchronous connection to RabbitMQ using aio_pika."""
        logging.info("Connecting to RabbitMQ...")
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        logging.info("RabbitMQ connection and channel initialized.")

    async def declare_queue(self, queue_name: str) -> aio_pika.Queue:
        """Declare a queue to ensure it exists."""
        return await self.channel.declare_queue(queue_name, durable=False)

    async def send_message(self, queue: str, message: dict) -> None:
        """Asynchronously send a message to the specified queue."""
        if not self.channel:
            await self.connect()
        await self.declare_queue(queue)
        message_body = json.dumps(message).encode()
        await self.channel.default_exchange.publish(
            aio_pika.Message(body=message_body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=queue
        )
        logging.info(f"Message sent to queue '{queue}': {message}")

    async def consume_messages(self, queue: str, callback):
        """Consume messages asynchronously from the queue."""
        if not self.channel:
            await self.connect()
        queue_obj = await self.declare_queue(queue)
        async with queue_obj.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await callback(message)
                    logging.info("Message processed")

    async def close_connection(self) -> None:
        """
        Gracefully close the connection to RabbitMQ.
        """
        try:
            if self.channel:
                await self.channel.close()
                self.logger.info("RabbitMQ channel closed.")
            if self.connection:
                await self.connection.close()
                self.logger.info("RabbitMQ connection closed.")
        except Exception as e:
            self.logger.error(f"Error closing RabbitMQ connection: {e}")
        finally:
            self.channel = None
            self.connection = None

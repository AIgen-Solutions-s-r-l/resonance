import aio_pika
import asyncio
import json
import logging

class AsyncRabbitMQClient:
    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None

    async def connect(self) -> None:
        """Establish an asynchronous connection to RabbitMQ using aio_pika."""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        logging.info("RabbitMQ connection and channel initialized.")

    async def declare_queue(self, queue_name: str) -> aio_pika.Queue:
        queue = await self.channel.declare_queue(queue_name, durable=True)
        logging.info(f"Declared queue '{queue_name}' with durability set to True.")
        return queue

    async def send_message(self, queue: str, message: dict):
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
        logging.info(f"Started consuming messages from queue '{queue}'")

        async with queue_obj.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await callback(message)

    async def close_connection(self):
        if self.connection:
            await self.connection.close()
            logging.info("RabbitMQ connection closed.")
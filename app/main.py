import logging
import asyncio
import json
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import Settings
from app.core.rabbitmq_client import AsyncRabbitMQClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
settings = Settings()
rabbitmq_client = AsyncRabbitMQClient(rabbitmq_url=settings.rabbitmq_url)

async def process_resume_callback(message):
    """Process the resume received from the queue and send back job matches."""
    resume = json.loads(message.body.decode('utf-8'))
    logging.info(f"Received resume: {resume}")

    # Simulate finding jobs for the resume
    jobs_to_apply = ["job1", "job2", "job3"]

    # Send the list of jobs back to the job_to_apply_queue
    await rabbitmq_client.send_message(queue=settings.job_to_apply_queue, message=jobs_to_apply)

async def consume_task():
    await rabbitmq_client.consume_messages(queue=settings.apply_to_job_queue, callback=process_resume_callback)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await rabbitmq_client.connect()
    task = asyncio.create_task(consume_task())
    yield
    task.cancel()  # Cancel the task when shutting down
    await rabbitmq_client.close_connection()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Matching Service is running!"}
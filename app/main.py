import logging
import asyncio
import json
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import Settings
from app.core.rabbitmq_client import AsyncRabbitMQClient
from app.services.lib_document_finder import match_cv

logging.basicConfig(level=logging.INFO)
settings = Settings()
rabbitmq_client = AsyncRabbitMQClient(rabbitmq_url=settings.rabbitmq_url)

async def process_resume_callback(message):
    resume = json.loads(message.body.decode('utf-8'))
    logging.info(f"Received resume: {resume}")

    # jobs_to_apply = ["job1", "job2", "job3"]
    jobs_to_apply = match_cv.process_job(resume)
    await rabbitmq_client.send_message(queue=settings.job_to_apply_queue, message=jobs_to_apply)
    # logging.info(f"Jobs to apply sent to job_to_apply_queue {jobs_to_apply}")

async def consume_task():
    await rabbitmq_client.consume_messages(queue=settings.apply_to_job_queue, callback=process_resume_callback)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await rabbitmq_client.connect()
    task = asyncio.create_task(consume_task())
    yield
    task.cancel()
    await rabbitmq_client.close_connection()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Matching Service is running!"}

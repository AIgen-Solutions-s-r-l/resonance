import sys
import os
# import psycopg
import asyncio
import json
from langchain.embeddings.openai import OpenAIEmbeddings
from app.core.config import Settings
from app.core.rabbitmq_client import RabbitMQClient
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.db import SessionLocal

# Define your PostgreSQL connection string
DATABASE_URL = "postgresql+psycopg2://testuser:testpassword@127.0.0.1:5432/hawk"

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Initialize settings and RabbitMQ client
settings = Settings()
rabbitmq_client = RabbitMQClient(settings.rabbitmq_url)
rabbitmq_client.connect()
rabbitmq_client.start()

# Initialize OpenAI embeddings
openai_api_key = "sk-tSeHC_UQYlf-5gaww6ZZKYrl8Mg2F_lqZ9TamxtfdMT3BlbkFJCrcgPy_EN-4pwJk8DKMhYV6PYrKoTkHjgRJ87IobkA"
os.environ["OPENAI_API_KEY"] = openai_api_key
embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Connect to the PostgreSQL database
conn = psycopg.connect(
    dbname="hawk",
    user="testuser",
    password="testpassword",
    host="127.0.0.1",
    port="5432",
    autocommit=True
)
cursor = conn.cursor()

async def process_job(job_data: dict):
    """
    Process the CV job when triggered by RabbitMQ.

    Args:
        job_data (dict): Data received from the RabbitMQ message.
    """
    cv_text = job_data.get("cv_text")

    if not cv_text:
        print(f"CV text not found for job {job_id}. Skipping.")
        return

    # Step 5: Create the embedding for the CV
    cv_embedding = embedding_model.embed_documents([cv_text])[0]
    cv_embedding_str = "[" + ",".join(map(str, cv_embedding)) + "]"

    # Step 6: Execute the SQL query to find the top job descriptions
    query = """
    SELECT job_description, embedding <=> %s::vector AS distance
    FROM job_descriptions
    ORDER BY distance
    LIMIT 50;
    """
    cursor.execute(query, (cv_embedding_str,))
    top_job_descriptions = cursor.fetchall()

    # Step 7: Write the ranked job descriptions to output files
    output_directory = os.path.join(os.getcwd(), "OutputJobDescriptions")
    os.makedirs(output_directory, exist_ok=True)

    for idx, (job_desc_text, distance) in enumerate(top_job_descriptions):
        output_filename = f"ranked_job_description_{idx + 1}.md"
        output_filepath = os.path.join(output_directory, output_filename)

        with open(output_filepath, "w", encoding="utf-8") as output_file:
            output_file.write("### Job Description\n")
            output_file.write(job_desc_text)
            output_file.write("\n")
            output_file.write("-" * 50 + "\n")
            output_file.write("### Cosine Distance\n")
            output_file.write(f"{distance:.4f}\n")
            print(f"Created {output_filename} with distance {distance:.4f}")

    # Step 8: Send notification to RabbitMQ once processing is done
    notify_apply([job[0] for job in top_job_descriptions])

def notify_apply(jobs: list[str]):
    """
    Publishes a message to the career_docs queue after a job is processed.

    Args:
        jobs (list): List of job descriptions.
        job_id (str): The ID of the processed job.
    """
    message = {
        "jobs": jobs,
    }
    try:
        rabbitmq_client.publish_message(queue=settings.jobs_to_apply_queue, message=message)
        print(f"Notification sent for job descriptions.")
    except Exception as e:
        print(f"Failed to send notification for job : {e}")

async def rabbitmq_callback(ch, method, properties, body):
    """
    Callback function to process incoming RabbitMQ messages.

    Args:
        ch: Channel.
        method: Method.
        properties: Properties of the message.
        body: The actual message.
    """
    try:
        message = json.loads(body.decode())
        print(f"Received message: {message}")
        await process_job(message)  # Trigger job processing
    except Exception as e:
        print(f"Error processing RabbitMQ message: {e}")

def start_rabbitmq_listener():
    """
    Start the RabbitMQ listener to listen for incoming job messages.
    """
    queue_name = "job_processing_queue"  # This is the queue to listen to for job data
    rabbitmq_client.subscribe(queue=queue_name, callback=rabbitmq_callback)

# Start listening for messages from RabbitMQ
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_rabbitmq_listener())
    loop.run_forever()

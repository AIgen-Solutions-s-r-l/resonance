import os
import logging
import asyncpg
import asyncio
from app.core.config import Settings
from langchain.embeddings.openai import OpenAIEmbeddings
from app.core.rabbitmq_client import AsyncRabbitMQClient

# Initialize logging config
logging.basicConfig(level=logging.INFO)

# Initialize settings and RabbitMQ client
settings = Settings()

async def initialize_rabbit():
    rabbitmq_client = await AsyncRabbitMQClient(
            rabbitmq_url=settings.rabbitmq_url,
            queue=settings.job_to_apply_queue
        )
    await rabbitmq_client.connect()

# Initialize OpenAI embeddings
openai_api_key = "sk-tSeHC_UQYlf-5gaww6ZZKYrl8Mg2F_lqZ9TamxtfdMT3BlbkFJCrcgPy_EN-4pwJk8DKMhYV6PYrKoTkHjgRJ87IobkA"
os.environ["OPENAI_API_KEY"] = openai_api_key
embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

# Connect to the PostgreSQL database asynchronously
async def connect_db():
    conn = await asyncpg.connect(
        user="testuser",
        password="testpassword",
        database="matching",
        host="127.0.0.1",
        port="5432"
    )
    return conn

async def process_job(resume: str):
    """
    Process the CV job when triggered by RabbitMQ.

    Args:
        resume (str): CV text to process.
    """
    logging.info(f"Start process job")
    
    cv_text = str(resume)
    logging.info(f"Starting embedding of cv...")

    # Step 5: Create the embedding for the CV
    cv_embedding = embedding_model.embed_documents([cv_text])[0]
    cv_embedding_str = "[" + ",".join(map(str, cv_embedding)) + "]"
    logging.info(f"Finished embedding of cv: {cv_embedding_str}")

    logging.info(f"Starting query db for jobs")
    
    # Step 6: Execute the SQL query to find the top job descriptions
    query = """
    SELECT description, embedding <=> %s::vector AS distance
    FROM Jobs
    ORDER BY distance
    LIMIT 50;
    """
    
    # Use asyncpg to execute the query
    conn = await connect_db()
    top_job_descriptions = await conn.fetch(query, cv_embedding_str)
    await conn.close()

    logging.info(f"Finished query db for jobs")
    
    # Step 7: Write the ranked job descriptions to output files
    output_directory = os.path.join(os.getcwd(), "OutputJobDescriptions")
    os.makedirs(output_directory, exist_ok=True)
    logging.info(f"Creating message with jobs")

    descriptions = []
    for idx, (job_desc_text, distance) in enumerate(top_job_descriptions):
        descriptions.append(job_desc_text)
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
            
    logging.info(f"Finished creating message with jobs descriptions: {descriptions}")
    return descriptions

# Example async job processing loop (replace with actual RabbitMQ integration)
async def main():
    # Initialize RabbitMQ and process a sample job
    await initialize_rabbit()
    resume = "Sample CV text"
    descriptions = await process_job(resume)
    print(descriptions)

# Run the async loop
if __name__ == "__main__":
    asyncio.run(main())

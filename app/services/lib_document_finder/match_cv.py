import os
import logging
import psycopg
from typing import List, Tuple
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
    rabbitmq_client.connect()

# Initialize OpenAI embeddings
openai_api_key = "sk-tSeHC_UQYlf-5gaww6ZZKYrl8Mg2F_lqZ9TamxtfdMT3BlbkFJCrcgPy_EN-4pwJk8DKMhYV6PYrKoTkHjgRJ87IobkA"
os.environ["OPENAI_API_KEY"] = openai_api_key
embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

# Connect to the PostgreSQL database
conn = psycopg.connect(
    dbname="matching",
    user="testuser",
    password="testpassword",
    host="127.0.0.1",
    port="5432",
    autocommit=True
)

def get_top_jobs_by_multiple_metrics(cursor, cv_embedding: List[float], limit: int = 50) -> List[Tuple]:
    """
    Get top jobs using multiple similarity metrics.
    
    Args:
        cursor: Database cursor
        cv_embedding: The embedding vector of the CV
        limit: Number of results to return
        
    Returns:
        List of tuples containing job descriptions and their similarity scores
    """
    
    query = """
    WITH combined_scores AS (
        SELECT 
            description,
            job_id,
            embedding <-> %s::vector as l2_distance,
            embedding <=> %s::vector as cosine_distance,
            -(embedding <#> %s::vector) as inner_product
        FROM "Jobs"
    ),
    normalized_scores AS (
        SELECT 
            description,
            job_id,
            (1 - (l2_distance - MIN(l2_distance) OVER()) / 
                NULLIF(MAX(l2_distance) OVER() - MIN(l2_distance) OVER(), 0)) * 0.4 +
            (1 - (cosine_distance - MIN(cosine_distance) OVER()) / 
                NULLIF(MAX(cosine_distance) OVER() - MIN(cosine_distance) OVER(), 0)) * 0.4 +
            (inner_product - MIN(inner_product) OVER()) / 
                NULLIF(MAX(inner_product) OVER() - MIN(inner_product) OVER(), 0) * 0.2 
            as combined_score
        FROM combined_scores
    )
    SELECT 
        description,
        combined_score
    FROM normalized_scores
    ORDER BY combined_score DESC
    LIMIT %s;
    """
    
    cursor.execute(query, (cv_embedding, cv_embedding, cv_embedding, limit))
    return cursor.fetchall()

def write_job_descriptions(descriptions: List[Tuple], output_directory: str):
    """
    Write job descriptions to output files.
    
    Args:
        descriptions: List of tuples containing job descriptions and scores
        output_directory: Directory to write the files to
    """
    os.makedirs(output_directory, exist_ok=True)
    
    for idx, (job_desc_text, combined_score) in enumerate(descriptions):
        output_filename = f"ranked_job_description_{idx + 1}.md"
        output_filepath = os.path.join(output_directory, output_filename)
        
        with open(output_filepath, "w", encoding="utf-8") as output_file:
            output_file.write("### Job Description\n")
            output_file.write(job_desc_text)
            output_file.write("\n")
            output_file.write("-" * 50 + "\n")
            output_file.write("### Combined Similarity Score\n")
            output_file.write(f"{combined_score:.4f}\n")

def process_job(resume: str):
    """
    Process the CV job when triggered by RabbitMQ.
    Args:
        resume (str): The resume text to process
    Returns:
        List of job descriptions
    """
    try:
        logging.info("Start process job")
        cv_text = resume
        
        logging.info("Starting embedding of cv...")
        with conn.cursor() as cursor:
            # Create the embedding for the CV
            cv_embedding = embedding_model.embed_documents([cv_text])[0]
            logging.info("Finished embedding of cv")
            
            logging.info("Starting query db for jobs")
            # Get top job descriptions using multiple similarity metrics
            top_job_descriptions = get_top_jobs_by_multiple_metrics(cursor, cv_embedding)
            logging.info("Finished query db for jobs")
            
            # Write the ranked job descriptions to output files
            output_directory = os.path.join(os.getcwd(), "OutputJobDescriptions")
            write_job_descriptions(top_job_descriptions, output_directory)
            
            logging.info("Creating message with jobs")
            descriptions = [job_desc for job_desc, _ in top_job_descriptions]
            logging.info(f"Finished creating message with jobs descriptions")
            
            return descriptions
            
    except Exception as e:
        raise Exception(f"Error processing job: {e}")
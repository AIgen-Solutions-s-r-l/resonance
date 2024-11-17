import os
import psycopg
from openai import OpenAI
from pgvector.psycopg import register_vector

# Step 1: Set up OpenAI API Key
openai_api_key = "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"
os.environ["OPENAI_API_KEY"] = openai_api_key

# Step 2: Initialize OpenAI client
client = OpenAI()

# Step 3: Hard-code job descriptions
job_descriptions = [
    """
    Tech Innovators Inc. is seeking a Senior Data Scientist with proficiency in Python, deep learning frameworks, and cloud platforms such as AWS and Azure. The ideal candidate should have a background in deploying machine learning models to production environments and a strong understanding of algorithms.
    """,
    """
    DataVision is hiring a Junior Data Analyst with experience in data wrangling, visualization, and basic machine learning. Familiarity with Python, Pandas, and Excel is required, and candidates should be comfortable working with large datasets to derive actionable insights.
    """,
    """
    CloudCorp is looking for a Senior Machine Learning Engineer with expertise in Python, TensorFlow, PyTorch, and large-scale machine learning systems. The ideal candidate should have a proven track record in designing and deploying machine learning models at scale in cloud environments.
    """,
    """
    AI Solutions seeks a Software Engineer with experience in building AI-powered applications. The candidate should be proficient in Python, Java, and C++, with a strong foundation in AI algorithms, data structures, and cloud computing. Experience with both backend and frontend development is a plus.
    """
]

# Step 4: Embed the job descriptions using OpenAI
response = client.embeddings.create(input=job_descriptions, model='text-embedding-ada-002')
embeddings = [v.embedding for v in response.data]

# Step 5: Connect to PostgreSQL and insert data
conn = psycopg.connect(dbname="hawk", user="user", password="pass", host="127.0.0.1", port="5432", autocommit=True)

# Register the pgvector extension
register_vector(conn)

# Create a cursor for executing SQL commands
cursor = conn.cursor()

# Ensure the table exists. You can use the following SQL schema to create it:
cursor.execute("""
CREATE TABLE IF NOT EXISTS job_descriptions (
    id bigserial PRIMARY KEY,
    job_description text,
    embedding vector(1536)  -- Assuming OpenAI's embedding has dimension 1536
);
""")

# Step 6: Insert the job descriptions and embeddings into the table
insert_sql = """
INSERT INTO job_descriptions (job_description, embedding)
VALUES (%s, %s);
"""

for job_desc, embedding in zip(job_descriptions, embeddings):
    cursor.execute(insert_sql, (job_desc, embedding))

# Close the cursor and the connection
cursor.close()
conn.close()

print("Job descriptions and embeddings have been inserted into the database.")

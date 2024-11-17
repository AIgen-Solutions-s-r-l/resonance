import os
import psycopg
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document

# Step 1: Set up OpenAI API Key
openai_api_key = "sk-tSeHC_UQYlf-5gaww6ZZKYrl8Mg2F_lqZ9TamxtfdMT3BlbkFJCrcgPy_EN-4pwJk8DKMhYV6PYrKoTkHjgRJ87IobkA"
os.environ["OPENAI_API_KEY"] = openai_api_key

# Step 2: Initialize OpenAI embeddings
embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

# Step 3: Connect to the PostgreSQL database
conn = psycopg.connect(dbname="hawk", user="user", password="pass", host="127.0.0.1", port="5432", autocommit=True)
cursor = conn.cursor()

# Step 4: Retrieve the CV text from the database
cursor.execute("SELECT cv_text FROM cvs WHERE cv_id = 1;")  # Retrieve CV (modify the query as needed)
cv_text = cursor.fetchone()[0]

# Step 5: Create the Document for the CV
cv_document = Document(page_content=cv_text)

# Step 6: Embed the CV
cv_embedding = embedding_model.embed_documents([cv_text])[0]

# Step 7: Query the database for the closest job descriptions
query = """
    SELECT job_description
    FROM job_descriptions
    ORDER BY embedding <-> %s  -- Calculate the distance between CV embedding and job description embeddings
    LIMIT 4;  -- Get the first 4 closest matches
"""
cursor.execute(query, (cv_embedding,))
job_descriptions = cursor.fetchall()

# Step 8: Display the closest job descriptions
for idx, job_desc in enumerate(job_descriptions, 1):
    print(f"Job Description {idx}:")
    print(job_desc[0])
    print("="*50)

# Close the connection
cursor.close()
conn.close()

print("Top 4 closest job descriptions have been retrieved.")

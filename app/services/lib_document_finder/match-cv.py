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
conn = psycopg.connect(
    dbname="hawk",
    user="user",
    password="pass",
    host="127.0.0.1",
    port="5432",
    autocommit=True
)
cursor = conn.cursor()

# Step 4: Retrieve the CV text from the database
# cursor.execute("SELECT cv_text FROM cvs WHERE cv_id = 1;")
# cv_text = cursor.fetchone()[0]
cv_text = """
John Doe is an experienced data scientist with a strong background in machine learning, deep learning, and cloud technologies. He has worked extensively with Python, TensorFlow, PyTorch, and AWS. John has a PhD in Computer Science and has published several papers on AI and machine learning algorithms. He has also led teams in deploying scalable ML models in production environments.
"""

# Step 5: Create the embedding for the CV
cv_embedding = embedding_model.embed_documents([cv_text])[0]

# Convert cv_embedding to a string format suitable for SQL
cv_embedding_str = "[" + ",".join(map(str, cv_embedding)) + "]"

# Step 6: Execute the SQL query to find the top 4 job descriptions
query = """
SELECT job_description, embedding <#> %s::vector AS distance
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

    # Write the job description and distance to file
    with open(output_filepath, "w", encoding="utf-8") as output_file:
        output_file.write("### Job Description\n")
        output_file.write(job_desc_text)
        output_file.write("\n")
        output_file.write("-" * 50 + "\n")
        output_file.write("### Cosine Distance\n")
        output_file.write(f"{distance:.4f}\n")
        print(f"Created {output_filename} with distance {distance:.4f}")

print("Top 4 job descriptions have been ranked and saved to the OutputJobDescriptions folder.")
import os
import psycopg
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
# from pgvector import Vector
from sklearn.metrics.pairwise import cosine_similarity

# Step 1: Set up OpenAI API Key
openai_api_key = "sk-tSeHC_UQYlf-5gaww6ZZKYrl8Mg2F_lqZ9TamxtfdMT3BlbkFJCrcgPy_EN-4pwJk8DKMhYV6PYrKoTkHjgRJ87IobkA"
os.environ["OPENAI_API_KEY"] = openai_api_key

# Step 2: Initialize OpenAI embeddings
embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

# Step 3: Connect to the PostgreSQL database
conn = psycopg.connect(dbname="hawk", user="user", password="pass", host="127.0.0.1", port="5432", autocommit=True)
cursor = conn.cursor()

# # Step 4: Retrieve the CV and job descriptions from the database
cursor.execute("SELECT cv_text FROM cvs WHERE cv_id = 1;")  # Retrieve the CV (you can modify the query)
cv_text = cursor.fetchone()[0]

cursor.execute("SELECT job_description FROM job_descriptions;")  # Retrieve all job descriptions
job_descriptions = cursor.fetchall()


# Hard-code the CV text (a single CV)
cv_text = """
John Doe is an experienced data scientist with a strong background in machine learning, deep learning, and cloud technologies. He has worked extensively with Python, TensorFlow, PyTorch, and AWS. John has a PhD in Computer Science and has published several papers on AI and machine learning algorithms. He has also led teams in deploying scalable ML models in production environments.
"""

# Hard-code the job descriptions (multiple job descriptions)
# job_descriptions = [
#     """
#     Tech Innovators Inc. is seeking a Senior Data Scientist with proficiency in Python, deep learning frameworks, and cloud platforms such as AWS and Azure. The ideal candidate should have a background in deploying machine learning models to production environments and a strong understanding of algorithms.
#     """,
#     """
#     DataVision is hiring a Junior Data Analyst with experience in data wrangling, visualization, and basic machine learning. Familiarity with Python, Pandas, and Excel is required, and candidates should be comfortable working with large datasets to derive actionable insights.
#     """,
#     """
#     CloudCorp is looking for a Senior Machine Learning Engineer with expertise in Python, TensorFlow, PyTorch, and large-scale machine learning systems. The ideal candidate should have a proven track record in designing and deploying machine learning models at scale in cloud environments.
#     """,
#     """
#     AI Solutions seeks a Software Engineer with experience in building AI-powered applications. The candidate should be proficient in Python, Java, and C++, with a strong foundation in AI algorithms, data structures, and cloud computing. Experience with both backend and frontend development is a plus.
#     """
# ]


# Step 5: Create the Document for the CV
cv_document = Document(page_content=cv_text)

# Step 6: Create embeddings for the CV and job descriptions
cv_embedding = embedding_model.embed_documents([cv_text])[0]

job_description_embeddings = []
for job_desc in job_descriptions:
    job_desc_text = job_desc[0]
    # job_desc_text = job_desc
    job_desc_embedding = embedding_model.embed_documents([job_desc_text])[0]
    job_description_embeddings.append((job_desc_text, job_desc_embedding))

# Step 7: Create a FAISS vector store for the job descriptions
documents = [Document(page_content=job_desc[0]) for job_desc in job_descriptions]
vector_store = FAISS.from_documents(documents, embedding_model)

# Step 8: Rank the job descriptions by cosine similarity to the CV
ranked_job_descriptions = []
for job_desc_text, job_desc_embedding in job_description_embeddings:
    cosine_sim = cosine_similarity([cv_embedding], [job_desc_embedding])[0][0]
    ranked_job_descriptions.append((job_desc_text, cosine_sim))

# Step 9: Sort job descriptions by cosine similarity in descending order
ranked_job_descriptions = sorted(ranked_job_descriptions, key=lambda x: x[1], reverse=True)

# Step 10: Write the ranked job descriptions to output files
output_directory = os.path.join(os.getcwd(), "OutputJobDescriptions")
os.makedirs(output_directory, exist_ok=True)

for idx, (job_desc, similarity) in enumerate(ranked_job_descriptions):
    output_filename = f"ranked_job_description_{idx + 1}.md"
    output_filepath = os.path.join(output_directory, output_filename)

    # Write the job description and similarity score to file
    with open(output_filepath, "w", encoding="utf-8") as output_file:
        output_file.write("### Job Description\n")
        output_file.write(job_desc)
        output_file.write("\n")
        output_file.write("-" * 50 + "\n")
        output_file.write("### Similarity Score\n")
        output_file.write(f"Cosine Similarity: {similarity:.4f}\n")
        print(f"Created {output_filename} with similarity {similarity:.4f}")

print("All job descriptions have been ranked and saved to the OutputJobDescriptions folder.")

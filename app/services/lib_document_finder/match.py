import os

from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

from textblob import TextBlob
from textstat.textstat import textstatistics

# Step 1: Set up OpenAI API Key
openai_api_key = "sk-tSeHC_UQYlf-5gaww6ZZKYrl8Mg2F_lqZ9TamxtfdMT3BlbkFJCrcgPy_EN-4pwJk8DKMhYV6PYrKoTkHjgRJ87IobkA"
os.environ["OPENAI_API_KEY"] = openai_api_key

# Step 2: Initialize OpenAI embeddings
embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

# Step 3: Leggi i curricula dalla cartella resumes
cartella = os.path.dirname(os.path.abspath(__file__))
cartella_curricula = os.path.join(cartella, "resumes")
curricula = []

for filename in os.listdir(cartella_curricula):
    if filename.startswith("curriculum_") and filename.endswith(".json"):
        filepath = os.path.join(cartella_curricula, filename)
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
            curricula.append(content)
            print(f"Letto {filename}")

# Step 4: Crea gli oggetti Document
documents = [Document(page_content=curriculum) for curriculum in curricula]

# Step 5: Esegui il modello di embedding sui curricula
resume_embeddings = embedding_model.embed_documents([doc.page_content for doc in documents])

# Step 6: Inizializza FAISS e memorizza gli embeddings
vector_store = FAISS.from_documents(documents, embedding_model)

# Step 7: Descrizione del lavoro e embedding
job_description = """
Tech Innovators Inc. is seeking a Senior Data Scientist with proficiency in Python, deep learning frameworks, and cloud platforms...
"""

job_description_embedding = embedding_model.embed_query(job_description)

# Step 8: Ricerca dei curricula simili
similar_resumes = vector_store.similarity_search_with_score_by_vector(job_description_embedding, k=10)

# Step 9: Definisci le funzioni per le nuove metriche

# Funzione per calcolare la similarità coseno
def calculate_cosine_similarity(embedding1, embedding2):
    return cosine_similarity([embedding1], [embedding2])[0][0]

# Funzione per estrarre le parole chiave
def extract_keywords(text):
    vectorizer = CountVectorizer(stop_words='english')
    X = vectorizer.fit_transform([text])
    return vectorizer.get_feature_names_out()

# Funzione per calcolare la percentuale di corrispondenza delle parole chiave
def calculate_keyword_match_percentage(resume_keywords, job_keywords):
    match_count = sum(1 for keyword in resume_keywords if keyword in job_keywords)
    return match_count / len(job_keywords) if len(job_keywords) > 0 else 0

# Funzione per calcolare la densità delle parole chiave
def calculate_keyword_density(resume, keywords):
    word_count = len(resume.split())
    keyword_count = sum(resume.lower().count(keyword.lower()) for keyword in keywords)
    return keyword_count / word_count if word_count else 0

# Funzione per analizzare la sentiment
def analyze_sentiment(text):
    analysis = TextBlob(text)
    return analysis.sentiment.polarity



# Funzione per calcolare il punteggio di leggibilità
def calculate_readability(text):
    return textstatistics().flesch_reading_ease(text)


# Liste predefinite di competenze
technical_skills_list = ['python', 'deep learning', 'machine learning', 'cloud', 'tensorflow', 'pytorch', 'aws', 'azure', 'gcp']
soft_skills_list = ['leadership', 'communication', 'teamwork', 'problem solving', 'adaptability']
education_keywords = ['bachelor', 'master', 'phd', 'degree', 'certification', 'diploma']


job_keywords = extract_keywords(job_description)

# Step 10: Analisi dei curricula e raccolta delle metriche
resume_scores = []
metrics_dict = {}

for doc, score in similar_resumes:
    # Similarità coseno
    resume_embedding = embedding_model.embed_query(doc.page_content)
    cosine_sim = calculate_cosine_similarity(job_description_embedding, resume_embedding)
    
    # Analisi delle parole chiave
    resume_keywords = extract_keywords(doc.page_content)
    keyword_match_percentage = calculate_keyword_match_percentage(resume_keywords, job_keywords)
    keyword_density = calculate_keyword_density(doc.page_content, job_keywords)
    
    # Analisi del sentiment
    sentiment_score = analyze_sentiment(doc.page_content)
    
    
    # Punteggio di leggibilità
    readability_score = calculate_readability(doc.page_content)

    
    # Aggiorna le metriche
    metrics = {
        "cosine_similarity": cosine_sim,
        "keyword_match_percentage": keyword_match_percentage,
        "keyword_density": keyword_density,
        "sentiment_score": sentiment_score,
        "readability_score": readability_score,
    }
    
    resume_scores.append((doc.page_content, cosine_sim))
    metrics_dict[doc.page_content[:30]] = metrics

# Step 11: Ordina i curricula per similarità coseno
ranked_resumes = sorted(resume_scores, key=lambda x: x[1], reverse=True)

# Step 12: Crea la cartella di output
output_directory = os.path.join(cartella, "OutputResumes")
os.makedirs(output_directory, exist_ok=True)

# Step 13: Scrivi i curricula classificati nei file
for idx, (resume, similarity) in enumerate(ranked_resumes):
    output_filename = f"ranked_resume_{idx + 1}.md"
    output_filepath = os.path.join(output_directory, output_filename)
    
    # Recupera le metriche
    metrics = metrics_dict[resume[:30]]
    keyword_match_percentage = metrics["keyword_match_percentage"]
    keyword_density = metrics["keyword_density"]
    sentiment_score = metrics["sentiment_score"]
    readability_score = metrics["readability_score"]

    # Scrivi nel file di output
    with open(output_filepath, "w", encoding="utf-8") as output_file:
        output_file.write("### Curriculum Vitae\n")
        output_file.write(resume)
        output_file.write("\n")
        output_file.write("-" * 50 + "\n")
        output_file.write("### Punteggio di Similarità e Metriche\n")
        output_file.write(f"Cosine Similarity: {similarity:.4f}\n")
        output_file.write(f"Keyword Match Percentage: {keyword_match_percentage:.2%}\n")
        output_file.write(f"Keyword Density: {keyword_density:.2%}\n")
        output_file.write(f"Sentiment Score: {sentiment_score:.4f}\n")
        output_file.write(f"Readability Score: {readability_score:.2f}\n")
        print(f"Creato {output_filename} con somiglianza {similarity:.4f}")

print("Tutti i curriculum sono stati creati nella cartella OutputResumes.")
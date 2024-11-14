import os
import numpy as np
from datetime import datetime
from typing import List, Dict
import json
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.vectorstores import FAISS
import openai

class CVMetricsAnalyzer:
    def __init__(self, api_key: str):
        """Initialize the CV Analyzer with OpenAI API key."""
        self.api_key = api_key
        os.environ["OPENAI_API_KEY"] = api_key
        openai.api_key = api_key
        self.embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

    def calculate_cosine_similarity(self, cv_text: str, job_description: str) -> float:
        """Calculate cosine similarity using OpenAI embeddings."""
        cv_embedding = self.embedding_model.embed_query(cv_text)
        job_embedding = self.embedding_model.embed_query(job_description)
        return np.dot(cv_embedding, job_embedding) / (np.linalg.norm(cv_embedding) * np.linalg.norm(job_embedding))

    def analyze_keywords_and_skills(self, text: str, job_description: str) -> dict:
        """Analyze keywords and skills using GPT."""
        prompt = f"""Analyze the following CV text and job description for keyword matching and skills.
        Calculate these metrics:
        1. Keyword match percentage (% of job keywords found in CV)
        2. Keyword density (frequency of job keywords in CV)
        3. Technical skills match percentage
        4. Soft skills match percentage
        5. Number of matched skills

        CV Text: {text}

        Job Description: {job_description}

        Return as JSON with these keys: 
        keyword_match_percentage, keyword_density, skill_match_percentage, 
        soft_skill_match_percentage, skill_match_count
        """

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a CV analysis expert. Return numeric values as decimals between 0 and 1."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def analyze_writing_quality(self, text: str) -> dict:
        """Analyze writing quality metrics using GPT."""
        prompt = f"""Analyze the following CV text for writing quality.
        Calculate these metrics:
        1. Sentiment score (-1 to 1)
        2. Readability score (0-100)
        3. Active voice percentage
        4. Overall writing quality

        Text: {text}

        Return as JSON with these keys:
        sentiment_score, readability_score, active_voice_percentage
        """

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a writing analysis expert. Provide detailed numeric analysis."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def analyze_experience_and_education(self, text: str) -> dict:
        """Analyze experience and education using GPT."""
        prompt = f"""Analyze the following CV text for experience and education.
        Calculate:
        1. Years of experience
        2. Education match percentage (based on relevant degrees/certifications)
        
        Text: {text}
        
        Return as JSON with these keys:
        years_of_experience, education_match_percentage
        """

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a CV analysis expert. Extract precise numeric values."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def analyze_cv(self, cv_text: str, job_description: str) -> Dict:
        """Perform comprehensive CV analysis using all metrics."""
        # Calculate similarity
        similarity = self.calculate_cosine_similarity(cv_text, job_description)
        
        # Get all other metrics using GPT
        keywords_skills = self.analyze_keywords_and_skills(cv_text, job_description)
        writing_quality = self.analyze_writing_quality(cv_text)
        experience_edu = self.analyze_experience_and_education(cv_text)
        
        # Combine all metrics
        return {
            "cosine_similarity": similarity,
            **keywords_skills,
            **writing_quality,
            **experience_edu
        }

    def process_curricula(self, folder_path: str, job_description: str, output_dir: str):
        """Process all CVs and save results."""
        # Read CVs
        curricula = []
        for filename in os.listdir(folder_path):
            if filename.startswith("curriculum_") and filename.endswith(".md"):
                filepath = os.path.join(folder_path, filename)
                with open(filepath, "r", encoding="utf-8") as file:
                    curricula.append(file.read())
                print(f"Read {filename}")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Process each CV
        analyzed_cvs = []
        for idx, cv in enumerate(curricula):
            print(f"Analyzing CV {idx + 1}/{len(curricula)}...")
            metrics = self.analyze_cv(cv, job_description)
            analyzed_cvs.append((cv, metrics))

        # Sort by similarity score
        analyzed_cvs.sort(key=lambda x: x[1]["cosine_similarity"], reverse=True)

        # Save results
        for idx, (cv, metrics) in enumerate(analyzed_cvs, 1):
            output_path = os.path.join(output_dir, f"ranked_resume_{idx}.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("### Curriculum Vitae\n")
                f.write(cv + "\n\n")
                f.write("### Metriche di Analisi\n")
                f.write(f"Cosine Similarity: {metrics['cosine_similarity']:.4f}\n")
                f.write(f"Keyword Match Percentage: {metrics['keyword_match_percentage']:.2%}\n")
                f.write(f"Keyword Density: {metrics['keyword_density']:.2%}\n")
                f.write(f"Sentiment Score: {metrics['sentiment_score']:.4f}\n")
                f.write(f"Skill Match Percentage: {metrics['skill_match_percentage']:.2%}\n")
                f.write(f"Skill Match Count: {metrics['skill_match_count']}\n")
                f.write(f"Readability Score: {metrics['readability_score']:.2f}\n")
                f.write(f"Active Voice Percentage: {metrics['active_voice_percentage']:.2%}\n")
                f.write(f"Soft Skill Match Percentage: {metrics['soft_skill_match_percentage']:.2%}\n")
                f.write(f"Education Match Percentage: {metrics['education_match_percentage']:.2%}\n")

def main():
    # Initialize analyzer
    api_key = "sk-tSeHC_UQYlf-5gaww6ZZKYrl8Mg2F_lqZ9TamxtfdMT3BlbkFJCrcgPy_EN-4pwJk8DKMhYV6PYrKoTkHjgRJ87IobkA"
    analyzer = CVMetricsAnalyzer(api_key)
    
    # Set paths
    current_dir = os.getcwd()
    cv_folder = os.path.join(current_dir, "CreateCV")
    output_folder = os.path.join(cv_folder, "OutputResumes")
    
    # Example job description
    job_description = """
    Tech Innovators Inc. is seeking a Senior Data Scientist with proficiency in Python, 
    deep learning frameworks, and cloud platforms...
    """
    
    # Process all CVs
    analyzer.process_curricula(cv_folder, job_description, output_folder)
    print("Analysis complete. Results saved in OutputResumes folder.")

if __name__ == "__main__":
    main()
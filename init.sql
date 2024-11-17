-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create job_descriptions table
CREATE TABLE IF NOT EXISTS job_descriptions (
    id SERIAL PRIMARY KEY,
    job_description TEXT,
    embedding VECTOR(198)  -- Assuming OpenAI's Ada model embedding of dimension 1536
);
#!/usr/bin/env python
"""
Script to populate the database with test data for evaluation.

This script inserts test data into the database, including countries, companies,
locations, and jobs with vector embeddings for testing the matching service.
"""

import asyncio
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta, UTC
import numpy as np

# Add project root to path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.config import settings
import psycopg
from psycopg.sql import SQL, Identifier

# Sample data
COUNTRIES = [
    {"name": "United States"},
    {"name": "Germany"},
    {"name": "United Kingdom"},
    {"name": "Canada"},
    {"name": "Australia"},
]

CITIES = {
    "United States": ["New York", "San Francisco", "Seattle", "Austin", "Boston", "remote"],
    "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "remote"],
    "United Kingdom": ["London", "Manchester", "Edinburgh", "Birmingham", "Cambridge", "remote"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "remote"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "remote"],
}

COMPANIES = [
    {"name": "TechGiant", "logo": "https://example.com/logo1.png"},
    {"name": "InnovateCorp", "logo": "https://example.com/logo2.png"},
    {"name": "DataSystems", "logo": "https://example.com/logo3.png"},
    {"name": "AIEngines", "logo": "https://example.com/logo4.png"},
    {"name": "CloudScale", "logo": "https://example.com/logo5.png"},
    {"name": "DevOpsHub", "logo": "https://example.com/logo6.png"},
    {"name": "SecurityNet", "logo": "https://example.com/logo7.png"},
    {"name": "MobileFirst", "logo": "https://example.com/logo8.png"},
]

JOB_TITLES = [
    "Software Engineer",
    "Senior Developer",
    "Data Scientist",
    "Machine Learning Engineer",
    "DevOps Specialist",
    "Full Stack Developer",
    "Backend Engineer",
    "Frontend Developer",
    "Product Manager",
    "UX Designer",
]

SKILLS = [
    "Python", "JavaScript", "React", "Node.js", "SQL", "PostgreSQL", 
    "AWS", "Docker", "Kubernetes", "TensorFlow", "PyTorch", "Git",
    "FastAPI", "Django", "Flask", "Express", "MongoDB", "Redis",
    "CI/CD", "Linux", "Agile", "REST", "GraphQL", "TypeScript"
]

WORKPLACE_TYPES = ["On-site", "Remote", "Hybrid"]
JOB_STATES = ["active", "filled", "expired"]
EXPERIENCE_LEVELS = ["Entry Level", "Mid Level", "Senior", "Lead", "Manager"]

# Function to generate random vector embeddings
def generate_vector_embedding(dimension=384):
    """Generate a random normalized vector embedding"""
    vec = np.random.normal(0, 1, dimension)
    vec = vec / np.linalg.norm(vec)  # Normalize to unit length
    return vec.tolist()

async def populate_database():
    """Populate the database with test data."""
    print("Populating database with test data...")
    
    conn = None
    try:
        # Connect to database
        print(f"Connecting to database: {settings.database_url}")
        conn = await psycopg.AsyncConnection.connect(settings.database_url)
        
        # Create cursor
        async with conn.cursor() as cursor:
            # Clear existing data first
            print("Clearing existing data...")
            await cursor.execute("DELETE FROM \"Jobs\"")
            await conn.commit()
            
            # Get existing countries or insert new ones
            print("Getting existing countries or inserting new ones...")
            country_ids = {}
            for country in COUNTRIES:
                # Check if country exists
                await cursor.execute(
                    "SELECT country_id FROM \"Countries\" WHERE country_name = %s",
                    (country["name"],)
                )
                result = await cursor.fetchone()
                
                if result:
                    # Country exists, use its ID
                    country_ids[country["name"]] = result[0]
                    print(f"Found existing country: {country['name']} (ID: {result[0]})")
                else:
                    # Country doesn't exist, insert it
                    try:
                        await cursor.execute(
                            "INSERT INTO \"Countries\" (country_name) VALUES (%s) RETURNING country_id",
                            (country["name"],)
                        )
                        country_id = await cursor.fetchone()
                        country_ids[country["name"]] = country_id[0]
                        print(f"Inserted new country: {country['name']} (ID: {country_id[0]})")
                    except Exception as e:
                        print(f"Error inserting country {country['name']}: {str(e)}")
                        # Try to get the ID even if insert failed
                        await cursor.execute(
                            "SELECT country_id FROM \"Countries\" WHERE country_name = %s",
                            (country["name"],)
                        )
                        result = await cursor.fetchone()
                        if result:
                            country_ids[country["name"]] = result[0]
                            print(f"Retrieved country ID after error: {country['name']} (ID: {result[0]})")
            
            await conn.commit()
            
            # Get existing companies or insert new ones
            print("Getting existing companies or inserting new ones...")
            company_ids = []
            for company in COMPANIES:
                # Check if company exists
                await cursor.execute(
                    "SELECT company_id FROM \"Companies\" WHERE company_name = %s",
                    (company["name"],)
                )
                result = await cursor.fetchone()
                
                if result:
                    # Company exists, use its ID
                    company_ids.append(result[0])
                    print(f"Found existing company: {company['name']} (ID: {result[0]})")
                else:
                    # Company doesn't exist, insert it
                    await cursor.execute(
                        "INSERT INTO \"Companies\" (company_name, logo) VALUES (%s, %s) RETURNING company_id",
                        (company["name"], company["logo"])
                    )
                    company_id = await cursor.fetchone()
                    company_ids.append(company_id[0])
                    print(f"Inserted new company: {company['name']} (ID: {company_id[0]})")
            
            await conn.commit()
            
            # Get existing locations or insert new ones
            print("Getting existing locations or inserting new ones...")
            location_ids = {}
            for country_name, cities in CITIES.items():
                if country_name not in country_ids:
                    print(f"Skipping cities for country not found: {country_name}")
                    continue
                    
                country_id = country_ids[country_name]
                for city in cities:
                    # Check if location exists
                    await cursor.execute(
                        "SELECT location_id FROM \"Locations\" WHERE city = %s AND country = %s",
                        (city, country_id)
                    )
                    result = await cursor.fetchone()
                    
                    if result:
                        # Location exists, use its ID
                        location_ids[(country_name, city)] = result[0]
                        print(f"Found existing location: {city}, {country_name} (ID: {result[0]})")
                    else:
                        # Location doesn't exist, insert it
                        latitude = random.uniform(-90, 90) if city != "remote" else None
                        longitude = random.uniform(-180, 180) if city != "remote" else None
                        
                        await cursor.execute(
                            "INSERT INTO \"Locations\" (city, country, latitude, longitude) "
                            "VALUES (%s, %s, %s, %s) RETURNING location_id",
                            (city, country_id, latitude, longitude)
                        )
                        location_id = await cursor.fetchone()
                        location_ids[(country_name, city)] = location_id[0]
                        print(f"Inserted new location: {city}, {country_name} (ID: {location_id[0]})")
            
            await conn.commit()
            
            # Insert jobs with vector embeddings
            print("Inserting jobs with vector embeddings...")
            num_jobs = 50
            for i in range(num_jobs):
                # Select random values
                title = random.choice(JOB_TITLES)
                company_id = random.choice(company_ids)
                country_name = random.choice(list(country_ids.keys()))
                city = random.choice(CITIES[country_name])
                
                # Skip if location doesn't exist
                if (country_name, city) not in location_ids:
                    print(f"Skipping job for location not found: {city}, {country_name}")
                    continue
                    
                location_id = location_ids[(country_name, city)]
                workplace_type = random.choice(WORKPLACE_TYPES)
                
                # Generate a posting date in the last 60 days
                days_ago = random.randint(0, 60)
                posted_date = datetime.now(UTC) - timedelta(days=days_ago)
                
                # Job state - newer jobs are more likely to be active
                job_state = random.choices(
                    JOB_STATES, 
                    weights=[0.8, 0.15, 0.05] if days_ago < 30 else [0.3, 0.5, 0.2]
                )[0]
                
                # Experience level
                experience = random.choice(EXPERIENCE_LEVELS)
                
                # Random set of skills
                num_skills = random.randint(3, 8)
                required_skills = random.sample(SKILLS, num_skills)
                skills_str = ", ".join(required_skills)
                
                # Description
                description = f"We are looking for a {title} to join our team. "
                description += f"The ideal candidate will have experience with {', '.join(required_skills[:-1])} and {required_skills[-1]}. "
                description += f"This is a {workplace_type.lower()} position for a {experience.lower()} professional."
                
                # Short description
                short_description = f"{title} position with {', '.join(required_skills[:3])} skills."
                
                # Apply link
                apply_link = f"https://example.com/jobs/{i+1}"
                
                # Vector embedding - we need this for the vector operations to work
                embedding = generate_vector_embedding()
                
                # Convert Python list to PostgreSQL vector
                embedding_str = f"[{','.join(str(x) for x in embedding)}]"
                
                await cursor.execute(
                    "INSERT INTO \"Jobs\" (title, workplace_type, posted_date, job_state, "
                    "description, short_description, field, experience, skills_required, "
                    "apply_link, embedding, company_id, location_id, portal) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s)",
                    (
                        title, workplace_type, posted_date, job_state, description, 
                        short_description, "Technology", experience, skills_str, 
                        apply_link, embedding_str, company_id, location_id, "test"
                    )
                )
                
                if (i + 1) % 10 == 0:
                    print(f"Inserted {i + 1}/{num_jobs} jobs")
                    await conn.commit()  # Commit in batches
            
            await conn.commit()
            
            # Verify insertion
            await cursor.execute("SELECT COUNT(*) FROM \"Jobs\"")
            job_count = await cursor.fetchone()
            print(f"Successfully inserted {job_count[0]} jobs")
            
            # Check if vector data is correct
            await cursor.execute("SELECT embedding FROM \"Jobs\" LIMIT 1")
            vector_example = await cursor.fetchone()
            if vector_example and vector_example[0]:
                vec_dimensions = len(vector_example[0])
                print(f"Vector embeddings have {vec_dimensions} dimensions")
            else:
                print("WARNING: Vector embeddings might not be correctly stored")
            
    except Exception as e:
        print(f"Error populating database: {str(e)}")
        if conn:
            await conn.rollback()
        raise
    finally:
        if conn:
            await conn.close()
        print("Database population completed")

if __name__ == "__main__":
    asyncio.run(populate_database())
    print("Script execution completed")
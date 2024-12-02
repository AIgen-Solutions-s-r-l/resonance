from dataclasses import dataclass
import psycopg
from loguru import logger
from psycopg.rows import Row
from psycopg.sql import SQL
from typing import List, Dict, Any
from cleaner import Cleaner

@dataclass
class DatabaseSettings:
    db_name: str
    db_user: str
    db_password: str
    db_host: str
    db_port: int

def get_logger_context(**kwargs) -> dict:
    """Helper function to create a standardized logging context."""
    return {
        "service": "job_description_cleaner",
        **kwargs
    }

class JobDescriptionCleaner:
    """
    Class to fetch job descriptions from PostgreSQL and clean them using the Cleaner class.
    """
    
    def __init__(self, settings: DatabaseSettings):
        """
        Initialize the connection to PostgreSQL and the text cleaner.
        
        Args:
            settings (DatabaseSettings): Database connection settings
        """
        self.settings = settings
        self.conn = None
        self.cleaner = Cleaner(
            remove_stopwords=True,
            remove_punctuation=True,
            remove_numbers=False,  # Keep numbers as they might be important in job descriptions
            remove_entities=False,  # Keep entity names as they might be company/technology names
            lowercase=True
        )
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize the database connection."""
        try:
            self.conn = psycopg.connect(
                dbname=self.settings.db_name,
                user=self.settings.db_user,
                password=self.settings.db_password,
                host=self.settings.db_host,
                port=self.settings.db_port,
                autocommit=True
            )
            context = get_logger_context(action="initialize_database")
            logger.info("Database connection established successfully", context)
        except psycopg.Error as e:
            context = get_logger_context(action="initialize_database", error=str(e))
            logger.error("Database connection failed", context)
            raise

    def get_sample_descriptions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch a sample of job descriptions from the database.
        
        Args:
            limit (int): Number of descriptions to fetch
            
        Returns:
            List[Dict[str, Any]]: List of job records
        """
        try:
            with self.conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                query = SQL("""
                    SELECT job_id, title, description 
                    FROM "Jobs" 
                    WHERE description IS NOT NULL 
                    LIMIT {limit}
                """).format(limit=limit)
                
                cur.execute(query)
                results = cur.fetchall()
                
                context = get_logger_context(
                    action="fetch_descriptions",
                    count=len(results)
                )
                logger.info("Successfully fetched job descriptions", context)
                return results
                
        except psycopg.Error as e:
            context = get_logger_context(
                action="fetch_descriptions",
                error=str(e)
            )
            logger.error("Failed to fetch job descriptions", context)
            raise

    def clean_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean the job descriptions using the Cleaner class.
        
        Args:
            jobs (List[Dict[str, Any]]): List of job records
            
        Returns:
            List[Dict[str, Any]]: Jobs with cleaned descriptions
        """
        cleaned_jobs = []
        for job in jobs:
            try:
                cleaned_description = self.cleaner.clean(job['description'])
                cleaned_jobs.append({
                    'job_id': job['job_id'],
                    'title': job['title'],
                    'original_description': job['description'],
                    'cleaned_description': cleaned_description
                })
                context = get_logger_context(
                    action="clean_description",
                    job_id=job['job_id']
                )
                logger.debug("Successfully cleaned job description", context)
            except Exception as e:
                context = get_logger_context(
                    action="clean_description",
                    job_id=job['job_id'],
                    error=str(e)
                )
                logger.error("Failed to clean job description", context)
                continue
        return cleaned_jobs

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            context = get_logger_context(action="close_connection")
            logger.info("Database connection closed", context)

def main():
    # Database settings
    settings = DatabaseSettings(
        db_name="matching",
        db_user="testuser",
        db_password="testpassword",
        db_host="localhost",
        db_port=5432
    )

    try:
        job_cleaner = JobDescriptionCleaner(settings)

        jobs = job_cleaner.get_sample_descriptions(limit=6)
        
        cleaned_jobs = job_cleaner.clean_descriptions(jobs)

        # Print results
        for job in cleaned_jobs:
            with open(f"job_{job['job_id']}.txt", "w") as file:
                file.write("=" * 80 + "\n")
                file.write(f"Job ID: {job['job_id']}\n")
                file.write(f"Title: {job['title']}\n")
                file.write("Original Description:\n")
                file.write(f"{job['original_description']}...\n")
                file.write("Cleaned Description:\n")
                file.write(f"{job['cleaned_description']}...\n")
            logger.info("=" * 80)
            logger.info(f"Job ID: {job['job_id']}")
            logger.info(f"Title: {job['title']}")
            logger.info("Original Description (first 200 chars):")
            logger.info(f"{job['original_description'][:200]}...")
            logger.info("Cleaned Description (first 200 chars):")
            logger.info(f"{job['cleaned_description'][:200]}...")

    except Exception as e:
        context = get_logger_context(
            action="main",
            error=str(e)
        )
        logger.error("An error occurred in main execution", context)
        raise
    finally:
        if 'job_cleaner' in locals():
            job_cleaner.close()

if __name__ == "__main__":
    main()
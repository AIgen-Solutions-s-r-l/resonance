from dataclasses import dataclass
from typing import List, Optional
import psycopg
from loguru import logger
from psycopg.rows import Row
from psycopg.sql import SQL

from app.core.config import Settings
from app.core.logging_config import get_logger_context


@dataclass
class JobMatch:
    """Data class for job matching results."""
    id: str
    job_id: str
    title: str
    description: str
    portal: str
    company: str
    score: float


class JobMatcher:
    """A class to handle job matching operations using CV embeddings and similarity metrics."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._initialize_database()

    def _initialize_database(self) -> None:
        # ... existing code unchanged ...
        pass

    def get_top_jobs_by_multiple_metrics(
        self,
        cursor: psycopg.Cursor[Row],
        cv_embedding: List[float],
        location: Optional[str] = None,
        limit: int = 50
    ) -> List[JobMatch]:
        """
        Get top matching jobs using multiple similarity metrics.
        
        Args:
            cursor: Database cursor for executing queries
            cv_embedding: The embedding vector of the CV
            location: Optional. Filter by job location if provided.
            limit: Maximum number of results to return

        Returns:
            List of JobMatch objects
        """
        try:
            # We’ll build a dynamic WHERE clause if location is provided:
            where_clauses = []
            params = [cv_embedding, cv_embedding, cv_embedding]

            if location:
                where_clauses.append("j.location = %s")
                params.append(location)

            # Combine all WHERE conditions into a single string
            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            query = SQL(f"""
                WITH combined_scores AS (
                    SELECT
                        j.title, 
                        j.description,
                        j.job_id,
                        j.company_id,
                        c.company_name,
                        embedding <-> %s::vector as l2_distance,
                        embedding <=> %s::vector as cosine_distance,
                        -(embedding <#> %s::vector) as inner_product
                    FROM "Jobs" j
                    LEFT JOIN "Companies" c ON j.company_id = c.company_id
                    {where_sql}
                ),
                normalized_scores AS (
                    SELECT 
                        title,
                        description,
                        job_id,
                        company_name,
                        (
                            (1 - (l2_distance - MIN(l2_distance) OVER()) / 
                              NULLIF(MAX(l2_distance) OVER() - MIN(l2_distance) OVER(), 0)) * 0.4
                          + (1 - (cosine_distance - MIN(cosine_distance) OVER()) /
                              NULLIF(MAX(cosine_distance) OVER() - MIN(cosine_distance) OVER(), 0)) * 0.4
                          + (
                              (inner_product - MIN(inner_product) OVER()) / 
                              NULLIF(MAX(inner_product) OVER() - MIN(inner_product) OVER(), 0)
                            ) * 0.2
                        ) as combined_score
                    FROM combined_scores
                )
                SELECT 
                    title,
                    description,
                    job_id,
                    company_name,
                    combined_score
                FROM normalized_scores
                ORDER BY combined_score DESC
                LIMIT %s;
            """)

            # The limit is always appended last
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            job_matches = [
                JobMatch(
                    id=str(row[2]),
                    job_id=str(row[2]),
                    title=row[0],
                    description=row[1],
                    company=row[3],
                    portal="test_portal",   # Or wherever this comes from
                    score=float(row[4])
                )
                for row in results
            ]

            context = get_logger_context(
                action="get_top_jobs",
                status="success",
                matches_found=len(job_matches)
            )
            logger.info("Successfully retrieved matching jobs", context)
            return job_matches

        except psycopg.Error as e:
            context = get_logger_context(
                action="get_top_jobs",
                status="error",
                error=str(e)
            )
            logger.error("Database query failed", context)
            raise

    async def process_job(
        self,
        resume: dict,
        location: Optional[str] = None
    ) -> dict[str, list[dict[str, str | float]]]:
        """
        Process a CV and find matching jobs.

        Args:
            resume: The resume object from MongoDB, including 'vector'
            location: Optional. Filter by job location.

        Returns:
            A dict with a "jobs" key containing a list of matched job dicts
        """
        try:
            context = get_logger_context(
                action="process_job",
                status="started"
            )
            logger.info("Starting job processing", context)

            cv_embedding = resume["vector"]

            with self.conn.cursor() as cursor:
                # Pass location to the retrieval method
                job_matches = self.get_top_jobs_by_multiple_metrics(
                    cursor,
                    cv_embedding,
                    location=location
                )

                job_results = {
                    "jobs": [
                        {
                            "id": str(match.id),
                            "job_id": str(match.job_id),
                            "description": match.description,
                            "company": match.company,
                            "portal": match.portal,
                            "title": match.title,
                        }
                        for match in job_matches
                    ]
                }

                context = get_logger_context(
                    action="process_job",
                    status="success",
                    matches_found=len(job_results["jobs"])
                )
                logger.success("Successfully processed job", context)
                return job_results

        except Exception as e:
            context = get_logger_context(
                action="process_job",
                status="error",
                error=str(e)
            )
            logger.error(f"Failed to process job: {e}", context)
            raise

settings = Settings()
job_matcher = JobMatcher(settings)

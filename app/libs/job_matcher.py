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
            logger.info(
                "Database connection established successfully", context)
        except psycopg.Error as e:
            context = get_logger_context(
                action="initialize_database", error=str(e))
            logger.error("Database connection failed", context)
            raise

    def get_top_jobs_by_multiple_metrics(
        self,
        cursor: psycopg.Cursor[Row],
        cv_embedding: List[float],
        location: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[JobMatch]:
        """
        Get top matching jobs using multiple similarity metrics.
        
        Args:
            cursor: Database cursor for executing queries
            cv_embedding: The embedding vector of the CV
            location: Optional. Filter by job location if provided
            keywords: Optional. Filter by presence of ANY of the given keywords 
                      in the job title or description
            limit: Maximum number of results to return

        Returns:
            List of JobMatch objects
        """
        try:
            where_clauses = []
            params = [cv_embedding, cv_embedding, cv_embedding]

            # Location filter
            if location:
                where_clauses.append("l.location = %s")
                params.append(location)

            # Keywords filter (title or description must contain ANY of the keywords)
            if keywords and len(keywords) > 0:
                # We'll build a sub-list of OR clauses for each keyword
                or_clauses = []
                for kw in keywords:
                    # ILIKE for case-insensitive match
                    or_clauses.append("(j.title ILIKE %s OR j.description ILIKE %s)")
                    # two parameters for each keyword: "%python%" for title, "%python%" for description
                    params.extend([f"%{kw}%", f"%{kw}%"])
                
                # Combine them with OR in a single group
                # e.g. ( j.title ILIKE %s OR j.description ILIKE %s ) OR ...
                where_clauses.append("(" + " OR ".join(or_clauses) + ")")

            # TODO & NOTE: Maybe here full-text search or pg_trgm (here was a mock pattern matching)

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
                    LEFT JOIN "Locations" l ON j.location_id = l.location_id
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

            # The last parameter is the limit
            params.append(limit)

            # Execute the query with all accumulated parameters
            cursor.execute(query, params)
            results = cursor.fetchall()

            job_matches = [
                JobMatch(
                    id=str(row[2]),
                    job_id=str(row[2]),
                    title=row[0],
                    description=row[1],
                    company=row[3],
                    portal="test_portal",
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
        location: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> dict[str, list[dict[str, str | float]]]:
        """
        Process a CV and find matching jobs.

        Args:
            resume: The resume data, including 'vector'
            location: Optional. Filter by job location
            keywords: Optional. Filter by job title/description that contains 
                      any of these keywords

        Returns:
            A dict with a "jobs" list containing matched job info
        """
        try:
            context = get_logger_context(
                action="process_job",
                status="started"
            )
            logger.info("Starting job processing", context)

            cv_embedding = resume["vector"]

            with self.conn.cursor() as cursor:
                job_matches = self.get_top_jobs_by_multiple_metrics(
                    cursor,
                    cv_embedding,
                    location=location,
                    keywords=keywords
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
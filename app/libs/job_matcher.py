from dataclasses import dataclass
from typing import List, Optional, Tuple
import psycopg
from psycopg.rows import Row
from psycopg.sql import SQL
import json
import datetime


from app.core.config import settings
from app.log.logging import logger
from app.schemas.location import LocationFilter


@dataclass
class JobMatch:
    """Data class for job matching results."""

    id: str
    job_id: str
    title: str
    description: str
    workplace: str
    short_description: str
    field: str
    experience: str
    skills: str
    country: str
    city: str
    company: str
    logo: str
    portal: str
    company: str
    score: float


class JobMatcher:
    """A class to handle job matching operations using CV embeddings and similarity metrics."""

    def __init__(self) -> None:
        self.settings = settings
        self._initialize_database()

    def _initialize_database(self) -> None:
        try:
            self.conn = psycopg.connect(self.settings.database_url, autocommit=True)
            logger.info("Database connection established successfully")
        except psycopg.Error as e:
            logger.error("Database connection failed")
            raise

    def get_top_jobs_by_multiple_metrics(
        self,
        cursor: psycopg.Cursor[Row],
        cv_embedding: List[float],
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 50,
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

            where_clauses = ["embedding IS NOT NULL"]
            count_params = []  # used for the COUNT & simpler fallback
            # embeddings_params will be the same as count_params, but we'll add embeddings later

            # Location filter
            if location and location.country:
                where_clauses.append("(co.country_name = %s)")
                count_params.append(location.country)

            if location and location.city:
                where_clauses.append("(l.city = %s OR l.city = 'remote')")
                count_params.append(location.city)

            if (
                location
                and location.latitude
                and location.longitude
                and location.radius_km
            ):
                where_clauses.append(
                    """
                    (
                        l.city = 'remote'
                        OR ST_DWithin(
                            ST_MakePoint(l.longitude::DOUBLE PRECISION, l.latitude::DOUBLE PRECISION)::geography,
                            ST_MakePoint(%s, %s)::geography,
                            %s * 1000
                        )
                    )
                """
                )
                count_params.extend(
                    [location.longitude, location.latitude, location.radius_km]
                )

            # Keywords filter (title or description must contain ANY of the keywords)
            if keywords and len(keywords) > 0:
                or_clauses = []
                for kw in keywords:
                    or_clauses.append("(j.title ILIKE %s OR j.description ILIKE %s)")
                    count_params.extend([f"%{kw}%", f"%{kw}%"])

                where_clauses.append("(" + " OR ".join(or_clauses) + ")")

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            count_query = SQL(
                f"""
                SELECT COUNT(*) AS total_count
                FROM "Jobs" j
                LEFT JOIN "Companies" c ON j.company_id = c.company_id
                LEFT JOIN "Locations" l ON j.location_id = l.location_id
                LEFT JOIN "Countries" co ON l.country = co.country_id
                {where_sql}
            """
            )

            cursor.execute(count_query, count_params)
            row_count = cursor.fetchone()[0]

            if row_count <= 5:
                simple_query = SQL(
                    f"""
                    SELECT
                        j.title,
                        j.description,
                        j.id,
                        j.workplace_type,
                        j.short_description,
                        j.field,
                        j.experience,
                        j.skills_required,
                        co.country_name,
                        l.city,
                        c.company_name,
                        c.logo,
                        0.0 AS combined_score
                    FROM "Jobs" j
                    LEFT JOIN "Companies" c ON j.company_id = c.company_id
                    LEFT JOIN "Locations" l ON j.location_id = l.location_id
                    LEFT JOIN "Countries" co ON l.country = co.country_id
                    {where_sql}
                    LIMIT 5
                """
                )

                cursor.execute(simple_query, count_params)
                results = cursor.fetchall()

                job_matches = [
                    JobMatch(
                        id=str(row[2]),
                        job_id=str(row[2]),
                        title=row[0],
                        description=row[1],
                        workplace=row[3],
                        short_description=row[4],
                        field=row[5],
                        experience=row[6],
                        skills=row[7],
                        country=row[8],
                        city=row[9],
                        company=row[10],
                        logo=row[11],
                        portal="test_portal",
                        score=float(row[12]),
                    )
                    for row in results
                ]

                return job_matches

            params = [cv_embedding, cv_embedding, cv_embedding]  # embeddings

            embeddings_params = params + count_params + [limit, offset]

            query = SQL(
                f"""
                WITH combined_scores AS (
                    SELECT
                        j.title,
                        j.description,
                        j.id,
                        j.workplace_type,
                        j.short_description,
                        j.field,
                        j.experience,
                        j.skills_required,
                        co.country_name,
                        l.city,
                        c.company_name,
                        c.logo,
                        embedding <-> %s::vector as l2_distance,
                        embedding <=> %s::vector as cosine_distance,
                        -(embedding <#> %s::vector) as inner_product
                    FROM "Jobs" j
                    LEFT JOIN "Companies" c ON j.company_id = c.company_id
                    LEFT JOIN "Locations" l ON j.location_id = l.location_id
                    LEFT JOIN "Countries" co ON l.country = co.country_id
                    {where_sql}
                ),
                normalized_scores AS (
                    SELECT 
                        title,
                        description,
                        id,
                        workplace_type,
                        short_description,
                        field,
                        experience,
                        skills_required,
                        country_name,
                        city,
                        company_name,
                        logo,
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
                    id,
                    workplace_type,
                    short_description,
                    field,
                    experience,
                    skills_required,
                    country_name,
                    city,
                    company_name,
                    logo,
                    combined_score
                FROM normalized_scores
                ORDER BY combined_score DESC
                LIMIT %s
                OFFSET %s
            """
            )

            cursor.execute(query, embeddings_params)
            results = cursor.fetchall()

            job_matches = [
                JobMatch(
                    id=str(row[2]),
                    job_id=str(row[2]),
                    title=row[0],
                    description=row[1],
                    workplace=row[3],
                    short_description=row[4],
                    field=row[5],
                    experience=row[6],
                    skills=row[7],
                    country=row[8],
                    city=row[9],
                    company=row[10],
                    logo=row[11],
                    portal="test_portal",
                    score=float(row[12]),
                )
                for row in results
            ]

            return job_matches

        except psycopg.Error as e:
            logger.error(
                "Database query failed",
                action="get_top_jobs",
                status="error",
                error=str(e),
            )
            raise

    async def save_matches(
        self, job_results: dict, resume_id: str, save_to_mongodb: bool = False
    ) -> None:
        """
        Save job matches to JSON file and optionally to MongoDB.

        Args:
            job_results: Dictionary containing matched jobs
            resume_id: ID of the resume used for matching
            save_to_mongodb: Whether to save to MongoDB (default: False)
        """
        try:
            # Save to JSON
            '''filename = f"job_matches_{resume_id}.json"
            with open(filename, "w") as f:
                json.dump(job_results, f, indent=2)'''

            logger.info("Matched jobs are: {job_results}", job_results=job_results, event_type="job_matches")

            # Save to MongoDB if flag is True
            if save_to_mongodb:
                from app.core.mongodb import database

                matches_collection = database.get_collection("job_matches")

                # Add metadata to job results
                job_results["resume_id"] = resume_id
                job_results["timestamp"] = datetime.datetime.utcnow()

                await matches_collection.insert_one(job_results)

                logger.info(
                    "Successfully saved matches to MongoDB",
                    action="save_matches",
                    status="success",
                    destination="mongodb",
                )

        except Exception as e:
            logger.error(
                "Failed to save matches",
                action="save_matches",
                status="error",
                error=str(e),
            )
            raise

    async def process_job(
        self,
        resume: dict,
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        save_to_mongodb: bool = False,
        offset: int = 0,
    ) -> dict[str, list[dict[str, str | float | bool]]]:
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
            logger.info(
                "Starting job processing", action="process_job", status="started"
            )

            if not "vector" in resume.keys():
                return {}

            cv_embedding = resume["vector"]

            with self.conn.cursor() as cursor:
                job_matches = self.get_top_jobs_by_multiple_metrics(
                    cursor,
                    cv_embedding,
                    location=location,
                    keywords=keywords,
                    offset=offset,
                )

                job_results = {
                    "jobs": [
                        {
                            "id": str(match.id),
                            "job_id": str(match.job_id),
                            "description": match.description,
                            "workplace_type": match.workplace,
                            "short_description": match.short_description,
                            "field": match.field,
                            "experience": match.experience,
                            "skills_required": match.skills,
                            "country": match.country,
                            "city": match.city,
                            "company_name": match.company,
                            "company_logo": match.logo,
                            "portal": match.portal,
                            "title": match.title,
                            "score": match.score,
                        }
                        for match in job_matches
                    ]
                }

                # Save matches to JSON and optionally MongoDB
                resume_id = str(resume.get("_id", "unknown"))
                await self.save_matches(job_results, resume_id, save_to_mongodb)

                logger.success(
                    "Successfully processed job",
                    action="process_job",
                    status="success",
                    matches_found=len(job_results["jobs"]),
                )
                return job_results

        except Exception as e:
            logger.error(
                f"Failed to process job: {e}",
                action="process_job",
                status="error",
                error=str(e),
            )
            raise

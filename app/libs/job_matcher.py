from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, UTC
import psycopg
from psycopg.rows import Row, dict_row
from psycopg.sql import SQL
import json

from app.core.config import settings
from app.log.logging import logger
from app.schemas.location import LocationFilter
from app.utils.data_parsers import parse_skills_string
from app.metrics.algorithm import (
    matching_algorithm_timer,
    async_matching_algorithm_timer,
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count
)
from app.metrics.database import (
    sql_query_timer,
    async_sql_query_timer
)


@dataclass
class JobMatch:
    """Data class for job matching results, aligned with JobSchema."""
    
    id: str
    title: str
    description: Optional[str] = None
    workplace_type: Optional[str] = None
    short_description: Optional[str] = None
    field: Optional[str] = None
    experience: Optional[str] = None
    skills_required: Optional[List[str]] = None
    country: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    portal: Optional[str] = None
    score: Optional[float] = None
    posted_date: Optional[datetime] = None
    job_state: Optional[str] = None
    apply_link: Optional[str] = None
    location: Optional[str] = None


class JobMatcher:
    """A class to handle job matching operations using CV embeddings and similarity metrics."""

    # Required fields that must be present in database results
    REQUIRED_FIELDS = {'id', 'title'}

    def __init__(self) -> None:
        self.settings = settings
        self._initialize_database()

    def _validate_row_data(self, row: dict) -> bool:
        """
        Validate that row has all required fields.
        
        Args:
            row: Dictionary containing database row data
            
        Returns:
            bool: True if all required fields are present, False otherwise
        """
        return all(field in row for field in self.REQUIRED_FIELDS)

    def _create_job_match(self, row: dict) -> Optional[JobMatch]:
        """
        Create a JobMatch instance from a database row dictionary.
        
        Args:
            row: Dictionary containing job data from database
            
        Returns:
            JobMatch instance if successful, None if required fields are missing
        """
        logger.debug(
            "Creating JobMatch from row",
            row_type=type(row),
            row_data=row
        )
        
        if not isinstance(row, dict):
            logger.error(
                "Row is not a dictionary",
                row_type=type(row),
                row_data=row
            )
            # Convert Row to dict if needed
            try:
                row = dict(row)
            except Exception as e:
                logger.error(
                    "Failed to convert row to dictionary",
                    error=str(e)
                )
                return None
                
        if not self._validate_row_data(row):
            logger.warning(
                "Skipping job match due to missing required fields",
                row=row,
                required_fields=self.REQUIRED_FIELDS
            )
            return None
            
        try:
            return JobMatch(
                id=str(row['id']),
                title=row['title'],
                description=row.get('description'),
                workplace_type=row.get('workplace_type'),
                short_description=row.get('short_description'),
                field=row.get('field'),
                experience=row.get('experience'),
                skills_required=parse_skills_string(row.get('skills_required')),
                country=row.get('country'),
                city=row.get('city'),
                company_name=row.get('company_name'),
                company_logo=row.get('company_logo'),
                portal=row.get('portal', 'test_portal'),
                score=float(row.get('score', 0.0)),
                posted_date=row.get('posted_date'),
                job_state=row.get('job_state'),
                apply_link=row.get('apply_link'),
                location=row.get('location')
            )
        except Exception as e:
            logger.error(
                "Failed to create JobMatch instance",
                error=str(e),
                row=row
            )
            return None

    def _initialize_database(self) -> None:
        """Initialize database connection with dictionary row factory."""
        try:
            logger.debug(
                "Connecting to database",
                database_url=self.settings.database_url.split('@')[-1]  # Log only host/db, not credentials
            )
            self.conn = psycopg.connect(
                self.settings.database_url,
                autocommit=True,
                row_factory=dict_row
            )
            logger.info("Database connection established successfully")
            
            # Test the connection by getting table info
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
                tables = cursor.fetchall()
                logger.debug("Available tables", tables=tables)
                
                # Report connection pool stats if metrics are enabled
                if settings.metrics_enabled:
                    from app.metrics.database import report_connection_pool_metrics
                    
                    # Get connection pool info if available
                    if hasattr(self.conn, 'info'):
                        conn_info = self.conn.info
                        if hasattr(conn_info, 'used') and hasattr(conn_info, 'size'):
                            report_connection_pool_metrics(
                                pool_name="postgres_main",
                                used_connections=conn_info.used,
                                total_connections=conn_info.size
                            )
        except psycopg.Error as e:
            logger.exception("Database connection failed")
            raise

    @matching_algorithm_timer("multiple_metrics_similarity")
    def get_top_jobs_by_multiple_metrics(
        self,
        cursor: psycopg.Cursor[dict],
        cv_embedding: List[float],
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> List[JobMatch]:
        """
        Get top matching jobs using multiple similarity metrics.

        Args:
            cursor: Database cursor for executing queries, configured to return dictionaries
            cv_embedding: The embedding vector of the CV
            location: Optional. Filter by job location if provided
            keywords: Optional. Filter by presence of ANY of the given keywords
                      in the job title or description
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List of JobMatch objects with normalized similarity scores
        """
        try:

            where_clauses = ["embedding IS NOT NULL"]
            count_params = []  # used for the COUNT & simpler fallback
            # embeddings_params will be the same as count_params, but we'll add embeddings later

            # Location filter
            if location and location.country:
                where_clauses.append("(co.country_name = CASE WHEN %s = 'USA' THEN 'United States' ELSE %s END)")
                count_params.extend([location.country, location.country])

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
                SELECT COUNT(*) AS count
                FROM "Jobs" j
                LEFT JOIN "Companies" c ON j.company_id = c.company_id
                LEFT JOIN "Locations" l ON j.location_id = l.location_id
                LEFT JOIN "Countries" co ON l.country = co.country_id
                {where_sql}
            """
            )

            logger.debug(
                "Executing count query",
                query=count_query.as_string(cursor.connection),
                params=count_params
            )
            # First check total number of jobs
            # Check what countries exist
            cursor.execute("""
                SELECT country_id, country_name
                FROM "Countries"
                ORDER BY country_name
            """)
            countries = cursor.fetchall()
            logger.debug(
                "Available countries",
                countries=countries
            )

            cursor.execute("SELECT COUNT(*) as count FROM \"Jobs\"")
            total_result = cursor.fetchone()
            logger.debug(
                "Total jobs in database",
                total_jobs=total_result['count']
            )

            # Then check jobs with embeddings
            cursor.execute("SELECT COUNT(*) as count FROM \"Jobs\" WHERE embedding IS NOT NULL")
            with_embedding_result = cursor.fetchone()
            logger.debug(
                "Jobs with embeddings",
                jobs_with_embedding=with_embedding_result['count']
            )

            # Then check jobs in USA
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM "Jobs" j
                LEFT JOIN "Locations" l ON j.location_id = l.location_id
                LEFT JOIN "Countries" co ON l.country = co.country_id
                WHERE co.country_name = 'United States'
            """)
            usa_result = cursor.fetchone()
            logger.debug(
                "Jobs in USA",
                jobs_in_usa=usa_result['count']
            )

            cursor.execute(count_query, count_params)
            result = cursor.fetchone()
            row_count = result['count'] if result else 0
            logger.debug(
                "Count query result",
                result=result,
                row_count=row_count
            )

            if row_count <= 5:
                simple_query = SQL(
                    f"""
                    SELECT
                        j.id as id,
                        j.title as title,
                        j.description as description,
                        j.workplace_type as workplace_type,
                        j.short_description as short_description,
                        j.field as field,
                        j.experience as experience,
                        j.skills_required as skills_required,
                        j.posted_date as posted_date,
                        j.job_state as job_state,
                        j.apply_link as apply_link,
                        co.country_name as country,
                        l.city as city,
                        c.company_name as company_name,
                        c.logo as company_logo,
                        'test_portal' as portal,
                        0.0 as score
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

                job_matches = []
                for row in results:
                    if job_match := self._create_job_match(row):
                        job_matches.append(job_match)
                
                # Report metrics for the fallback path
                if settings.metrics_enabled:
                    report_algorithm_path("simple_fallback", {"reason": "few_results"})
                    report_match_count(len(job_matches), {"path": "simple_fallback"})
                    
                return job_matches

            params = [cv_embedding, cv_embedding, cv_embedding]  # embeddings

            embeddings_params = params + count_params + [limit, offset]

            query = SQL(
                f"""
                WITH combined_scores AS (
                    SELECT
                        j.id as id,
                        j.title as title,
                        j.description as description,
                        j.workplace_type as workplace_type,
                        j.short_description as short_description,
                        j.field as field,
                        j.experience as experience,
                        j.skills_required as skills_required,
                        j.posted_date as posted_date,
                        j.job_state as job_state,
                        j.apply_link as apply_link,
                        co.country_name as country,
                        l.city as city,
                        c.company_name as company_name,
                        c.logo as company_logo,
                        'test_portal' as portal,
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
                        id,
                        title,
                        description,
                        workplace_type,
                        short_description,
                        field,
                        experience,
                        skills_required,
                        posted_date,
                        job_state,
                        apply_link,
                        country,
                        city,
                        company_name,
                        company_logo,
                        portal,
                        (
                            (1 - (l2_distance - MIN(l2_distance) OVER()) /
                            NULLIF(MAX(l2_distance) OVER() - MIN(l2_distance) OVER(), 0)) * 0.4
                        + (1 - (cosine_distance - MIN(cosine_distance) OVER()) /
                            NULLIF(MAX(cosine_distance) OVER() - MIN(cosine_distance) OVER(), 0)) * 0.4
                        + (
                            (inner_product - MIN(inner_product) OVER()) /
                            NULLIF(MAX(inner_product) OVER() - MIN(inner_product) OVER(), 0)
                            ) * 0.2
                        ) as score
                    FROM combined_scores
                )
                SELECT *
                FROM normalized_scores
                ORDER BY score DESC
                LIMIT %s
                OFFSET %s
            """
            )

            cursor.execute(query, embeddings_params)
            results = cursor.fetchall()

            job_matches = []
            for row in results:
                if job_match := self._create_job_match(row):
                    job_matches.append(job_match)
            
            # Report metrics for the vector similarity path
            if settings.metrics_enabled:
                report_algorithm_path("vector_similarity", {"reason": "normal"})
                report_match_count(len(job_matches), {"path": "vector_similarity"})
                
                # Report score distribution if we have matches
                if job_matches:
                    scores = [match.score for match in job_matches if match.score is not None]
                    if scores:
                        report_match_score_distribution(scores, {"path": "vector_similarity"})

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
            filename = f"job_matches_{resume_id}.json"
            with open(filename, "w") as f:
                json.dump(job_results, f, indent=2)

            logger.info("Matched jobs are: {job_results}", job_results=job_results, event_type="job_matches")

            # Save to MongoDB if flag is True
            if save_to_mongodb:
                from app.core.mongodb import database

                matches_collection = database.get_collection("job_matches")

                # Add metadata to job results
                job_results["resume_id"] = resume_id
                job_results["timestamp"] = datetime.now(UTC)

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

    @async_matching_algorithm_timer("process_job")
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

            logger.debug(
                "Processing resume",
                resume_data=resume,
                location=location,
                keywords=keywords,
                offset=offset
            )

            if not "vector" in resume.keys():
                logger.warning("No vector found in resume")
                return {}

            cv_embedding = resume["vector"]
            logger.debug("Using CV embedding", vector_length=len(cv_embedding))

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
                            "title": match.title,
                            "description": match.description,
                            "workplace_type": match.workplace_type,
                            "short_description": match.short_description,
                            "field": match.field,
                            "experience": match.experience,
                            "skills_required": match.skills_required,
                            "country": match.country,
                            "city": match.city,
                            "company_name": match.company_name,
                            "company_logo": match.company_logo,
                            "portal": match.portal,
                            "score": match.score,
                            "posted_date": match.posted_date.isoformat() if match.posted_date else None,
                            "job_state": match.job_state,
                            "apply_link": match.apply_link,
                            "location": match.location
                        }
                        for match in job_matches
                    ]
                }

                # Save matches to JSON and optionally MongoDB
                resume_id = str(resume.get("_id", "unknown"))
                #await self.save_matches(job_results, resume_id, save_to_mongodb)

                logger.success(
                    "Successfully processed job",
                    action="process_job",
                    status="success",
                    matches_found=len(job_results["jobs"]),
                )
                return job_results

        except Exception as e:
            logger.exception(
                "Failed to process job: {e}",
                e=e
            )
            raise

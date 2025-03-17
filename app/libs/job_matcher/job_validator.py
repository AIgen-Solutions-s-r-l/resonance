"""
Job validation and transformation functionality.

This module handles validation and creation of JobMatch objects from database rows.
"""

from typing import Optional, Dict, Any
from loguru import logger
from time import time

from app.utils.data_parsers import parse_skills_string
from app.libs.job_matcher.models import JobMatch
from app.libs.job_matcher.exceptions import ValidationError


class JobValidator:
    """Handles validation and transformation of job data."""
    
    # Required fields that must be present in database results
    REQUIRED_FIELDS = {'id', 'title'}

    """
    cosine similarity returns a value between 2 and 0, where lower is better.
    doing min I get 0.92 and max 1.1 and documenting ourselves in the case of posgres there are no negative values
    Score	Similarity
    0.0	    1.0000
    0.5	    1.0000
    0.7	    0.9990
    0.8	    0.9895
    0.9	    0.9800
    0.92	0.9480
    0.95	0.9000
    1.0	    0.8572
    1.5	    0.4287
    2.0	    0.0000
    """

    @staticmethod
    def score_to_percentage(score):
        if score <= 0.7:
            return 1.0000
        elif score <= 0.9:
            # From 0.7 to 0.9 → 0.999 to 0.98
            return round(0.999 - (0.095 * (score - 0.7)), 4)
        elif score <= 0.95:
            # From 0.9 to 0.95 → 0.98 to 0.9
            return round(0.98 - (1.6 * (score - 0.9)), 4)
        elif score <= 2.0:
            # From 0.95 to 2.0 → 0.9 to 0.0
            return round(max(0.9 - (0.857 * (score - 0.95)), 0.0), 4)
        else:
            return 0.0000
    
    def validate_row_data(self, row: dict) -> bool:
        """
        Validate that row has all required fields.
        
        Args:
            row: Dictionary containing database row data
            
        Returns:
            bool: True if all required fields are present, False otherwise
        """
        return all(field in row for field in self.REQUIRED_FIELDS)
    
    def create_job_match(self, row: dict) -> Optional[JobMatch]:
        """
        Create a JobMatch instance from a database row dictionary.
        
        Args:
            row: Dictionary containing job data from database
            
        Returns:
            JobMatch instance if successful, None if required fields are missing
        """
        start_time = time()
        if not isinstance(row, dict):
            logger.error(
                "Row is not a dictionary",
                row_type=type(row),
                row_data=row
            )
            try:
                row = dict(row)
            except Exception as e:
                logger.error(
                    "Failed to convert row to dictionary",
                    error=str(e),
                    error_type=type(e).__name__,
                    elapsed_time=f"{time() - start_time:.6f}s"
                )
                return None
                
        if not self.validate_row_data(row):
            logger.warning(
                "Skipping job match due to missing required fields",
                row=row,
                required_fields=self.REQUIRED_FIELDS
            )
            return None
            
        try:
            job_match = JobMatch(
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
                score=float(JobValidator.score_to_percentage(
                    row.get('score', 0.0))),
                posted_date=row.get('posted_date'),
                job_state=row.get('job_state'),
                apply_link=row.get('apply_link'),
                location=row.get('location')
            )
            
            elapsed = time() - start_time
            logger.trace(
                "Job match created",
                job_id=job_match.id,
                elapsed_time=f"{elapsed:.6f}s"
            )
            
            return job_match
            
        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                "Failed to create JobMatch instance",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s",
                row=row
            )
            return None


# Singleton instance
job_validator = JobValidator()
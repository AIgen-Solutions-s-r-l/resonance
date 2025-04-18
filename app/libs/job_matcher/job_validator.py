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
    0.0	    1.000
    0.1	    0.993
    0.2	    0.987
    0.3	    0.980
    0.4	    0.883
    0.5	    0.786
    0.6	    0.690
    0.7	    0.593
    0.8	    0.497
    0.9	    0.400
    0.95    0.300
    1.0	    0.200
    1.2	    0.160
    1.4	    0.120
    1.6	    0.080
    1.8	    0.040
    2.0	    0.000
    >2.0	0.000
    """

    @staticmethod
    def score_to_percentage(score):
        """
        Convert cosine similarity score to a percentage using an exponential transformation.
        
        Mathematical Theory:
        -------------------
        The exponential function f(x) = e^(-αx) has several properties that make it
        ideal for transforming similarity scores:
        
        1. It maps the domain [0, ∞) to the range (0, 1], with f(0) = 1
        2. It decreases monotonically, preserving the ordering of scores
        3. It has a non-linear decay rate, which helps spread out compressed scores
        
        For cosine similarity scores where:
        - 0 represents perfect similarity (should map to 100%)
        - 2 represents no similarity (should map to near 0%)
        
        We use the formula: percentage = 100 * e^(-α*score)
        
        Where α (alpha) controls the steepness of the decay:
        - Higher α values create steeper initial drops (better for distinguishing high similarities)
        - Lower α values create more gradual curves (better for distinguishing low similarities)
        
        With α = 3.0:
        - score = 0.0 → 100.00% (perfect match)
        - score = 0.1 → 74.08% (excellent match)
        - score = 0.3 → 40.66% (good match)
        - score = 0.5 → 22.31% (moderate match)
        - score = 0.7 → 12.25% (weak match)
        - score = 1.0 → 4.98% (poor match)
        - score = 2.0 → 0.25% (essentially no match)
        
        Why This Helps with Score Distribution:
        -------------------------------------
        1. The previous piecewise linear approach created artificial "steps" in the score
           distribution, compressing many scores into the 70-80% range.
        
        2. The exponential transformation provides a smooth, continuous curve that:
           - Maintains high sensitivity for the best matches (near 0 score)
           - Spreads out the middle range scores that were previously compressed
           - Rapidly approaches 0 for poor matches (high scores)
        
        3. The exponential nature better reflects the semantic meaning of similarity:
           small differences in highly similar items are more significant than
           the same numerical differences between dissimilar items.
        
        Args:
            score (float): Raw cosine similarity score (0 to 2, where 0 is perfect similarity)
            
        Returns:
            float: Percentage score (0 to 100, where 100 is perfect similarity)
        """
        import math
        
        # Alpha controls the steepness of the exponential decay
        alpha = 3.0
        
        # Apply exponential transformation
        # This maps score=0 to 100% and score=2 to approximately 0.25%
        if score < 0:
            # Handle potential negative scores (shouldn't occur in cosine similarity)
            return 100.0
        elif score > 2.0:
            # Cap extremely dissimilar scores at 0%
            return 0.0
        else:
            # Apply exponential transformation: 100 * e^(-alpha*score)
            percentage = 100.0 * math.exp(-alpha * score)
            return round(percentage, 2)

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
                skills_required=parse_skills_string(
                    row.get('skills_required')),
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

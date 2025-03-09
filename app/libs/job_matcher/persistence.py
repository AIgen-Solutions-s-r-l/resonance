"""
Persistence functionality for job matcher.

This module handles saving job matches to various stores.
"""

import json
from datetime import datetime, UTC
from typing import Dict, Any
from loguru import logger
from time import time

from app.libs.job_matcher.exceptions import PersistenceError


class JobMatchPersistence:
    """Handle persistence of job matches."""
    
    async def save_matches(
        self,
        job_results: Dict[str, Any], 
        resume_id: str, 
        save_to_mongodb: bool = False
    ) -> None:
        """
        Save job matches to JSON file and optionally to MongoDB.
        
        Args:
            job_results: Matching results
            resume_id: Resume ID
            save_to_mongodb: Whether to save to MongoDB
        """
        start_time = time()
        try:
            # Save to JSON
            filename = f"job_matches_{resume_id}.json"
            with open(filename, "w") as f:
                json.dump(job_results, f, indent=2)
            
            json_elapsed = time() - start_time
            logger.info(
                "Matched jobs saved to file",
                filename=filename,
                elapsed_time=f"{json_elapsed:.6f}s",
                job_count=len(job_results.get("jobs", []))
            )
            
            # Save to MongoDB if requested
            if save_to_mongodb:
                mongo_start = time()
                from app.core.mongodb import database
                
                matches_collection = database.get_collection("job_matches")
                
                # Add metadata to job results
                job_results_with_meta = job_results.copy()
                job_results_with_meta["resume_id"] = resume_id
                job_results_with_meta["timestamp"] = datetime.now(UTC)
                
                await matches_collection.insert_one(job_results_with_meta)
                
                mongo_elapsed = time() - mongo_start
                logger.info(
                    "Successfully saved matches to MongoDB",
                    resume_id=resume_id,
                    elapsed_time=f"{mongo_elapsed:.6f}s"
                )
            
            total_elapsed = time() - start_time
            logger.success(
                "All persistence operations completed",
                elapsed_time=f"{total_elapsed:.6f}s"
            )
            
        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                "Failed to save matches",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s",
                resume_id=resume_id
            )
            raise PersistenceError(f"Failed to save matches: {str(e)}")


# Singleton instance
persistence = JobMatchPersistence()
"""
Test script to verify that apply_link, portal, and location fields are not returned in API responses.
"""

import asyncio
import json
from app.libs.job_matcher.models import JobMatch

async def test_job_match_to_dict():
    """Test that JobMatch.to_dict() excludes apply_link, portal, and location fields."""
    # Create a JobMatch instance with all fields
    job_match = JobMatch(
        id="123e4567-e89b-12d3-a456-426614174000",
        title="Software Engineer",
        description="A software engineering position",
        workplace_type="Remote",
        short_description="SE position",
        field="Software",
        experience="Mid-level",
        skills_required=["Python", "FastAPI"],
        country="USA",
        city="New York",
        company_name="Example Corp",
        company_logo="https://example.com/logo.png",
        portal="example_portal",
        score=95.5,
        posted_date=None,
        job_state="active",
        apply_link="https://example.com/apply",
        location="New York, USA"
    )
    
    # Convert to dictionary
    job_dict = job_match.to_dict()
    
    # Print the dictionary for inspection
    print("JobMatch.to_dict() result:")
    print(json.dumps(job_dict, indent=2))
    
    # Check that the fields are excluded
    assert "apply_link" not in job_dict, "apply_link field should be excluded"
    assert "portal" not in job_dict, "portal field should be excluded"
    assert "location" not in job_dict, "location field should be excluded"
    
    # Check that other fields are included
    assert "id" in job_dict, "id field should be included"
    assert "title" in job_dict, "title field should be included"
    assert "description" in job_dict, "description field should be included"
    
    print("All assertions passed! The fields are correctly excluded from the API responses.")

if __name__ == "__main__":
    asyncio.run(test_job_match_to_dict())
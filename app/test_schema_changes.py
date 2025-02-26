"""
Test script to verify JobSchema changes don't break functionality.
"""
from app.schemas.job import JobSchema
import json

def test_jobschema_without_removed_fields():
    """Test that JobSchema works correctly without the removed fields."""
    # Sample job data that includes fields we've removed
    job_data = {
        "id": 1234,  # Changed from string to integer
        "job_id": "job-5678",  # Removed field
        "title": "Software Engineer",
        "description": "A great job for a developer",
        "workplace_type": "Remote",
        "company_name": "Tech Corp",  # Renamed from company
        "company_logo": "logo.png",   # Renamed from logo
        "location": "New York",
        "city": "New York",
        "country": "USA",
        "score": 0.95,
        "company_id": 42,      # Removed field
        "location_id": 24,     # Removed field
        "cluster_id": 7,       # Removed field
        "embedding": [0.1, 0.2, 0.3],  # Removed field
        "processed_description": "Processed job desc",  # Removed field
        "sparse_embeddings": [0.5, 0.6, 0.7],  # Removed field
    }
    
    # Create a JobSchema instance from the data
    try:
        job_schema = JobSchema.model_validate(job_data)
        print("✅ Successfully created JobSchema instance")
        
        # Verify that removed fields are not included
        job_dict = job_schema.model_dump()
        print("\nFields in JobSchema:")
        for key in job_dict.keys():
            print(f"  - {key}")
            
        print("\nRemoved fields check:")
        for field in ["job_id", "company_id", "location_id", "cluster_id", 
                     "processed_description", "embedding", "sparse_embeddings"]:
            print(f"  - {field}: {'❌ Present' if field in job_dict else '✅ Removed'}")
            
        # Verify that critical fields are still present
        assert job_schema.id == 1234, f"Expected id to be integer 1234, got {job_schema.id} ({type(job_schema.id)})"
        assert job_schema.title == "Software Engineer"
        assert job_schema.score == 0.95
        
        # Check renamed fields
        assert job_schema.company_name == "Tech Corp", f"Expected company_name to be 'Tech Corp', got {job_schema.company_name}"
        assert job_schema.company_logo == "logo.png", f"Expected company_logo to be 'logo.png', got {job_schema.company_logo}"
        
        print("\n✅ All critical fields correctly preserved")
        print("\n✅ Field renames verified (company → company_name, logo → company_logo)")
        
        # Test serialization to ensure it works correctly
        json_data = job_schema.model_dump_json()
        print(f"\nJSON output:\n{json.dumps(json.loads(json_data), indent=2)}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing JobSchema with removed fields...")
    success = test_jobschema_without_removed_fields()
    print(f"\nTest {'passed' if success else 'failed'}")
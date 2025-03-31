import asyncio
from app.schemas.location import LocationFilter
from app.libs.job_matcher.vector_matcher import vector_matcher

async def test_keyword_search():
    """Test that keyword search with '%' characters in SQL works properly."""
    print("Testing keyword search with special SQL characters...")
    
    # Create a simple embedding (1024 dimensions of zeros)
    embedding = [0.0] * 1024
    
    # Test with keywords that would trigger the previous error
    keywords = ["ruby", "python"]
    location = LocationFilter(
        country="Germany",
        city=None,
        latitude=None,
        longitude=None,
        radius_km=20.0
    )
    
    try:
        # This would have failed before with: only '%s', '%b', '%t' are allowed as placeholders, got '%''
        results = await vector_matcher.get_top_jobs_by_vector_similarity(
            cv_embedding=embedding,
            location=location, 
            keywords=keywords
        )
        print(f"Search successful! Found {len(results)} matching jobs.")
        return True
    except Exception as e:
        print(f"Search failed with error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_keyword_search())
    if success:
        print("✅ PASS: The fix for keyword search was successful!")
    else:
        print("❌ FAIL: The fix did not resolve the issue.")
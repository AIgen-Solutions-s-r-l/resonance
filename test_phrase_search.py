import asyncio
from app.schemas.location import LocationFilter
from app.libs.job_matcher.vector_matcher import vector_matcher
from app.libs.job_matcher.query_builder import query_builder

async def test_phrase_search():
    """Test that phrase search works properly."""
    print("Testing phrase search functionality...")
    
    # Create a simple embedding (1024 dimensions of zeros)
    embedding = [0.0] * 1024
    
    # Test with a multi-word phrase
    phrase = ["business account manager"]
    location = LocationFilter(
        country="Germany",
        city=None,
        latitude=None,
        longitude=None,
        radius_km=20.0
    )
    
    # First, let's check how the query is built
    print("Testing query building for phrase search...")
    where_clauses, query_params = query_builder.build_filter_conditions(
        location=location,
        keywords=phrase
    )
    
    print(f"Generated where clauses: {where_clauses}")
    print(f"Generated query params: {query_params}")
    
    # Now test the actual search
    try:
        print("Executing search with phrase...")
        results = await vector_matcher.get_top_jobs_by_vector_similarity(
            cv_embedding=embedding,
            location=location, 
            keywords=phrase
        )
        print(f"Search successful! Found {len(results)} matching jobs.")
        
        # Test with multiple keywords that might be a split phrase
        split_phrase = ["business", "account", "manager"]
        print("\nTesting with split phrase...")
        where_clauses, query_params = query_builder.build_filter_conditions(
            location=location,
            keywords=split_phrase
        )
        
        print(f"Generated where clauses for split phrase: {where_clauses}")
        print(f"Generated query params for split phrase: {query_params}")
        
        results = await vector_matcher.get_top_jobs_by_vector_similarity(
            cv_embedding=embedding,
            location=location, 
            keywords=split_phrase
        )
        print(f"Search successful! Found {len(results)} matching jobs.")
        
        return True
    except Exception as e:
        print(f"Search failed with error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_phrase_search())
    if success:
        print("✅ PASS: The phrase search functionality works correctly!")
    else:
        print("❌ FAIL: The phrase search functionality has issues.")
"""
Test script to verify the embedding format handling fix.
"""

import asyncio
from app.libs.job_matcher.vector_matcher import vector_matcher
from loguru import logger

async def test_string_embedding():
    """Test with a string embedding format."""
    try:
        # Test with a string representation of an embedding
        string_embedding = "[0.1, 0.2, 0.3, 0.4, 0.5]"
        logger.info(f"Testing with string embedding: {string_embedding}")
        
        # This should now work with our fixes
        results = await vector_matcher.get_top_jobs_by_vector_similarity(
            cv_embedding=string_embedding,
            limit=2
        )
        
        logger.info(f"Test passed! Got {len(results)} results")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

async def test_list_embedding():
    """Test with a proper list embedding format."""
    try:
        # Test with a proper list of floats
        list_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        logger.info(f"Testing with list embedding: {list_embedding}")
        
        # This should work as before
        results = await vector_matcher.get_top_jobs_by_vector_similarity(
            cv_embedding=list_embedding,
            limit=2
        )
        
        logger.info(f"Test passed! Got {len(results)} results")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

async def main():
    """Run all tests."""
    string_test = await test_string_embedding()
    list_test = await test_list_embedding()
    
    if string_test and list_test:
        print("✅ All tests passed! The fix is working correctly.")
    else:
        print("❌ Some tests failed. The fix needs more work.")

if __name__ == "__main__":
    asyncio.run(main())
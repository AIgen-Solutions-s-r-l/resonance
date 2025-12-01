"""Tests for BM25 Index."""

import pytest
import tempfile
from pathlib import Path

from app.ml.training.bm25_index import BM25Index, BM25Document


class TestBM25Index:
    """Test cases for BM25Index."""

    def test_initialization(self):
        """Test BM25Index initialization with default parameters."""
        index = BM25Index()

        assert index.k1 == 1.5
        assert index.b == 0.75
        assert len(index) == 0
        assert not index._is_built

    def test_initialization_custom_params(self):
        """Test BM25Index with custom parameters."""
        index = BM25Index(k1=2.0, b=0.5)

        assert index.k1 == 2.0
        assert index.b == 0.5

    def test_tokenize_basic(self):
        """Test basic tokenization."""
        index = BM25Index()

        tokens = index.tokenize("Python Developer with FastAPI experience")

        assert "python" in tokens
        assert "developer" in tokens
        assert "fastapi" in tokens
        assert "experience" in tokens
        # Stopwords should be filtered
        assert "with" not in tokens

    def test_tokenize_special_chars(self):
        """Test tokenization with special characters."""
        index = BM25Index()

        tokens = index.tokenize("C++ and C# developers needed!")

        # Should handle programming language names
        assert len(tokens) > 0

    def test_add_document(self):
        """Test adding a single document."""
        index = BM25Index()

        index.add_document("job1", "Senior Python Developer")

        assert "job1" in index
        assert len(index.documents) == 1
        assert not index._is_built

    def test_add_documents(self):
        """Test adding multiple documents."""
        index = BM25Index()

        documents = [
            ("job1", "Senior Python Developer"),
            ("job2", "Junior JavaScript Developer"),
            ("job3", "Full Stack Engineer"),
        ]

        index.add_documents(documents)

        assert len(index.documents) == 3
        assert "job1" in index
        assert "job2" in index
        assert "job3" in index

    def test_build_index(self):
        """Test building the index."""
        index = BM25Index()

        documents = [
            ("job1", "Senior Python Developer"),
            ("job2", "Junior Python Developer"),
            ("job3", "Full Stack JavaScript Engineer"),
        ]
        index.add_documents(documents)
        index.build()

        assert index._is_built
        assert index.doc_count == 3
        assert index.avg_doc_length > 0
        assert len(index.doc_frequencies) > 0
        assert "python" in index.doc_frequencies
        assert index.doc_frequencies["python"] == 2  # Appears in 2 docs

    def test_search_basic(self):
        """Test basic search functionality."""
        index = BM25Index()

        documents = [
            ("job1", "Senior Python Developer with FastAPI"),
            ("job2", "Junior JavaScript Developer with React"),
            ("job3", "Python Machine Learning Engineer"),
            ("job4", "DevOps Engineer with Kubernetes"),
        ]
        index.add_documents(documents)
        index.build()

        results = index.search("Python developer", top_k=3)

        assert len(results) > 0
        # Python jobs should rank higher
        top_ids = [r[0] for r in results[:2]]
        assert "job1" in top_ids or "job3" in top_ids

    def test_search_with_exclusions(self):
        """Test search with excluded IDs."""
        index = BM25Index()

        documents = [
            ("job1", "Senior Python Developer"),
            ("job2", "Junior Python Developer"),
            ("job3", "Python Engineer"),
        ]
        index.add_documents(documents)
        index.build()

        results = index.search(
            "Python developer",
            top_k=10,
            exclude_ids={"job1", "job2"}
        )

        result_ids = [r[0] for r in results]
        assert "job1" not in result_ids
        assert "job2" not in result_ids
        assert "job3" in result_ids

    def test_search_empty_query(self):
        """Test search with empty query."""
        index = BM25Index()

        documents = [("job1", "Python Developer")]
        index.add_documents(documents)
        index.build()

        results = index.search("", top_k=10)

        assert len(results) == 0

    def test_search_no_matches(self):
        """Test search with no matching documents."""
        index = BM25Index()

        documents = [
            ("job1", "Python Developer"),
            ("job2", "JavaScript Developer"),
        ]
        index.add_documents(documents)
        index.build()

        results = index.search("Rust embedded systems", top_k=10)

        # May return results with partial matches or empty
        # The key is it shouldn't crash
        assert isinstance(results, list)

    def test_save_and_load(self):
        """Test saving and loading the index."""
        index = BM25Index()

        documents = [
            ("job1", "Senior Python Developer"),
            ("job2", "Junior JavaScript Developer"),
        ]
        index.add_documents(documents)
        index.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "bm25_index.pkl"
            index.save(save_path)

            loaded_index = BM25Index.load(save_path)

            assert len(loaded_index) == len(index)
            assert loaded_index.k1 == index.k1
            assert loaded_index.b == index.b
            assert loaded_index._is_built

            # Search should work on loaded index
            results = loaded_index.search("Python", top_k=5)
            assert len(results) > 0

    def test_build_empty_index(self):
        """Test building an empty index."""
        index = BM25Index()
        index.build()

        assert index._is_built
        assert index.doc_count == 0

        results = index.search("Python", top_k=5)
        assert len(results) == 0

    def test_idf_calculation(self):
        """Test IDF values are calculated correctly."""
        index = BM25Index()

        # Add documents where 'python' appears in all
        # and 'fastapi' appears in only one
        documents = [
            ("job1", "Python FastAPI Developer"),
            ("job2", "Python Django Developer"),
            ("job3", "Python Flask Developer"),
        ]
        index.add_documents(documents)
        index.build()

        # 'fastapi' should have higher IDF (rarer term)
        assert index.idf_cache["fastapi"] > index.idf_cache["python"]

    def test_bm25_scoring(self):
        """Test BM25 scoring produces reasonable results."""
        index = BM25Index()

        documents = [
            ("job1", "Python Python Python Developer"),  # High TF for Python
            ("job2", "Python Developer"),  # Normal TF
            ("job3", "JavaScript Developer"),  # No Python
        ]
        index.add_documents(documents)
        index.build()

        results = index.search("Python", top_k=3)

        # job1 should rank first (higher TF)
        assert results[0][0] == "job1"
        # job3 should not appear or rank last
        if len(results) == 3:
            assert results[2][0] == "job3"

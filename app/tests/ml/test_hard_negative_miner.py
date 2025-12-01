"""Tests for Hard Negative Miner."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from app.ml.training.hard_negative_miner import HardNegativeMiner, JobCandidate
from app.ml.training.bm25_index import BM25Index
from app.ml.training.dataset import TrainingSample


class TestJobCandidate:
    """Test cases for JobCandidate dataclass."""

    def test_creation(self):
        """Test JobCandidate creation."""
        candidate = JobCandidate(
            job_id="job1",
            text="Python Developer",
            bm25_score=0.5,
            embedding_score=0.7,
        )

        assert candidate.job_id == "job1"
        assert candidate.text == "Python Developer"
        assert candidate.bm25_score == 0.5
        assert candidate.embedding_score == 0.7
        assert candidate.combined_score == 0.0


class TestHardNegativeMiner:
    """Test cases for HardNegativeMiner."""

    @pytest.fixture
    def sample_jobs(self):
        """Sample job documents for testing."""
        return [
            ("job1", "Senior Python Developer with FastAPI experience"),
            ("job2", "Junior JavaScript Developer with React"),
            ("job3", "Python Machine Learning Engineer"),
            ("job4", "DevOps Engineer with Kubernetes"),
            ("job5", "Full Stack Python Developer"),
            ("job6", "Data Scientist with Python"),
            ("job7", "Frontend Developer with Vue.js"),
            ("job8", "Backend Engineer with Node.js"),
        ]

    @pytest.fixture
    def bm25_index(self, sample_jobs):
        """Create a BM25 index with sample jobs."""
        index = BM25Index()
        index.add_documents(sample_jobs)
        index.build()
        return index

    @pytest.fixture
    def miner(self, bm25_index):
        """Create a HardNegativeMiner with pre-built index."""
        miner = HardNegativeMiner(
            bm25_index=bm25_index,
            hard_negative_ratio=3,
            min_similarity=0.1,
            max_similarity=0.95,
        )

        # Add job texts
        for job_id, text in [
            ("job1", "Senior Python Developer with FastAPI experience"),
            ("job2", "Junior JavaScript Developer with React"),
            ("job3", "Python Machine Learning Engineer"),
            ("job4", "DevOps Engineer with Kubernetes"),
            ("job5", "Full Stack Python Developer"),
            ("job6", "Data Scientist with Python"),
            ("job7", "Frontend Developer with Vue.js"),
            ("job8", "Backend Engineer with Node.js"),
        ]:
            miner._job_texts[job_id] = text

        return miner

    def test_initialization(self):
        """Test HardNegativeMiner initialization."""
        miner = HardNegativeMiner()

        assert miner.hard_negative_ratio == 7  # Default from config
        assert miner.min_similarity == 0.3
        assert miner.max_similarity == 0.9

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        miner = HardNegativeMiner(
            hard_negative_ratio=5,
            min_similarity=0.2,
            max_similarity=0.8,
        )

        assert miner.hard_negative_ratio == 5
        assert miner.min_similarity == 0.2
        assert miner.max_similarity == 0.8

    def test_cosine_similarity(self, miner):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        sim = miner._cosine_similarity(vec1, vec2)
        assert sim == pytest.approx(1.0, abs=0.01)

        vec3 = [0.0, 1.0, 0.0]
        sim_orth = miner._cosine_similarity(vec1, vec3)
        assert sim_orth == pytest.approx(0.0, abs=0.01)

        vec4 = [-1.0, 0.0, 0.0]
        sim_opp = miner._cosine_similarity(vec1, vec4)
        assert sim_opp == pytest.approx(-1.0, abs=0.01)

    def test_cosine_similarity_zero_vector(self, miner):
        """Test cosine similarity with zero vector."""
        vec1 = [1.0, 0.0, 0.0]
        vec_zero = [0.0, 0.0, 0.0]

        sim = miner._cosine_similarity(vec1, vec_zero)
        assert sim == 0.0

    def test_mine_bm25_negatives(self, miner):
        """Test BM25-based negative mining."""
        resume_text = "Experienced Python developer with FastAPI and machine learning skills"
        positive_job_ids = {"job1"}  # Exclude this job

        candidates = miner.mine_bm25_negatives(
            resume_text=resume_text,
            positive_job_ids=positive_job_ids,
            k=5,
        )

        assert len(candidates) > 0
        # job1 should be excluded
        candidate_ids = [c.job_id for c in candidates]
        assert "job1" not in candidate_ids

        # Python-related jobs should rank higher
        # (job3, job5, job6 are Python jobs)
        top_3_ids = candidate_ids[:3]
        python_jobs_in_top_3 = sum(1 for jid in top_3_ids if jid in ["job3", "job5", "job6"])
        assert python_jobs_in_top_3 >= 1

    def test_mine_bm25_negatives_exclude_multiple(self, miner):
        """Test BM25 mining with multiple exclusions."""
        resume_text = "Python developer"
        positive_job_ids = {"job1", "job3", "job5"}

        candidates = miner.mine_bm25_negatives(
            resume_text=resume_text,
            positive_job_ids=positive_job_ids,
            k=10,
        )

        candidate_ids = set(c.job_id for c in candidates)
        assert "job1" not in candidate_ids
        assert "job3" not in candidate_ids
        assert "job5" not in candidate_ids

    def test_mine_embedding_negatives(self, miner):
        """Test embedding-based negative mining."""
        # Create fake embeddings
        dim = 3
        miner._job_embeddings = {
            "job1": [1.0, 0.0, 0.0],
            "job2": [0.0, 1.0, 0.0],
            "job3": [0.9, 0.1, 0.0],  # Similar to job1
            "job4": [0.0, 0.0, 1.0],
            "job5": [0.8, 0.2, 0.0],  # Similar to job1
        }

        resume_embedding = [1.0, 0.0, 0.0]
        positive_job_ids = {"job1"}

        candidates = miner.mine_embedding_negatives(
            resume_embedding=resume_embedding,
            positive_job_ids=positive_job_ids,
            k=3,
        )

        assert len(candidates) > 0
        # job1 should be excluded
        candidate_ids = [c.job_id for c in candidates]
        assert "job1" not in candidate_ids

        # job3 and job5 should rank high (similar embeddings)
        if len(candidates) >= 2:
            top_2_ids = set(candidate_ids[:2])
            assert "job3" in top_2_ids or "job5" in top_2_ids

    def test_mine_embedding_negatives_no_embeddings(self, miner):
        """Test embedding mining when no embeddings available."""
        miner._job_embeddings = {}

        candidates = miner.mine_embedding_negatives(
            resume_embedding=[1.0, 0.0, 0.0],
            positive_job_ids=set(),
            k=5,
        )

        assert len(candidates) == 0

    def test_mine_combined_negatives(self, miner):
        """Test combined negative mining."""
        # Add embeddings
        miner._job_embeddings = {
            "job1": [1.0, 0.0, 0.0],
            "job2": [0.0, 1.0, 0.0],
            "job3": [0.9, 0.1, 0.0],
            "job5": [0.8, 0.2, 0.0],
            "job6": [0.7, 0.3, 0.0],
        }

        resume_text = "Python developer with machine learning experience"
        resume_embedding = [1.0, 0.0, 0.0]
        positive_job_ids = {"job1"}

        candidates = miner.mine_combined_negatives(
            resume_text=resume_text,
            resume_embedding=resume_embedding,
            positive_job_ids=positive_job_ids,
            k=3,
        )

        assert len(candidates) == 3
        assert all(c.combined_score > 0 for c in candidates)
        # Sorted by combined score
        scores = [c.combined_score for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_mine_combined_negatives_no_embedding(self, miner):
        """Test combined mining without resume embedding."""
        resume_text = "Python developer"

        candidates = miner.mine_combined_negatives(
            resume_text=resume_text,
            resume_embedding=None,
            positive_job_ids={"job1"},
            k=3,
        )

        # Should still work using BM25 only
        assert len(candidates) > 0

    @pytest.mark.asyncio
    async def test_create_training_sample(self, miner):
        """Test creating a training sample."""
        sample = await miner.create_training_sample(
            resume_id="resume1",
            resume_text="Experienced Python developer",
            resume_embedding=[1.0, 0.0, 0.0],
            positive_job_id="job1",
            positive_job_text="Senior Python Developer",
            applied_job_ids={"job1", "job2"},
            source="application",
        )

        assert isinstance(sample, TrainingSample)
        assert sample.resume_id == "resume1"
        assert sample.positive_job_id == "job1"
        assert len(sample.hard_negative_job_ids) <= miner.hard_negative_ratio
        assert "job1" not in sample.hard_negative_job_ids
        assert "job2" not in sample.hard_negative_job_ids
        assert sample.source == "application"
        assert sample.mining_strategy == "combined"

    def test_get_statistics(self, miner):
        """Test getting miner statistics."""
        # Add some embeddings
        miner._job_embeddings = {"job1": [1.0, 0.0]}

        stats = miner.get_statistics()

        assert stats["bm25_index_size"] == 8
        assert stats["job_embeddings_count"] == 1
        assert stats["job_texts_count"] == 8
        assert stats["hard_negative_ratio"] == 3


class TestHardNegativeMinerIntegration:
    """Integration tests for HardNegativeMiner."""

    @pytest.mark.asyncio
    async def test_load_jobs_from_db(self):
        """Test loading jobs from database (mocked)."""
        miner = HardNegativeMiner()

        mock_rows = [
            {
                "id": "uuid-1",
                "title": "Python Developer",
                "description": "We are looking for a Python developer",
                "embedding": [0.1] * 1024,
            },
            {
                "id": "uuid-2",
                "title": "JavaScript Developer",
                "description": "Frontend developer needed",
                "embedding": [0.2] * 1024,
            },
        ]

        with patch("app.ml.training.hard_negative_miner.get_db_cursor") as mock_cursor:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.execute = AsyncMock()
            mock_ctx.fetchall = AsyncMock(return_value=mock_rows)
            mock_cursor.return_value = mock_ctx

            count = await miner.load_jobs_from_db()

            assert count == 2
            assert len(miner.bm25_index) == 2
            assert len(miner._job_embeddings) == 2

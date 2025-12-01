"""Tests for Training Dataset."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from app.ml.training.dataset import TrainingSample, TrainingBatch, TrainingDataset


class TestTrainingSample:
    """Test cases for TrainingSample."""

    def test_creation(self):
        """Test TrainingSample creation."""
        sample = TrainingSample(
            sample_id="sample1",
            resume_id="resume1",
            resume_text="Experienced Python developer",
            positive_job_id="job1",
            positive_job_text="Senior Python Developer",
            hard_negative_job_ids=["job2", "job3"],
            hard_negative_job_texts=["JavaScript Dev", "Java Dev"],
        )

        assert sample.sample_id == "sample1"
        assert sample.resume_id == "resume1"
        assert sample.positive_job_id == "job1"
        assert len(sample.hard_negative_job_ids) == 2

    def test_to_dict(self):
        """Test conversion to dictionary."""
        sample = TrainingSample(
            sample_id="sample1",
            resume_id="resume1",
            resume_text="Python developer",
            positive_job_id="job1",
            positive_job_text="Python Dev",
            source="application",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
        )

        data = sample.to_dict()

        assert data["sample_id"] == "sample1"
        assert data["resume_id"] == "resume1"
        assert data["source"] == "application"
        assert data["timestamp"] == "2025-01-01T12:00:00"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "sample_id": "sample1",
            "resume_id": "resume1",
            "resume_text": "Python developer",
            "positive_job_id": "job1",
            "positive_job_text": "Python Dev",
            "hard_negative_job_ids": ["job2"],
            "hard_negative_job_texts": ["Java Dev"],
            "source": "hire",
            "timestamp": "2025-01-01T12:00:00",
            "mining_strategy": "bm25",
        }

        sample = TrainingSample.from_dict(data)

        assert sample.sample_id == "sample1"
        assert sample.source == "hire"
        assert sample.mining_strategy == "bm25"
        assert sample.timestamp == datetime(2025, 1, 1, 12, 0, 0)

    def test_from_dict_missing_optional(self):
        """Test creation from dict with missing optional fields."""
        data = {
            "sample_id": "sample1",
            "resume_id": "resume1",
            "resume_text": "Developer",
        }

        sample = TrainingSample.from_dict(data)

        assert sample.sample_id == "sample1"
        assert sample.positive_job_id == ""
        assert sample.hard_negative_job_ids == []
        assert sample.source == "application"
        assert sample.timestamp is None


class TestTrainingBatch:
    """Test cases for TrainingBatch."""

    def test_creation(self):
        """Test TrainingBatch creation."""
        batch = TrainingBatch(
            resume_texts=["Resume 1", "Resume 2"],
            positive_job_texts=["Job 1", "Job 2"],
            negative_job_texts=[["Neg1A", "Neg1B"], ["Neg2A", "Neg2B"]],
            sample_ids=["s1", "s2"],
        )

        assert len(batch) == 2
        assert batch.resume_texts[0] == "Resume 1"
        assert len(batch.negative_job_texts[0]) == 2


class TestTrainingDataset:
    """Test cases for TrainingDataset."""

    @pytest.fixture
    def sample_samples(self):
        """Create sample training samples."""
        return [
            TrainingSample(
                sample_id=f"sample{i}",
                resume_id=f"resume{i}",
                resume_text=f"Developer {i}",
                positive_job_id=f"job{i}",
                positive_job_text=f"Job {i}",
                hard_negative_job_ids=[f"neg{i}a", f"neg{i}b"],
                hard_negative_job_texts=[f"Neg {i}A", f"Neg {i}B"],
            )
            for i in range(100)
        ]

    def test_initialization_empty(self):
        """Test empty dataset initialization."""
        dataset = TrainingDataset()

        assert len(dataset) == 0
        assert dataset.validation_split == 0.1
        assert dataset.test_split == 0.1

    def test_initialization_with_samples(self, sample_samples):
        """Test initialization with samples."""
        dataset = TrainingDataset(samples=sample_samples)

        assert len(dataset) == 100

    def test_add_sample(self):
        """Test adding a single sample."""
        dataset = TrainingDataset()

        sample = TrainingSample(
            sample_id="s1",
            resume_id="r1",
            resume_text="Developer",
        )
        dataset.add_sample(sample)

        assert len(dataset) == 1

    def test_add_samples(self, sample_samples):
        """Test adding multiple samples."""
        dataset = TrainingDataset()
        dataset.add_samples(sample_samples[:10])

        assert len(dataset) == 10

    def test_split(self, sample_samples):
        """Test dataset splitting."""
        dataset = TrainingDataset(
            samples=sample_samples,
            validation_split=0.1,
            test_split=0.1,
        )
        dataset.split(seed=42)

        assert len(dataset.train_samples) == 80
        assert len(dataset.val_samples) == 10
        assert len(dataset.test_samples) == 10

        # Check no overlap
        train_ids = set(s.sample_id for s in dataset.train_samples)
        val_ids = set(s.sample_id for s in dataset.val_samples)
        test_ids = set(s.sample_id for s in dataset.test_samples)

        assert len(train_ids & val_ids) == 0
        assert len(train_ids & test_ids) == 0
        assert len(val_ids & test_ids) == 0

    def test_split_no_shuffle(self, sample_samples):
        """Test splitting without shuffle."""
        dataset = TrainingDataset(samples=sample_samples)
        dataset.split(shuffle=False)

        # First 80 should be train
        assert dataset.train_samples[0].sample_id == "sample0"

    def test_get_batches(self, sample_samples):
        """Test batch iteration."""
        dataset = TrainingDataset(samples=sample_samples)
        dataset.split()

        batches = list(dataset.get_batches(split="train", batch_size=16, shuffle=False))

        assert len(batches) == 5  # 80 / 16 = 5
        assert len(batches[0]) == 16

    def test_get_batches_last_incomplete(self, sample_samples):
        """Test that last batch can be incomplete."""
        dataset = TrainingDataset(samples=sample_samples[:25])
        dataset.split(shuffle=False)  # 20 train, 2 val, 3 test

        batches = list(dataset.get_batches(split="train", batch_size=8, shuffle=False))

        # 20 samples / 8 = 2.5 -> 3 batches
        assert len(batches) == 3
        assert len(batches[-1]) == 4  # Last batch has 4 samples

    def test_get_batches_validation(self, sample_samples):
        """Test getting validation batches."""
        dataset = TrainingDataset(samples=sample_samples)
        dataset.split()

        batches = list(dataset.get_batches(split="val", batch_size=5))

        assert len(batches) == 2  # 10 / 5 = 2

    def test_save_and_load(self, sample_samples):
        """Test saving and loading dataset."""
        dataset = TrainingDataset(samples=sample_samples[:10])

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "dataset"
            dataset.save(save_path)

            loaded = TrainingDataset.load(save_path)

            assert len(loaded) == 10
            assert loaded.samples[0].sample_id == dataset.samples[0].sample_id

    def test_get_statistics(self, sample_samples):
        """Test getting dataset statistics."""
        dataset = TrainingDataset(samples=sample_samples)
        dataset.split()

        stats = dataset.get_statistics()

        assert stats["sample_count"] == 100
        assert stats["avg_hard_negatives"] == 2.0
        assert stats["train_count"] == 80
        assert stats["val_count"] == 10
        assert stats["test_count"] == 10

    def test_get_statistics_empty(self):
        """Test statistics for empty dataset."""
        dataset = TrainingDataset()
        stats = dataset.get_statistics()

        assert stats["sample_count"] == 0

    def test_indexing(self, sample_samples):
        """Test dataset indexing."""
        dataset = TrainingDataset(samples=sample_samples)

        assert dataset[0].sample_id == "sample0"
        assert dataset[50].sample_id == "sample50"

    def test_properties_auto_split(self, sample_samples):
        """Test that accessing properties triggers split."""
        dataset = TrainingDataset(samples=sample_samples)

        # Accessing train_samples should trigger split
        train = dataset.train_samples

        assert len(train) == 80
        assert dataset._is_split

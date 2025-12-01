"""
Training dataset management for Resonance v2.

Handles loading, preprocessing, and batching of training data
for contrastive learning.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator, Tuple
from pathlib import Path
import json
import random
from datetime import datetime

from app.log.logging import logger
from app.ml.config import ml_config


@dataclass
class TrainingSample:
    """
    A single training sample for contrastive learning.

    Contains a resume, a positive job (applied/hired), and hard negatives.
    """
    sample_id: str
    resume_id: str
    resume_text: str
    resume_embedding: Optional[List[float]] = None

    positive_job_id: str = ""
    positive_job_text: str = ""
    positive_job_embedding: Optional[List[float]] = None

    hard_negative_job_ids: List[str] = field(default_factory=list)
    hard_negative_job_texts: List[str] = field(default_factory=list)
    hard_negative_job_embeddings: List[List[float]] = field(default_factory=list)

    # Metadata
    source: str = "application"  # application, hire, feedback
    timestamp: Optional[datetime] = None
    mining_strategy: str = "combined"  # bm25, embedding, combined

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sample_id": self.sample_id,
            "resume_id": self.resume_id,
            "resume_text": self.resume_text,
            "positive_job_id": self.positive_job_id,
            "positive_job_text": self.positive_job_text,
            "hard_negative_job_ids": self.hard_negative_job_ids,
            "hard_negative_job_texts": self.hard_negative_job_texts,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "mining_strategy": self.mining_strategy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingSample":
        """Create from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])

        return cls(
            sample_id=data["sample_id"],
            resume_id=data["resume_id"],
            resume_text=data["resume_text"],
            positive_job_id=data.get("positive_job_id", ""),
            positive_job_text=data.get("positive_job_text", ""),
            hard_negative_job_ids=data.get("hard_negative_job_ids", []),
            hard_negative_job_texts=data.get("hard_negative_job_texts", []),
            source=data.get("source", "application"),
            timestamp=timestamp,
            mining_strategy=data.get("mining_strategy", "combined"),
        )


@dataclass
class TrainingBatch:
    """A batch of training samples."""
    resume_texts: List[str]
    positive_job_texts: List[str]
    negative_job_texts: List[List[str]]  # List of negatives per sample

    sample_ids: List[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.resume_texts)


class TrainingDataset:
    """
    Dataset manager for contrastive learning training.

    Handles:
    - Loading samples from disk
    - Splitting into train/val/test
    - Batching with dynamic negative sampling
    - Data augmentation (Phase 2)
    """

    def __init__(
        self,
        samples: Optional[List[TrainingSample]] = None,
        validation_split: float = None,
        test_split: float = None,
    ):
        """
        Initialize the dataset.

        Args:
            samples: Optional list of training samples
            validation_split: Fraction for validation set
            test_split: Fraction for test set
        """
        self.samples = samples or []
        self.validation_split = validation_split or ml_config.validation_split
        self.test_split = test_split or ml_config.test_split

        self._train_samples: List[TrainingSample] = []
        self._val_samples: List[TrainingSample] = []
        self._test_samples: List[TrainingSample] = []

        self._is_split = False

        logger.info(
            "TrainingDataset initialized",
            sample_count=len(self.samples),
            val_split=self.validation_split,
            test_split=self.test_split
        )

    def add_sample(self, sample: TrainingSample) -> None:
        """Add a sample to the dataset."""
        self.samples.append(sample)
        self._is_split = False

    def add_samples(self, samples: List[TrainingSample]) -> None:
        """Add multiple samples to the dataset."""
        self.samples.extend(samples)
        self._is_split = False

    def split(self, shuffle: bool = True, seed: int = 42) -> None:
        """
        Split dataset into train/val/test sets.

        Args:
            shuffle: Whether to shuffle before splitting
            seed: Random seed for reproducibility
        """
        if shuffle:
            random.seed(seed)
            samples = self.samples.copy()
            random.shuffle(samples)
        else:
            samples = self.samples

        n = len(samples)
        n_test = int(n * self.test_split)
        n_val = int(n * self.validation_split)
        n_train = n - n_test - n_val

        self._train_samples = samples[:n_train]
        self._val_samples = samples[n_train:n_train + n_val]
        self._test_samples = samples[n_train + n_val:]

        self._is_split = True

        logger.info(
            "Dataset split completed",
            train=len(self._train_samples),
            val=len(self._val_samples),
            test=len(self._test_samples)
        )

    @property
    def train_samples(self) -> List[TrainingSample]:
        """Get training samples."""
        if not self._is_split:
            self.split()
        return self._train_samples

    @property
    def val_samples(self) -> List[TrainingSample]:
        """Get validation samples."""
        if not self._is_split:
            self.split()
        return self._val_samples

    @property
    def test_samples(self) -> List[TrainingSample]:
        """Get test samples."""
        if not self._is_split:
            self.split()
        return self._test_samples

    def get_batches(
        self,
        split: str = "train",
        batch_size: int = None,
        shuffle: bool = True,
    ) -> Iterator[TrainingBatch]:
        """
        Iterate over batches.

        Args:
            split: Which split to use ("train", "val", "test")
            batch_size: Batch size (default from config)
            shuffle: Whether to shuffle samples

        Yields:
            TrainingBatch objects
        """
        batch_size = batch_size or ml_config.contrastive_batch_size

        if split == "train":
            samples = self.train_samples
        elif split == "val":
            samples = self.val_samples
        elif split == "test":
            samples = self.test_samples
        else:
            raise ValueError(f"Unknown split: {split}")

        if shuffle:
            samples = samples.copy()
            random.shuffle(samples)

        for i in range(0, len(samples), batch_size):
            batch_samples = samples[i:i + batch_size]

            batch = TrainingBatch(
                resume_texts=[s.resume_text for s in batch_samples],
                positive_job_texts=[s.positive_job_text for s in batch_samples],
                negative_job_texts=[s.hard_negative_job_texts for s in batch_samples],
                sample_ids=[s.sample_id for s in batch_samples],
            )

            yield batch

    def save(self, path: Path) -> None:
        """
        Save dataset to disk.

        Args:
            path: Directory to save the dataset
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save samples as JSONL
        samples_path = path / "samples.jsonl"
        with open(samples_path, "w") as f:
            for sample in self.samples:
                f.write(json.dumps(sample.to_dict()) + "\n")

        # Save metadata
        metadata = {
            "sample_count": len(self.samples),
            "validation_split": self.validation_split,
            "test_split": self.test_split,
            "created_at": datetime.now().isoformat(),
        }
        metadata_path = path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            f"Dataset saved to {path}",
            sample_count=len(self.samples)
        )

    @classmethod
    def load(cls, path: Path) -> "TrainingDataset":
        """
        Load dataset from disk.

        Args:
            path: Directory containing the dataset

        Returns:
            Loaded TrainingDataset
        """
        path = Path(path)

        # Load metadata
        metadata_path = path / "metadata.json"
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Load samples
        samples_path = path / "samples.jsonl"
        samples = []
        with open(samples_path, "r") as f:
            for line in f:
                data = json.loads(line.strip())
                samples.append(TrainingSample.from_dict(data))

        dataset = cls(
            samples=samples,
            validation_split=metadata.get("validation_split", 0.1),
            test_split=metadata.get("test_split", 0.1),
        )

        logger.info(
            f"Dataset loaded from {path}",
            sample_count=len(samples)
        )

        return dataset

    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        if not self.samples:
            return {"sample_count": 0}

        avg_negatives = sum(
            len(s.hard_negative_job_ids) for s in self.samples
        ) / len(self.samples)

        sources = {}
        for s in self.samples:
            sources[s.source] = sources.get(s.source, 0) + 1

        strategies = {}
        for s in self.samples:
            strategies[s.mining_strategy] = strategies.get(s.mining_strategy, 0) + 1

        return {
            "sample_count": len(self.samples),
            "avg_hard_negatives": avg_negatives,
            "sources": sources,
            "mining_strategies": strategies,
            "train_count": len(self._train_samples) if self._is_split else None,
            "val_count": len(self._val_samples) if self._is_split else None,
            "test_count": len(self._test_samples) if self._is_split else None,
        }

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> TrainingSample:
        return self.samples[idx]

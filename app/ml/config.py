"""
ML Configuration for Resonance v2.

Centralized configuration for training pipelines, model parameters,
and hard negative mining settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal
from pathlib import Path


class MLConfig(BaseSettings):
    """ML Training and Inference Configuration."""

    # Hard Negative Mining
    hard_negative_ratio: int = Field(
        default=7,
        description="Number of hard negatives per positive sample"
    )
    bm25_candidates_multiplier: int = Field(
        default=3,
        description="Multiplier for BM25 candidate retrieval (k * multiplier)"
    )
    embedding_candidates_multiplier: int = Field(
        default=3,
        description="Multiplier for embedding-based candidate retrieval"
    )
    min_negative_similarity: float = Field(
        default=0.3,
        description="Minimum similarity threshold for hard negatives"
    )
    max_negative_similarity: float = Field(
        default=0.9,
        description="Maximum similarity threshold (too similar = possibly mislabeled)"
    )

    # BM25 Configuration
    bm25_k1: float = Field(default=1.5, description="BM25 k1 parameter")
    bm25_b: float = Field(default=0.75, description="BM25 b parameter")

    # Contrastive Learning (Phase 2)
    contrastive_temperature: float = Field(
        default=0.07,
        description="Temperature for InfoNCE loss"
    )
    contrastive_batch_size: int = Field(
        default=64,
        description="Batch size for contrastive training"
    )
    contrastive_learning_rate: float = Field(
        default=2e-5,
        description="Learning rate for contrastive fine-tuning"
    )
    contrastive_epochs: int = Field(
        default=10,
        description="Number of training epochs"
    )
    contrastive_warmup_ratio: float = Field(
        default=0.1,
        description="Warmup ratio for learning rate scheduler"
    )

    # Model Configuration
    base_model_name: str = Field(
        default="bert-base-uncased",
        description="Base transformer model for encoding"
    )
    embedding_dim: int = Field(
        default=1024,
        description="Output embedding dimension"
    )
    max_seq_length: int = Field(
        default=512,
        description="Maximum sequence length for tokenization"
    )
    pooling_strategy: Literal["mean", "cls", "max"] = Field(
        default="mean",
        description="Pooling strategy for sentence embeddings"
    )

    # Data Augmentation (Phase 2)
    augmentation_paraphrase_prob: float = Field(
        default=0.3,
        description="Probability of applying paraphrase augmentation"
    )
    augmentation_eda_prob: float = Field(
        default=0.2,
        description="Probability of applying EDA augmentation"
    )
    augmentation_skill_mask_prob: float = Field(
        default=0.15,
        description="Probability of masking skills"
    )

    # Paths
    models_dir: Path = Field(
        default=Path("models"),
        description="Directory for saved models"
    )
    training_data_dir: Path = Field(
        default=Path("data/training"),
        description="Directory for training data"
    )
    cache_dir: Path = Field(
        default=Path(".cache/ml"),
        description="Cache directory for intermediate results"
    )

    # Training Data
    min_positive_samples: int = Field(
        default=1000,
        description="Minimum positive samples required for training"
    )
    validation_split: float = Field(
        default=0.1,
        description="Validation set split ratio"
    )
    test_split: float = Field(
        default=0.1,
        description="Test set split ratio"
    )

    class Config:
        env_prefix = "ML_"
        env_file = ".env"
        extra = "ignore"


# Singleton instance
ml_config = MLConfig()

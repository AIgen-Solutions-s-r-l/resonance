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

    # Cross-Encoder Reranking (Phase 4)
    cross_encoder_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-encoder model for reranking"
    )
    cross_encoder_max_length: int = Field(
        default=512,
        description="Maximum sequence length for cross-encoder"
    )
    cross_encoder_batch_size: int = Field(
        default=32,
        description="Batch size for cross-encoder inference"
    )
    rerank_top_k_retrieve: int = Field(
        default=100,
        description="Number of candidates to retrieve for reranking"
    )
    rerank_top_k_final: int = Field(
        default=25,
        description="Number of final results after reranking"
    )
    cross_encoder_weight: float = Field(
        default=0.5,
        description="Weight for cross-encoder score in final ranking"
    )
    bi_encoder_weight: float = Field(
        default=0.3,
        description="Weight for bi-encoder score in final ranking"
    )
    skill_graph_weight: float = Field(
        default=0.2,
        description="Weight for skill graph score in final ranking"
    )

    # Pipeline Feature Flags (Phase 4)
    use_cross_encoder: bool = Field(
        default=True,
        description="Enable cross-encoder reranking"
    )
    use_skill_graph: bool = Field(
        default=True,
        description="Enable skill graph enrichment"
    )
    use_explainability: bool = Field(
        default=True,
        description="Enable match explanations"
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

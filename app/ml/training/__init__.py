"""
Training pipelines for Resonance v2.

This module contains:
- Hard negative mining
- Contrastive learning training
- Data augmentation utilities
- Dataset management
"""

from app.ml.training.hard_negative_miner import HardNegativeMiner
from app.ml.training.bm25_index import BM25Index
from app.ml.training.dataset import TrainingDataset, TrainingSample
from app.ml.training.trainer import ContrastiveTrainer, TrainingConfig, TrainingState
from app.ml.training.augmentation import (
    TextAugmenter,
    EasyDataAugmentation,
    SkillAugmentation,
    AugmentationConfig,
)

__all__ = [
    # Phase 1: Hard Negative Mining
    "HardNegativeMiner",
    "BM25Index",
    "TrainingDataset",
    "TrainingSample",
    # Phase 2: Contrastive Learning
    "ContrastiveTrainer",
    "TrainingConfig",
    "TrainingState",
    # Data Augmentation
    "TextAugmenter",
    "EasyDataAugmentation",
    "SkillAugmentation",
    "AugmentationConfig",
]

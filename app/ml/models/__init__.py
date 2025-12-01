"""
Neural network models for Resonance v2.

This module contains:
- Bi-encoder for contrastive learning
- Cross-encoder for reranking (Phase 4)
- Loss functions
"""

from app.ml.models.bi_encoder import BiEncoder
from app.ml.models.losses import InfoNCELoss, ContrastiveLoss

__all__ = [
    "BiEncoder",
    "InfoNCELoss",
    "ContrastiveLoss",
]

"""
Neural network models for Resonance v2.

This module contains:
- Bi-encoder for contrastive learning
- Cross-encoder for reranking (Phase 4)
- Reranker for two-stage retrieval
- Match explainer for interpretability
- Loss functions
"""

from app.ml.models.bi_encoder import BiEncoder
from app.ml.models.losses import InfoNCELoss, ContrastiveLoss
from app.ml.models.cross_encoder import CrossEncoder, CrossEncoderOutput
from app.ml.models.reranker import Reranker, RerankResult, RerankingConfig
from app.ml.models.explainer import (
    MatchExplainer,
    MatchExplanation,
    SkillMatchExplanation,
    ExperienceMatchExplanation,
    LocationMatchExplanation,
    MatchStrength,
)

__all__ = [
    # Bi-encoder
    "BiEncoder",
    # Cross-encoder (Phase 4)
    "CrossEncoder",
    "CrossEncoderOutput",
    # Reranker (Phase 4)
    "Reranker",
    "RerankResult",
    "RerankingConfig",
    # Explainer (Phase 4)
    "MatchExplainer",
    "MatchExplanation",
    "SkillMatchExplanation",
    "ExperienceMatchExplanation",
    "LocationMatchExplanation",
    "MatchStrength",
    # Losses
    "InfoNCELoss",
    "ContrastiveLoss",
]

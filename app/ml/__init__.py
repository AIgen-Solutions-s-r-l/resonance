"""
Machine Learning module for Resonance v2.

This module contains training pipelines, model management, and inference utilities
for the next-generation matching system.

Components:
- Phase 1: Hard Negative Mining
- Phase 2: Contrastive Learning
- Phase 3: Skill Knowledge Graph + GNN
- Phase 4: Cross-Encoder Reranking + Explainability
"""

from app.ml.config import MLConfig
from app.ml.pipeline import MatchingPipeline, MatchResult, PipelineConfig

__all__ = [
    "MLConfig",
    # Full pipeline (Phase 4)
    "MatchingPipeline",
    "MatchResult",
    "PipelineConfig",
]

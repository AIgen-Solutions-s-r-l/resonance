"""
Skill Knowledge Graph for Resonance v2.

This module contains:
- Skill extraction from text
- Knowledge graph construction and storage
- GNN for skill embedding enrichment
- Integration with the matching pipeline
"""

from app.ml.knowledge_graph.skill_extractor import SkillExtractor, ExtractedSkill
from app.ml.knowledge_graph.taxonomy import SkillTaxonomy, Skill, SkillRelation
from app.ml.knowledge_graph.graph import SkillGraph
from app.ml.knowledge_graph.gnn import SkillGNN, GraphEnrichedEncoder

__all__ = [
    "SkillExtractor",
    "ExtractedSkill",
    "SkillTaxonomy",
    "Skill",
    "SkillRelation",
    "SkillGraph",
    "SkillGNN",
    "GraphEnrichedEncoder",
]

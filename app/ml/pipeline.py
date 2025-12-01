"""
Full Matching Pipeline for Resonance v2.

Integrates all components:
1. Bi-encoder for initial retrieval
2. Skill graph enrichment (optional)
3. Cross-encoder reranking
4. Explainability
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import time

from app.log.logging import logger
from app.ml.config import ml_config

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class MatchResult:
    """Complete match result with all scores and explanations."""
    job_id: str
    job_title: str
    rank: int

    # Scores
    bi_encoder_score: float
    cross_encoder_score: Optional[float] = None
    skill_graph_score: Optional[float] = None
    final_score: float = 0.0

    # Explanation
    explanation: Optional[Dict[str, Any]] = None

    # Metadata
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "title": self.job_title,
            "rank": self.rank,
            "score": self.final_score,
            "scores": {
                "bi_encoder": self.bi_encoder_score,
                "cross_encoder": self.cross_encoder_score,
                "skill_graph": self.skill_graph_score,
            },
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
            **self.metadata,
        }


@dataclass
class PipelineConfig:
    """Configuration for the matching pipeline."""
    # Retrieval
    top_k_retrieve: int = 100
    top_k_final: int = 25

    # Component weights
    bi_encoder_weight: float = 0.3
    cross_encoder_weight: float = 0.5
    skill_graph_weight: float = 0.2

    # Feature flags
    use_skill_graph: bool = True
    use_cross_encoder: bool = True
    use_explainability: bool = True

    # Performance
    batch_size: int = 32
    use_gpu: bool = True


class MatchingPipeline:
    """
    End-to-end matching pipeline for Resonance v2.

    Implements the full matching flow:
    1. Encode resume with bi-encoder
    2. Retrieve top-K candidates via ANN search
    3. (Optional) Enrich with skill graph embeddings
    4. (Optional) Rerank with cross-encoder
    5. Generate explanations
    """

    def __init__(
        self,
        bi_encoder=None,
        cross_encoder=None,
        skill_graph=None,
        skill_gnn=None,
        explainer=None,
        config: PipelineConfig = None,
    ):
        """
        Initialize the pipeline.

        Args:
            bi_encoder: BiEncoder for initial encoding
            cross_encoder: CrossEncoder for reranking
            skill_graph: SkillGraph for enrichment
            skill_gnn: SkillGNN for graph embeddings
            explainer: MatchExplainer for explanations
            config: Pipeline configuration
        """
        self.bi_encoder = bi_encoder
        self.cross_encoder = cross_encoder
        self.skill_graph = skill_graph
        self.skill_gnn = skill_gnn
        self.explainer = explainer
        self.config = config or PipelineConfig()

        if TORCH_AVAILABLE:
            self.device = torch.device(
                "cuda" if self.config.use_gpu and torch.cuda.is_available() else "cpu"
            )

            if self.bi_encoder:
                self.bi_encoder.to(self.device)
            if self.cross_encoder:
                self.cross_encoder.to(self.device)
            if self.skill_gnn:
                self.skill_gnn.to(self.device)

        logger.info(
            "MatchingPipeline initialized",
            use_skill_graph=self.config.use_skill_graph and self.skill_graph is not None,
            use_cross_encoder=self.config.use_cross_encoder and self.cross_encoder is not None,
            use_explainability=self.config.use_explainability and self.explainer is not None,
        )

    def match(
        self,
        resume_text: str,
        candidates: List[Dict[str, Any]],
        resume_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MatchResult]:
        """
        Match a resume against job candidates.

        Args:
            resume_text: Resume content
            candidates: List of job candidate dictionaries
            resume_metadata: Optional resume metadata (experience, location)

        Returns:
            List of MatchResult sorted by score
        """
        if not candidates:
            return []

        start_time = time.time()
        resume_metadata = resume_metadata or {}

        # Stage 1: Bi-encoder retrieval
        stage1_start = time.time()
        bi_scores = self._bi_encoder_score(resume_text, candidates)
        stage1_time = time.time() - stage1_start

        # Get top-K for further processing
        scored = list(zip(range(len(candidates)), bi_scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        top_k_indices = [idx for idx, _ in scored[:self.config.top_k_retrieve]]

        # Stage 2: Skill graph enrichment (optional)
        skill_scores = {}
        stage2_time = 0
        if self.config.use_skill_graph and self.skill_graph:
            stage2_start = time.time()
            skill_scores = self._skill_graph_score(resume_text, candidates, top_k_indices)
            stage2_time = time.time() - stage2_start

        # Stage 3: Cross-encoder reranking (optional)
        cross_scores = {}
        stage3_time = 0
        if self.config.use_cross_encoder and self.cross_encoder:
            stage3_start = time.time()
            cross_scores = self._cross_encoder_score(resume_text, candidates, top_k_indices)
            stage3_time = time.time() - stage3_start

        # Combine scores
        results = []
        for idx in top_k_indices:
            candidate = candidates[idx]

            bi_score = bi_scores[idx]
            cross_score = cross_scores.get(idx)
            skill_score = skill_scores.get(idx)

            # Weighted combination
            final_score = bi_score * self.config.bi_encoder_weight

            if cross_score is not None:
                final_score += cross_score * self.config.cross_encoder_weight
            else:
                # If no cross-encoder, redistribute weight
                final_score = bi_score

            if skill_score is not None:
                final_score += skill_score * self.config.skill_graph_weight

            results.append(MatchResult(
                job_id=str(candidate.get("id", idx)),
                job_title=candidate.get("title", ""),
                rank=0,
                bi_encoder_score=bi_score,
                cross_encoder_score=cross_score,
                skill_graph_score=skill_score,
                final_score=final_score,
                metadata={
                    "company": candidate.get("company_name"),
                    "location": candidate.get("location"),
                    "posted_date": candidate.get("posted_date"),
                },
            ))

        # Sort by final score
        results.sort(key=lambda x: x.final_score, reverse=True)

        # Set ranks and trim
        for i, result in enumerate(results[:self.config.top_k_final]):
            result.rank = i + 1

        results = results[:self.config.top_k_final]

        # Stage 4: Explainability (optional)
        stage4_time = 0
        if self.config.use_explainability and self.explainer:
            stage4_start = time.time()
            self._add_explanations(resume_text, candidates, results, resume_metadata)
            stage4_time = time.time() - stage4_start

        # Set latency
        total_time = time.time() - start_time
        for result in results:
            result.latency_ms = total_time * 1000

        logger.info(
            "Pipeline match completed",
            candidates=len(candidates),
            returned=len(results),
            total_ms=f"{total_time * 1000:.1f}",
            stage1_ms=f"{stage1_time * 1000:.1f}",
            stage2_ms=f"{stage2_time * 1000:.1f}",
            stage3_ms=f"{stage3_time * 1000:.1f}",
            stage4_ms=f"{stage4_time * 1000:.1f}",
        )

        return results

    def _bi_encoder_score(
        self,
        resume_text: str,
        candidates: List[Dict[str, Any]],
    ) -> List[float]:
        """Score with bi-encoder."""
        if not self.bi_encoder:
            return [0.5] * len(candidates)

        resume_emb = self.bi_encoder.encode([resume_text], device=self.device)
        candidate_texts = [c.get("description", c.get("short_description", "")) for c in candidates]
        candidate_embs = self.bi_encoder.encode(
            candidate_texts,
            batch_size=self.config.batch_size,
            device=self.device,
        )

        if TORCH_AVAILABLE:
            scores = torch.matmul(resume_emb, candidate_embs.t()).squeeze(0)
            return scores.cpu().tolist()
        else:
            import numpy as np
            return np.dot(resume_emb, candidate_embs.T).flatten().tolist()

    def _skill_graph_score(
        self,
        resume_text: str,
        candidates: List[Dict[str, Any]],
        indices: List[int],
    ) -> Dict[int, float]:
        """Score with skill graph."""
        from app.ml.knowledge_graph.skill_extractor import SkillExtractor

        extractor = SkillExtractor()
        resume_skills = extractor.extract(resume_text)

        scores = {}
        for idx in indices:
            candidate = candidates[idx]
            job_skills = extractor.extract(
                candidate.get("description", candidate.get("short_description", ""))
            )

            # Compute overlap
            overlap = extractor.compute_skill_overlap(resume_skills, job_skills)
            scores[idx] = overlap["jaccard_similarity"]

        return scores

    def _cross_encoder_score(
        self,
        resume_text: str,
        candidates: List[Dict[str, Any]],
        indices: List[int],
    ) -> Dict[int, float]:
        """Score with cross-encoder."""
        if not self.cross_encoder:
            return {}

        pairs = [
            (resume_text, candidates[idx].get("description", candidates[idx].get("short_description", "")))
            for idx in indices
        ]

        scores_list = self.cross_encoder.predict(pairs, batch_size=self.config.batch_size)

        return {idx: score for idx, score in zip(indices, scores_list)}

    def _add_explanations(
        self,
        resume_text: str,
        candidates: List[Dict[str, Any]],
        results: List[MatchResult],
        resume_metadata: Dict[str, Any],
    ) -> None:
        """Add explanations to results."""
        if not self.explainer:
            return

        for result in results:
            # Find candidate
            candidate = next(
                (c for c in candidates if str(c.get("id")) == result.job_id),
                None
            )
            if not candidate:
                continue

            explanation = self.explainer.explain(
                resume_text=resume_text,
                job_text=candidate.get("description", ""),
                job_id=result.job_id,
                job_title=result.job_title,
                overall_score=result.final_score,
                resume_metadata=resume_metadata,
                job_metadata={
                    "experience_level": candidate.get("experience"),
                    "location": candidate.get("location"),
                    "is_remote": candidate.get("workplace_type", "").lower() == "remote",
                },
            )
            result.explanation = explanation.to_dict()

    @classmethod
    def load(cls, path: Path, config: PipelineConfig = None) -> "MatchingPipeline":
        """
        Load pipeline from disk.

        Args:
            path: Directory containing saved models
            config: Pipeline configuration

        Returns:
            Loaded MatchingPipeline
        """
        from app.ml.models.bi_encoder import BiEncoder
        from app.ml.models.cross_encoder import CrossEncoder
        from app.ml.models.explainer import MatchExplainer
        from app.ml.knowledge_graph import SkillGraph, SkillTaxonomy

        path = Path(path)
        config = config or PipelineConfig()

        # Load bi-encoder
        bi_encoder = None
        bi_encoder_path = path / "bi_encoder"
        if bi_encoder_path.exists():
            bi_encoder = BiEncoder.from_pretrained(str(bi_encoder_path))
            logger.info("Loaded bi-encoder")

        # Load cross-encoder
        cross_encoder = None
        cross_encoder_path = path / "cross_encoder"
        if cross_encoder_path.exists() and config.use_cross_encoder:
            cross_encoder = CrossEncoder.from_pretrained(str(cross_encoder_path))
            logger.info("Loaded cross-encoder")

        # Load skill graph
        skill_graph = None
        taxonomy_path = path / "skill_taxonomy.json"
        if taxonomy_path.exists() and config.use_skill_graph:
            taxonomy = SkillTaxonomy.load(taxonomy_path)
            skill_graph = SkillGraph(taxonomy)
            logger.info("Loaded skill graph")

        # Create explainer
        explainer = None
        if config.use_explainability:
            explainer = MatchExplainer()

        return cls(
            bi_encoder=bi_encoder,
            cross_encoder=cross_encoder,
            skill_graph=skill_graph,
            explainer=explainer,
            config=config,
        )

    def save(self, path: Path) -> None:
        """
        Save pipeline to disk.

        Args:
            path: Directory to save models
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        if self.bi_encoder:
            self.bi_encoder.save_pretrained(str(path / "bi_encoder"))

        if self.cross_encoder:
            self.cross_encoder.save_pretrained(str(path / "cross_encoder"))

        if self.skill_graph and self.skill_graph.taxonomy:
            self.skill_graph.taxonomy.save(path / "skill_taxonomy.json")

        logger.info(f"Pipeline saved to {path}")

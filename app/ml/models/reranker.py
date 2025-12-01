"""
Reranking Pipeline for Two-Stage Retrieval.

Implements the retrieve-then-rerank pattern:
1. Bi-encoder retrieves top-K candidates (fast)
2. Cross-encoder reranks candidates (accurate)
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import time

from app.log.logging import logger
from app.ml.config import ml_config

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class RerankResult:
    """Result from reranking."""
    job_id: str
    title: str
    bi_encoder_score: float
    cross_encoder_score: float
    final_score: float
    rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RerankingConfig:
    """Configuration for reranking."""
    top_k_retrieve: int = 100    # Number of candidates from bi-encoder
    top_k_rerank: int = 25       # Number of final results
    cross_encoder_weight: float = 0.7  # Weight for cross-encoder score
    bi_encoder_weight: float = 0.3     # Weight for bi-encoder score
    batch_size: int = 32
    use_gpu: bool = True


class Reranker:
    """
    Two-stage reranking pipeline.

    Stage 1: Bi-encoder retrieves top-K candidates efficiently
    Stage 2: Cross-encoder reranks candidates with high precision
    """

    def __init__(
        self,
        bi_encoder,
        cross_encoder,
        config: RerankingConfig = None,
    ):
        """
        Initialize the reranker.

        Args:
            bi_encoder: BiEncoder for initial retrieval
            cross_encoder: CrossEncoder for reranking
            config: Reranking configuration
        """
        self.bi_encoder = bi_encoder
        self.cross_encoder = cross_encoder
        self.config = config or RerankingConfig()

        if TORCH_AVAILABLE:
            self.device = torch.device(
                "cuda" if self.config.use_gpu and torch.cuda.is_available() else "cpu"
            )
            self.bi_encoder.to(self.device)
            self.cross_encoder.to(self.device)

        logger.info(
            "Reranker initialized",
            top_k_retrieve=self.config.top_k_retrieve,
            top_k_rerank=self.config.top_k_rerank,
        )

    def rerank(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        candidate_text_key: str = "description",
        candidate_id_key: str = "id",
    ) -> List[RerankResult]:
        """
        Rerank candidates for a query.

        Args:
            query_text: Query text (resume)
            candidates: List of candidate dicts (jobs)
            candidate_text_key: Key for candidate text in dict
            candidate_id_key: Key for candidate ID in dict

        Returns:
            List of RerankResult sorted by final score
        """
        if not candidates:
            return []

        start_time = time.time()

        # Stage 1: Bi-encoder scoring
        logger.debug(f"Stage 1: Scoring {len(candidates)} candidates with bi-encoder")

        query_embedding = self.bi_encoder.encode([query_text], device=self.device)
        candidate_texts = [c.get(candidate_text_key, "") for c in candidates]
        candidate_embeddings = self.bi_encoder.encode(
            candidate_texts,
            batch_size=self.config.batch_size,
            device=self.device,
        )

        # Compute bi-encoder similarities
        if TORCH_AVAILABLE:
            bi_scores = torch.matmul(query_embedding, candidate_embeddings.t()).squeeze(0)
            bi_scores = bi_scores.cpu().tolist()
        else:
            import numpy as np
            bi_scores = np.dot(query_embedding, candidate_embeddings.T).flatten().tolist()

        # Get top-K for reranking
        scored_candidates = list(zip(range(len(candidates)), bi_scores))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_k_indices = [idx for idx, _ in scored_candidates[:self.config.top_k_retrieve]]

        stage1_time = time.time() - start_time
        logger.debug(f"Stage 1 completed in {stage1_time:.3f}s")

        # Stage 2: Cross-encoder reranking
        logger.debug(f"Stage 2: Reranking top {len(top_k_indices)} with cross-encoder")

        pairs = [
            (query_text, candidates[idx].get(candidate_text_key, ""))
            for idx in top_k_indices
        ]

        cross_scores = self.cross_encoder.predict(
            pairs,
            batch_size=self.config.batch_size,
        )

        stage2_time = time.time() - start_time - stage1_time
        logger.debug(f"Stage 2 completed in {stage2_time:.3f}s")

        # Combine scores
        results = []
        for i, idx in enumerate(top_k_indices):
            candidate = candidates[idx]
            bi_score = bi_scores[idx]
            cross_score = cross_scores[i]

            final_score = (
                self.config.cross_encoder_weight * cross_score +
                self.config.bi_encoder_weight * bi_score
            )

            results.append(RerankResult(
                job_id=str(candidate.get(candidate_id_key, idx)),
                title=candidate.get("title", ""),
                bi_encoder_score=bi_score,
                cross_encoder_score=cross_score,
                final_score=final_score,
                rank=0,  # Will be set after sorting
                metadata={
                    "original_index": idx,
                    **{k: v for k, v in candidate.items()
                       if k not in [candidate_text_key, candidate_id_key, "title"]},
                },
            ))

        # Sort by final score
        results.sort(key=lambda x: x.final_score, reverse=True)

        # Set ranks and trim to top_k_rerank
        for i, result in enumerate(results[:self.config.top_k_rerank]):
            result.rank = i + 1

        total_time = time.time() - start_time
        logger.info(
            f"Reranking completed",
            candidates=len(candidates),
            retrieved=len(top_k_indices),
            returned=min(len(results), self.config.top_k_rerank),
            time=f"{total_time:.3f}s",
        )

        return results[:self.config.top_k_rerank]

    def rerank_batch(
        self,
        queries: List[str],
        candidates_list: List[List[Dict[str, Any]]],
        candidate_text_key: str = "description",
        candidate_id_key: str = "id",
    ) -> List[List[RerankResult]]:
        """
        Rerank multiple queries.

        Args:
            queries: List of query texts
            candidates_list: List of candidate lists per query
            candidate_text_key: Key for candidate text
            candidate_id_key: Key for candidate ID

        Returns:
            List of reranked results per query
        """
        results = []
        for query, candidates in zip(queries, candidates_list):
            result = self.rerank(
                query,
                candidates,
                candidate_text_key,
                candidate_id_key,
            )
            results.append(result)
        return results

    def get_latency_breakdown(
        self,
        query_text: str,
        candidates: List[Dict[str, Any]],
        num_runs: int = 10,
    ) -> Dict[str, float]:
        """
        Benchmark latency breakdown.

        Args:
            query_text: Sample query
            candidates: Sample candidates
            num_runs: Number of runs for averaging

        Returns:
            Dictionary with latency statistics
        """
        import numpy as np

        bi_times = []
        cross_times = []
        total_times = []

        candidate_texts = [c.get("description", "") for c in candidates]

        for _ in range(num_runs):
            # Bi-encoder timing
            start = time.time()
            query_emb = self.bi_encoder.encode([query_text], device=self.device)
            cand_emb = self.bi_encoder.encode(candidate_texts, device=self.device)
            if TORCH_AVAILABLE:
                _ = torch.matmul(query_emb, cand_emb.t())
            bi_time = time.time() - start
            bi_times.append(bi_time * 1000)

            # Cross-encoder timing (on top-K)
            pairs = [(query_text, t) for t in candidate_texts[:self.config.top_k_retrieve]]
            start = time.time()
            _ = self.cross_encoder.predict(pairs, batch_size=self.config.batch_size)
            cross_time = time.time() - start
            cross_times.append(cross_time * 1000)

            total_times.append(bi_time * 1000 + cross_time * 1000)

        return {
            "bi_encoder_mean_ms": float(np.mean(bi_times)),
            "bi_encoder_p95_ms": float(np.percentile(bi_times, 95)),
            "cross_encoder_mean_ms": float(np.mean(cross_times)),
            "cross_encoder_p95_ms": float(np.percentile(cross_times, 95)),
            "total_mean_ms": float(np.mean(total_times)),
            "total_p95_ms": float(np.percentile(total_times, 95)),
            "num_candidates": len(candidates),
            "top_k_retrieve": self.config.top_k_retrieve,
        }

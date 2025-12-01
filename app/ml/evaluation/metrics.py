"""
Ranking Metrics for Model Evaluation.

Implements standard IR metrics for evaluating the quality
of the matching model's rankings.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import math
import numpy as np


@dataclass
class EvaluationResult:
    """Container for evaluation results."""
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    ndcg_at_25: float = 0.0
    mrr: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    recall_at_25: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    precision_at_25: float = 0.0
    map_score: float = 0.0  # Mean Average Precision
    num_queries: int = 0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "nDCG@5": self.ndcg_at_5,
            "nDCG@10": self.ndcg_at_10,
            "nDCG@25": self.ndcg_at_25,
            "MRR": self.mrr,
            "Recall@5": self.recall_at_5,
            "Recall@10": self.recall_at_10,
            "Recall@25": self.recall_at_25,
            "Precision@5": self.precision_at_5,
            "Precision@10": self.precision_at_10,
            "Precision@25": self.precision_at_25,
            "MAP": self.map_score,
            "num_queries": self.num_queries,
        }

    def __str__(self) -> str:
        """String representation."""
        return (
            f"nDCG@10: {self.ndcg_at_10:.4f} | "
            f"MRR: {self.mrr:.4f} | "
            f"Recall@10: {self.recall_at_10:.4f}"
        )


def compute_dcg(relevances: List[float], k: int = None) -> float:
    """
    Compute Discounted Cumulative Gain.

    DCG = sum(rel_i / log2(i + 1)) for i in 1..k

    Args:
        relevances: List of relevance scores (1 for relevant, 0 for not)
        k: Number of results to consider

    Returns:
        DCG score
    """
    if k is not None:
        relevances = relevances[:k]

    dcg = 0.0
    for i, rel in enumerate(relevances):
        # Position is 1-indexed for the formula
        position = i + 1
        dcg += rel / math.log2(position + 1)

    return dcg


def compute_ndcg(
    ranked_items: List[str],
    relevant_items: Set[str],
    k: int = 10,
) -> float:
    """
    Compute Normalized Discounted Cumulative Gain.

    nDCG = DCG / IDCG, where IDCG is the ideal DCG.

    Args:
        ranked_items: List of item IDs in ranked order
        relevant_items: Set of relevant item IDs
        k: Number of results to consider

    Returns:
        nDCG score (0 to 1)
    """
    if not relevant_items:
        return 0.0

    # Create relevance scores for ranked items
    relevances = [1.0 if item in relevant_items else 0.0 for item in ranked_items]

    # Compute DCG
    dcg = compute_dcg(relevances, k)

    # Compute ideal DCG (all relevant items at top)
    ideal_relevances = [1.0] * min(len(relevant_items), k)
    idcg = compute_dcg(ideal_relevances, k)

    if idcg == 0:
        return 0.0

    return dcg / idcg


def compute_mrr(
    ranked_items: List[str],
    relevant_items: Set[str],
) -> float:
    """
    Compute Mean Reciprocal Rank.

    MRR = 1 / rank of first relevant item

    Args:
        ranked_items: List of item IDs in ranked order
        relevant_items: Set of relevant item IDs

    Returns:
        MRR score (0 to 1)
    """
    if not relevant_items:
        return 0.0

    for i, item in enumerate(ranked_items):
        if item in relevant_items:
            return 1.0 / (i + 1)

    return 0.0


def compute_recall_at_k(
    ranked_items: List[str],
    relevant_items: Set[str],
    k: int = 10,
) -> float:
    """
    Compute Recall@K.

    Recall@K = |relevant in top K| / |all relevant|

    Args:
        ranked_items: List of item IDs in ranked order
        relevant_items: Set of relevant item IDs
        k: Number of results to consider

    Returns:
        Recall score (0 to 1)
    """
    if not relevant_items:
        return 0.0

    top_k = set(ranked_items[:k])
    hits = len(top_k & relevant_items)

    return hits / len(relevant_items)


def compute_precision_at_k(
    ranked_items: List[str],
    relevant_items: Set[str],
    k: int = 10,
) -> float:
    """
    Compute Precision@K.

    Precision@K = |relevant in top K| / K

    Args:
        ranked_items: List of item IDs in ranked order
        relevant_items: Set of relevant item IDs
        k: Number of results to consider

    Returns:
        Precision score (0 to 1)
    """
    if k == 0:
        return 0.0

    top_k = set(ranked_items[:k])
    hits = len(top_k & relevant_items)

    return hits / k


def compute_average_precision(
    ranked_items: List[str],
    relevant_items: Set[str],
) -> float:
    """
    Compute Average Precision.

    AP = sum(P@k * rel(k)) / |relevant|

    Args:
        ranked_items: List of item IDs in ranked order
        relevant_items: Set of relevant item IDs

    Returns:
        AP score (0 to 1)
    """
    if not relevant_items:
        return 0.0

    hits = 0
    sum_precision = 0.0

    for i, item in enumerate(ranked_items):
        if item in relevant_items:
            hits += 1
            precision_at_i = hits / (i + 1)
            sum_precision += precision_at_i

    return sum_precision / len(relevant_items)


class RankingMetrics:
    """
    Computes and aggregates ranking metrics over a dataset.

    Usage:
        metrics = RankingMetrics()
        for query in queries:
            ranked = model.rank(query)
            metrics.add(ranked, relevant[query])
        result = metrics.compute()
    """

    def __init__(self, ks: List[int] = None):
        """
        Initialize metrics aggregator.

        Args:
            ks: List of K values for @K metrics
        """
        self.ks = ks or [5, 10, 25]
        self.reset()

    def reset(self) -> None:
        """Reset all accumulated metrics."""
        self.ndcg_scores = {k: [] for k in self.ks}
        self.mrr_scores = []
        self.recall_scores = {k: [] for k in self.ks}
        self.precision_scores = {k: [] for k in self.ks}
        self.ap_scores = []
        self.num_queries = 0

    def add(
        self,
        ranked_items: List[str],
        relevant_items: Set[str],
    ) -> None:
        """
        Add a single query result to the metrics.

        Args:
            ranked_items: List of item IDs in ranked order
            relevant_items: Set of relevant item IDs
        """
        if not relevant_items:
            return

        self.num_queries += 1

        # Compute metrics
        self.mrr_scores.append(compute_mrr(ranked_items, relevant_items))
        self.ap_scores.append(compute_average_precision(ranked_items, relevant_items))

        for k in self.ks:
            self.ndcg_scores[k].append(compute_ndcg(ranked_items, relevant_items, k))
            self.recall_scores[k].append(compute_recall_at_k(ranked_items, relevant_items, k))
            self.precision_scores[k].append(compute_precision_at_k(ranked_items, relevant_items, k))

    def compute(self) -> EvaluationResult:
        """
        Compute aggregated metrics.

        Returns:
            EvaluationResult with all metrics
        """
        if self.num_queries == 0:
            return EvaluationResult()

        def safe_mean(scores: List[float]) -> float:
            return float(np.mean(scores)) if scores else 0.0

        result = EvaluationResult(
            mrr=safe_mean(self.mrr_scores),
            map_score=safe_mean(self.ap_scores),
            num_queries=self.num_queries,
        )

        # Set @K metrics
        if 5 in self.ks:
            result.ndcg_at_5 = safe_mean(self.ndcg_scores[5])
            result.recall_at_5 = safe_mean(self.recall_scores[5])
            result.precision_at_5 = safe_mean(self.precision_scores[5])

        if 10 in self.ks:
            result.ndcg_at_10 = safe_mean(self.ndcg_scores[10])
            result.recall_at_10 = safe_mean(self.recall_scores[10])
            result.precision_at_10 = safe_mean(self.precision_scores[10])

        if 25 in self.ks:
            result.ndcg_at_25 = safe_mean(self.ndcg_scores[25])
            result.recall_at_25 = safe_mean(self.recall_scores[25])
            result.precision_at_25 = safe_mean(self.precision_scores[25])

        return result

    def get_score_distributions(self) -> Dict[str, Dict[str, float]]:
        """
        Get distribution statistics for each metric.

        Returns:
            Dictionary with mean, std, min, max for each metric
        """
        def compute_stats(scores: List[float]) -> Dict[str, float]:
            if not scores:
                return {"mean": 0, "std": 0, "min": 0, "max": 0}
            return {
                "mean": float(np.mean(scores)),
                "std": float(np.std(scores)),
                "min": float(np.min(scores)),
                "max": float(np.max(scores)),
            }

        stats = {
            "mrr": compute_stats(self.mrr_scores),
            "map": compute_stats(self.ap_scores),
        }

        for k in self.ks:
            stats[f"ndcg@{k}"] = compute_stats(self.ndcg_scores[k])
            stats[f"recall@{k}"] = compute_stats(self.recall_scores[k])
            stats[f"precision@{k}"] = compute_stats(self.precision_scores[k])

        return stats

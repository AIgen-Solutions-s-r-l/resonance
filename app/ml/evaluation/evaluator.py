"""
Model Evaluator for Resonance v2.

Provides comprehensive evaluation of the bi-encoder model
on ranking tasks.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import time
import torch
import numpy as np

from app.log.logging import logger
from app.ml.models.bi_encoder import BiEncoder
from app.ml.training.dataset import TrainingDataset, TrainingSample
from app.ml.evaluation.metrics import RankingMetrics, EvaluationResult


@dataclass
class EvaluationConfig:
    """Configuration for evaluation."""
    batch_size: int = 64
    top_k_values: List[int] = None
    num_candidates: int = 100  # Number of candidates to rank per query
    use_gpu: bool = True

    def __post_init__(self):
        self.top_k_values = self.top_k_values or [5, 10, 25]


class ModelEvaluator:
    """
    Evaluator for the bi-encoder matching model.

    Supports:
    - Ranking evaluation on test sets
    - Latency benchmarking
    - Embedding quality analysis
    """

    def __init__(
        self,
        model: BiEncoder,
        config: EvaluationConfig = None,
    ):
        """
        Initialize the evaluator.

        Args:
            model: BiEncoder model to evaluate
            config: Evaluation configuration
        """
        self.model = model
        self.config = config or EvaluationConfig()

        self.device = torch.device(
            "cuda" if self.config.use_gpu and torch.cuda.is_available() else "cpu"
        )
        self.model.to(self.device)
        self.model.eval()

        logger.info(
            "ModelEvaluator initialized",
            device=str(self.device),
            config=self.config.__dict__,
        )

    def evaluate_dataset(
        self,
        dataset: TrainingDataset,
        split: str = "test",
    ) -> EvaluationResult:
        """
        Evaluate on a dataset split.

        Args:
            dataset: TrainingDataset with test samples
            split: Which split to evaluate ("test", "val")

        Returns:
            EvaluationResult with all metrics
        """
        if split == "test":
            samples = dataset.test_samples
        elif split == "val":
            samples = dataset.val_samples
        else:
            samples = dataset.train_samples

        if not samples:
            logger.warning(f"No samples in {split} split")
            return EvaluationResult()

        logger.info(f"Evaluating on {len(samples)} {split} samples")

        metrics = RankingMetrics(ks=self.config.top_k_values)
        start_time = time.time()

        # Group samples by resume for efficient evaluation
        resume_samples: Dict[str, List[TrainingSample]] = {}
        for sample in samples:
            if sample.resume_id not in resume_samples:
                resume_samples[sample.resume_id] = []
            resume_samples[sample.resume_id].append(sample)

        # Evaluate each resume
        for resume_id, resume_samps in resume_samples.items():
            # Get resume embedding
            resume_text = resume_samps[0].resume_text
            resume_embedding = self._encode_text(resume_text)

            # Collect all jobs (positives and negatives)
            positive_job_ids = set()
            all_job_texts = {}

            for sample in resume_samps:
                if sample.positive_job_id:
                    positive_job_ids.add(sample.positive_job_id)
                    all_job_texts[sample.positive_job_id] = sample.positive_job_text

                for job_id, job_text in zip(
                    sample.hard_negative_job_ids,
                    sample.hard_negative_job_texts,
                ):
                    if job_id not in all_job_texts:
                        all_job_texts[job_id] = job_text

            if not positive_job_ids or not all_job_texts:
                continue

            # Encode all jobs
            job_ids = list(all_job_texts.keys())
            job_texts = [all_job_texts[jid] for jid in job_ids]
            job_embeddings = self._encode_texts(job_texts)

            # Compute similarities and rank
            similarities = torch.matmul(
                resume_embedding, job_embeddings.t()
            ).squeeze(0).cpu().numpy()

            ranked_indices = np.argsort(-similarities)
            ranked_job_ids = [job_ids[i] for i in ranked_indices]

            # Add to metrics
            metrics.add(ranked_job_ids, positive_job_ids)

        elapsed = time.time() - start_time
        result = metrics.compute()

        logger.info(
            f"Evaluation completed in {elapsed:.2f}s",
            result=str(result),
        )

        return result

    def evaluate_ranking(
        self,
        queries: List[str],
        candidates: List[List[str]],
        relevant: List[Set[str]],
    ) -> EvaluationResult:
        """
        Evaluate ranking quality.

        Args:
            queries: List of query texts (resumes)
            candidates: List of candidate texts per query (jobs)
            relevant: List of relevant candidate IDs per query

        Returns:
            EvaluationResult
        """
        if len(queries) != len(candidates) != len(relevant):
            raise ValueError("Lengths of queries, candidates, and relevant must match")

        metrics = RankingMetrics(ks=self.config.top_k_values)

        for query, cands, rel in zip(queries, candidates, relevant):
            if not cands or not rel:
                continue

            # Encode query
            query_emb = self._encode_text(query)

            # Encode candidates
            cand_embs = self._encode_texts(cands)

            # Rank by similarity
            similarities = torch.matmul(query_emb, cand_embs.t()).squeeze(0)
            ranked_indices = torch.argsort(similarities, descending=True).cpu().numpy()

            # Create ranked list of candidate IDs
            ranked_ids = [str(i) for i in ranked_indices]
            relevant_ids = {str(i) for i, c in enumerate(cands) if c in rel}

            metrics.add(ranked_ids, relevant_ids)

        return metrics.compute()

    def benchmark_latency(
        self,
        texts: List[str],
        num_iterations: int = 100,
    ) -> Dict[str, float]:
        """
        Benchmark encoding latency.

        Args:
            texts: Sample texts to encode
            num_iterations: Number of iterations for averaging

        Returns:
            Dictionary with latency statistics
        """
        if not texts:
            return {}

        # Warmup
        for _ in range(10):
            self._encode_texts(texts[:5])

        # Single text latency
        single_latencies = []
        for _ in range(num_iterations):
            text = texts[0]
            start = time.time()
            self._encode_text(text)
            single_latencies.append((time.time() - start) * 1000)

        # Batch latency
        batch_latencies = []
        for _ in range(num_iterations):
            start = time.time()
            self._encode_texts(texts[:self.config.batch_size])
            batch_latencies.append((time.time() - start) * 1000)

        return {
            "single_mean_ms": float(np.mean(single_latencies)),
            "single_p50_ms": float(np.percentile(single_latencies, 50)),
            "single_p95_ms": float(np.percentile(single_latencies, 95)),
            "single_p99_ms": float(np.percentile(single_latencies, 99)),
            "batch_mean_ms": float(np.mean(batch_latencies)),
            "batch_p50_ms": float(np.percentile(batch_latencies, 50)),
            "batch_p95_ms": float(np.percentile(batch_latencies, 95)),
            "batch_size": min(len(texts), self.config.batch_size),
        }

    def analyze_embeddings(
        self,
        texts: List[str],
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze embedding quality and distribution.

        Args:
            texts: Texts to analyze
            labels: Optional labels for grouping

        Returns:
            Dictionary with embedding statistics
        """
        embeddings = self._encode_texts(texts).cpu().numpy()

        # Basic statistics
        norms = np.linalg.norm(embeddings, axis=1)
        similarities = np.dot(embeddings, embeddings.T)

        # Self-similarity distribution (excluding diagonal)
        mask = ~np.eye(len(texts), dtype=bool)
        pairwise_sims = similarities[mask]

        stats = {
            "num_embeddings": len(texts),
            "embedding_dim": embeddings.shape[1],
            "norm_mean": float(np.mean(norms)),
            "norm_std": float(np.std(norms)),
            "similarity_mean": float(np.mean(pairwise_sims)),
            "similarity_std": float(np.std(pairwise_sims)),
            "similarity_min": float(np.min(pairwise_sims)),
            "similarity_max": float(np.max(pairwise_sims)),
        }

        # If labels provided, compute inter/intra class similarities
        if labels:
            unique_labels = list(set(labels))
            if len(unique_labels) > 1:
                intra_class_sims = []
                inter_class_sims = []

                for i in range(len(texts)):
                    for j in range(i + 1, len(texts)):
                        if labels[i] == labels[j]:
                            intra_class_sims.append(similarities[i, j])
                        else:
                            inter_class_sims.append(similarities[i, j])

                if intra_class_sims:
                    stats["intra_class_similarity"] = float(np.mean(intra_class_sims))
                if inter_class_sims:
                    stats["inter_class_similarity"] = float(np.mean(inter_class_sims))
                if intra_class_sims and inter_class_sims:
                    stats["class_separation"] = (
                        stats["intra_class_similarity"] - stats["inter_class_similarity"]
                    )

        return stats

    def _encode_text(self, text: str) -> torch.Tensor:
        """Encode a single text."""
        return self.model.encode([text], device=self.device)

    def _encode_texts(self, texts: List[str]) -> torch.Tensor:
        """Encode multiple texts."""
        return self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            device=self.device,
        )

    def compare_models(
        self,
        other_model: BiEncoder,
        dataset: TrainingDataset,
        split: str = "test",
    ) -> Dict[str, EvaluationResult]:
        """
        Compare this model with another model.

        Args:
            other_model: Another BiEncoder to compare with
            dataset: Dataset to evaluate on
            split: Which split to use

        Returns:
            Dictionary with results for both models
        """
        # Evaluate this model
        result_self = self.evaluate_dataset(dataset, split)

        # Create evaluator for other model
        other_evaluator = ModelEvaluator(other_model, self.config)
        result_other = other_evaluator.evaluate_dataset(dataset, split)

        return {
            "model_1": result_self,
            "model_2": result_other,
            "delta": EvaluationResult(
                ndcg_at_10=result_self.ndcg_at_10 - result_other.ndcg_at_10,
                mrr=result_self.mrr - result_other.mrr,
                recall_at_10=result_self.recall_at_10 - result_other.recall_at_10,
            ),
        }

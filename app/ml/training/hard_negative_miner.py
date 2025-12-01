"""
Hard Negative Mining for Contrastive Learning.

This module implements strategies for mining hard negatives:
1. BM25-based: Lexically similar but not applied
2. Embedding-based: Semantically similar but not applied
3. Combined: Merge and rank from both strategies
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
import asyncio
import uuid
from datetime import datetime

import numpy as np

from app.log.logging import logger
from app.ml.config import ml_config
from app.ml.training.bm25_index import BM25Index
from app.ml.training.dataset import TrainingSample, TrainingDataset
from app.utils.db_utils import get_db_cursor
from app.core.mongodb import database


@dataclass
class JobCandidate:
    """A candidate job for hard negative mining."""
    job_id: str
    text: str
    embedding: Optional[List[float]] = None
    bm25_score: float = 0.0
    embedding_score: float = 0.0
    combined_score: float = 0.0


class HardNegativeMiner:
    """
    Mines hard negatives for contrastive learning.

    Hard negatives are jobs that are similar to what the user might apply to,
    but weren't actually applied to. These provide stronger training signal
    than random negatives.
    """

    def __init__(
        self,
        bm25_index: Optional[BM25Index] = None,
        hard_negative_ratio: int = None,
        min_similarity: float = None,
        max_similarity: float = None,
    ):
        """
        Initialize the hard negative miner.

        Args:
            bm25_index: Pre-built BM25 index (will be created if None)
            hard_negative_ratio: Number of hard negatives per positive
            min_similarity: Minimum similarity threshold
            max_similarity: Maximum similarity threshold
        """
        self.bm25_index = bm25_index or BM25Index()
        self.hard_negative_ratio = hard_negative_ratio or ml_config.hard_negative_ratio
        self.min_similarity = min_similarity or ml_config.min_negative_similarity
        self.max_similarity = max_similarity or ml_config.max_negative_similarity

        self._job_embeddings: Dict[str, List[float]] = {}
        self._job_texts: Dict[str, str] = {}

        logger.info(
            "HardNegativeMiner initialized",
            hard_negative_ratio=self.hard_negative_ratio,
            min_similarity=self.min_similarity,
            max_similarity=self.max_similarity,
        )

    async def load_jobs_from_db(self, limit: int = None) -> int:
        """
        Load jobs from database into the index.

        Args:
            limit: Maximum number of jobs to load

        Returns:
            Number of jobs loaded
        """
        logger.info("Loading jobs from database for BM25 index")

        query = """
            SELECT
                j.id,
                j.title,
                j.description,
                j.short_description,
                j.embedding
            FROM jobs j
            WHERE j.job_state = 'Active'
            AND j.embedding IS NOT NULL
        """

        if limit:
            query += f" LIMIT {limit}"

        async with get_db_cursor("default") as cursor:
            await cursor.execute(query)
            rows = await cursor.fetchall()

        documents = []
        for row in rows:
            job_id = str(row["id"])
            title = row.get("title", "")
            description = row.get("description", "") or row.get("short_description", "")
            text = f"{title} {description}".strip()

            if text:
                documents.append((job_id, text))
                self._job_texts[job_id] = text

                # Store embedding if available
                if row.get("embedding"):
                    self._job_embeddings[job_id] = row["embedding"]

        self.bm25_index.add_documents(documents)
        self.bm25_index.build()

        logger.info(
            "Jobs loaded into BM25 index",
            job_count=len(documents),
            with_embeddings=len(self._job_embeddings)
        )

        return len(documents)

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))

    def mine_bm25_negatives(
        self,
        resume_text: str,
        positive_job_ids: Set[str],
        k: int = None,
    ) -> List[JobCandidate]:
        """
        Mine hard negatives using BM25 text similarity.

        Args:
            resume_text: The resume text to search against
            positive_job_ids: Job IDs to exclude (applied/hired)
            k: Number of candidates to retrieve

        Returns:
            List of JobCandidate objects
        """
        k = k or (self.hard_negative_ratio * ml_config.bm25_candidates_multiplier)

        # Search BM25 index
        results = self.bm25_index.search(
            query=resume_text,
            top_k=k * 2,  # Get more to filter
            exclude_ids=positive_job_ids,
        )

        candidates = []
        for job_id, score in results[:k]:
            if job_id in positive_job_ids:
                continue

            candidates.append(JobCandidate(
                job_id=job_id,
                text=self._job_texts.get(job_id, ""),
                embedding=self._job_embeddings.get(job_id),
                bm25_score=score,
            ))

        logger.debug(
            "BM25 negative mining completed",
            candidates=len(candidates)
        )

        return candidates

    def mine_embedding_negatives(
        self,
        resume_embedding: List[float],
        positive_job_ids: Set[str],
        k: int = None,
    ) -> List[JobCandidate]:
        """
        Mine hard negatives using embedding similarity.

        Args:
            resume_embedding: Resume vector embedding
            positive_job_ids: Job IDs to exclude
            k: Number of candidates to retrieve

        Returns:
            List of JobCandidate objects
        """
        k = k or (self.hard_negative_ratio * ml_config.embedding_candidates_multiplier)

        if not self._job_embeddings:
            logger.warning("No job embeddings available for mining")
            return []

        # Compute similarities
        similarities: List[Tuple[str, float]] = []
        for job_id, job_embedding in self._job_embeddings.items():
            if job_id in positive_job_ids:
                continue

            sim = self._cosine_similarity(resume_embedding, job_embedding)

            # Filter by similarity thresholds
            if self.min_similarity <= sim <= self.max_similarity:
                similarities.append((job_id, sim))

        # Sort by similarity descending (hardest negatives first)
        similarities.sort(key=lambda x: x[1], reverse=True)

        candidates = []
        for job_id, score in similarities[:k]:
            candidates.append(JobCandidate(
                job_id=job_id,
                text=self._job_texts.get(job_id, ""),
                embedding=self._job_embeddings.get(job_id),
                embedding_score=score,
            ))

        logger.debug(
            "Embedding negative mining completed",
            candidates=len(candidates)
        )

        return candidates

    def mine_combined_negatives(
        self,
        resume_text: str,
        resume_embedding: Optional[List[float]],
        positive_job_ids: Set[str],
        k: int = None,
    ) -> List[JobCandidate]:
        """
        Mine hard negatives using both BM25 and embedding similarity.

        Combines results from both strategies and ranks by combined score.

        Args:
            resume_text: Resume text
            resume_embedding: Resume vector embedding (optional)
            positive_job_ids: Job IDs to exclude
            k: Number of final candidates

        Returns:
            List of JobCandidate objects
        """
        k = k or self.hard_negative_ratio

        # Get BM25 candidates
        bm25_candidates = self.mine_bm25_negatives(
            resume_text=resume_text,
            positive_job_ids=positive_job_ids,
            k=k * 2,
        )

        # Get embedding candidates if available
        embedding_candidates = []
        if resume_embedding:
            embedding_candidates = self.mine_embedding_negatives(
                resume_embedding=resume_embedding,
                positive_job_ids=positive_job_ids,
                k=k * 2,
            )

        # Merge candidates
        candidates_dict: Dict[str, JobCandidate] = {}

        for c in bm25_candidates:
            candidates_dict[c.job_id] = c

        for c in embedding_candidates:
            if c.job_id in candidates_dict:
                # Merge scores
                candidates_dict[c.job_id].embedding_score = c.embedding_score
            else:
                candidates_dict[c.job_id] = c

        # Compute combined score
        # Normalize scores to [0, 1] range
        all_candidates = list(candidates_dict.values())

        if all_candidates:
            max_bm25 = max(c.bm25_score for c in all_candidates) or 1.0
            max_emb = max(c.embedding_score for c in all_candidates) or 1.0

            for c in all_candidates:
                norm_bm25 = c.bm25_score / max_bm25
                norm_emb = c.embedding_score / max_emb if max_emb else 0

                # Weighted combination (favor embedding when available)
                if c.embedding_score > 0:
                    c.combined_score = 0.4 * norm_bm25 + 0.6 * norm_emb
                else:
                    c.combined_score = norm_bm25

        # Sort by combined score
        all_candidates.sort(key=lambda x: x.combined_score, reverse=True)

        logger.debug(
            "Combined negative mining completed",
            total_candidates=len(all_candidates),
            returning=min(k, len(all_candidates))
        )

        return all_candidates[:k]

    async def create_training_sample(
        self,
        resume_id: str,
        resume_text: str,
        resume_embedding: Optional[List[float]],
        positive_job_id: str,
        positive_job_text: str,
        applied_job_ids: Set[str],
        source: str = "application",
    ) -> TrainingSample:
        """
        Create a training sample with mined hard negatives.

        Args:
            resume_id: Resume identifier
            resume_text: Resume text content
            resume_embedding: Resume vector embedding
            positive_job_id: The positive job (applied/hired)
            positive_job_text: Positive job text
            applied_job_ids: All job IDs to exclude
            source: Source of the positive signal

        Returns:
            TrainingSample with hard negatives
        """
        # Mine hard negatives
        hard_negatives = self.mine_combined_negatives(
            resume_text=resume_text,
            resume_embedding=resume_embedding,
            positive_job_ids=applied_job_ids | {positive_job_id},
            k=self.hard_negative_ratio,
        )

        sample = TrainingSample(
            sample_id=str(uuid.uuid4()),
            resume_id=resume_id,
            resume_text=resume_text,
            resume_embedding=resume_embedding,
            positive_job_id=positive_job_id,
            positive_job_text=positive_job_text,
            hard_negative_job_ids=[c.job_id for c in hard_negatives],
            hard_negative_job_texts=[c.text for c in hard_negatives],
            hard_negative_job_embeddings=[c.embedding for c in hard_negatives if c.embedding],
            source=source,
            timestamp=datetime.now(),
            mining_strategy="combined",
        )

        return sample

    async def build_training_dataset(
        self,
        min_samples: int = None,
    ) -> TrainingDataset:
        """
        Build a complete training dataset from application history.

        Fetches resume-job pairs from MongoDB and mines hard negatives
        for each pair.

        Args:
            min_samples: Minimum number of samples required

        Returns:
            TrainingDataset ready for training
        """
        min_samples = min_samples or ml_config.min_positive_samples

        logger.info("Building training dataset from application history")

        # Ensure jobs are loaded
        if len(self.bm25_index) == 0:
            await self.load_jobs_from_db()

        # Fetch application history from MongoDB
        resumes_collection = database.get_collection("resumes")
        applications_collection = database.get_collection("applied_jobs")

        # Get resumes with embeddings
        resumes_cursor = resumes_collection.find(
            {"vector": {"$exists": True}},
            {"_id": 1, "user_id": 1, "text": 1, "vector": 1}
        )
        resumes = await resumes_cursor.to_list(length=None)

        logger.info(f"Found {len(resumes)} resumes with embeddings")

        samples = []
        processed = 0

        for resume in resumes:
            user_id = resume.get("user_id")
            if not user_id:
                continue

            resume_id = str(resume["_id"])
            resume_text = resume.get("text", "")
            resume_embedding = resume.get("vector")

            if not resume_text:
                continue

            # Get applied jobs for this user
            applications = await applications_collection.find(
                {"user_id": user_id}
            ).to_list(length=None)

            if not applications:
                continue

            applied_job_ids = {str(app["job_id"]) for app in applications}

            # Create samples for each application
            for app in applications:
                job_id = str(app["job_id"])
                job_text = self._job_texts.get(job_id, "")

                if not job_text:
                    continue

                sample = await self.create_training_sample(
                    resume_id=resume_id,
                    resume_text=resume_text,
                    resume_embedding=resume_embedding,
                    positive_job_id=job_id,
                    positive_job_text=job_text,
                    applied_job_ids=applied_job_ids,
                    source="application",
                )

                samples.append(sample)
                processed += 1

                if processed % 100 == 0:
                    logger.info(f"Processed {processed} samples")

        logger.info(
            "Training dataset built",
            total_samples=len(samples),
            min_required=min_samples
        )

        if len(samples) < min_samples:
            logger.warning(
                f"Insufficient samples: {len(samples)} < {min_samples}. "
                "Consider synthetic data augmentation."
            )

        dataset = TrainingDataset(samples=samples)
        return dataset

    def get_statistics(self) -> Dict[str, Any]:
        """Get miner statistics."""
        return {
            "bm25_index_size": len(self.bm25_index),
            "job_embeddings_count": len(self._job_embeddings),
            "job_texts_count": len(self._job_texts),
            "hard_negative_ratio": self.hard_negative_ratio,
            "min_similarity": self.min_similarity,
            "max_similarity": self.max_similarity,
        }

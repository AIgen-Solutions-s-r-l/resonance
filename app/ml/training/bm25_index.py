"""
BM25 Index for text-based candidate retrieval.

Used for mining hard negatives that are lexically similar
but not actual matches.
"""

import math
import re
from collections import Counter
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
import pickle
from pathlib import Path

from app.log.logging import logger
from app.ml.config import ml_config


@dataclass
class BM25Document:
    """A document in the BM25 index."""
    doc_id: str
    text: str
    tokens: List[str] = field(default_factory=list)
    token_counts: Dict[str, int] = field(default_factory=dict)


class BM25Index:
    """
    BM25 (Best Matching 25) index for text similarity search.

    Used for finding lexically similar documents, which are good
    candidates for hard negatives in contrastive learning.
    """

    def __init__(
        self,
        k1: float = None,
        b: float = None,
        stopwords: Optional[Set[str]] = None
    ):
        """
        Initialize BM25 index.

        Args:
            k1: Term frequency saturation parameter (default from config)
            b: Length normalization parameter (default from config)
            stopwords: Set of stopwords to filter out
        """
        self.k1 = k1 or ml_config.bm25_k1
        self.b = b or ml_config.bm25_b

        # Default English stopwords
        self.stopwords = stopwords or {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "is", "was", "are",
            "were", "been", "be", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must",
            "shall", "can", "this", "that", "these", "those", "i", "you",
            "he", "she", "it", "we", "they", "what", "which", "who", "whom",
            "where", "when", "why", "how", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very",
            "just", "also", "now", "here", "there", "then", "once",
        }

        self.documents: Dict[str, BM25Document] = {}
        self.doc_count = 0
        self.avg_doc_length = 0.0
        self.doc_frequencies: Dict[str, int] = Counter()
        self.idf_cache: Dict[str, float] = {}

        self._is_built = False

        logger.info(
            "BM25Index initialized",
            k1=self.k1,
            b=self.b,
            stopwords_count=len(self.stopwords)
        )

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into normalized tokens.

        Args:
            text: Input text

        Returns:
            List of normalized tokens
        """
        # Lowercase and extract words
        text = text.lower()
        tokens = re.findall(r'\b[a-z][a-z0-9+#]*\b', text)

        # Filter stopwords and short tokens
        tokens = [
            t for t in tokens
            if t not in self.stopwords and len(t) > 1
        ]

        return tokens

    def add_document(self, doc_id: str, text: str) -> None:
        """
        Add a document to the index.

        Args:
            doc_id: Unique document identifier
            text: Document text content
        """
        tokens = self.tokenize(text)
        token_counts = Counter(tokens)

        doc = BM25Document(
            doc_id=doc_id,
            text=text,
            tokens=tokens,
            token_counts=dict(token_counts)
        )

        self.documents[doc_id] = doc
        self._is_built = False

    def add_documents(self, documents: List[Tuple[str, str]]) -> None:
        """
        Add multiple documents to the index.

        Args:
            documents: List of (doc_id, text) tuples
        """
        for doc_id, text in documents:
            self.add_document(doc_id, text)

        logger.info(f"Added {len(documents)} documents to BM25 index")

    def build(self) -> None:
        """Build the index after adding documents."""
        if self._is_built:
            return

        self.doc_count = len(self.documents)

        if self.doc_count == 0:
            logger.warning("Building empty BM25 index")
            self._is_built = True
            return

        # Calculate average document length
        total_length = sum(len(doc.tokens) for doc in self.documents.values())
        self.avg_doc_length = total_length / self.doc_count

        # Calculate document frequencies
        self.doc_frequencies = Counter()
        for doc in self.documents.values():
            unique_tokens = set(doc.tokens)
            for token in unique_tokens:
                self.doc_frequencies[token] += 1

        # Pre-compute IDF values
        self.idf_cache = {}
        for token, df in self.doc_frequencies.items():
            # IDF with smoothing
            self.idf_cache[token] = math.log(
                (self.doc_count - df + 0.5) / (df + 0.5) + 1
            )

        self._is_built = True

        logger.info(
            "BM25 index built",
            doc_count=self.doc_count,
            avg_doc_length=f"{self.avg_doc_length:.2f}",
            vocabulary_size=len(self.doc_frequencies)
        )

    def _compute_score(
        self,
        query_tokens: List[str],
        doc: BM25Document
    ) -> float:
        """
        Compute BM25 score for a document given a query.

        Args:
            query_tokens: Tokenized query
            doc: Document to score

        Returns:
            BM25 score
        """
        score = 0.0
        doc_length = len(doc.tokens)

        for token in query_tokens:
            if token not in doc.token_counts:
                continue

            # Get term frequency in document
            tf = doc.token_counts[token]

            # Get IDF (default to 0 if not in vocabulary)
            idf = self.idf_cache.get(token, 0)

            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * (doc_length / self.avg_doc_length)
            )

            score += idf * (numerator / denominator)

        return score

    def search(
        self,
        query: str,
        top_k: int = 10,
        exclude_ids: Optional[Set[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        Search for documents similar to query.

        Args:
            query: Query text
            top_k: Number of results to return
            exclude_ids: Document IDs to exclude from results

        Returns:
            List of (doc_id, score) tuples, sorted by score descending
        """
        if not self._is_built:
            self.build()

        if self.doc_count == 0:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        exclude_ids = exclude_ids or set()

        # Score all documents
        scores: List[Tuple[str, float]] = []
        for doc_id, doc in self.documents.items():
            if doc_id in exclude_ids:
                continue
            score = self._compute_score(query_tokens, doc)
            if score > 0:
                scores.append((doc_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def save(self, path: Path) -> None:
        """
        Save the index to disk.

        Args:
            path: Path to save the index
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "k1": self.k1,
            "b": self.b,
            "documents": self.documents,
            "doc_count": self.doc_count,
            "avg_doc_length": self.avg_doc_length,
            "doc_frequencies": dict(self.doc_frequencies),
            "idf_cache": self.idf_cache,
            "is_built": self._is_built,
        }

        with open(path, "wb") as f:
            pickle.dump(data, f)

        logger.info(f"BM25 index saved to {path}")

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        """
        Load an index from disk.

        Args:
            path: Path to load the index from

        Returns:
            Loaded BM25Index instance
        """
        with open(path, "rb") as f:
            data = pickle.load(f)

        index = cls(k1=data["k1"], b=data["b"])
        index.documents = data["documents"]
        index.doc_count = data["doc_count"]
        index.avg_doc_length = data["avg_doc_length"]
        index.doc_frequencies = Counter(data["doc_frequencies"])
        index.idf_cache = data["idf_cache"]
        index._is_built = data["is_built"]

        logger.info(
            f"BM25 index loaded from {path}",
            doc_count=index.doc_count
        )

        return index

    def __len__(self) -> int:
        return self.doc_count

    def __contains__(self, doc_id: str) -> bool:
        return doc_id in self.documents

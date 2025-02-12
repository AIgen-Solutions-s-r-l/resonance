"""
Core interfaces for the quality tracking system.

This module defines the abstract base classes and protocols that form the
foundation of the quality tracking system, following the Interface Segregation
Principle and Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Protocol, TypeVar, Generic, Optional
from datetime import datetime
from uuid import UUID


T = TypeVar('T')
Score = TypeVar('Score')


class QualityScore(Protocol):
    """Protocol defining the structure of a quality score."""
    match_score: float
    quality_score: float
    skill_alignment_score: float
    experience_match_score: float
    evaluation_text: str


class Repository(Generic[T], ABC):
    """Abstract base class for repositories."""
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save an entity to the repository."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Retrieve an entity by its ID."""
        pass
    
    @abstractmethod
    async def get_all(self, filters: Dict = None) -> List[T]:
        """Retrieve all entities matching the given filters."""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Delete an entity by its ID."""
        pass


class QualityEvaluator(ABC):
    """Abstract base class for quality evaluators."""
    
    @abstractmethod
    async def evaluate_match(self, resume: Dict, job: Dict) -> QualityScore:
        """
        Evaluate the quality of a resume-job match.
        
        Args:
            resume: Resume data dictionary
            job: Job data dictionary
            
        Returns:
            QualityScore object containing evaluation results
        """
        pass
    
    @abstractmethod
    async def batch_evaluate(
        self,
        matches: List[tuple[Dict, Dict]]
    ) -> List[QualityScore]:
        """
        Evaluate multiple matches in batch.
        
        Args:
            matches: List of (resume, job) tuples to evaluate
            
        Returns:
            List of QualityScore objects
        """
        pass


class FeedbackCollector(ABC):
    """Abstract base class for feedback collection."""
    
    @abstractmethod
    async def collect_feedback(
        self,
        evaluation_id: UUID,
        feedback_score: float,
        feedback_text: Optional[str],
        reviewer: str
    ) -> None:
        """
        Collect feedback for a quality evaluation.
        
        Args:
            evaluation_id: ID of the evaluation
            feedback_score: Numerical feedback score
            feedback_text: Optional textual feedback
            reviewer: Identity of the reviewer
        """
        pass
    
    @abstractmethod
    async def get_feedback_history(
        self,
        evaluation_id: UUID
    ) -> List[Dict]:
        """
        Retrieve feedback history for an evaluation.
        
        Args:
            evaluation_id: ID of the evaluation
            
        Returns:
            List of feedback entries
        """
        pass


class MetricsTracker(ABC):
    """Abstract base class for tracking evaluation metrics."""
    
    @abstractmethod
    async def record_metric(
        self,
        evaluation_id: UUID,
        metric_name: str,
        metric_value: float,
        timestamp: datetime = None
    ) -> None:
        """
        Record a metric value for an evaluation.
        
        Args:
            evaluation_id: ID of the evaluation
            metric_name: Name of the metric
            metric_value: Value of the metric
            timestamp: Optional timestamp (defaults to current time)
        """
        pass
    
    @abstractmethod
    async def get_metric_history(
        self,
        evaluation_id: UUID,
        metric_name: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[Dict]:
        """
        Retrieve metric history for an evaluation.
        
        Args:
            evaluation_id: ID of the evaluation
            metric_name: Optional filter by metric name
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of metric entries
        """
        pass
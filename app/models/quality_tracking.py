"""
Quality tracking models for the matching service.

This module defines the SQLAlchemy models for storing match quality evaluations,
feedback, and metrics history. It follows the Single Responsibility Principle
by focusing solely on data modeling.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from sqlalchemy import Column, Float, String, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped
from app.core.base import Base
from app.log.logging import logger


class MatchQualityEvaluation(Base):
    """Stores quality evaluations for resume-job matches."""
    
    __tablename__ = "match_quality_evaluations"
    
    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    resume_id: str = Column(String, nullable=False)
    job_id: str = Column(
        String,
        ForeignKey("Jobs.id", ondelete="CASCADE"),
        nullable=False
    )
    match_score: float = Column(Float, nullable=False)
    quality_score: float = Column(Float, nullable=False)
    skill_alignment_score: float = Column(Float, nullable=False)
    experience_match_score: float = Column(Float, nullable=False)
    evaluation_text: str = Column(Text, nullable=False)
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="quality_evaluations")
    feedback: Mapped[List["ManualFeedback"]] = relationship(
        "ManualFeedback",
        back_populates="evaluation",
        cascade="all, delete-orphan"
    )
    metrics: Mapped[List["EvaluationMetricsHistory"]] = relationship(
        "EvaluationMetricsHistory",
        back_populates="evaluation",
        cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        """Initialize a new quality evaluation."""
        super().__init__(**kwargs)
        logger.info(
            "Created new match quality evaluation",
            resume_id=self.resume_id,
            job_id=self.job_id
        )


class ManualFeedback(Base):
    """Stores manual feedback on match quality evaluations."""
    
    __tablename__ = "manual_feedback"
    
    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    evaluation_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("match_quality_evaluations.id", ondelete="CASCADE"),
        nullable=False
    )
    feedback_score: float = Column(Float, nullable=False)
    feedback_text: Optional[str] = Column(Text)
    reviewer: str = Column(String, nullable=False)
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationship
    evaluation: Mapped["MatchQualityEvaluation"] = relationship(
        "MatchQualityEvaluation",
        back_populates="feedback"
    )

    def __init__(self, **kwargs):
        """Initialize a new manual feedback entry."""
        super().__init__(**kwargs)
        logger.info(
            "Created new manual feedback",
            evaluation_id=self.evaluation_id,
            reviewer=self.reviewer
        )


class EvaluationMetricsHistory(Base):
    """Tracks historical metrics for quality evaluations."""
    
    __tablename__ = "evaluation_metrics_history"
    
    id: UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    evaluation_id: UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("match_quality_evaluations.id", ondelete="CASCADE"),
        nullable=False
    )
    metric_name: str = Column(String, nullable=False)
    metric_value: float = Column(Float, nullable=False)
    recorded_at: datetime = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationship
    evaluation: Mapped["MatchQualityEvaluation"] = relationship(
        "MatchQualityEvaluation",
        back_populates="metrics"
    )

    def __init__(self, **kwargs):
        """Initialize a new metrics history entry."""
        super().__init__(**kwargs)
        logger.info(
            "Created new evaluation metric",
            evaluation_id=self.evaluation_id,
            metric_name=self.metric_name,
            metric_value=self.metric_value
        )


# Update Job model to include quality evaluations relationship
from app.models.job import Job
Job.quality_evaluations: Mapped[List["MatchQualityEvaluation"]] = relationship(
    "MatchQualityEvaluation",
    back_populates="job",
    cascade="all, delete-orphan"
)
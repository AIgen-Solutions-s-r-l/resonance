"""
Repository implementation for quality tracking.

This module implements the repository pattern for quality tracking data access,
following the Single Responsibility Principle and providing a clean interface
for data operations.
"""
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.quality_tracking.interfaces import Repository
from app.models.quality_tracking import (
    MatchQualityEvaluation,
    ManualFeedback,
    EvaluationMetricsHistory
)


class QualityTrackingRepository(Repository[MatchQualityEvaluation]):
    """Repository implementation for quality tracking data."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        logger.info("Initialized quality tracking repository")
    
    async def save(self, entity: MatchQualityEvaluation) -> MatchQualityEvaluation:
        """
        Save a quality evaluation to the database.
        
        Args:
            entity: Quality evaluation to save
            
        Returns:
            Saved quality evaluation
        """
        try:
            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)
            
            logger.info(
                "Saved quality evaluation",
                evaluation_id=str(entity.id),
                resume_id=entity.resume_id,
                job_id=entity.job_id
            )
            
            return entity
            
        except Exception as e:
            logger.error(
                "Failed to save quality evaluation",
                error=str(e),
                error_type=type(e).__name__
            )
            await self.session.rollback()
            raise
    
    async def get_by_id(self, entity_id: UUID) -> Optional[MatchQualityEvaluation]:
        """
        Retrieve a quality evaluation by ID.
        
        Args:
            entity_id: ID of the evaluation to retrieve
            
        Returns:
            Quality evaluation if found, None otherwise
        """
        try:
            query = (
                select(MatchQualityEvaluation)
                .options(
                    selectinload(MatchQualityEvaluation.feedback),
                    selectinload(MatchQualityEvaluation.metrics)
                )
                .where(MatchQualityEvaluation.id == entity_id)
            )
            
            result = await self.session.execute(query)
            evaluation = result.scalar_one_or_none()
            
            if evaluation:
                logger.info(
                    "Retrieved quality evaluation",
                    evaluation_id=str(entity_id)
                )
            else:
                logger.warning(
                    "Quality evaluation not found",
                    evaluation_id=str(entity_id)
                )
            
            return evaluation
            
        except Exception as e:
            logger.error(
                "Failed to retrieve quality evaluation",
                error=str(e),
                error_type=type(e).__name__,
                evaluation_id=str(entity_id)
            )
            raise
    
    async def get_all(self, filters: Dict = None) -> List[MatchQualityEvaluation]:
        """
        Retrieve all quality evaluations matching the given filters.
        
        Args:
            filters: Optional dictionary of filter criteria
            
        Returns:
            List of matching quality evaluations
        """
        try:
            query = select(MatchQualityEvaluation).options(
                selectinload(MatchQualityEvaluation.feedback),
                selectinload(MatchQualityEvaluation.metrics)
            )
            
            if filters:
                if resume_id := filters.get("resume_id"):
                    query = query.where(
                        MatchQualityEvaluation.resume_id == resume_id
                    )
                if job_id := filters.get("job_id"):
                    query = query.where(
                        MatchQualityEvaluation.job_id == job_id
                    )
                if min_score := filters.get("min_quality_score"):
                    query = query.where(
                        MatchQualityEvaluation.quality_score >= min_score
                    )
                if max_score := filters.get("max_quality_score"):
                    query = query.where(
                        MatchQualityEvaluation.quality_score <= max_score
                    )
            
            result = await self.session.execute(query)
            evaluations = result.scalars().all()
            
            logger.info(
                "Retrieved quality evaluations",
                count=len(evaluations),
                filters=filters
            )
            
            return list(evaluations)
            
        except Exception as e:
            logger.error(
                "Failed to retrieve quality evaluations",
                error=str(e),
                error_type=type(e).__name__,
                filters=filters
            )
            raise
    
    async def update(self, entity: MatchQualityEvaluation) -> MatchQualityEvaluation:
        """
        Update an existing quality evaluation.
        
        Args:
            entity: Quality evaluation to update
            
        Returns:
            Updated quality evaluation
        """
        try:
            merged_entity = await self.session.merge(entity)
            await self.session.commit()
            await self.session.refresh(merged_entity)
            
            logger.info(
                "Updated quality evaluation",
                evaluation_id=str(entity.id)
            )
            
            return merged_entity
            
        except Exception as e:
            logger.error(
                "Failed to update quality evaluation",
                error=str(e),
                error_type=type(e).__name__,
                evaluation_id=str(entity.id)
            )
            await self.session.rollback()
            raise
    
    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete a quality evaluation by ID.
        
        Args:
            entity_id: ID of the evaluation to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            query = (
                select(MatchQualityEvaluation)
                .where(MatchQualityEvaluation.id == entity_id)
            )
            result = await self.session.execute(query)
            evaluation = result.scalar_one_or_none()
            
            if not evaluation:
                logger.warning(
                    "Quality evaluation not found for deletion",
                    evaluation_id=str(entity_id)
                )
                return False
            
            await self.session.delete(evaluation)
            await self.session.commit()
            
            logger.info(
                "Deleted quality evaluation",
                evaluation_id=str(entity_id)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete quality evaluation",
                error=str(e),
                error_type=type(e).__name__,
                evaluation_id=str(entity_id)
            )
            await self.session.rollback()
            raise
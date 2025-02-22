"""
Metrics tracking service implementation.

This module implements the metrics tracking service for quality evaluations,
following the Single Responsibility Principle and providing comprehensive
logging of quality metrics.
"""
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.quality_tracking.interfaces import MetricsTracker
from app.models.quality_tracking import (
    EvaluationMetricsHistory,
    MatchQualityEvaluation
)


class QualityMetricsTracker(MetricsTracker):
    """Implementation of metrics tracking for quality evaluations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the metrics tracker.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        logger.info("Initialized quality metrics tracker")
    
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
        try:
            # Verify evaluation exists
            eval_query = select(MatchQualityEvaluation).where(
                MatchQualityEvaluation.id == evaluation_id
            )
            result = await self.session.execute(eval_query)
            if not result.scalar_one_or_none():
                raise ValueError(f"Evaluation {evaluation_id} not found")
            
            metric = EvaluationMetricsHistory(
                evaluation_id=evaluation_id,
                metric_name=metric_name,
                metric_value=metric_value,
                recorded_at=timestamp or datetime.utcnow()
            )
            
            self.session.add(metric)
            await self.session.commit()
            
            logger.info(
                "Recorded quality metric",
                evaluation_id=str(evaluation_id),
                metric_name=metric_name,
                metric_value=metric_value
            )
            
        except Exception as e:
            logger.error(
                "Failed to record quality metric",
                error=str(e),
                error_type=type(e).__name__,
                evaluation_id=str(evaluation_id),
                metric_name=metric_name
            )
            await self.session.rollback()
            raise
    
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
        try:
            query = select(EvaluationMetricsHistory).where(
                EvaluationMetricsHistory.evaluation_id == evaluation_id
            )
            
            if metric_name:
                query = query.where(
                    EvaluationMetricsHistory.metric_name == metric_name
                )
            if start_time:
                query = query.where(
                    EvaluationMetricsHistory.recorded_at >= start_time
                )
            if end_time:
                query = query.where(
                    EvaluationMetricsHistory.recorded_at <= end_time
                )
            
            query = query.order_by(EvaluationMetricsHistory.recorded_at)
            
            result = await self.session.execute(query)
            metrics = result.scalars().all()
            
            metric_history = [
                {
                    "metric_name": metric.metric_name,
                    "metric_value": metric.metric_value,
                    "recorded_at": metric.recorded_at.isoformat()
                }
                for metric in metrics
            ]
            
            logger.info(
                "Retrieved metric history",
                evaluation_id=str(evaluation_id),
                metric_count=len(metric_history)
            )
            
            return metric_history
            
        except Exception as e:
            logger.error(
                "Failed to retrieve metric history",
                error=str(e),
                error_type=type(e).__name__,
                evaluation_id=str(evaluation_id)
            )
            raise
    
    async def get_aggregated_metrics(
        self,
        metric_name: str,
        start_time: datetime = None,
        end_time: datetime = None,
        group_by: str = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated metrics across all evaluations.
        
        Args:
            metric_name: Name of the metric to aggregate
            start_time: Optional start time filter
            end_time: Optional end time filter
            group_by: Optional grouping field (e.g., 'job_id')
            
        Returns:
            Dictionary containing aggregated metrics
        """
        try:
            base_query = select(
                EvaluationMetricsHistory.metric_value,
                MatchQualityEvaluation.job_id
            ).join(
                MatchQualityEvaluation,
                EvaluationMetricsHistory.evaluation_id == MatchQualityEvaluation.id
            ).where(
                EvaluationMetricsHistory.metric_name == metric_name
            )
            
            if start_time:
                base_query = base_query.where(
                    EvaluationMetricsHistory.recorded_at >= start_time
                )
            if end_time:
                base_query = base_query.where(
                    EvaluationMetricsHistory.recorded_at <= end_time
                )
            
            result = await self.session.execute(base_query)
            metrics = result.all()
            
            if not metrics:
                return {"overall": self._empty_aggregation()}
            
            if not group_by:
                return {
                    "overall": self._calculate_aggregation(
                        [m.metric_value for m in metrics]
                    )
                }
            
            # Group metrics
            grouped_metrics = {}
            for metric in metrics:
                group_value = getattr(metric, group_by, "unknown")
                if group_value not in grouped_metrics:
                    grouped_metrics[group_value] = []
                grouped_metrics[group_value].append(metric.metric_value)
            
            # Calculate aggregations for each group
            aggregations = {
                group: self._calculate_aggregation(values)
                for group, values in grouped_metrics.items()
            }
            
            logger.info(
                "Retrieved aggregated metrics",
                metric_name=metric_name,
                group_by=group_by,
                group_count=len(aggregations)
            )
            
            return aggregations
            
        except Exception as e:
            logger.error(
                "Failed to retrieve aggregated metrics",
                error=str(e),
                error_type=type(e).__name__,
                metric_name=metric_name
            )
            raise
    
    def _empty_aggregation(self) -> Dict[str, float]:
        """Return empty aggregation structure."""
        return {
            "count": 0,
            "average": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std_dev": 0.0
        }
    
    def _calculate_aggregation(self, values: List[float]) -> Dict[str, float]:
        """Calculate aggregation metrics for a list of values."""
        count = len(values)
        avg = sum(values) / count
        
        # Calculate standard deviation
        squared_diff_sum = sum((x - avg) ** 2 for x in values)
        std_dev = (squared_diff_sum / count) ** 0.5
        
        return {
            "count": count,
            "average": avg,
            "min": min(values),
            "max": max(values),
            "std_dev": std_dev
        }
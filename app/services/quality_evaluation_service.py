"""
Quality evaluation service implementation.

This module implements the quality evaluation service using LLMs to assess
resume-job match quality. It follows the Single Responsibility Principle and
uses dependency injection for flexibility.
"""
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import json
from datetime import datetime

from loguru import logger
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.quality_tracking.interfaces import (
    QualityEvaluator,
    QualityScore,
    Repository,
    MetricsTracker
)
from app.core.config import settings
from app.models.quality_tracking import (
    MatchQualityEvaluation,
    EvaluationMetricsHistory
)


class LLMQualityScore(QualityScore):
    """Implementation of QualityScore protocol for LLM evaluations."""
    
    def __init__(
        self,
        match_score: float,
        quality_score: float,
        skill_alignment_score: float,
        experience_match_score: float,
        evaluation_text: str
    ):
        self.match_score = match_score
        self.quality_score = quality_score
        self.skill_alignment_score = skill_alignment_score
        self.experience_match_score = experience_match_score
        self.evaluation_text = evaluation_text


class OpenAIQualityEvaluator(QualityEvaluator):
    """Quality evaluator implementation using OpenAI's API."""
    
    def __init__(
        self,
        repository: Repository[MatchQualityEvaluation],
        metrics_tracker: MetricsTracker,
        model: str = "gpt-4-turbo-preview"
    ):
        """
        Initialize the evaluator with dependencies.
        
        Args:
            repository: Repository for storing evaluations
            metrics_tracker: Tracker for evaluation metrics
            model: OpenAI model to use
        """
        self.repository = repository
        self.metrics_tracker = metrics_tracker
        self.model = model
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        logger.info(f"Initialized OpenAI quality evaluator with model: {model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _call_openai(self, prompt: str) -> Dict:
        """
        Make an API call to OpenAI with retry logic.
        
        Args:
            prompt: The evaluation prompt
            
        Returns:
            Parsed JSON response
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert recruiter evaluating job matches."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(
                "OpenAI API call failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _create_evaluation_prompt(self, resume: Dict, job: Dict) -> str:
        """
        Create the evaluation prompt for the LLM.
        
        Args:
            resume: Resume data
            job: Job data
            
        Returns:
            Formatted prompt string
        """
        return f"""
        Please analyze the following resume and job posting:

        Resume:
        {json.dumps(resume, indent=2)}

        Job Posting:
        {json.dumps(job, indent=2)}

        Evaluate the match based on the following criteria:
        1. Skills Alignment (0-100)
        2. Experience Match (0-100)
        3. Overall Fit (0-100)

        Provide a detailed explanation for each score and conclude with an overall recommendation.
        Format your response as JSON:
        {{
            "skills_alignment": {{
                "score": <0-100>,
                "explanation": "<detailed explanation>"
            }},
            "experience_match": {{
                "score": <0-100>,
                "explanation": "<detailed explanation>"
            }},
            "overall_fit": {{
                "score": <0-100>,
                "explanation": "<detailed explanation>"
            }},
            "recommendation": "<overall recommendation>"
        }}
        """
    
    async def evaluate_match(self, resume: Dict, job: Dict) -> QualityScore:
        """
        Evaluate a single resume-job match.
        
        Args:
            resume: Resume data
            job: Job data
            
        Returns:
            QualityScore containing evaluation results
        """
        try:
            logger.info(
                "Starting match evaluation",
                resume_id=resume.get("_id"),
                job_id=job.get("id")
            )
            
            prompt = self._create_evaluation_prompt(resume, job)
            evaluation = await self._call_openai(prompt)
            
            # Calculate weighted quality score
            skill_score = evaluation["skills_alignment"]["score"]
            exp_score = evaluation["experience_match"]["score"]
            fit_score = evaluation["overall_fit"]["score"]
            
            quality_score = (
                skill_score * 0.4 +
                exp_score * 0.4 +
                fit_score * 0.2
            )
            
            # Create evaluation text
            evaluation_text = (
                f"Skills Alignment ({skill_score}): {evaluation['skills_alignment']['explanation']}\n\n"
                f"Experience Match ({exp_score}): {evaluation['experience_match']['explanation']}\n\n"
                f"Overall Fit ({fit_score}): {evaluation['overall_fit']['explanation']}\n\n"
                f"Recommendation: {evaluation['recommendation']}"
            )
            
            score = LLMQualityScore(
                match_score=float(job.get("score", 0.0)),
                quality_score=quality_score,
                skill_alignment_score=skill_score,
                experience_match_score=exp_score,
                evaluation_text=evaluation_text
            )
            
            # Store evaluation
            evaluation_record = MatchQualityEvaluation(
                resume_id=str(resume.get("_id")),
                job_id=str(job.get("id")),
                match_score=score.match_score,
                quality_score=score.quality_score,
                skill_alignment_score=score.skill_alignment_score,
                experience_match_score=score.experience_match_score,
                evaluation_text=score.evaluation_text
            )
            
            stored_evaluation = await self.repository.save(evaluation_record)
            
            # Track metrics
            await self.metrics_tracker.record_metric(
                evaluation_id=stored_evaluation.id,
                metric_name="quality_score",
                metric_value=quality_score
            )
            
            logger.success(
                "Match evaluation completed",
                resume_id=resume.get("_id"),
                job_id=job.get("id"),
                quality_score=quality_score
            )
            
            return score
            
        except Exception as e:
            logger.error(
                "Match evaluation failed",
                error=str(e),
                error_type=type(e).__name__,
                resume_id=resume.get("_id"),
                job_id=job.get("id")
            )
            raise
    
    async def batch_evaluate(
        self,
        matches: List[Tuple[Dict, Dict]]
    ) -> List[QualityScore]:
        """
        Evaluate multiple matches in batch.
        
        Args:
            matches: List of (resume, job) tuples to evaluate
            
        Returns:
            List of QualityScore objects
        """
        try:
            logger.info(f"Starting batch evaluation of {len(matches)} matches")
            
            results = []
            for resume, job in matches:
                score = await self.evaluate_match(resume, job)
                results.append(score)
            
            logger.success(f"Completed batch evaluation of {len(matches)} matches")
            return results
            
        except Exception as e:
            logger.error(
                "Batch evaluation failed",
                error=str(e),
                error_type=type(e).__name__,
                batch_size=len(matches)
            )
            raise
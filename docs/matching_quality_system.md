# Matching Quality Tracking System Design

## 1. System Overview

The matching quality tracking system will implement a self-supervised approach using LLMs to evaluate and score resume-job matches. The system will store these evaluations for manual review and continuous improvement.

## 2. Architecture Components

### 2.1 Core Components

#### Quality Evaluation Service
```python
class QualityEvaluator:
    """Evaluates the quality of resume-job matches using LLM-based analysis."""
    
    def evaluate_match(self, resume: Dict, job: Dict) -> MatchQualityScore:
        """Evaluates a single resume-job match."""
        
    def batch_evaluate(self, matches: List[Tuple[Dict, Dict]]) -> List[MatchQualityScore]:
        """Evaluates multiple matches in batch."""
```

#### Match Quality Repository
```python
class MatchQualityRepository:
    """Handles storage and retrieval of match quality data."""
    
    def save_evaluation(self, score: MatchQualityScore) -> None:
        """Stores a single evaluation result."""
        
    def get_evaluations(self, filters: Dict) -> List[MatchQualityScore]:
        """Retrieves evaluation results based on filters."""
```

#### Feedback Loop System
```python
class FeedbackLoopManager:
    """Manages the feedback loop for improving match quality."""
    
    def collect_feedback(self, evaluation_id: str, feedback: Dict) -> None:
        """Collects manual feedback on evaluations."""
        
    def adjust_scoring(self, feedback_data: List[Dict]) -> None:
        """Adjusts scoring based on collected feedback."""
```

### 2.2 Database Schema

```sql
-- Match quality evaluations table
CREATE TABLE match_quality_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id VARCHAR NOT NULL,
    job_id VARCHAR NOT NULL REFERENCES "Jobs"(id),
    match_score FLOAT NOT NULL,
    quality_score FLOAT NOT NULL,
    skill_alignment_score FLOAT NOT NULL,
    experience_match_score FLOAT NOT NULL,
    evaluation_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES "Jobs"(id)
);

-- Manual feedback table
CREATE TABLE manual_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL,
    feedback_score FLOAT NOT NULL,
    feedback_text TEXT,
    reviewer VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES match_quality_evaluations(id)
);

-- Evaluation metrics history
CREATE TABLE evaluation_metrics_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL,
    metric_name VARCHAR NOT NULL,
    metric_value FLOAT NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES match_quality_evaluations(id)
);
```

## 3. LLM Evaluation Prompt Engineering

### 3.1 Base Evaluation Prompt Template
```
You are an expert recruiter tasked with evaluating the quality of a job match. 
Please analyze the following resume and job posting:

Resume:
{resume_content}

Job Posting:
{job_content}

Evaluate the match based on the following criteria:
1. Skills Alignment (0-100)
2. Experience Match (0-100)
3. Overall Fit (0-100)

Provide a detailed explanation for each score and conclude with an overall recommendation.
Format your response as JSON:
{
    "skills_alignment": {
        "score": <0-100>,
        "explanation": "<detailed explanation>"
    },
    "experience_match": {
        "score": <0-100>,
        "explanation": "<detailed explanation>"
    },
    "overall_fit": {
        "score": <0-100>,
        "explanation": "<detailed explanation>"
    },
    "recommendation": "<overall recommendation>"
}
```

### 3.2 Evaluation Criteria

1. **Skills Alignment (40%)**
   - Technical skills match
   - Soft skills alignment
   - Tool/technology proficiency

2. **Experience Match (40%)**
   - Years of relevant experience
   - Industry alignment
   - Role responsibility match

3. **Overall Fit (20%)**
   - Career trajectory alignment
   - Company culture fit
   - Growth potential

## 4. Implementation Strategy

### 4.1 Integration with Existing System

1. Extend the JobMatcher class to include quality evaluation:
```python
class JobMatcher:
    def __init__(self):
        self.quality_evaluator = QualityEvaluator()
        self.quality_repository = MatchQualityRepository()
    
    async def process_job(self, resume: Dict, ...) -> Dict:
        # Existing matching logic
        matches = self.get_top_jobs_by_multiple_metrics(...)
        
        # Add quality evaluation
        for match in matches:
            quality_score = await self.quality_evaluator.evaluate_match(
                resume, match
            )
            await self.quality_repository.save_evaluation(quality_score)
```

2. Add quality metrics to the API response:
```python
class JobMatchResponse(BaseModel):
    id: str
    title: str
    score: float
    quality_score: float
    quality_details: Dict[str, Any]
```

### 4.2 Monitoring and Analytics

1. Track key metrics:
   - Average quality scores over time
   - Distribution of scores by job category
   - Correlation between initial match scores and quality scores
   - Manual feedback alignment rate

2. Create monitoring dashboards for:
   - Quality score trends
   - Feedback analysis
   - System performance metrics
   - Error rates and issues

### 4.3 Continuous Improvement

1. Regular evaluation of prompt effectiveness
2. Feedback loop integration for prompt refinement
3. Periodic model retraining based on collected data
4. Manual review sampling for quality assurance

## 5. Error Handling and Reliability

1. Implement retry mechanisms for LLM API calls
2. Handle edge cases in resume and job data
3. Validate evaluation scores and feedback
4. Monitor and alert on quality degradation

## 6. Security and Privacy

1. Ensure PII handling compliance
2. Implement access controls for quality data
3. Audit logging for all quality evaluations
4. Secure storage of evaluation results

## 7. Next Steps

1. Implement core quality evaluation service
2. Set up database schema and migrations
3. Integrate with existing matching system
4. Develop monitoring and analytics
5. Create feedback collection interface
6. Deploy and validate initial version

This design provides a robust foundation for implementing a self-supervised quality tracking system that will continuously improve the matching service's effectiveness. Use SOLID pattern, loguru and python best practices.
# Quality Tracking System Enhancement Plan

## Current System vs New Requirements

### Current System
- Evaluates individual resume-job matches
- Stores evaluations in match_quality_evaluations table
- Collects manual feedback
- Tracks various metrics

### New Requirements
- Focus on top 10 matches per resume
- OpenAI validation with specific scoring criteria
- New tracking-system table
- Enhanced visualization and filtering
- Document download capabilities

## Implementation Plan

### 1. Database Schema Updates

#### New Table: tracking-system
```sql
CREATE TABLE tracking_system (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id VARCHAR NOT NULL,
    job_id VARCHAR NOT NULL REFERENCES "Jobs"(id),
    our_matching_score FLOAT NOT NULL,  -- Internal algorithm score
    llm_skill_score FLOAT NOT NULL,     -- OpenAI skill assessment
    llm_experience_score FLOAT NOT NULL, -- OpenAI experience assessment
    llm_overall_score FLOAT NOT NULL,    -- OpenAI overall assessment
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(resume_id, job_id)
);

-- Indexes for performance
CREATE INDEX idx_tracking_resume_id ON tracking_system(resume_id);
CREATE INDEX idx_tracking_job_id ON tracking_system(job_id);
CREATE INDEX idx_tracking_our_score ON tracking_system(our_matching_score);
```

### 2. Service Layer Updates

#### 2.1 Quality Evaluation Service
```python
class QualityEvaluationService:
    async def evaluate_top_matches(self, resume_id: str, job_matches: List[Dict]) -> List[Dict]:
        """
        Evaluate top 10 job matches for a resume using OpenAI.
        
        Args:
            resume_id: ID of the resume
            job_matches: List of top job matches with scores
            
        Returns:
            List of evaluated matches with LLM scores
        """
        # 1. Get resume data
        # 2. Filter top 10 matches
        # 3. Evaluate each match with OpenAI
        # 4. Store results in tracking_system
        # 5. Return comprehensive results
```

#### 2.2 OpenAI Prompt Template
```python
EVALUATION_PROMPT = """
Analyze the following resume and job match:

Resume:
{resume_text}

Job Description:
{job_description}

Evaluate and score (0-100) the following aspects:
1. Skills Match: Assess the alignment of technical and soft skills
2. Experience Match: Evaluate years of experience, industry fit, and role responsibilities
3. Overall Match: Consider career trajectory and potential fit

Provide your evaluation in JSON format:
{
    "skill_score": <0-100>,
    "experience_score": <0-100>,
    "overall_score": <0-100>,
    "analysis": {
        "skills": "<detailed analysis>",
        "experience": "<detailed analysis>",
        "overall": "<detailed analysis>"
    }
}
"""
```

### 3. API Endpoint Updates

#### 3.1 New Endpoints in quality_tracking_router.py
```python
@router.get("/high-scoring-matches")
async def get_high_scoring_matches(
    min_score: float = 0.8,
    limit: int = 50
) -> List[Dict]:
    """Return high-scoring matches with correlation analysis."""

@router.get("/match-statistics")
async def get_match_statistics() -> Dict:
    """Return statistical analysis of matching scores."""

@router.get("/download/{resume_id}/{job_id}")
async def download_documents(
    resume_id: str,
    job_id: str
) -> StreamingResponse:
    """Download resume and job description."""
```

### 4. Statistical Analysis Implementation

#### 4.1 Score Analysis
- Calculate correlation between internal scores and LLM scores
- Generate distribution analysis
- Identify patterns and trends
- Create visualization data

#### 4.2 Metrics to Track
- Score distributions
- Internal vs LLM score correlation
- Success rate of top 10 matches
- Time-based trends

### 5. Implementation Phases

#### Phase 1: Database and Core Logic
1. Create new tracking_system table
2. Implement OpenAI evaluation service
3. Update existing matching service to store top 10 matches

#### Phase 2: API and Analysis
1. Implement new API endpoints
2. Add statistical analysis functions
3. Create document download functionality

#### Phase 3: Monitoring and Optimization
1. Add performance monitoring
2. Implement caching for frequent queries
3. Optimize database queries
4. Add error handling and logging

### 6. Technical Considerations

#### 6.1 Performance
- Batch OpenAI requests for efficiency
- Cache frequent database queries
- Use appropriate indexes
- Implement pagination for large result sets

#### 6.2 Security
- Validate all input parameters
- Implement rate limiting
- Secure document downloads
- Log access to sensitive data

#### 6.3 Monitoring
- Track API response times
- Monitor OpenAI API usage
- Track error rates
- Monitor database performance

## Next Steps

1. Review and approve database schema changes
2. Begin implementation of Phase 1
3. Set up monitoring and logging
4. Create test cases for new functionality
5. Document API changes and new features

This plan provides a structured approach to implementing the new requirements while maintaining the existing system's functionality. The implementation will be done in phases to ensure smooth integration and minimal disruption to existing services.
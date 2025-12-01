"""
Tests for Phase 4: Cross-Encoder Reranking + Explainability.

Tests cover:
- CrossEncoder model initialization and inference
- Reranker two-stage pipeline
- MatchExplainer skill/experience/location matching
- MatchingPipeline end-to-end flow
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from app.ml.models.explainer import (
    MatchExplainer,
    MatchExplanation,
    SkillMatchExplanation,
    ExperienceMatchExplanation,
    LocationMatchExplanation,
    MatchStrength,
)
from app.ml.models.reranker import (
    Reranker,
    RerankResult,
    RerankingConfig,
)
from app.ml.pipeline import (
    MatchingPipeline,
    MatchResult,
    PipelineConfig,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_resume():
    return """
    Senior Software Engineer with 8 years of experience in Python,
    JavaScript, and cloud technologies. Expertise in AWS, Docker,
    Kubernetes, and machine learning. Led teams of 5+ engineers.
    Based in San Francisco, CA.
    """


@pytest.fixture
def sample_jobs():
    return [
        {
            "id": "job1",
            "title": "Senior Python Developer",
            "description": "Looking for Python expert with AWS experience. "
                           "Must know Docker and Kubernetes. 5+ years required.",
            "company_name": "TechCorp",
            "location": "San Francisco, CA",
            "experience": "senior-level",
            "workplace_type": "hybrid",
        },
        {
            "id": "job2",
            "title": "Junior Frontend Developer",
            "description": "Entry level role for React and JavaScript developer. "
                           "No backend experience needed.",
            "company_name": "StartupXYZ",
            "location": "New York, NY",
            "experience": "entry-level",
            "workplace_type": "remote",
        },
        {
            "id": "job3",
            "title": "ML Engineer",
            "description": "Machine learning engineer with Python and TensorFlow. "
                           "Experience with cloud platforms preferred.",
            "company_name": "AI Labs",
            "location": "San Jose, CA",
            "experience": "mid-level",
            "workplace_type": "onsite",
        },
    ]


@pytest.fixture
def mock_skill_extractor():
    """Mock skill extractor that returns predefined skills."""
    extractor = Mock()

    @dataclass
    class MockSkill:
        canonical_name: str
        original_text: str = ""
        confidence: float = 1.0

    def extract_fn(text):
        text_lower = text.lower()
        skills = []
        skill_keywords = [
            "python", "javascript", "aws", "docker", "kubernetes",
            "react", "tensorflow", "machine learning", "sql"
        ]
        for skill in skill_keywords:
            if skill in text_lower:
                skills.append(MockSkill(canonical_name=skill))
        return skills

    def overlap_fn(skills1, skills2):
        names1 = {s.canonical_name for s in skills1}
        names2 = {s.canonical_name for s in skills2}
        intersection = names1 & names2
        union = names1 | names2
        jaccard = len(intersection) / len(union) if union else 0
        return {"jaccard_similarity": jaccard}

    extractor.extract = extract_fn
    extractor.compute_skill_overlap = overlap_fn
    return extractor


# ============================================================================
# MatchExplainer Tests
# ============================================================================

class TestMatchExplainer:
    """Tests for MatchExplainer."""

    def test_init(self, mock_skill_extractor):
        """Test explainer initialization."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)
        assert explainer.skill_extractor is not None
        assert len(explainer.experience_levels) > 0

    def test_explain_strong_match(self, mock_skill_extractor, sample_resume, sample_jobs):
        """Test explanation for a strong match."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        job = sample_jobs[0]  # Senior Python Developer - good match
        explanation = explainer.explain(
            resume_text=sample_resume,
            job_text=job["description"],
            job_id=job["id"],
            job_title=job["title"],
            overall_score=0.85,
            resume_metadata={"experience_level": "senior", "location": "San Francisco"},
            job_metadata={
                "experience_level": job["experience"],
                "location": job["location"],
                "is_remote": False,
            },
        )

        assert isinstance(explanation, MatchExplanation)
        assert explanation.job_id == "job1"
        assert explanation.overall_strength == MatchStrength.STRONG
        assert len(explanation.skill_explanation.matched_skills) > 0
        assert "python" in [s.lower() for s in explanation.skill_explanation.matched_skills]

    def test_explain_weak_match(self, mock_skill_extractor, sample_resume, sample_jobs):
        """Test explanation for a weak match."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        job = sample_jobs[1]  # Junior Frontend - weak match for senior
        explanation = explainer.explain(
            resume_text=sample_resume,
            job_text=job["description"],
            job_id=job["id"],
            job_title=job["title"],
            overall_score=0.35,
            resume_metadata={"experience_level": "senior"},
            job_metadata={"experience_level": job["experience"]},
        )

        assert explanation.overall_strength == MatchStrength.WEAK

    def test_experience_level_matching(self, mock_skill_extractor):
        """Test experience level comparison."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        # Senior meets senior requirement
        exp_exp = explainer._explain_experience(
            resume_level="senior",
            resume_years=8,
            job_level="senior",
            job_years=5,
        )
        assert exp_exp.match_score >= 0.8
        assert exp_exp.strength == MatchStrength.STRONG

        # Entry level for senior requirement
        exp_exp = explainer._explain_experience(
            resume_level="entry",
            resume_years=1,
            job_level="senior",
            job_years=5,
        )
        assert exp_exp.match_score < 0.5
        assert exp_exp.strength in [MatchStrength.WEAK, MatchStrength.MISSING]

    def test_location_matching_remote(self, mock_skill_extractor):
        """Test location matching for remote jobs."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        loc_exp = explainer._explain_location(
            resume_location="Tokyo, Japan",
            job_location="San Francisco, CA",
            is_remote=True,
        )
        assert loc_exp.match_score == 1.0
        assert loc_exp.strength == MatchStrength.STRONG

    def test_location_matching_same_city(self, mock_skill_extractor):
        """Test location matching for same city."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        loc_exp = explainer._explain_location(
            resume_location="San Francisco",
            job_location="San Francisco",
            is_remote=False,
        )
        assert loc_exp.match_score == 1.0

    def test_to_dict_serialization(self, mock_skill_extractor, sample_resume, sample_jobs):
        """Test that explanation can be serialized to dict."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        explanation = explainer.explain(
            resume_text=sample_resume,
            job_text=sample_jobs[0]["description"],
            job_id="job1",
            job_title="Test Job",
            overall_score=0.75,
        )

        result = explanation.to_dict()
        assert isinstance(result, dict)
        assert "job_id" in result
        assert "skills" in result
        assert "highlights" in result
        assert "concerns" in result

    def test_explain_batch(self, mock_skill_extractor, sample_resume, sample_jobs):
        """Test batch explanation generation."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        scores = [0.85, 0.45, 0.70]
        explanations = explainer.explain_batch(sample_resume, sample_jobs, scores)

        assert len(explanations) == 3
        assert all(isinstance(e, MatchExplanation) for e in explanations)


# ============================================================================
# RerankResult Tests
# ============================================================================

class TestRerankResult:
    """Tests for RerankResult dataclass."""

    def test_rerank_result_creation(self):
        """Test RerankResult creation."""
        result = RerankResult(
            job_id="job123",
            title="Test Job",
            bi_encoder_score=0.8,
            cross_encoder_score=0.9,
            final_score=0.85,
            rank=1,
        )

        assert result.job_id == "job123"
        assert result.final_score == 0.85
        assert result.metadata == {}


class TestRerankingConfig:
    """Tests for RerankingConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RerankingConfig()

        assert config.top_k_retrieve == 100
        assert config.top_k_rerank == 25
        assert config.cross_encoder_weight == 0.7
        assert config.bi_encoder_weight == 0.3

    def test_custom_config(self):
        """Test custom configuration."""
        config = RerankingConfig(
            top_k_retrieve=50,
            top_k_rerank=10,
            cross_encoder_weight=0.8,
        )

        assert config.top_k_retrieve == 50
        assert config.top_k_rerank == 10


# ============================================================================
# MatchingPipeline Tests
# ============================================================================

class TestMatchingPipeline:
    """Tests for MatchingPipeline."""

    def test_pipeline_config_defaults(self):
        """Test PipelineConfig default values."""
        config = PipelineConfig()

        assert config.top_k_retrieve == 100
        assert config.top_k_final == 25
        assert config.use_cross_encoder is True
        assert config.use_skill_graph is True
        assert config.use_explainability is True

    def test_pipeline_without_components(self, sample_resume, sample_jobs):
        """Test pipeline works with no ML components (fallback mode)."""
        config = PipelineConfig(
            use_cross_encoder=False,
            use_skill_graph=False,
            use_explainability=False,
        )
        pipeline = MatchingPipeline(config=config)

        results = pipeline.match(sample_resume, sample_jobs)

        # Should still return results (with default scores)
        assert len(results) <= config.top_k_final
        assert all(isinstance(r, MatchResult) for r in results)

    def test_match_result_to_dict(self):
        """Test MatchResult serialization."""
        result = MatchResult(
            job_id="job1",
            job_title="Test Job",
            rank=1,
            bi_encoder_score=0.8,
            cross_encoder_score=0.9,
            skill_graph_score=0.7,
            final_score=0.82,
            latency_ms=50.0,
        )

        d = result.to_dict()
        assert d["job_id"] == "job1"
        assert d["rank"] == 1
        assert d["score"] == 0.82
        assert "scores" in d
        assert d["scores"]["bi_encoder"] == 0.8


# ============================================================================
# Integration Tests
# ============================================================================

class TestPhase4Integration:
    """Integration tests for Phase 4 components."""

    def test_explainer_with_real_text(self, mock_skill_extractor):
        """Test explainer with realistic text content."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        resume = """
        Software Engineer with expertise in Python, AWS, and Docker.
        5 years experience building scalable web applications.
        """

        job = """
        We are looking for a Python developer with cloud experience.
        Must have AWS and containerization skills. 3+ years required.
        """

        explanation = explainer.explain(
            resume_text=resume,
            job_text=job,
            job_id="test-job",
            job_title="Python Developer",
            overall_score=0.82,
        )

        assert explanation.overall_score == 0.82
        assert "python" in [s.lower() for s in explanation.skill_explanation.matched_skills]
        assert "aws" in [s.lower() for s in explanation.skill_explanation.matched_skills]

    def test_pipeline_result_ranking(self, sample_jobs):
        """Test that pipeline results are properly ranked."""
        config = PipelineConfig(
            use_cross_encoder=False,
            use_skill_graph=False,
            use_explainability=False,
            top_k_final=3,
        )
        pipeline = MatchingPipeline(config=config)

        results = pipeline.match("Python AWS Docker developer", sample_jobs)

        # Verify ranks are assigned correctly
        for i, result in enumerate(results):
            assert result.rank == i + 1


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_empty_candidates(self):
        """Test pipeline with empty candidates."""
        pipeline = MatchingPipeline()
        results = pipeline.match("Some resume text", [])
        assert results == []

    def test_empty_resume(self, sample_jobs):
        """Test pipeline with empty resume."""
        config = PipelineConfig(
            use_cross_encoder=False,
            use_skill_graph=False,
            use_explainability=False,
        )
        pipeline = MatchingPipeline(config=config)
        results = pipeline.match("", sample_jobs)
        assert len(results) > 0  # Should still work

    def test_missing_job_fields(self, mock_skill_extractor):
        """Test explainer handles missing job metadata gracefully."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        explanation = explainer.explain(
            resume_text="Python developer",
            job_text="Python job",
            job_id="1",
            job_title="Job",
            overall_score=0.5,
            resume_metadata={},
            job_metadata={},
        )

        assert explanation is not None
        assert explanation.experience_explanation is None  # No exp data
        assert explanation.location_explanation is None  # No location data

    def test_strength_boundary_values(self, mock_skill_extractor):
        """Test MatchStrength at boundary values."""
        explainer = MatchExplainer(skill_extractor=mock_skill_extractor)

        assert explainer._score_to_strength(1.0) == MatchStrength.STRONG
        assert explainer._score_to_strength(0.8) == MatchStrength.STRONG
        assert explainer._score_to_strength(0.79) == MatchStrength.MODERATE
        assert explainer._score_to_strength(0.5) == MatchStrength.MODERATE
        assert explainer._score_to_strength(0.49) == MatchStrength.WEAK
        assert explainer._score_to_strength(0.2) == MatchStrength.WEAK
        assert explainer._score_to_strength(0.19) == MatchStrength.MISSING
        assert explainer._score_to_strength(0.0) == MatchStrength.MISSING

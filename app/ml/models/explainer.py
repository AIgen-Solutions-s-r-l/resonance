"""
Explainability Module for Match Results.

Provides human-readable explanations for why a resume
matches (or doesn't match) a job posting.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.log.logging import logger
from app.ml.knowledge_graph.skill_extractor import SkillExtractor, ExtractedSkill


class MatchStrength(Enum):
    """Strength of a match component."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    MISSING = "missing"


@dataclass
class SkillMatchExplanation:
    """Explanation for skill matching."""
    matched_skills: List[str]
    missing_skills: List[str]
    related_skills: List[Tuple[str, str, float]]  # (resume_skill, job_skill, similarity)
    bonus_skills: List[str]  # Resume skills not required but valuable
    match_score: float
    strength: MatchStrength


@dataclass
class ExperienceMatchExplanation:
    """Explanation for experience matching."""
    required_level: str
    candidate_level: str
    years_required: Optional[int]
    years_candidate: Optional[int]
    match_score: float
    strength: MatchStrength
    notes: str = ""


@dataclass
class LocationMatchExplanation:
    """Explanation for location matching."""
    job_location: str
    candidate_location: str
    is_remote: bool
    distance_km: Optional[float]
    match_score: float
    strength: MatchStrength


@dataclass
class MatchExplanation:
    """Complete match explanation."""
    job_id: str
    job_title: str
    overall_score: float
    overall_strength: MatchStrength

    skill_explanation: SkillMatchExplanation
    experience_explanation: Optional[ExperienceMatchExplanation] = None
    location_explanation: Optional[LocationMatchExplanation] = None

    summary: str = ""
    highlights: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "job_id": self.job_id,
            "job_title": self.job_title,
            "overall_score": self.overall_score,
            "overall_strength": self.overall_strength.value,
            "summary": self.summary,
            "highlights": self.highlights,
            "concerns": self.concerns,
            "skills": {
                "matched": self.skill_explanation.matched_skills,
                "missing": self.skill_explanation.missing_skills,
                "related": [
                    {"resume": r, "job": j, "similarity": s}
                    for r, j, s in self.skill_explanation.related_skills
                ],
                "bonus": self.skill_explanation.bonus_skills,
                "score": self.skill_explanation.match_score,
            },
            "experience": {
                "required": self.experience_explanation.required_level if self.experience_explanation else None,
                "candidate": self.experience_explanation.candidate_level if self.experience_explanation else None,
                "score": self.experience_explanation.match_score if self.experience_explanation else None,
            } if self.experience_explanation else None,
            "location": {
                "job": self.location_explanation.job_location if self.location_explanation else None,
                "candidate": self.location_explanation.candidate_location if self.location_explanation else None,
                "remote": self.location_explanation.is_remote if self.location_explanation else None,
                "score": self.location_explanation.match_score if self.location_explanation else None,
            } if self.location_explanation else None,
        }


class MatchExplainer:
    """
    Generates explanations for job-resume matches.

    Analyzes:
    - Skill overlap and related skills
    - Experience level matching
    - Location compatibility
    """

    def __init__(
        self,
        skill_extractor: SkillExtractor = None,
        skill_taxonomy=None,
    ):
        """
        Initialize the explainer.

        Args:
            skill_extractor: Skill extraction module
            skill_taxonomy: Skill taxonomy for related skills
        """
        self.skill_extractor = skill_extractor or SkillExtractor()
        self.skill_taxonomy = skill_taxonomy

        # Experience level hierarchy
        self.experience_levels = {
            "internship": 0,
            "entry": 1,
            "entry-level": 1,
            "junior": 1,
            "mid": 2,
            "mid-level": 2,
            "senior": 3,
            "senior-level": 3,
            "lead": 4,
            "principal": 4,
            "staff": 4,
            "executive": 5,
            "director": 5,
            "vp": 6,
            "c-level": 7,
        }

        logger.info("MatchExplainer initialized")

    def explain(
        self,
        resume_text: str,
        job_text: str,
        job_id: str,
        job_title: str,
        overall_score: float,
        resume_metadata: Dict[str, Any] = None,
        job_metadata: Dict[str, Any] = None,
    ) -> MatchExplanation:
        """
        Generate explanation for a match.

        Args:
            resume_text: Resume content
            job_text: Job description
            job_id: Job identifier
            job_title: Job title
            overall_score: Overall match score
            resume_metadata: Additional resume info (experience, location)
            job_metadata: Additional job info (experience required, location)

        Returns:
            MatchExplanation with detailed breakdown
        """
        resume_metadata = resume_metadata or {}
        job_metadata = job_metadata or {}

        # Extract skills
        resume_skills = self.skill_extractor.extract(resume_text)
        job_skills = self.skill_extractor.extract(job_text)

        # Explain skills
        skill_explanation = self._explain_skills(resume_skills, job_skills)

        # Explain experience
        experience_explanation = self._explain_experience(
            resume_metadata.get("experience_level"),
            resume_metadata.get("years_experience"),
            job_metadata.get("experience_level"),
            job_metadata.get("years_required"),
        )

        # Explain location
        location_explanation = self._explain_location(
            resume_metadata.get("location"),
            job_metadata.get("location"),
            job_metadata.get("is_remote", False),
        )

        # Determine overall strength
        overall_strength = self._score_to_strength(overall_score)

        # Generate summary and highlights
        summary, highlights, concerns = self._generate_summary(
            skill_explanation,
            experience_explanation,
            location_explanation,
            overall_score,
        )

        return MatchExplanation(
            job_id=job_id,
            job_title=job_title,
            overall_score=overall_score,
            overall_strength=overall_strength,
            skill_explanation=skill_explanation,
            experience_explanation=experience_explanation,
            location_explanation=location_explanation,
            summary=summary,
            highlights=highlights,
            concerns=concerns,
        )

    def _explain_skills(
        self,
        resume_skills: List[ExtractedSkill],
        job_skills: List[ExtractedSkill],
    ) -> SkillMatchExplanation:
        """Explain skill matching."""
        resume_skill_names = {s.canonical_name for s in resume_skills}
        job_skill_names = {s.canonical_name for s in job_skills}

        # Direct matches
        matched = list(resume_skill_names & job_skill_names)

        # Missing skills (in job but not resume)
        missing = list(job_skill_names - resume_skill_names)

        # Bonus skills (in resume but not required)
        bonus = list(resume_skill_names - job_skill_names)

        # Find related skills
        related = []
        if self.skill_taxonomy:
            for resume_skill in resume_skill_names - job_skill_names:
                for job_skill in job_skill_names - resume_skill_names:
                    similarity = self.skill_taxonomy.compute_skill_similarity(
                        resume_skill, job_skill
                    )
                    if similarity > 0.3:
                        related.append((resume_skill, job_skill, similarity))

            # Sort by similarity
            related.sort(key=lambda x: x[2], reverse=True)
            related = related[:5]  # Top 5 related

        # Calculate match score
        if job_skill_names:
            direct_match_ratio = len(matched) / len(job_skill_names)
            related_bonus = sum(s for _, _, s in related) * 0.5 / max(len(job_skill_names), 1)
            match_score = min(1.0, direct_match_ratio + related_bonus)
        else:
            match_score = 1.0 if resume_skill_names else 0.5

        strength = self._score_to_strength(match_score)

        return SkillMatchExplanation(
            matched_skills=matched,
            missing_skills=missing,
            related_skills=related,
            bonus_skills=bonus[:5],  # Top 5 bonus
            match_score=match_score,
            strength=strength,
        )

    def _explain_experience(
        self,
        resume_level: Optional[str],
        resume_years: Optional[int],
        job_level: Optional[str],
        job_years: Optional[int],
    ) -> Optional[ExperienceMatchExplanation]:
        """Explain experience matching."""
        if not job_level and not job_years:
            return None

        resume_level = resume_level or "unknown"
        resume_level_num = self.experience_levels.get(resume_level.lower(), 2)

        job_level = job_level or "unknown"
        job_level_num = self.experience_levels.get(job_level.lower(), 2)

        # Calculate score
        if resume_level_num >= job_level_num:
            level_score = 1.0
            notes = "Experience level meets or exceeds requirement"
        elif resume_level_num == job_level_num - 1:
            level_score = 0.7
            notes = "Slightly below required level, may be acceptable"
        else:
            level_score = 0.4
            notes = "Below required experience level"

        # Factor in years if available
        if resume_years and job_years:
            if resume_years >= job_years:
                years_score = 1.0
            elif resume_years >= job_years * 0.7:
                years_score = 0.8
            else:
                years_score = 0.5
            match_score = (level_score + years_score) / 2
        else:
            match_score = level_score

        strength = self._score_to_strength(match_score)

        return ExperienceMatchExplanation(
            required_level=job_level,
            candidate_level=resume_level,
            years_required=job_years,
            years_candidate=resume_years,
            match_score=match_score,
            strength=strength,
            notes=notes,
        )

    def _explain_location(
        self,
        resume_location: Optional[str],
        job_location: Optional[str],
        is_remote: bool,
    ) -> Optional[LocationMatchExplanation]:
        """Explain location matching."""
        if not job_location:
            return None

        resume_location = resume_location or "Unknown"

        # Simple matching logic
        if is_remote:
            match_score = 1.0
            strength = MatchStrength.STRONG
        elif resume_location.lower() == job_location.lower():
            match_score = 1.0
            strength = MatchStrength.STRONG
        elif self._same_region(resume_location, job_location):
            match_score = 0.8
            strength = MatchStrength.MODERATE
        else:
            match_score = 0.3
            strength = MatchStrength.WEAK

        return LocationMatchExplanation(
            job_location=job_location,
            candidate_location=resume_location,
            is_remote=is_remote,
            distance_km=None,
            match_score=match_score,
            strength=strength,
        )

    def _same_region(self, loc1: str, loc2: str) -> bool:
        """Check if two locations are in the same region."""
        # Simple check - could be enhanced with geo data
        regions = {
            "bay area": ["san francisco", "oakland", "san jose", "palo alto"],
            "nyc": ["new york", "brooklyn", "manhattan"],
            "london": ["london", "city of london"],
        }

        loc1_lower = loc1.lower()
        loc2_lower = loc2.lower()

        for region, cities in regions.items():
            in_region_1 = any(c in loc1_lower for c in cities)
            in_region_2 = any(c in loc2_lower for c in cities)
            if in_region_1 and in_region_2:
                return True

        return False

    def _score_to_strength(self, score: float) -> MatchStrength:
        """Convert score to strength category."""
        if score >= 0.8:
            return MatchStrength.STRONG
        elif score >= 0.5:
            return MatchStrength.MODERATE
        elif score >= 0.2:
            return MatchStrength.WEAK
        else:
            return MatchStrength.MISSING

    def _generate_summary(
        self,
        skill_exp: SkillMatchExplanation,
        exp_exp: Optional[ExperienceMatchExplanation],
        loc_exp: Optional[LocationMatchExplanation],
        overall_score: float,
    ) -> Tuple[str, List[str], List[str]]:
        """Generate summary and highlights."""
        highlights = []
        concerns = []

        # Skill highlights
        if skill_exp.matched_skills:
            highlights.append(
                f"Matches {len(skill_exp.matched_skills)} required skills: "
                f"{', '.join(skill_exp.matched_skills[:3])}"
            )
        if skill_exp.bonus_skills:
            highlights.append(
                f"Brings additional skills: {', '.join(skill_exp.bonus_skills[:3])}"
            )

        # Skill concerns
        if skill_exp.missing_skills:
            concerns.append(
                f"Missing {len(skill_exp.missing_skills)} required skills: "
                f"{', '.join(skill_exp.missing_skills[:3])}"
            )

        # Experience
        if exp_exp:
            if exp_exp.strength == MatchStrength.STRONG:
                highlights.append(f"Experience level ({exp_exp.candidate_level}) meets requirements")
            elif exp_exp.strength in [MatchStrength.WEAK, MatchStrength.MISSING]:
                concerns.append(f"Experience level may be below requirement ({exp_exp.required_level})")

        # Location
        if loc_exp:
            if loc_exp.is_remote:
                highlights.append("Remote work available")
            elif loc_exp.strength == MatchStrength.STRONG:
                highlights.append(f"Location matches: {loc_exp.job_location}")
            elif loc_exp.strength == MatchStrength.WEAK:
                concerns.append(f"Location mismatch: job in {loc_exp.job_location}")

        # Generate summary
        if overall_score >= 0.8:
            summary = "Strong match with aligned skills and qualifications."
        elif overall_score >= 0.6:
            summary = "Good match with some areas for consideration."
        elif overall_score >= 0.4:
            summary = "Partial match - review specific requirements carefully."
        else:
            summary = "Limited match - significant gaps in requirements."

        return summary, highlights, concerns

    def explain_batch(
        self,
        resume_text: str,
        jobs: List[Dict[str, Any]],
        scores: List[float],
    ) -> List[MatchExplanation]:
        """
        Generate explanations for multiple jobs.

        Args:
            resume_text: Resume content
            jobs: List of job dictionaries
            scores: Match scores for each job

        Returns:
            List of MatchExplanation objects
        """
        explanations = []

        for job, score in zip(jobs, scores):
            exp = self.explain(
                resume_text=resume_text,
                job_text=job.get("description", ""),
                job_id=str(job.get("id", "")),
                job_title=job.get("title", ""),
                overall_score=score,
                job_metadata={
                    "experience_level": job.get("experience"),
                    "location": job.get("location"),
                    "is_remote": job.get("workplace_type", "").lower() == "remote",
                },
            )
            explanations.append(exp)

        return explanations

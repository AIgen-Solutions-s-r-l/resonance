"""
Skill Extraction from Text.

Extracts skills from resumes and job descriptions using
pattern matching, NER, and fuzzy matching against a taxonomy.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from app.log.logging import logger


class SkillCategory(Enum):
    """Categories of skills."""
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    DEVOPS = "devops"
    DATA_SCIENCE = "data_science"
    SOFT_SKILL = "soft_skill"
    METHODOLOGY = "methodology"
    TOOL = "tool"
    OTHER = "other"


@dataclass
class ExtractedSkill:
    """A skill extracted from text."""
    name: str
    canonical_name: str  # Normalized form
    category: SkillCategory
    confidence: float  # 0-1
    start_pos: int = -1
    end_pos: int = -1
    context: str = ""  # Surrounding text
    aliases: List[str] = field(default_factory=list)


class SkillExtractor:
    """
    Extracts skills from text using multiple strategies.

    Strategies:
    1. Pattern matching against known skill patterns
    2. Fuzzy matching against skill taxonomy
    3. Context-aware extraction for implicit skills
    """

    def __init__(self):
        """Initialize the skill extractor."""
        self._init_skill_patterns()
        self._init_skill_taxonomy()
        logger.info(
            "SkillExtractor initialized",
            patterns=len(self.skill_patterns),
            taxonomy_size=len(self.skill_taxonomy),
        )

    def _init_skill_patterns(self):
        """Initialize regex patterns for skill extraction."""
        # Programming languages
        self.programming_languages = {
            "python": ["python", "python3", "py"],
            "javascript": ["javascript", "js", "ecmascript"],
            "typescript": ["typescript", "ts"],
            "java": ["java"],
            "csharp": ["c#", "csharp", "c-sharp"],
            "cpp": ["c++", "cpp", "c plus plus"],
            "c": ["\\bc\\b"],
            "go": ["golang", "\\bgo\\b"],
            "rust": ["rust"],
            "ruby": ["ruby"],
            "php": ["php"],
            "swift": ["swift"],
            "kotlin": ["kotlin"],
            "scala": ["scala"],
            "r": ["\\br\\b", "r language"],
            "sql": ["sql", "tsql", "plsql", "pl/sql"],
        }

        # Frameworks and libraries
        self.frameworks = {
            "react": ["react", "reactjs", "react.js"],
            "angular": ["angular", "angularjs"],
            "vue": ["vue", "vuejs", "vue.js"],
            "django": ["django"],
            "flask": ["flask"],
            "fastapi": ["fastapi", "fast api"],
            "spring": ["spring", "spring boot", "springboot"],
            "express": ["express", "expressjs"],
            "nextjs": ["next.js", "nextjs", "next js"],
            "nodejs": ["node.js", "nodejs", "node js"],
            "rails": ["rails", "ruby on rails"],
            "laravel": ["laravel"],
            "dotnet": [".net", "dotnet", ".net core"],
            "tensorflow": ["tensorflow", "tf"],
            "pytorch": ["pytorch", "torch"],
            "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
            "pandas": ["pandas"],
            "numpy": ["numpy"],
            "keras": ["keras"],
        }

        # Databases
        self.databases = {
            "postgresql": ["postgresql", "postgres", "psql"],
            "mysql": ["mysql"],
            "mongodb": ["mongodb", "mongo"],
            "redis": ["redis"],
            "elasticsearch": ["elasticsearch", "elastic search", "es"],
            "cassandra": ["cassandra"],
            "dynamodb": ["dynamodb", "dynamo db"],
            "sqlite": ["sqlite"],
            "oracle": ["oracle", "oracle db"],
            "sqlserver": ["sql server", "mssql", "microsoft sql"],
        }

        # Cloud platforms
        self.cloud = {
            "aws": ["aws", "amazon web services"],
            "azure": ["azure", "microsoft azure"],
            "gcp": ["gcp", "google cloud", "google cloud platform"],
            "heroku": ["heroku"],
            "digitalocean": ["digitalocean", "digital ocean"],
            "vercel": ["vercel"],
            "netlify": ["netlify"],
        }

        # DevOps tools
        self.devops = {
            "docker": ["docker"],
            "kubernetes": ["kubernetes", "k8s"],
            "jenkins": ["jenkins"],
            "terraform": ["terraform"],
            "ansible": ["ansible"],
            "gitlab-ci": ["gitlab ci", "gitlab-ci"],
            "github-actions": ["github actions"],
            "circleci": ["circleci", "circle ci"],
            "prometheus": ["prometheus"],
            "grafana": ["grafana"],
            "nginx": ["nginx"],
        }

        # Data science
        self.data_science = {
            "machine-learning": ["machine learning", "ml"],
            "deep-learning": ["deep learning", "dl"],
            "nlp": ["nlp", "natural language processing"],
            "computer-vision": ["computer vision", "cv"],
            "data-analysis": ["data analysis", "data analytics"],
            "statistics": ["statistics", "statistical"],
            "spark": ["spark", "apache spark", "pyspark"],
            "hadoop": ["hadoop"],
            "airflow": ["airflow", "apache airflow"],
        }

        # Compile all patterns
        self.skill_patterns: Dict[str, Tuple[SkillCategory, List[re.Pattern]]] = {}

        for skill, aliases in self.programming_languages.items():
            patterns = [re.compile(rf'\b{a}\b', re.IGNORECASE) for a in aliases]
            self.skill_patterns[skill] = (SkillCategory.PROGRAMMING_LANGUAGE, patterns)

        for skill, aliases in self.frameworks.items():
            patterns = [re.compile(rf'\b{a}\b', re.IGNORECASE) for a in aliases]
            self.skill_patterns[skill] = (SkillCategory.FRAMEWORK, patterns)

        for skill, aliases in self.databases.items():
            patterns = [re.compile(rf'\b{a}\b', re.IGNORECASE) for a in aliases]
            self.skill_patterns[skill] = (SkillCategory.DATABASE, patterns)

        for skill, aliases in self.cloud.items():
            patterns = [re.compile(rf'\b{a}\b', re.IGNORECASE) for a in aliases]
            self.skill_patterns[skill] = (SkillCategory.CLOUD, patterns)

        for skill, aliases in self.devops.items():
            patterns = [re.compile(rf'\b{a}\b', re.IGNORECASE) for a in aliases]
            self.skill_patterns[skill] = (SkillCategory.DEVOPS, patterns)

        for skill, aliases in self.data_science.items():
            patterns = [re.compile(rf'\b{a}\b', re.IGNORECASE) for a in aliases]
            self.skill_patterns[skill] = (SkillCategory.DATA_SCIENCE, patterns)

    def _init_skill_taxonomy(self):
        """Initialize the skill taxonomy for fuzzy matching."""
        self.skill_taxonomy: Dict[str, SkillCategory] = {}

        # Add all known skills to taxonomy
        for skill in self.programming_languages:
            self.skill_taxonomy[skill] = SkillCategory.PROGRAMMING_LANGUAGE
        for skill in self.frameworks:
            self.skill_taxonomy[skill] = SkillCategory.FRAMEWORK
        for skill in self.databases:
            self.skill_taxonomy[skill] = SkillCategory.DATABASE
        for skill in self.cloud:
            self.skill_taxonomy[skill] = SkillCategory.CLOUD
        for skill in self.devops:
            self.skill_taxonomy[skill] = SkillCategory.DEVOPS
        for skill in self.data_science:
            self.skill_taxonomy[skill] = SkillCategory.DATA_SCIENCE

        # Soft skills
        soft_skills = [
            "communication", "leadership", "teamwork", "problem-solving",
            "critical-thinking", "time-management", "adaptability",
            "creativity", "collaboration", "presentation",
        ]
        for skill in soft_skills:
            self.skill_taxonomy[skill] = SkillCategory.SOFT_SKILL

        # Methodologies
        methodologies = [
            "agile", "scrum", "kanban", "waterfall", "devops",
            "ci-cd", "tdd", "bdd", "pair-programming",
        ]
        for skill in methodologies:
            self.skill_taxonomy[skill] = SkillCategory.METHODOLOGY

    def extract(self, text: str) -> List[ExtractedSkill]:
        """
        Extract skills from text.

        Args:
            text: Input text (resume or job description)

        Returns:
            List of extracted skills
        """
        if not text:
            return []

        extracted: Dict[str, ExtractedSkill] = {}

        # Pattern-based extraction
        for skill_name, (category, patterns) in self.skill_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    if skill_name not in extracted:
                        # Get context (50 chars before and after)
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end]

                        extracted[skill_name] = ExtractedSkill(
                            name=match.group(),
                            canonical_name=skill_name,
                            category=category,
                            confidence=0.95,  # High confidence for exact match
                            start_pos=match.start(),
                            end_pos=match.end(),
                            context=context,
                        )
                    else:
                        # Add alias
                        if match.group().lower() not in [a.lower() for a in extracted[skill_name].aliases]:
                            extracted[skill_name].aliases.append(match.group())

        # Look for skill list patterns
        skill_list_matches = self._extract_skill_lists(text)
        for skill in skill_list_matches:
            if skill.canonical_name not in extracted:
                extracted[skill.canonical_name] = skill

        return list(extracted.values())

    def _extract_skill_lists(self, text: str) -> List[ExtractedSkill]:
        """Extract skills from list patterns like 'Skills: X, Y, Z'."""
        skills = []

        # Pattern for skill sections
        section_patterns = [
            r'(?:skills?|technologies?|tech stack|requirements?)[:\s]+([^.]+?)(?:\.|$)',
            r'(?:proficient|experienced?|expertise|familiar) (?:in|with)[:\s]+([^.]+?)(?:\.|$)',
        ]

        for pattern in section_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                skill_text = match.group(1)
                # Split by common delimiters
                potential_skills = re.split(r'[,;/•·\n]|\band\b', skill_text)

                for potential in potential_skills:
                    potential = potential.strip().lower()
                    if len(potential) < 2 or len(potential) > 50:
                        continue

                    # Check if it's a known skill
                    for skill_name in self.skill_taxonomy:
                        if skill_name in potential or potential in skill_name:
                            skills.append(ExtractedSkill(
                                name=potential,
                                canonical_name=skill_name,
                                category=self.skill_taxonomy[skill_name],
                                confidence=0.8,
                                context=skill_text[:100],
                            ))
                            break

        return skills

    def extract_with_context(
        self,
        text: str,
        window_size: int = 100,
    ) -> List[Tuple[ExtractedSkill, str]]:
        """
        Extract skills with surrounding context.

        Args:
            text: Input text
            window_size: Size of context window

        Returns:
            List of (skill, context) tuples
        """
        skills = self.extract(text)
        result = []

        for skill in skills:
            if skill.start_pos >= 0:
                start = max(0, skill.start_pos - window_size)
                end = min(len(text), skill.end_pos + window_size)
                context = text[start:end]
            else:
                context = skill.context or ""

            result.append((skill, context))

        return result

    def get_skill_vector(
        self,
        skills: List[ExtractedSkill],
    ) -> Dict[str, float]:
        """
        Create a skill vector representation.

        Args:
            skills: List of extracted skills

        Returns:
            Dictionary mapping canonical skill names to confidence scores
        """
        vector = {}
        for skill in skills:
            if skill.canonical_name in vector:
                # Take max confidence
                vector[skill.canonical_name] = max(
                    vector[skill.canonical_name],
                    skill.confidence,
                )
            else:
                vector[skill.canonical_name] = skill.confidence
        return vector

    def compute_skill_overlap(
        self,
        skills1: List[ExtractedSkill],
        skills2: List[ExtractedSkill],
    ) -> Dict[str, any]:
        """
        Compute overlap between two skill sets.

        Args:
            skills1: First skill set
            skills2: Second skill set

        Returns:
            Dictionary with overlap statistics
        """
        set1 = {s.canonical_name for s in skills1}
        set2 = {s.canonical_name for s in skills2}

        intersection = set1 & set2
        union = set1 | set2

        return {
            "matched": list(intersection),
            "only_in_first": list(set1 - set2),
            "only_in_second": list(set2 - set1),
            "jaccard_similarity": len(intersection) / len(union) if union else 0,
            "recall": len(intersection) / len(set2) if set2 else 0,
            "precision": len(intersection) / len(set1) if set1 else 0,
        }

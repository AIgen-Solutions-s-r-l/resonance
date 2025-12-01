"""
Skill Taxonomy for Knowledge Graph.

Defines the structure and relationships between skills
for graph-based matching.
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from app.log.logging import logger
from app.ml.knowledge_graph.skill_extractor import SkillCategory


class RelationType(Enum):
    """Types of relationships between skills."""
    RELATED_TO = "related_to"      # General relation
    REQUIRES = "requires"          # Skill A requires skill B
    PART_OF = "part_of"            # Skill A is part of skill B
    ALTERNATIVE_TO = "alternative" # Skill A is alternative to B
    SPECIALIZATION_OF = "specialization"  # A is a specialization of B
    USED_WITH = "used_with"        # Commonly used together


@dataclass
class Skill:
    """A skill in the taxonomy."""
    id: str
    name: str
    canonical_name: str
    category: SkillCategory
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    popularity: float = 0.0  # 0-1, based on job posting frequency
    embedding: Optional[List[float]] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "canonical_name": self.canonical_name,
            "category": self.category.value,
            "aliases": self.aliases,
            "description": self.description,
            "popularity": self.popularity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        return cls(
            id=data["id"],
            name=data["name"],
            canonical_name=data["canonical_name"],
            category=SkillCategory(data["category"]),
            aliases=data.get("aliases", []),
            description=data.get("description", ""),
            popularity=data.get("popularity", 0.0),
        )


@dataclass
class SkillRelation:
    """A relation between two skills."""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0  # Strength of relation
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillRelation":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data["relation_type"]),
            weight=data.get("weight", 1.0),
            metadata=data.get("metadata", {}),
        )


class SkillTaxonomy:
    """
    Skill taxonomy with hierarchical relationships.

    Provides:
    - Skill lookup by name/alias
    - Relationship traversal
    - Skill similarity based on graph distance
    """

    def __init__(self):
        """Initialize the taxonomy."""
        self.skills: Dict[str, Skill] = {}
        self.relations: List[SkillRelation] = []

        # Indexes for fast lookup
        self._name_to_id: Dict[str, str] = {}
        self._alias_to_id: Dict[str, str] = {}
        self._category_index: Dict[SkillCategory, Set[str]] = {}
        self._adjacency: Dict[str, List[Tuple[str, RelationType, float]]] = {}

        self._build_default_taxonomy()

    def _build_default_taxonomy(self):
        """Build the default skill taxonomy."""
        # Programming languages
        self._add_skill_group(
            SkillCategory.PROGRAMMING_LANGUAGE,
            [
                ("python", "Python", ["py", "python3"]),
                ("javascript", "JavaScript", ["js", "ecmascript"]),
                ("typescript", "TypeScript", ["ts"]),
                ("java", "Java", []),
                ("csharp", "C#", ["c-sharp"]),
                ("cpp", "C++", ["cplusplus"]),
                ("go", "Go", ["golang"]),
                ("rust", "Rust", []),
                ("ruby", "Ruby", []),
                ("php", "PHP", []),
                ("swift", "Swift", []),
                ("kotlin", "Kotlin", []),
                ("scala", "Scala", []),
                ("sql", "SQL", ["tsql", "plsql"]),
            ]
        )

        # Frameworks
        self._add_skill_group(
            SkillCategory.FRAMEWORK,
            [
                ("react", "React", ["reactjs"]),
                ("angular", "Angular", ["angularjs"]),
                ("vue", "Vue.js", ["vuejs"]),
                ("django", "Django", []),
                ("flask", "Flask", []),
                ("fastapi", "FastAPI", []),
                ("spring", "Spring", ["spring-boot"]),
                ("express", "Express.js", ["expressjs"]),
                ("nextjs", "Next.js", []),
                ("nodejs", "Node.js", []),
                ("rails", "Ruby on Rails", ["ror"]),
                ("laravel", "Laravel", []),
                ("dotnet", ".NET", ["dotnet-core"]),
                ("tensorflow", "TensorFlow", ["tf"]),
                ("pytorch", "PyTorch", ["torch"]),
                ("scikit-learn", "Scikit-learn", ["sklearn"]),
            ]
        )

        # Databases
        self._add_skill_group(
            SkillCategory.DATABASE,
            [
                ("postgresql", "PostgreSQL", ["postgres"]),
                ("mysql", "MySQL", []),
                ("mongodb", "MongoDB", ["mongo"]),
                ("redis", "Redis", []),
                ("elasticsearch", "Elasticsearch", ["es"]),
                ("cassandra", "Cassandra", []),
                ("dynamodb", "DynamoDB", []),
            ]
        )

        # Cloud
        self._add_skill_group(
            SkillCategory.CLOUD,
            [
                ("aws", "AWS", ["amazon-web-services"]),
                ("azure", "Azure", ["microsoft-azure"]),
                ("gcp", "Google Cloud", ["google-cloud-platform"]),
            ]
        )

        # DevOps
        self._add_skill_group(
            SkillCategory.DEVOPS,
            [
                ("docker", "Docker", []),
                ("kubernetes", "Kubernetes", ["k8s"]),
                ("terraform", "Terraform", []),
                ("ansible", "Ansible", []),
                ("jenkins", "Jenkins", []),
                ("github-actions", "GitHub Actions", []),
                ("gitlab-ci", "GitLab CI", []),
            ]
        )

        # Data Science
        self._add_skill_group(
            SkillCategory.DATA_SCIENCE,
            [
                ("machine-learning", "Machine Learning", ["ml"]),
                ("deep-learning", "Deep Learning", ["dl"]),
                ("nlp", "NLP", ["natural-language-processing"]),
                ("computer-vision", "Computer Vision", ["cv"]),
                ("data-analysis", "Data Analysis", []),
                ("spark", "Apache Spark", ["pyspark"]),
            ]
        )

        # Build default relations
        self._build_default_relations()

        logger.info(
            "Taxonomy built",
            skills=len(self.skills),
            relations=len(self.relations),
        )

    def _add_skill_group(
        self,
        category: SkillCategory,
        skills: List[Tuple[str, str, List[str]]],
    ):
        """Add a group of skills."""
        for skill_id, name, aliases in skills:
            skill = Skill(
                id=skill_id,
                name=name,
                canonical_name=skill_id,
                category=category,
                aliases=aliases,
            )
            self.add_skill(skill)

    def _build_default_relations(self):
        """Build default skill relations."""
        # Language -> Framework relations
        lang_framework = [
            ("python", ["django", "flask", "fastapi", "tensorflow", "pytorch", "scikit-learn"]),
            ("javascript", ["react", "angular", "vue", "express", "nodejs", "nextjs"]),
            ("typescript", ["react", "angular", "nextjs", "nodejs"]),
            ("java", ["spring"]),
            ("ruby", ["rails"]),
            ("php", ["laravel"]),
            ("csharp", ["dotnet"]),
        ]

        for lang, frameworks in lang_framework:
            for fw in frameworks:
                if lang in self.skills and fw in self.skills:
                    self.add_relation(SkillRelation(
                        source_id=fw,
                        target_id=lang,
                        relation_type=RelationType.REQUIRES,
                        weight=0.9,
                    ))

        # Related frameworks
        related_frameworks = [
            (["react", "angular", "vue"], RelationType.ALTERNATIVE_TO, 0.7),
            (["django", "flask", "fastapi"], RelationType.ALTERNATIVE_TO, 0.7),
            (["tensorflow", "pytorch"], RelationType.ALTERNATIVE_TO, 0.8),
            (["postgresql", "mysql"], RelationType.ALTERNATIVE_TO, 0.6),
            (["aws", "azure", "gcp"], RelationType.ALTERNATIVE_TO, 0.5),
            (["docker", "kubernetes"], RelationType.USED_WITH, 0.9),
        ]

        for skills, rel_type, weight in related_frameworks:
            for i, s1 in enumerate(skills):
                for s2 in skills[i+1:]:
                    if s1 in self.skills and s2 in self.skills:
                        self.add_relation(SkillRelation(
                            source_id=s1,
                            target_id=s2,
                            relation_type=rel_type,
                            weight=weight,
                        ))

        # Category relations
        ds_requires = [
            ("machine-learning", "python"),
            ("deep-learning", "python"),
            ("nlp", "machine-learning"),
            ("computer-vision", "deep-learning"),
        ]

        for source, target in ds_requires:
            if source in self.skills and target in self.skills:
                self.add_relation(SkillRelation(
                    source_id=source,
                    target_id=target,
                    relation_type=RelationType.REQUIRES,
                    weight=0.8,
                ))

    def add_skill(self, skill: Skill) -> None:
        """Add a skill to the taxonomy."""
        self.skills[skill.id] = skill
        self._name_to_id[skill.name.lower()] = skill.id
        self._name_to_id[skill.canonical_name.lower()] = skill.id

        for alias in skill.aliases:
            self._alias_to_id[alias.lower()] = skill.id

        if skill.category not in self._category_index:
            self._category_index[skill.category] = set()
        self._category_index[skill.category].add(skill.id)

    def add_relation(self, relation: SkillRelation) -> None:
        """Add a relation between skills."""
        self.relations.append(relation)

        # Update adjacency list
        if relation.source_id not in self._adjacency:
            self._adjacency[relation.source_id] = []
        self._adjacency[relation.source_id].append(
            (relation.target_id, relation.relation_type, relation.weight)
        )

        # Add reverse for bidirectional relations
        if relation.relation_type in [RelationType.RELATED_TO, RelationType.ALTERNATIVE_TO, RelationType.USED_WITH]:
            if relation.target_id not in self._adjacency:
                self._adjacency[relation.target_id] = []
            self._adjacency[relation.target_id].append(
                (relation.source_id, relation.relation_type, relation.weight)
            )

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name or alias."""
        name_lower = name.lower()

        # Try direct ID lookup
        if name_lower in self.skills:
            return self.skills[name_lower]

        # Try name lookup
        if name_lower in self._name_to_id:
            return self.skills[self._name_to_id[name_lower]]

        # Try alias lookup
        if name_lower in self._alias_to_id:
            return self.skills[self._alias_to_id[name_lower]]

        return None

    def get_related_skills(
        self,
        skill_id: str,
        relation_types: Optional[List[RelationType]] = None,
        max_depth: int = 1,
    ) -> List[Tuple[Skill, float]]:
        """
        Get skills related to the given skill.

        Args:
            skill_id: ID of the skill
            relation_types: Types of relations to follow (None = all)
            max_depth: Maximum traversal depth

        Returns:
            List of (skill, weight) tuples
        """
        if skill_id not in self.skills:
            return []

        visited: Set[str] = {skill_id}
        result: Dict[str, float] = {}

        def traverse(current_id: str, depth: int, cumulative_weight: float):
            if depth > max_depth:
                return

            neighbors = self._adjacency.get(current_id, [])
            for neighbor_id, rel_type, weight in neighbors:
                if relation_types and rel_type not in relation_types:
                    continue

                new_weight = cumulative_weight * weight

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    if neighbor_id in result:
                        result[neighbor_id] = max(result[neighbor_id], new_weight)
                    else:
                        result[neighbor_id] = new_weight
                    traverse(neighbor_id, depth + 1, new_weight)

        traverse(skill_id, 0, 1.0)

        return [
            (self.skills[sid], weight)
            for sid, weight in sorted(result.items(), key=lambda x: -x[1])
        ]

    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get all skills in a category."""
        skill_ids = self._category_index.get(category, set())
        return [self.skills[sid] for sid in skill_ids]

    def compute_skill_similarity(
        self,
        skill1_id: str,
        skill2_id: str,
    ) -> float:
        """
        Compute similarity between two skills based on graph distance.

        Args:
            skill1_id: First skill ID
            skill2_id: Second skill ID

        Returns:
            Similarity score (0-1)
        """
        if skill1_id == skill2_id:
            return 1.0

        if skill1_id not in self.skills or skill2_id not in self.skills:
            return 0.0

        # Check direct connection
        for neighbor_id, _, weight in self._adjacency.get(skill1_id, []):
            if neighbor_id == skill2_id:
                return weight

        # Check 2-hop connection
        for neighbor_id, _, weight1 in self._adjacency.get(skill1_id, []):
            for n2_id, _, weight2 in self._adjacency.get(neighbor_id, []):
                if n2_id == skill2_id:
                    return weight1 * weight2 * 0.5  # Discount for 2-hop

        # Same category gives some similarity
        skill1 = self.skills[skill1_id]
        skill2 = self.skills[skill2_id]
        if skill1.category == skill2.category:
            return 0.3

        return 0.0

    def save(self, path: Path) -> None:
        """Save taxonomy to disk."""
        data = {
            "skills": [s.to_dict() for s in self.skills.values()],
            "relations": [r.to_dict() for r in self.relations],
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Taxonomy saved to {path}")

    @classmethod
    def load(cls, path: Path) -> "SkillTaxonomy":
        """Load taxonomy from disk."""
        with open(path, "r") as f:
            data = json.load(f)

        taxonomy = cls.__new__(cls)
        taxonomy.skills = {}
        taxonomy.relations = []
        taxonomy._name_to_id = {}
        taxonomy._alias_to_id = {}
        taxonomy._category_index = {}
        taxonomy._adjacency = {}

        for skill_data in data["skills"]:
            skill = Skill.from_dict(skill_data)
            taxonomy.add_skill(skill)

        for rel_data in data["relations"]:
            relation = SkillRelation.from_dict(rel_data)
            taxonomy.add_relation(relation)

        logger.info(f"Taxonomy loaded from {path}")
        return taxonomy

    def __len__(self) -> int:
        return len(self.skills)

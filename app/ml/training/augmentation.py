"""
Data Augmentation for Contrastive Learning.

Implements various text augmentation strategies to increase
training data diversity and improve model robustness.
"""

import random
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

from app.log.logging import logger
from app.ml.config import ml_config


@dataclass
class AugmentationConfig:
    """Configuration for data augmentation."""
    # EDA (Easy Data Augmentation) parameters
    synonym_replace_prob: float = 0.1
    random_insert_prob: float = 0.1
    random_swap_prob: float = 0.1
    random_delete_prob: float = 0.1

    # Skill-specific augmentation
    skill_mask_prob: float = 0.15
    skill_shuffle_prob: float = 0.1

    # Section-level augmentation
    section_drop_prob: float = 0.1

    # General
    min_words: int = 5  # Minimum words to apply augmentation


class EasyDataAugmentation:
    """
    Easy Data Augmentation (EDA) techniques.

    Reference: https://arxiv.org/abs/1901.11196
    """

    def __init__(self, config: AugmentationConfig = None):
        """Initialize EDA augmenter."""
        self.config = config or AugmentationConfig()

        # Simple synonym dictionary for common job-related terms
        self.synonyms = {
            "develop": ["build", "create", "design", "implement"],
            "manage": ["lead", "oversee", "direct", "coordinate"],
            "experience": ["expertise", "background", "knowledge", "proficiency"],
            "skills": ["abilities", "competencies", "capabilities"],
            "team": ["group", "department", "unit"],
            "project": ["initiative", "program", "assignment"],
            "software": ["application", "system", "program"],
            "responsible": ["accountable", "in charge of", "tasked with"],
            "working": ["collaborating", "operating", "functioning"],
            "excellent": ["outstanding", "exceptional", "superior"],
            "strong": ["solid", "robust", "powerful"],
            "required": ["needed", "necessary", "essential"],
            "preferred": ["desired", "ideal", "advantageous"],
        }

        # Filler words for random insertion
        self.filler_words = [
            "and", "also", "with", "including", "such as",
            "for", "in", "on", "the", "a",
        ]

    def synonym_replacement(self, text: str, n: int = None) -> str:
        """
        Replace n random words with synonyms.

        Args:
            text: Input text
            n: Number of words to replace (default: based on text length)

        Returns:
            Augmented text
        """
        words = text.split()
        if len(words) < self.config.min_words:
            return text

        n = n or max(1, int(len(words) * self.config.synonym_replace_prob))

        # Find replaceable words
        replaceable = [
            (i, w.lower()) for i, w in enumerate(words)
            if w.lower() in self.synonyms
        ]

        if not replaceable:
            return text

        # Random selection
        to_replace = random.sample(replaceable, min(n, len(replaceable)))

        for idx, word in to_replace:
            synonym = random.choice(self.synonyms[word])
            # Preserve capitalization
            if words[idx][0].isupper():
                synonym = synonym.capitalize()
            words[idx] = synonym

        return " ".join(words)

    def random_insertion(self, text: str, n: int = None) -> str:
        """
        Insert n random words at random positions.

        Args:
            text: Input text
            n: Number of insertions

        Returns:
            Augmented text
        """
        words = text.split()
        if len(words) < self.config.min_words:
            return text

        n = n or max(1, int(len(words) * self.config.random_insert_prob))

        for _ in range(n):
            word = random.choice(self.filler_words)
            pos = random.randint(0, len(words))
            words.insert(pos, word)

        return " ".join(words)

    def random_swap(self, text: str, n: int = None) -> str:
        """
        Swap n pairs of adjacent words.

        Args:
            text: Input text
            n: Number of swaps

        Returns:
            Augmented text
        """
        words = text.split()
        if len(words) < self.config.min_words:
            return text

        n = n or max(1, int(len(words) * self.config.random_swap_prob))

        for _ in range(n):
            if len(words) < 2:
                break
            idx = random.randint(0, len(words) - 2)
            words[idx], words[idx + 1] = words[idx + 1], words[idx]

        return " ".join(words)

    def random_deletion(self, text: str, p: float = None) -> str:
        """
        Delete words with probability p.

        Args:
            text: Input text
            p: Deletion probability per word

        Returns:
            Augmented text
        """
        words = text.split()
        if len(words) < self.config.min_words:
            return text

        p = p or self.config.random_delete_prob

        # Keep at least min_words
        remaining = [w for w in words if random.random() > p]

        if len(remaining) < self.config.min_words:
            remaining = random.sample(words, self.config.min_words)

        return " ".join(remaining)

    def augment(self, text: str, num_augmentations: int = 1) -> List[str]:
        """
        Apply random EDA augmentations.

        Args:
            text: Input text
            num_augmentations: Number of augmented versions to generate

        Returns:
            List of augmented texts
        """
        augmented = []

        for _ in range(num_augmentations):
            aug_text = text

            # Apply random augmentations
            if random.random() < 0.25:
                aug_text = self.synonym_replacement(aug_text)
            if random.random() < 0.25:
                aug_text = self.random_insertion(aug_text)
            if random.random() < 0.25:
                aug_text = self.random_swap(aug_text)
            if random.random() < 0.25:
                aug_text = self.random_deletion(aug_text)

            augmented.append(aug_text)

        return augmented


class SkillAugmentation:
    """
    Skill-specific augmentation for resumes and job descriptions.

    Focuses on augmenting skill mentions while preserving meaning.
    """

    def __init__(self, config: AugmentationConfig = None):
        """Initialize skill augmenter."""
        self.config = config or AugmentationConfig()

        # Common skills patterns
        self.skill_patterns = [
            r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|PHP)\b',
            r'\b(React|Angular|Vue|Django|Flask|FastAPI|Spring|Node\.js)\b',
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|Terraform)\b',
            r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch)\b',
            r'\b(Machine Learning|Deep Learning|NLP|Computer Vision)\b',
            r'\b(TensorFlow|PyTorch|Scikit-learn|Keras)\b',
            r'\b(Git|CI/CD|Agile|Scrum)\b',
        ]

        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.skill_patterns
        ]

    def extract_skills(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Extract skills from text with their positions.

        Returns:
            List of (start, end, skill) tuples
        """
        skills = []

        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                skills.append((match.start(), match.end(), match.group()))

        return sorted(skills, key=lambda x: x[0])

    def mask_skills(self, text: str, mask_token: str = "[SKILL]") -> str:
        """
        Randomly mask skills in text.

        Args:
            text: Input text
            mask_token: Token to replace skills with

        Returns:
            Text with some skills masked
        """
        skills = self.extract_skills(text)
        if not skills:
            return text

        # Select skills to mask
        num_to_mask = max(1, int(len(skills) * self.config.skill_mask_prob))
        to_mask = random.sample(skills, min(num_to_mask, len(skills)))
        to_mask = sorted(to_mask, key=lambda x: x[0], reverse=True)

        # Replace from end to preserve indices
        result = text
        for start, end, _ in to_mask:
            result = result[:start] + mask_token + result[end:]

        return result

    def shuffle_skills(self, text: str) -> str:
        """
        Shuffle the order of skills in lists.

        Args:
            text: Input text

        Returns:
            Text with skills shuffled
        """
        # Find skill lists (comma-separated)
        list_pattern = r'(?:skills?|technologies?|experience with)[:\s]+([^.]+)'
        match = re.search(list_pattern, text, re.IGNORECASE)

        if not match:
            return text

        skill_list = match.group(1)
        skills = [s.strip() for s in skill_list.split(",")]

        if len(skills) < 2:
            return text

        random.shuffle(skills)
        shuffled_list = ", ".join(skills)

        return text[:match.start(1)] + shuffled_list + text[match.end(1):]

    def augment(self, text: str) -> str:
        """
        Apply skill-specific augmentation.

        Args:
            text: Input text

        Returns:
            Augmented text
        """
        if random.random() < self.config.skill_mask_prob:
            text = self.mask_skills(text)

        if random.random() < self.config.skill_shuffle_prob:
            text = self.shuffle_skills(text)

        return text


class SectionAugmentation:
    """
    Section-level augmentation for structured documents.

    Drops or reorders sections to improve robustness.
    """

    def __init__(self, config: AugmentationConfig = None):
        """Initialize section augmenter."""
        self.config = config or AugmentationConfig()

        # Common section headers
        self.section_patterns = [
            r'^(?:experience|work experience|employment)\s*:?\s*$',
            r'^(?:education|academic background)\s*:?\s*$',
            r'^(?:skills|technical skills|core competencies)\s*:?\s*$',
            r'^(?:projects|personal projects)\s*:?\s*$',
            r'^(?:certifications?|certificates?)\s*:?\s*$',
            r'^(?:summary|objective|profile)\s*:?\s*$',
        ]

    def drop_section(self, text: str) -> str:
        """
        Randomly drop a section from the text.

        Args:
            text: Input text with sections

        Returns:
            Text with one section potentially dropped
        """
        if random.random() > self.config.section_drop_prob:
            return text

        lines = text.split('\n')
        sections = []
        current_section_start = 0

        for i, line in enumerate(lines):
            for pattern in self.section_patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    if current_section_start < i:
                        sections.append((current_section_start, i))
                    current_section_start = i
                    break

        if current_section_start < len(lines):
            sections.append((current_section_start, len(lines)))

        if len(sections) <= 1:
            return text

        # Drop a random section (not the first one usually)
        if len(sections) > 2:
            drop_idx = random.randint(1, len(sections) - 1)
        else:
            drop_idx = random.randint(0, len(sections) - 1)

        start, end = sections[drop_idx]
        remaining_lines = lines[:start] + lines[end:]

        return '\n'.join(remaining_lines)


class TextAugmenter:
    """
    Combined text augmenter for contrastive learning.

    Applies multiple augmentation strategies based on configuration.
    """

    def __init__(self, config: AugmentationConfig = None):
        """Initialize the combined augmenter."""
        self.config = config or AugmentationConfig()
        self.eda = EasyDataAugmentation(self.config)
        self.skill_aug = SkillAugmentation(self.config)
        self.section_aug = SectionAugmentation(self.config)

    def augment(
        self,
        text: str,
        apply_eda: bool = True,
        apply_skill: bool = True,
        apply_section: bool = True,
    ) -> str:
        """
        Apply augmentations to text.

        Args:
            text: Input text
            apply_eda: Whether to apply EDA augmentations
            apply_skill: Whether to apply skill augmentations
            apply_section: Whether to apply section augmentations

        Returns:
            Augmented text
        """
        result = text

        if apply_section:
            result = self.section_aug.drop_section(result)

        if apply_skill:
            result = self.skill_aug.augment(result)

        if apply_eda:
            # Apply single EDA augmentation
            augmented = self.eda.augment(result, num_augmentations=1)
            result = augmented[0] if augmented else result

        return result

    def augment_batch(
        self,
        texts: List[str],
        augmentation_prob: float = None,
    ) -> List[str]:
        """
        Augment a batch of texts with probability.

        Args:
            texts: List of texts
            augmentation_prob: Probability of augmenting each text

        Returns:
            List of (possibly augmented) texts
        """
        prob = augmentation_prob or ml_config.augmentation_eda_prob

        return [
            self.augment(text) if random.random() < prob else text
            for text in texts
        ]

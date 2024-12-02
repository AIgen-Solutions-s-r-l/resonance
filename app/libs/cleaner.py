import spacy
from spacy.language import Language
from typing import Optional, Set, Dict, Any
import logging
from pathlib import Path

class Cleaner:
    """
    A text cleaning class using SpaCy's NLP pipeline for preprocessing text data.
    
    This class provides functionality to clean and normalize text by:
    - Removing stop words
    - Converting text to lowercase
    - Removing special characters and unnecessary punctuation
    - Lemmatizing tokens
    - Optionally removing named entities
    
    Attributes:
        nlp (Language): SpaCy language model
        config (Dict[str, Any]): Configuration settings for text cleaning
        logger (logging.Logger): Logger instance for the class
    """
    
    def __init__(
        self,
        model_name: str = "en_core_web_lg",
        remove_stopwords: bool = True,
        remove_punctuation: bool = True,
        remove_numbers: bool = True,
        remove_entities: bool = False,
        custom_stopwords: Optional[Set[str]] = None,
        lowercase: bool = True
    ):
        """
        Initialize the Cleaner with specified configuration.
        
        Args:
            model_name (str): Name of the SpaCy model to use
            remove_stopwords (bool): Whether to remove stop words
            remove_punctuation (bool): Whether to remove punctuation
            remove_numbers (bool): Whether to remove numeric tokens
            remove_entities (bool): Whether to remove named entities
            custom_stopwords (Set[str], optional): Additional stop words to remove
            lowercase (bool): Whether to convert text to lowercase
            
        Raises:
            OSError: If the specified SpaCy model is not found
            ImportError: If SpaCy or required components are not installed
        """
        self.logger = logging.getLogger(__name__)
        
        try:
            self.nlp = spacy.load(model_name)
            self.logger.info(f"Loaded SpaCy model: {model_name}")
        except OSError:
            self.logger.error(f"SpaCy model '{model_name}' not found. Please install it using: python -m spacy download {model_name}")
            raise
        
        self.config = {
            "remove_stopwords": remove_stopwords,
            "remove_punctuation": remove_punctuation,
            "remove_numbers": remove_numbers,
            "remove_entities": remove_entities,
            "lowercase": lowercase
        }
        
        # Update stop words with custom ones if provided
        if custom_stopwords:
            self.nlp.Defaults.stop_words.update(custom_stopwords)
            self.logger.info(f"Added {len(custom_stopwords)} custom stop words")
    
    def clean(self, text: str) -> str:
        """
        Clean and normalize the input text based on the configuration.
        
        Args:
            text (str): Input text to clean
            
        Returns:
            str: Cleaned and normalized text
            
        Raises:
            ValueError: If input text is empty or not a string
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Input text must be a non-empty string")
        
        doc = self.nlp(text)
        
        tokens = []
        
        entities = set() if self.config["remove_entities"] else set()
        if self.config["remove_entities"]:
            entities.update((ent.start, ent.end) for ent in doc.ents)
        
        for i, token in enumerate(doc):
            if self.config["remove_entities"] and any(start <= i < end for start, end in entities):
                continue
                
            if (
                (not self.config["remove_stopwords"] or not token.is_stop) and
                (not self.config["remove_punctuation"] or not token.is_punct) and
                (not self.config["remove_numbers"] or not token.like_num)
            ):
                text = token.lemma_
                
                if self.config["lowercase"]:
                    text = text.lower()
                
                tokens.append(text)
        
        cleaned_text = " ".join(tokens).strip()
        self.logger.debug(f"Cleaned text length: {len(cleaned_text)} characters")
        
        return cleaned_text
    
    def update_config(self, **kwargs) -> None:
        """
        Update the configuration settings.
        
        Args:
            **kwargs: Configuration key-value pairs to update
        """
        valid_keys = self.config.keys()
        for key, value in kwargs.items():
            if key in valid_keys:
                self.config[key] = value
                self.logger.info(f"Updated config: {key} = {value}")
            else:
                self.logger.warning(f"Ignored invalid config key: {key}")


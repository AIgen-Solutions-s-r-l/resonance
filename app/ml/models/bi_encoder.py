"""
Bi-Encoder for Contrastive Learning.

A bi-encoder architecture that separately encodes resumes and jobs
into a shared embedding space for efficient similarity search.
"""

from typing import Optional, List, Dict, Any, Literal, Union
from dataclasses import dataclass
import torch
import torch.nn as nn
import torch.nn.functional as F

from app.log.logging import logger
from app.ml.config import ml_config

# Check if transformers is available
try:
    from transformers import AutoModel, AutoTokenizer, AutoConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers library not available. BiEncoder will not work.")


@dataclass
class EncoderOutput:
    """Output from the bi-encoder."""
    embeddings: torch.Tensor  # [batch_size, embedding_dim]
    attention_mask: Optional[torch.Tensor] = None
    pooler_output: Optional[torch.Tensor] = None


class BiEncoder(nn.Module):
    """
    Bi-Encoder for contrastive learning.

    Uses a shared transformer backbone to encode both resumes and jobs
    into a common embedding space. Supports multiple pooling strategies.
    """

    def __init__(
        self,
        model_name: str = None,
        embedding_dim: int = None,
        max_seq_length: int = None,
        pooling_strategy: Literal["mean", "cls", "max"] = None,
        normalize_embeddings: bool = True,
        freeze_backbone: bool = False,
    ):
        """
        Initialize the bi-encoder.

        Args:
            model_name: HuggingFace model name or path
            embedding_dim: Output embedding dimension
            max_seq_length: Maximum sequence length for tokenization
            pooling_strategy: How to pool token embeddings ("mean", "cls", "max")
            normalize_embeddings: Whether to L2-normalize output embeddings
            freeze_backbone: Whether to freeze the backbone weights
        """
        super().__init__()

        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers library required. Install with: pip install transformers"
            )

        self.model_name = model_name or ml_config.base_model_name
        self.embedding_dim = embedding_dim or ml_config.embedding_dim
        self.max_seq_length = max_seq_length or ml_config.max_seq_length
        self.pooling_strategy = pooling_strategy or ml_config.pooling_strategy
        self.normalize_embeddings = normalize_embeddings

        # Load tokenizer and model
        logger.info(f"Loading bi-encoder from {self.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.config = AutoConfig.from_pretrained(self.model_name)
        self.backbone = AutoModel.from_pretrained(self.model_name)

        # Get hidden size from config
        self.hidden_size = self.config.hidden_size

        # Projection layer if embedding_dim differs from hidden_size
        if self.embedding_dim != self.hidden_size:
            self.projection = nn.Linear(self.hidden_size, self.embedding_dim)
            logger.info(
                f"Added projection layer: {self.hidden_size} -> {self.embedding_dim}"
            )
        else:
            self.projection = None

        # Freeze backbone if requested
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False
            logger.info("Backbone weights frozen")

        logger.info(
            f"BiEncoder initialized: {self.model_name}, "
            f"embedding_dim={self.embedding_dim}, "
            f"pooling={self.pooling_strategy}"
        )

    def _pool(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Pool token embeddings into sentence embedding.

        Args:
            hidden_states: [batch_size, seq_len, hidden_size]
            attention_mask: [batch_size, seq_len]

        Returns:
            Pooled embeddings [batch_size, hidden_size]
        """
        if self.pooling_strategy == "cls":
            # Use [CLS] token embedding
            return hidden_states[:, 0]

        elif self.pooling_strategy == "max":
            # Max pooling over non-padding tokens
            attention_mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size())
            hidden_states[attention_mask_expanded == 0] = -1e9
            return torch.max(hidden_states, dim=1)[0]

        else:  # mean pooling (default)
            # Mean pooling over non-padding tokens
            attention_mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
            sum_embeddings = torch.sum(hidden_states * attention_mask_expanded, dim=1)
            sum_mask = torch.clamp(attention_mask_expanded.sum(dim=1), min=1e-9)
            return sum_embeddings / sum_mask

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        device: Optional[torch.device] = None,
    ) -> torch.Tensor:
        """
        Encode texts into embeddings.

        Args:
            texts: Single text or list of texts
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
            device: Device to use for encoding

        Returns:
            Embeddings tensor [num_texts, embedding_dim]
        """
        if isinstance(texts, str):
            texts = [texts]

        device = device or next(self.parameters()).device
        self.eval()

        all_embeddings = []

        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]

                # Tokenize
                encoded = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.max_seq_length,
                    return_tensors="pt",
                )

                # Move to device
                encoded = {k: v.to(device) for k, v in encoded.items()}

                # Forward pass
                outputs = self.backbone(**encoded)
                hidden_states = outputs.last_hidden_state

                # Pool
                pooled = self._pool(hidden_states, encoded["attention_mask"])

                # Project if needed
                if self.projection is not None:
                    pooled = self.projection(pooled)

                # Normalize if requested
                if self.normalize_embeddings:
                    pooled = F.normalize(pooled, p=2, dim=1)

                all_embeddings.append(pooled.cpu())

        return torch.cat(all_embeddings, dim=0)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: Optional[torch.Tensor] = None,
    ) -> EncoderOutput:
        """
        Forward pass for training.

        Args:
            input_ids: Token IDs [batch_size, seq_len]
            attention_mask: Attention mask [batch_size, seq_len]
            token_type_ids: Token type IDs (optional)

        Returns:
            EncoderOutput with embeddings
        """
        # Build inputs
        inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
        if token_type_ids is not None:
            inputs["token_type_ids"] = token_type_ids

        # Forward through backbone
        outputs = self.backbone(**inputs)
        hidden_states = outputs.last_hidden_state

        # Pool
        pooled = self._pool(hidden_states, attention_mask)

        # Project if needed
        if self.projection is not None:
            pooled = self.projection(pooled)

        # Normalize if requested
        if self.normalize_embeddings:
            pooled = F.normalize(pooled, p=2, dim=1)

        return EncoderOutput(
            embeddings=pooled,
            attention_mask=attention_mask,
            pooler_output=outputs.pooler_output if hasattr(outputs, "pooler_output") else None,
        )

    def tokenize(
        self,
        texts: List[str],
        max_length: Optional[int] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Tokenize texts for training.

        Args:
            texts: List of texts to tokenize
            max_length: Maximum sequence length (defaults to self.max_seq_length)

        Returns:
            Dictionary with input_ids, attention_mask, etc.
        """
        return self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_length or self.max_seq_length,
            return_tensors="pt",
        )

    def save_pretrained(self, path: str) -> None:
        """
        Save the model to disk.

        Args:
            path: Directory to save the model
        """
        import os
        os.makedirs(path, exist_ok=True)

        # Save backbone
        self.backbone.save_pretrained(path)
        self.tokenizer.save_pretrained(path)

        # Save projection layer if exists
        if self.projection is not None:
            torch.save(
                self.projection.state_dict(),
                os.path.join(path, "projection.pt")
            )

        # Save config
        config = {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "max_seq_length": self.max_seq_length,
            "pooling_strategy": self.pooling_strategy,
            "normalize_embeddings": self.normalize_embeddings,
            "hidden_size": self.hidden_size,
        }

        import json
        with open(os.path.join(path, "bi_encoder_config.json"), "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"BiEncoder saved to {path}")

    @classmethod
    def from_pretrained(cls, path: str) -> "BiEncoder":
        """
        Load a model from disk.

        Args:
            path: Directory containing the saved model

        Returns:
            Loaded BiEncoder instance
        """
        import os
        import json

        # Load config
        with open(os.path.join(path, "bi_encoder_config.json"), "r") as f:
            config = json.load(f)

        # Create instance
        encoder = cls(
            model_name=path,  # Load from saved path
            embedding_dim=config["embedding_dim"],
            max_seq_length=config["max_seq_length"],
            pooling_strategy=config["pooling_strategy"],
            normalize_embeddings=config["normalize_embeddings"],
        )

        # Load projection layer if exists
        projection_path = os.path.join(path, "projection.pt")
        if os.path.exists(projection_path) and encoder.projection is not None:
            encoder.projection.load_state_dict(torch.load(projection_path))

        logger.info(f"BiEncoder loaded from {path}")
        return encoder

    def get_num_parameters(self, trainable_only: bool = True) -> int:
        """Get number of parameters."""
        if trainable_only:
            return sum(p.numel() for p in self.parameters() if p.requires_grad)
        return sum(p.numel() for p in self.parameters())

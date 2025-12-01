"""
Cross-Encoder for High-Precision Reranking.

Unlike bi-encoders that encode texts separately, cross-encoders
process the pair together, enabling cross-attention between them
for more accurate similarity scoring.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np

from app.log.logging import logger
from app.ml.config import ml_config

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer, AutoConfig
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("torch/transformers not available. CrossEncoder will not work.")


@dataclass
class CrossEncoderOutput:
    """Output from the cross-encoder."""
    scores: List[float]
    logits: Optional[Any] = None  # torch.Tensor
    attention_weights: Optional[Any] = None


if TORCH_AVAILABLE:

    class CrossEncoder(nn.Module):
        """
        Cross-Encoder for pairwise scoring.

        Takes a pair of texts (resume, job) and outputs a relevance score.
        Uses cross-attention between the texts for accurate matching.
        """

        def __init__(
            self,
            model_name: str = None,
            max_seq_length: int = 512,
            num_labels: int = 1,
            dropout: float = 0.1,
        ):
            """
            Initialize the cross-encoder.

            Args:
                model_name: HuggingFace model name
                max_seq_length: Maximum combined sequence length
                num_labels: Number of output labels (1 for regression)
                dropout: Dropout rate
            """
            super().__init__()

            self.model_name = model_name or ml_config.base_model_name
            self.max_seq_length = max_seq_length
            self.num_labels = num_labels

            # Load model and tokenizer
            logger.info(f"Loading cross-encoder from {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.config = AutoConfig.from_pretrained(self.model_name)
            self.backbone = AutoModel.from_pretrained(self.model_name)

            # Classification head
            self.dropout = nn.Dropout(dropout)
            self.classifier = nn.Linear(self.config.hidden_size, num_labels)

            # For attention extraction
            self.config.output_attentions = True

            logger.info(
                f"CrossEncoder initialized: {self.model_name}",
                max_seq_length=max_seq_length,
            )

        def forward(
            self,
            input_ids: torch.Tensor,
            attention_mask: torch.Tensor,
            token_type_ids: Optional[torch.Tensor] = None,
            return_attention: bool = False,
        ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
            """
            Forward pass.

            Args:
                input_ids: Token IDs [batch_size, seq_len]
                attention_mask: Attention mask [batch_size, seq_len]
                token_type_ids: Token type IDs for segment distinction
                return_attention: Whether to return attention weights

            Returns:
                Tuple of (scores, attention_weights or None)
            """
            outputs = self.backbone(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
                output_attentions=return_attention,
            )

            # Use [CLS] token representation
            cls_output = outputs.last_hidden_state[:, 0, :]
            cls_output = self.dropout(cls_output)

            # Get scores
            logits = self.classifier(cls_output)

            if self.num_labels == 1:
                scores = torch.sigmoid(logits).squeeze(-1)
            else:
                scores = F.softmax(logits, dim=-1)

            attention = None
            if return_attention and hasattr(outputs, "attentions"):
                # Average attention across heads and layers
                attention = torch.stack(outputs.attentions).mean(dim=(0, 1))

            return scores, attention

        def predict(
            self,
            text_pairs: List[Tuple[str, str]],
            batch_size: int = 32,
            show_progress: bool = False,
        ) -> List[float]:
            """
            Predict scores for text pairs.

            Args:
                text_pairs: List of (text1, text2) tuples
                batch_size: Batch size for inference
                show_progress: Whether to show progress

            Returns:
                List of scores
            """
            self.eval()
            device = next(self.parameters()).device
            all_scores = []

            with torch.no_grad():
                for i in range(0, len(text_pairs), batch_size):
                    batch_pairs = text_pairs[i:i + batch_size]

                    # Tokenize pairs
                    texts1 = [p[0] for p in batch_pairs]
                    texts2 = [p[1] for p in batch_pairs]

                    encoded = self.tokenizer(
                        texts1,
                        texts2,
                        padding=True,
                        truncation=True,
                        max_length=self.max_seq_length,
                        return_tensors="pt",
                    )

                    # Move to device
                    encoded = {k: v.to(device) for k, v in encoded.items()}

                    # Forward
                    scores, _ = self.forward(**encoded)
                    all_scores.extend(scores.cpu().tolist())

            return all_scores

        def predict_with_attention(
            self,
            text1: str,
            text2: str,
        ) -> Tuple[float, np.ndarray]:
            """
            Predict score with attention weights for explainability.

            Args:
                text1: First text (resume)
                text2: Second text (job)

            Returns:
                Tuple of (score, attention_matrix)
            """
            self.eval()
            device = next(self.parameters()).device

            with torch.no_grad():
                encoded = self.tokenizer(
                    text1,
                    text2,
                    padding=True,
                    truncation=True,
                    max_length=self.max_seq_length,
                    return_tensors="pt",
                )
                encoded = {k: v.to(device) for k, v in encoded.items()}

                scores, attention = self.forward(**encoded, return_attention=True)

            return scores[0].item(), attention[0].cpu().numpy()

        def save_pretrained(self, path: str) -> None:
            """Save model to disk."""
            import os
            os.makedirs(path, exist_ok=True)

            self.backbone.save_pretrained(path)
            self.tokenizer.save_pretrained(path)

            # Save classifier
            torch.save(self.classifier.state_dict(), os.path.join(path, "classifier.pt"))

            # Save config
            import json
            config = {
                "model_name": self.model_name,
                "max_seq_length": self.max_seq_length,
                "num_labels": self.num_labels,
            }
            with open(os.path.join(path, "cross_encoder_config.json"), "w") as f:
                json.dump(config, f, indent=2)

            logger.info(f"CrossEncoder saved to {path}")

        @classmethod
        def from_pretrained(cls, path: str) -> "CrossEncoder":
            """Load model from disk."""
            import os
            import json

            with open(os.path.join(path, "cross_encoder_config.json"), "r") as f:
                config = json.load(f)

            encoder = cls(
                model_name=path,
                max_seq_length=config["max_seq_length"],
                num_labels=config["num_labels"],
            )

            # Load classifier
            classifier_path = os.path.join(path, "classifier.pt")
            if os.path.exists(classifier_path):
                encoder.classifier.load_state_dict(torch.load(classifier_path))

            logger.info(f"CrossEncoder loaded from {path}")
            return encoder


else:

    class CrossEncoder:
        """Placeholder when torch is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "torch and transformers required for CrossEncoder. "
                "Install with: pip install torch transformers"
            )

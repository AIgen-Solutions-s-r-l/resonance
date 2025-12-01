"""
Loss functions for contrastive learning.

Implements InfoNCE and other contrastive losses for training
the bi-encoder matching model.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional

from app.ml.config import ml_config


class InfoNCELoss(nn.Module):
    """
    InfoNCE (Noise Contrastive Estimation) Loss.

    Also known as NT-Xent (Normalized Temperature-scaled Cross Entropy).
    Used in SimCLR, CLIP, and similar contrastive learning methods.

    For each positive pair (anchor, positive), treats all other positives
    in the batch as negatives, giving O(B²) training signal per batch.
    """

    def __init__(
        self,
        temperature: float = None,
        reduction: str = "mean",
    ):
        """
        Initialize InfoNCE loss.

        Args:
            temperature: Temperature scaling factor (lower = sharper distribution)
            reduction: How to reduce the loss ("mean", "sum", "none")
        """
        super().__init__()
        self.temperature = temperature or ml_config.contrastive_temperature
        self.reduction = reduction

    def forward(
        self,
        anchor_embeddings: torch.Tensor,
        positive_embeddings: torch.Tensor,
        negative_embeddings: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute InfoNCE loss.

        Args:
            anchor_embeddings: Anchor embeddings [batch_size, dim]
                (e.g., resume embeddings)
            positive_embeddings: Positive embeddings [batch_size, dim]
                (e.g., job embeddings that match the resumes)
            negative_embeddings: Optional explicit negatives [batch_size, num_neg, dim]
                If None, uses in-batch negatives

        Returns:
            Loss value
        """
        batch_size = anchor_embeddings.size(0)
        device = anchor_embeddings.device

        # Normalize embeddings (should already be normalized, but ensure)
        anchor_embeddings = F.normalize(anchor_embeddings, p=2, dim=1)
        positive_embeddings = F.normalize(positive_embeddings, p=2, dim=1)

        if negative_embeddings is None:
            # In-batch negatives: all positives become negatives for other anchors
            # Similarity matrix: [batch_size, batch_size]
            similarity_matrix = torch.matmul(
                anchor_embeddings, positive_embeddings.t()
            ) / self.temperature

            # Labels: diagonal elements are positives (index i matches with i)
            labels = torch.arange(batch_size, device=device)

            # Cross entropy loss treats it as classification
            loss = F.cross_entropy(similarity_matrix, labels, reduction=self.reduction)

        else:
            # Explicit negatives provided
            # Shape: [batch_size, num_neg, dim]
            num_negatives = negative_embeddings.size(1)
            negative_embeddings = F.normalize(negative_embeddings, p=2, dim=2)

            # Positive similarities: [batch_size, 1]
            pos_sim = torch.sum(
                anchor_embeddings * positive_embeddings, dim=1, keepdim=True
            ) / self.temperature

            # Negative similarities: [batch_size, num_neg]
            neg_sim = torch.bmm(
                negative_embeddings,
                anchor_embeddings.unsqueeze(2)
            ).squeeze(2) / self.temperature

            # Concatenate: [batch_size, 1 + num_neg]
            # First column is positive, rest are negatives
            logits = torch.cat([pos_sim, neg_sim], dim=1)

            # Labels: positive is always at index 0
            labels = torch.zeros(batch_size, dtype=torch.long, device=device)

            loss = F.cross_entropy(logits, labels, reduction=self.reduction)

        return loss


class ContrastiveLoss(nn.Module):
    """
    General contrastive loss with support for multiple negative mining strategies.

    Combines InfoNCE with hard negative mining and optional margin-based losses.
    """

    def __init__(
        self,
        temperature: float = None,
        hard_negative_weight: float = 1.0,
        in_batch_negatives: bool = True,
        margin: Optional[float] = None,
    ):
        """
        Initialize contrastive loss.

        Args:
            temperature: Temperature for InfoNCE
            hard_negative_weight: Weight for hard negatives vs in-batch negatives
            in_batch_negatives: Whether to use in-batch negatives
            margin: Optional margin for triplet-like loss
        """
        super().__init__()
        self.temperature = temperature or ml_config.contrastive_temperature
        self.hard_negative_weight = hard_negative_weight
        self.in_batch_negatives = in_batch_negatives
        self.margin = margin

        self.info_nce = InfoNCELoss(temperature=self.temperature)

    def forward(
        self,
        anchor_embeddings: torch.Tensor,
        positive_embeddings: torch.Tensor,
        hard_negative_embeddings: Optional[torch.Tensor] = None,
    ) -> dict:
        """
        Compute contrastive loss.

        Args:
            anchor_embeddings: [batch_size, dim]
            positive_embeddings: [batch_size, dim]
            hard_negative_embeddings: [batch_size, num_hard_neg, dim]

        Returns:
            Dictionary with loss components
        """
        losses = {}

        # In-batch negatives loss
        if self.in_batch_negatives:
            in_batch_loss = self.info_nce(
                anchor_embeddings,
                positive_embeddings,
                negative_embeddings=None,  # Use in-batch
            )
            losses["in_batch_loss"] = in_batch_loss

        # Hard negatives loss
        if hard_negative_embeddings is not None:
            hard_neg_loss = self.info_nce(
                anchor_embeddings,
                positive_embeddings,
                negative_embeddings=hard_negative_embeddings,
            )
            losses["hard_negative_loss"] = hard_neg_loss

        # Compute total loss
        total_loss = torch.tensor(0.0, device=anchor_embeddings.device)

        if "in_batch_loss" in losses:
            total_loss = total_loss + losses["in_batch_loss"]

        if "hard_negative_loss" in losses:
            total_loss = total_loss + self.hard_negative_weight * losses["hard_negative_loss"]

        # Optional margin-based loss
        if self.margin is not None and hard_negative_embeddings is not None:
            margin_loss = self._margin_loss(
                anchor_embeddings,
                positive_embeddings,
                hard_negative_embeddings,
            )
            losses["margin_loss"] = margin_loss
            total_loss = total_loss + margin_loss

        losses["total_loss"] = total_loss
        return losses

    def _margin_loss(
        self,
        anchors: torch.Tensor,
        positives: torch.Tensor,
        negatives: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute margin-based triplet loss.

        Ensures positive similarity > negative similarity + margin.
        """
        # Positive distances
        pos_dist = 1 - torch.sum(anchors * positives, dim=1)  # Cosine distance

        # Negative distances (min over all negatives)
        neg_sim = torch.bmm(negatives, anchors.unsqueeze(2)).squeeze(2)
        neg_dist = 1 - torch.max(neg_sim, dim=1)[0]  # Hardest negative

        # Triplet loss with margin
        loss = F.relu(pos_dist - neg_dist + self.margin)

        return loss.mean()


class MultipleNegativesRankingLoss(nn.Module):
    """
    Multiple Negatives Ranking Loss.

    Efficient loss that uses all other examples in the batch as negatives.
    Equivalent to InfoNCE but sometimes used with different temperature schedules.

    Reference: https://arxiv.org/abs/1705.00652
    """

    def __init__(
        self,
        scale: float = 20.0,
        similarity_fct: str = "cosine",
    ):
        """
        Initialize MNRL.

        Args:
            scale: Scaling factor for similarities (similar to 1/temperature)
            similarity_fct: Similarity function ("cosine" or "dot")
        """
        super().__init__()
        self.scale = scale
        self.similarity_fct = similarity_fct

    def forward(
        self,
        anchor_embeddings: torch.Tensor,
        positive_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute MNRL loss.

        Args:
            anchor_embeddings: [batch_size, dim]
            positive_embeddings: [batch_size, dim]

        Returns:
            Loss value
        """
        if self.similarity_fct == "cosine":
            anchor_embeddings = F.normalize(anchor_embeddings, p=2, dim=1)
            positive_embeddings = F.normalize(positive_embeddings, p=2, dim=1)

        # Compute similarity matrix
        scores = torch.matmul(anchor_embeddings, positive_embeddings.t()) * self.scale

        # Labels: diagonal is positive
        labels = torch.arange(scores.size(0), device=scores.device)

        # Cross entropy
        return F.cross_entropy(scores, labels)


class OnlineContrastiveLoss(nn.Module):
    """
    Online Contrastive Loss with hard example mining.

    Dynamically selects the hardest negatives within each batch
    for more efficient learning.
    """

    def __init__(
        self,
        margin: float = 0.5,
        hard_negative_ratio: float = 0.5,
    ):
        """
        Initialize online contrastive loss.

        Args:
            margin: Margin for contrastive loss
            hard_negative_ratio: Ratio of hard negatives to use
        """
        super().__init__()
        self.margin = margin
        self.hard_negative_ratio = hard_negative_ratio

    def forward(
        self,
        anchor_embeddings: torch.Tensor,
        positive_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute online contrastive loss with hard mining.

        Args:
            anchor_embeddings: [batch_size, dim]
            positive_embeddings: [batch_size, dim]

        Returns:
            Loss value
        """
        batch_size = anchor_embeddings.size(0)
        device = anchor_embeddings.device

        # Normalize
        anchor_embeddings = F.normalize(anchor_embeddings, p=2, dim=1)
        positive_embeddings = F.normalize(positive_embeddings, p=2, dim=1)

        # Similarity matrix
        similarity_matrix = torch.matmul(anchor_embeddings, positive_embeddings.t())

        # Positive pairs (diagonal)
        positive_similarities = torch.diag(similarity_matrix)

        # Create mask for negative pairs
        mask = ~torch.eye(batch_size, dtype=torch.bool, device=device)

        # Get negative similarities
        negative_similarities = similarity_matrix[mask].view(batch_size, batch_size - 1)

        # Select hard negatives (highest similarity)
        num_hard = max(1, int((batch_size - 1) * self.hard_negative_ratio))
        hard_negatives, _ = torch.topk(negative_similarities, num_hard, dim=1)

        # Contrastive loss: positive should be closer than hardest negative + margin
        loss = F.relu(
            hard_negatives - positive_similarities.unsqueeze(1) + self.margin
        ).mean()

        return loss

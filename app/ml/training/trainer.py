"""
Trainer for Contrastive Learning.

Handles the training loop, optimization, checkpointing, and logging
for fine-tuning the bi-encoder with contrastive learning.
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from pathlib import Path
import time
import json
from datetime import datetime

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import LinearLR, CosineAnnealingLR, SequentialLR

from app.log.logging import logger
from app.ml.config import ml_config
from app.ml.models.bi_encoder import BiEncoder
from app.ml.models.losses import ContrastiveLoss, InfoNCELoss
from app.ml.training.dataset import TrainingDataset, TrainingBatch


@dataclass
class TrainingConfig:
    """Configuration for training."""
    # Optimization
    learning_rate: float = None
    batch_size: int = None
    epochs: int = None
    warmup_ratio: float = None
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    gradient_accumulation_steps: int = 1

    # Loss
    temperature: float = None
    use_hard_negatives: bool = True
    hard_negative_weight: float = 1.0

    # Checkpointing
    save_steps: int = 500
    eval_steps: int = 100
    save_total_limit: int = 3
    output_dir: Path = None

    # Early stopping
    early_stopping_patience: int = 5
    early_stopping_threshold: float = 0.001

    # Logging
    logging_steps: int = 10

    def __post_init__(self):
        self.learning_rate = self.learning_rate or ml_config.contrastive_learning_rate
        self.batch_size = self.batch_size or ml_config.contrastive_batch_size
        self.epochs = self.epochs or ml_config.contrastive_epochs
        self.warmup_ratio = self.warmup_ratio or ml_config.contrastive_warmup_ratio
        self.temperature = self.temperature or ml_config.contrastive_temperature
        self.output_dir = self.output_dir or ml_config.models_dir / "bi_encoder"


@dataclass
class TrainingState:
    """Tracks training state for checkpointing and logging."""
    epoch: int = 0
    global_step: int = 0
    best_metric: float = float("-inf")
    best_epoch: int = 0
    epochs_without_improvement: int = 0
    train_loss_history: List[float] = field(default_factory=list)
    val_loss_history: List[float] = field(default_factory=list)
    learning_rates: List[float] = field(default_factory=list)


class ContrastiveTrainer:
    """
    Trainer for contrastive learning of the bi-encoder.

    Features:
    - Mixed precision training (if available)
    - Gradient accumulation
    - Learning rate scheduling with warmup
    - Checkpointing and early stopping
    - Validation during training
    """

    def __init__(
        self,
        model: BiEncoder,
        config: TrainingConfig = None,
        device: Optional[torch.device] = None,
    ):
        """
        Initialize the trainer.

        Args:
            model: BiEncoder model to train
            config: Training configuration
            device: Device to train on
        """
        self.model = model
        self.config = config or TrainingConfig()
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.model.to(self.device)

        # Initialize loss
        self.loss_fn = ContrastiveLoss(
            temperature=self.config.temperature,
            hard_negative_weight=self.config.hard_negative_weight,
            in_batch_negatives=True,
        )

        # State
        self.state = TrainingState()

        # Will be initialized in train()
        self.optimizer = None
        self.scheduler = None

        logger.info(
            f"ContrastiveTrainer initialized on {self.device}",
            config=self.config.__dict__
        )

    def _create_optimizer(self) -> AdamW:
        """Create optimizer with weight decay."""
        # Separate parameters for weight decay
        no_decay = ["bias", "LayerNorm.weight", "layer_norm.weight"]
        optimizer_grouped_parameters = [
            {
                "params": [
                    p for n, p in self.model.named_parameters()
                    if not any(nd in n for nd in no_decay) and p.requires_grad
                ],
                "weight_decay": self.config.weight_decay,
            },
            {
                "params": [
                    p for n, p in self.model.named_parameters()
                    if any(nd in n for nd in no_decay) and p.requires_grad
                ],
                "weight_decay": 0.0,
            },
        ]

        return AdamW(
            optimizer_grouped_parameters,
            lr=self.config.learning_rate,
        )

    def _create_scheduler(
        self,
        optimizer: AdamW,
        num_training_steps: int,
    ):
        """Create learning rate scheduler with warmup."""
        num_warmup_steps = int(num_training_steps * self.config.warmup_ratio)

        # Linear warmup
        warmup_scheduler = LinearLR(
            optimizer,
            start_factor=0.1,
            end_factor=1.0,
            total_iters=num_warmup_steps,
        )

        # Cosine decay
        decay_scheduler = CosineAnnealingLR(
            optimizer,
            T_max=num_training_steps - num_warmup_steps,
            eta_min=self.config.learning_rate * 0.1,
        )

        # Combine
        return SequentialLR(
            optimizer,
            schedulers=[warmup_scheduler, decay_scheduler],
            milestones=[num_warmup_steps],
        )

    def _prepare_batch(
        self,
        batch: TrainingBatch,
    ) -> Dict[str, torch.Tensor]:
        """
        Prepare a batch for training.

        Args:
            batch: TrainingBatch from dataset

        Returns:
            Dictionary with tokenized inputs on device
        """
        # Tokenize resumes
        resume_inputs = self.model.tokenize(batch.resume_texts)

        # Tokenize positive jobs
        positive_inputs = self.model.tokenize(batch.positive_job_texts)

        # Tokenize hard negatives if present
        hard_neg_inputs = None
        if batch.negative_job_texts and any(batch.negative_job_texts):
            # Flatten negatives for tokenization
            flat_negatives = []
            neg_counts = []
            for negs in batch.negative_job_texts:
                flat_negatives.extend(negs)
                neg_counts.append(len(negs))

            if flat_negatives:
                hard_neg_inputs = self.model.tokenize(flat_negatives)
                hard_neg_inputs["neg_counts"] = neg_counts

        # Move to device
        result = {
            "resume": {k: v.to(self.device) for k, v in resume_inputs.items()},
            "positive": {k: v.to(self.device) for k, v in positive_inputs.items()},
        }

        if hard_neg_inputs:
            neg_counts = hard_neg_inputs.pop("neg_counts")
            result["hard_negative"] = {
                k: v.to(self.device) for k, v in hard_neg_inputs.items()
            }
            result["neg_counts"] = neg_counts

        return result

    def _training_step(
        self,
        batch_inputs: Dict[str, Any],
    ) -> Dict[str, torch.Tensor]:
        """
        Execute a single training step.

        Args:
            batch_inputs: Prepared batch inputs

        Returns:
            Loss dictionary
        """
        # Forward pass for resumes
        resume_output = self.model(
            input_ids=batch_inputs["resume"]["input_ids"],
            attention_mask=batch_inputs["resume"]["attention_mask"],
        )

        # Forward pass for positives
        positive_output = self.model(
            input_ids=batch_inputs["positive"]["input_ids"],
            attention_mask=batch_inputs["positive"]["attention_mask"],
        )

        # Forward pass for hard negatives if present
        hard_neg_embeddings = None
        if "hard_negative" in batch_inputs and self.config.use_hard_negatives:
            hard_neg_output = self.model(
                input_ids=batch_inputs["hard_negative"]["input_ids"],
                attention_mask=batch_inputs["hard_negative"]["attention_mask"],
            )

            # Reshape to [batch_size, num_neg, dim]
            neg_counts = batch_inputs["neg_counts"]
            batch_size = len(neg_counts)

            if all(c > 0 for c in neg_counts):
                # Uniform number of negatives
                num_neg = neg_counts[0]
                hard_neg_embeddings = hard_neg_output.embeddings.view(
                    batch_size, num_neg, -1
                )

        # Compute loss
        losses = self.loss_fn(
            anchor_embeddings=resume_output.embeddings,
            positive_embeddings=positive_output.embeddings,
            hard_negative_embeddings=hard_neg_embeddings,
        )

        return losses

    def train(
        self,
        train_dataset: TrainingDataset,
        eval_dataset: Optional[TrainingDataset] = None,
        eval_callback: Optional[Callable] = None,
    ) -> TrainingState:
        """
        Train the model.

        Args:
            train_dataset: Training dataset
            eval_dataset: Optional evaluation dataset
            eval_callback: Optional callback for custom evaluation

        Returns:
            Final training state
        """
        # Calculate total steps
        num_batches = len(list(train_dataset.get_batches(
            split="train",
            batch_size=self.config.batch_size,
            shuffle=False,
        )))
        steps_per_epoch = num_batches // self.config.gradient_accumulation_steps
        num_training_steps = steps_per_epoch * self.config.epochs

        logger.info(
            f"Starting training",
            epochs=self.config.epochs,
            batches_per_epoch=num_batches,
            total_steps=num_training_steps,
            device=str(self.device),
        )

        # Create optimizer and scheduler
        self.optimizer = self._create_optimizer()
        self.scheduler = self._create_scheduler(self.optimizer, num_training_steps)

        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Training loop
        self.model.train()
        accumulated_loss = 0.0
        accumulated_steps = 0

        for epoch in range(self.config.epochs):
            self.state.epoch = epoch
            epoch_loss = 0.0
            epoch_steps = 0
            epoch_start = time.time()

            for batch in train_dataset.get_batches(
                split="train",
                batch_size=self.config.batch_size,
                shuffle=True,
            ):
                # Prepare batch
                batch_inputs = self._prepare_batch(batch)

                # Forward pass
                losses = self._training_step(batch_inputs)
                loss = losses["total_loss"]

                # Scale loss for gradient accumulation
                loss = loss / self.config.gradient_accumulation_steps

                # Backward pass
                loss.backward()

                accumulated_loss += loss.item()
                accumulated_steps += 1

                # Gradient accumulation step
                if accumulated_steps % self.config.gradient_accumulation_steps == 0:
                    # Clip gradients
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        self.config.max_grad_norm,
                    )

                    # Optimizer step
                    self.optimizer.step()
                    self.scheduler.step()
                    self.optimizer.zero_grad()

                    self.state.global_step += 1
                    epoch_loss += accumulated_loss
                    epoch_steps += 1

                    # Logging
                    if self.state.global_step % self.config.logging_steps == 0:
                        avg_loss = accumulated_loss
                        lr = self.scheduler.get_last_lr()[0]
                        self.state.learning_rates.append(lr)

                        logger.info(
                            f"Step {self.state.global_step}",
                            loss=f"{avg_loss:.4f}",
                            lr=f"{lr:.2e}",
                        )

                    accumulated_loss = 0.0

                    # Evaluation
                    if (
                        eval_dataset is not None
                        and self.state.global_step % self.config.eval_steps == 0
                    ):
                        eval_loss = self._evaluate(eval_dataset)
                        self.state.val_loss_history.append(eval_loss)
                        logger.info(f"Eval loss: {eval_loss:.4f}")

                        # Early stopping check
                        if eval_loss > self.state.best_metric + self.config.early_stopping_threshold:
                            self.state.best_metric = eval_loss
                            self.state.best_epoch = epoch
                            self.state.epochs_without_improvement = 0
                            self._save_checkpoint("best")
                        else:
                            self.state.epochs_without_improvement += 1

                        self.model.train()

                    # Checkpointing
                    if self.state.global_step % self.config.save_steps == 0:
                        self._save_checkpoint(f"step_{self.state.global_step}")

            # End of epoch
            epoch_time = time.time() - epoch_start
            avg_epoch_loss = epoch_loss / max(epoch_steps, 1)
            self.state.train_loss_history.append(avg_epoch_loss)

            logger.info(
                f"Epoch {epoch + 1}/{self.config.epochs} completed",
                avg_loss=f"{avg_epoch_loss:.4f}",
                time=f"{epoch_time:.1f}s",
            )

            # Save epoch checkpoint
            self._save_checkpoint(f"epoch_{epoch + 1}")

            # Early stopping
            if self.state.epochs_without_improvement >= self.config.early_stopping_patience:
                logger.info(
                    f"Early stopping triggered after {epoch + 1} epochs"
                )
                break

        # Save final model
        self._save_checkpoint("final")

        logger.info(
            "Training completed",
            total_steps=self.state.global_step,
            best_metric=self.state.best_metric,
            best_epoch=self.state.best_epoch,
        )

        return self.state

    def _evaluate(self, eval_dataset: TrainingDataset) -> float:
        """Evaluate on validation set."""
        self.model.eval()
        total_loss = 0.0
        num_batches = 0

        with torch.no_grad():
            for batch in eval_dataset.get_batches(
                split="val",
                batch_size=self.config.batch_size,
                shuffle=False,
            ):
                batch_inputs = self._prepare_batch(batch)
                losses = self._training_step(batch_inputs)
                total_loss += losses["total_loss"].item()
                num_batches += 1

        return -total_loss / max(num_batches, 1)  # Return negative for maximization

    def _save_checkpoint(self, name: str) -> None:
        """Save a checkpoint."""
        checkpoint_dir = self.config.output_dir / name
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        self.model.save_pretrained(str(checkpoint_dir))

        # Save training state
        state_dict = {
            "epoch": self.state.epoch,
            "global_step": self.state.global_step,
            "best_metric": self.state.best_metric,
            "best_epoch": self.state.best_epoch,
            "train_loss_history": self.state.train_loss_history,
            "val_loss_history": self.state.val_loss_history,
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "config": self.config.__dict__,
            "timestamp": datetime.now().isoformat(),
        }

        # Convert Path objects to strings for JSON serialization
        state_dict["config"]["output_dir"] = str(self.config.output_dir)

        with open(checkpoint_dir / "training_state.json", "w") as f:
            json.dump(state_dict, f, indent=2, default=str)

        logger.info(f"Checkpoint saved: {checkpoint_dir}")

        # Clean up old checkpoints
        self._cleanup_checkpoints()

    def _cleanup_checkpoints(self) -> None:
        """Remove old checkpoints beyond save_total_limit."""
        if self.config.save_total_limit <= 0:
            return

        # Get all step checkpoints
        checkpoints = sorted(
            self.config.output_dir.glob("step_*"),
            key=lambda p: int(p.name.split("_")[1]),
        )

        # Keep best, final, and recent checkpoints
        protected = {"best", "final"}
        for epoch_dir in self.config.output_dir.glob("epoch_*"):
            protected.add(epoch_dir.name)

        # Remove old step checkpoints
        while len(checkpoints) > self.config.save_total_limit:
            old_checkpoint = checkpoints.pop(0)
            if old_checkpoint.name not in protected:
                import shutil
                shutil.rmtree(old_checkpoint)
                logger.debug(f"Removed old checkpoint: {old_checkpoint}")

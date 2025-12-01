#!/usr/bin/env python3
"""
Train Contrastive Bi-Encoder for Job Matching.

This script trains the bi-encoder model using contrastive learning
with hard negative mining.

Usage:
    python -m app.ml.scripts.train_contrastive --help
    python -m app.ml.scripts.train_contrastive --epochs 10 --batch-size 32
    python -m app.ml.scripts.train_contrastive --resume-from models/bi_encoder/epoch_5
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

import torch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.log.logging import logger
from app.ml.config import ml_config
from app.ml.models.bi_encoder import BiEncoder
from app.ml.training import (
    HardNegativeMiner,
    TrainingDataset,
    ContrastiveTrainer,
    TrainingConfig,
)
from app.ml.evaluation import ModelEvaluator, EvaluationConfig


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Train contrastive bi-encoder for job matching"
    )

    # Model configuration
    parser.add_argument(
        "--model-name",
        type=str,
        default=ml_config.base_model_name,
        help="Base model name (HuggingFace model ID)",
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=ml_config.embedding_dim,
        help="Output embedding dimension",
    )
    parser.add_argument(
        "--pooling",
        type=str,
        choices=["mean", "cls", "max"],
        default=ml_config.pooling_strategy,
        help="Pooling strategy for embeddings",
    )

    # Training configuration
    parser.add_argument(
        "--epochs",
        type=int,
        default=ml_config.contrastive_epochs,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=ml_config.contrastive_batch_size,
        help="Training batch size",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=ml_config.contrastive_learning_rate,
        help="Learning rate",
    )
    parser.add_argument(
        "--warmup-ratio",
        type=float,
        default=ml_config.contrastive_warmup_ratio,
        help="Warmup ratio for learning rate scheduler",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=ml_config.contrastive_temperature,
        help="Temperature for InfoNCE loss",
    )
    parser.add_argument(
        "--gradient-accumulation",
        type=int,
        default=1,
        help="Gradient accumulation steps",
    )

    # Data configuration
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory containing training data (if already prepared)",
    )
    parser.add_argument(
        "--hard-negatives",
        type=int,
        default=ml_config.hard_negative_ratio,
        help="Number of hard negatives per positive",
    )
    parser.add_argument(
        "--no-augmentation",
        action="store_true",
        help="Disable data augmentation",
    )

    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ml_config.models_dir / "bi_encoder",
        help="Output directory for model checkpoints",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Experiment name for logging",
    )

    # Checkpointing
    parser.add_argument(
        "--resume-from",
        type=Path,
        default=None,
        help="Resume training from checkpoint",
    )
    parser.add_argument(
        "--save-steps",
        type=int,
        default=500,
        help="Save checkpoint every N steps",
    )
    parser.add_argument(
        "--eval-steps",
        type=int,
        default=100,
        help="Evaluate every N steps",
    )

    # Hardware
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="Device to train on",
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        help="Use mixed precision training (requires CUDA)",
    )

    # Evaluation
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Only run evaluation, no training",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run latency benchmarks",
    )

    return parser.parse_args()


def get_device(device_arg: str) -> torch.device:
    """Determine the device to use."""
    if device_arg == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")
    return torch.device(device_arg)


async def prepare_data(args) -> TrainingDataset:
    """Prepare training data."""
    if args.data_dir and args.data_dir.exists():
        logger.info(f"Loading dataset from {args.data_dir}")
        return TrainingDataset.load(args.data_dir)

    logger.info("Mining training data from database...")

    # Initialize miner
    miner = HardNegativeMiner(hard_negative_ratio=args.hard_negatives)

    # Load jobs
    await miner.load_jobs_from_db()

    # Build dataset
    dataset = await miner.build_training_dataset()

    # Save for future use
    save_path = args.output_dir / "training_data"
    dataset.save(save_path)
    logger.info(f"Dataset saved to {save_path}")

    return dataset


def train(args, dataset: TrainingDataset, device: torch.device):
    """Run training."""
    # Create or load model
    if args.resume_from:
        logger.info(f"Resuming from {args.resume_from}")
        model = BiEncoder.from_pretrained(str(args.resume_from))
    else:
        logger.info(f"Creating new model: {args.model_name}")
        model = BiEncoder(
            model_name=args.model_name,
            embedding_dim=args.embedding_dim,
            pooling_strategy=args.pooling,
        )

    # Log model info
    num_params = model.get_num_parameters()
    logger.info(f"Model parameters: {num_params:,} trainable")

    # Create training config
    config = TrainingConfig(
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        epochs=args.epochs,
        warmup_ratio=args.warmup_ratio,
        temperature=args.temperature,
        gradient_accumulation_steps=args.gradient_accumulation,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        output_dir=args.output_dir,
    )

    # Create trainer
    trainer = ContrastiveTrainer(
        model=model,
        config=config,
        device=device,
    )

    # Train
    state = trainer.train(
        train_dataset=dataset,
        eval_dataset=dataset if len(dataset) > 100 else None,
    )

    logger.info("Training completed!")
    logger.info(f"Best metric: {state.best_metric:.4f} at epoch {state.best_epoch}")

    return model, state


def evaluate(args, model: BiEncoder, dataset: TrainingDataset, device: torch.device):
    """Run evaluation."""
    logger.info("Running evaluation...")

    eval_config = EvaluationConfig(
        batch_size=args.batch_size,
        use_gpu=(device.type == "cuda"),
    )

    evaluator = ModelEvaluator(model, eval_config)

    # Evaluate on test set
    result = evaluator.evaluate_dataset(dataset, split="test")

    logger.info("=" * 50)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 50)
    logger.info(f"nDCG@10:    {result.ndcg_at_10:.4f}")
    logger.info(f"MRR:        {result.mrr:.4f}")
    logger.info(f"Recall@10:  {result.recall_at_10:.4f}")
    logger.info(f"Recall@25:  {result.recall_at_25:.4f}")
    logger.info("=" * 50)

    # Save results
    results_path = args.output_dir / "evaluation_results.json"
    with open(results_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    logger.info(f"Results saved to {results_path}")

    return result


def benchmark(args, model: BiEncoder, device: torch.device):
    """Run latency benchmarks."""
    logger.info("Running latency benchmarks...")

    eval_config = EvaluationConfig(
        batch_size=args.batch_size,
        use_gpu=(device.type == "cuda"),
    )

    evaluator = ModelEvaluator(model, eval_config)

    # Sample texts for benchmarking
    sample_texts = [
        "Experienced Python developer with 5 years of experience in FastAPI and Django.",
        "Senior software engineer skilled in machine learning and data science.",
        "Full-stack developer proficient in React, Node.js, and PostgreSQL.",
    ] * 20

    latencies = evaluator.benchmark_latency(sample_texts)

    logger.info("=" * 50)
    logger.info("LATENCY BENCHMARK")
    logger.info("=" * 50)
    logger.info(f"Single encode (mean):  {latencies['single_mean_ms']:.2f} ms")
    logger.info(f"Single encode (P95):   {latencies['single_p95_ms']:.2f} ms")
    logger.info(f"Single encode (P99):   {latencies['single_p99_ms']:.2f} ms")
    logger.info(f"Batch encode (mean):   {latencies['batch_mean_ms']:.2f} ms")
    logger.info(f"Batch size:            {latencies['batch_size']}")
    logger.info("=" * 50)

    return latencies


async def main():
    """Main entry point."""
    args = parse_args()

    # Setup
    experiment_name = args.experiment_name or datetime.now().strftime("%Y%m%d_%H%M%S")
    args.output_dir = args.output_dir / experiment_name
    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Experiment: {experiment_name}")
    logger.info(f"Output directory: {args.output_dir}")

    # Save configuration
    config_path = args.output_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(vars(args), f, indent=2, default=str)

    # Determine device
    device = get_device(args.device)
    logger.info(f"Using device: {device}")

    # Prepare data
    dataset = await prepare_data(args)
    logger.info(f"Dataset: {dataset.get_statistics()}")

    # Load model for eval-only mode
    if args.eval_only:
        if not args.resume_from:
            logger.error("--resume-from required for --eval-only mode")
            sys.exit(1)
        model = BiEncoder.from_pretrained(str(args.resume_from))
    else:
        # Train
        model, state = train(args, dataset, device)

    # Evaluate
    evaluate(args, model, dataset, device)

    # Benchmark if requested
    if args.benchmark:
        benchmark(args, model, device)

    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Script to compare raw scores with transformed scores using the sigmoid function.

This script loads the raw scores from the CSV file and applies the sigmoid
transformation to show the difference between raw and transformed scores.
"""

import matplotlib.pyplot as plt
import numpy as np
import csv
import math
import sys
import os

# Add app directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the sigmoid transformation function
from app.libs.job_matcher.job_validator import JobValidator


def load_raw_scores(csv_file="raw_scores.csv"):
    """Load raw scores from CSV file."""
    scores = []
    try:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scores.append(float(row["raw_score"]))
        print(f"Loaded {len(scores)} raw scores from {csv_file}")
        return scores
    except Exception as e:
        print(f"Error loading raw scores: {e}")
        return []


def apply_transformations(raw_scores):
    """Apply different transformations to the raw scores."""
    # Original linear transformation (0-100%)
    original_scores = []
    
    # Sigmoid transformation
    sigmoid_scores = []
    
    for score in raw_scores:
        # Original transformation (linear mapping from 0-2 to 100-0%)
        original = max(0, 100 - score * 50) if score <= 2.0 else 0
        original_scores.append(original)
        
        # Sigmoid transformation
        sigmoid = JobValidator.score_to_percentage(score)
        sigmoid_scores.append(sigmoid)
    
    return original_scores, sigmoid_scores


def plot_comparison(raw_scores, original_scores, sigmoid_scores):
    """Plot comparison of raw and transformed scores."""
    plt.figure(figsize=(12, 10))
    
    # Sort scores for better visualization
    indices = np.argsort(raw_scores)
    sorted_raw = [raw_scores[i] for i in indices]
    sorted_original = [original_scores[i] for i in indices]
    sorted_sigmoid = [sigmoid_scores[i] for i in indices]
    
    # Plot raw scores vs. transformations
    plt.subplot(2, 1, 1)
    plt.scatter(range(len(sorted_raw)), sorted_raw, alpha=0.5, label="Raw Scores", color="blue")
    plt.ylabel("Raw Score (lower is better)")
    plt.title("Raw Scores vs. Transformed Scores")
    plt.grid(True, alpha=0.3)
    
    # Add second y-axis for percentages
    ax2 = plt.twinx()
    ax2.scatter(range(len(sorted_original)), sorted_original, alpha=0.5, label="Original %", color="green")
    ax2.scatter(range(len(sorted_sigmoid)), sorted_sigmoid, alpha=0.5, label="Sigmoid %", color="red")
    ax2.set_ylabel("Match Percentage (%)")
    ax2.set_ylim(0, 100)
    
    # Add legend
    lines1, labels1 = plt.gca().get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    
    # Plot transformation curves
    plt.subplot(2, 1, 2)
    x = np.linspace(0, 2, 100)
    y_original = [max(0, 100 - score * 50) for score in x]
    y_sigmoid = [JobValidator.score_to_percentage(score) for score in x]
    
    plt.plot(x, y_original, label="Original Transformation", color="green")
    plt.plot(x, y_sigmoid, label="Sigmoid Transformation", color="red")
    plt.xlabel("Raw Score")
    plt.ylabel("Match Percentage (%)")
    plt.title("Transformation Functions")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Add vertical lines for key thresholds
    thresholds = [0.1, 0.25, 0.5, 0.7, 0.9]
    colors = ["purple", "blue", "cyan", "orange", "magenta"]
    
    for threshold, color in zip(thresholds, colors):
        plt.axvline(x=threshold, color=color, linestyle="--", alpha=0.5)
        plt.text(threshold, 10, f"{threshold}", ha="center", va="bottom", color=color)
    
    plt.tight_layout()
    plt.savefig("score_transformation_comparison.png")
    print("Comparison plot saved as score_transformation_comparison.png")


def print_key_points(raw_scores, original_scores, sigmoid_scores):
    """Print key points for comparison."""
    # Select some key percentiles
    percentiles = [10, 25, 50, 75, 90]
    raw_percentiles = np.percentile(raw_scores, percentiles)
    
    print("\nKey Points Comparison:")
    print("=" * 60)
    print(f"{'Raw Score':<10} | {'Original %':<10} | {'Sigmoid %':<10} | {'Percentile':<10}")
    print("-" * 60)
    
    # Print values at specific raw scores
    key_scores = [0.0, 0.1, 0.25, 0.5, 0.7, 0.9, 1.0, 1.5, 2.0]
    for score in key_scores:
        original = max(0, 100 - score * 50) if score <= 2.0 else 0
        sigmoid = JobValidator.score_to_percentage(score)
        print(f"{score:<10.2f} | {original:<10.2f} | {sigmoid:<10.2f} | {'Fixed Value':<10}")
    
    # Print values at percentiles
    print("\nValues at Percentiles:")
    print("-" * 60)
    for p, raw in zip(percentiles, raw_percentiles):
        idx = np.searchsorted(sorted(raw_scores), raw)
        if idx < len(raw_scores):
            original = original_scores[idx]
            sigmoid = sigmoid_scores[idx]
            print(f"{raw:<10.2f} | {original:<10.2f} | {sigmoid:<10.2f} | {p:<3}th %ile")


def main():
    """Main function."""
    # Load raw scores
    raw_scores = load_raw_scores()
    if not raw_scores:
        print("No raw scores found. Run analyze_raw_scores.py first.")
        return
    
    # Apply transformations
    original_scores, sigmoid_scores = apply_transformations(raw_scores)
    
    # Plot comparison
    plot_comparison(raw_scores, original_scores, sigmoid_scores)
    
    # Print key points
    print_key_points(raw_scores, original_scores, sigmoid_scores)


if __name__ == "__main__":
    main()
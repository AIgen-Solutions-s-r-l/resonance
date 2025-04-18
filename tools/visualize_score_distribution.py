#!/usr/bin/env python3
"""
Script to visualize the distribution of raw and transformed scores.

This script loads the raw scores from the CSV file, applies the sigmoid
transformation, and creates a comprehensive visualization showing how
the distribution changes after transformation.
"""

import matplotlib.pyplot as plt
import numpy as np
import csv
import math
import sys
import os
from scipy.stats import norm

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


def visualize_distributions(raw_scores, original_scores, sigmoid_scores):
    """Create a comprehensive visualization of score distributions."""
    plt.figure(figsize=(15, 12))
    
    # 1. Raw Score Distribution (Histogram) with Gaussian Fit
    plt.subplot(3, 2, 1)
    
    # Plot histogram
    n, bins, patches = plt.hist(raw_scores, bins=30, alpha=0.7, color='blue', density=True)
    
    # Fit Gaussian distribution
    mu, sigma = norm.fit(raw_scores)
    x = np.linspace(min(raw_scores), max(raw_scores), 100)
    y = norm.pdf(x, mu, sigma)
    
    # Plot Gaussian fit
    plt.plot(x, y, 'r--', linewidth=2, label=f'Gaussian Fit\nμ={mu:.2f}, σ={sigma:.2f}')
    plt.legend()
    
    plt.title("Raw Score Distribution with Gaussian Fit")
    plt.xlabel("Raw Score (lower is better)")
    plt.ylabel("Density")
    plt.grid(True, alpha=0.3)
    
    # Add vertical lines for key thresholds
    thresholds = [0.1, 0.25, 0.5, 0.7, 0.9]
    colors = ['purple', 'blue', 'cyan', 'orange', 'magenta']
    
    for threshold, color in zip(thresholds, colors):
        plt.axvline(x=threshold, color=color, linestyle='--', alpha=0.5)
        plt.text(threshold, 0, f"{threshold}", ha='center', va='bottom', color=color)
    
    # 2. Original Transformation Distribution (Histogram) with Gaussian Fit
    plt.subplot(3, 2, 2)
    
    # Plot histogram
    n, bins, patches = plt.hist(original_scores, bins=30, alpha=0.7, color='green', density=True)
    
    # Fit Gaussian distribution
    mu, sigma = norm.fit(original_scores)
    x = np.linspace(min(original_scores), max(original_scores), 100)
    y = norm.pdf(x, mu, sigma)
    
    # Plot Gaussian fit
    plt.plot(x, y, 'r--', linewidth=2, label=f'Gaussian Fit\nμ={mu:.2f}, σ={sigma:.2f}')
    plt.legend()
    
    plt.title("Original Transformation Distribution with Gaussian Fit")
    plt.xlabel("Match Percentage (%)")
    plt.ylabel("Density")
    plt.grid(True, alpha=0.3)
    
    # Add vertical lines for key thresholds
    key_percentages = [60, 80, 90]
    for pct in key_percentages:
        plt.axvline(x=pct, color='red', linestyle='--', alpha=0.5)
        plt.text(pct, 0, f"{pct}%", ha='center', va='bottom', color='red')
    
    # 3. Sigmoid Transformation Distribution (Histogram) with Gaussian Fit
    plt.subplot(3, 2, 3)
    
    # Plot histogram
    n, bins, patches = plt.hist(sigmoid_scores, bins=30, alpha=0.7, color='red', density=True)
    
    # Fit Gaussian distribution
    mu, sigma = norm.fit(sigmoid_scores)
    x = np.linspace(min(sigmoid_scores), max(sigmoid_scores), 100)
    y = norm.pdf(x, mu, sigma)
    
    # Plot Gaussian fit
    plt.plot(x, y, 'r--', linewidth=2, label=f'Gaussian Fit\nμ={mu:.2f}, σ={sigma:.2f}')
    plt.legend()
    
    plt.title("Sigmoid Transformation Distribution with Gaussian Fit")
    plt.xlabel("Match Percentage (%)")
    plt.ylabel("Density")
    plt.grid(True, alpha=0.3)
    
    # Add vertical lines for key thresholds
    for pct in key_percentages:
        plt.axvline(x=pct, color='blue', linestyle='--', alpha=0.5)
        plt.text(pct, 0, f"{pct}%", ha='center', va='bottom', color='blue')
    
    # 4. Transformation Functions
    plt.subplot(3, 2, 4)
    x = np.linspace(0, 2, 100)
    y_original = [max(0, 100 - score * 50) for score in x]
    y_sigmoid = [JobValidator.score_to_percentage(score) for score in x]
    
    plt.plot(x, y_original, label="Original", color="green")
    plt.plot(x, y_sigmoid, label="Sigmoid", color="red")
    plt.xlabel("Raw Score")
    plt.ylabel("Match Percentage (%)")
    plt.title("Transformation Functions")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Add vertical lines for key thresholds
    for threshold, color in zip(thresholds, colors):
        plt.axvline(x=threshold, color=color, linestyle="--", alpha=0.5)
        plt.text(threshold, 10, f"{threshold}", ha="center", va="bottom", color=color)
    
    # 5. Scatter Plot: Raw vs. Transformed
    plt.subplot(3, 2, 5)
    plt.scatter(raw_scores, original_scores, alpha=0.5, label="Original", color="green")
    plt.scatter(raw_scores, sigmoid_scores, alpha=0.5, label="Sigmoid", color="red")
    plt.xlabel("Raw Score")
    plt.ylabel("Match Percentage (%)")
    plt.title("Raw vs. Transformed Scores")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 6. Cumulative Distribution
    plt.subplot(3, 2, 6)
    
    # Sort scores for CDF
    sorted_raw = np.sort(raw_scores)
    sorted_original = np.sort(original_scores)
    sorted_sigmoid = np.sort(sigmoid_scores)
    
    # Calculate CDFs
    cdf_raw = np.arange(1, len(sorted_raw) + 1) / len(sorted_raw)
    cdf_original = np.arange(1, len(sorted_original) + 1) / len(sorted_original)
    cdf_sigmoid = np.arange(1, len(sorted_sigmoid) + 1) / len(sorted_sigmoid)
    
    # Plot CDFs
    plt.plot(sorted_raw, cdf_raw, label="Raw", color="blue")
    plt.plot(sorted_original, cdf_original, label="Original", color="green")
    plt.plot(sorted_sigmoid, cdf_sigmoid, label="Sigmoid", color="red")
    plt.xlabel("Score Value")
    plt.ylabel("Cumulative Probability")
    plt.title("Cumulative Distribution Functions")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("score_distribution_visualization.png")
    print("Visualization saved as score_distribution_visualization.png")


def print_distribution_statistics(raw_scores, original_scores, sigmoid_scores):
    """Print statistics about the distributions."""
    print("\nDistribution Statistics:")
    print("=" * 60)
    print(f"{'Metric':<15} | {'Raw Scores':<15} | {'Original %':<15} | {'Sigmoid %':<15}")
    print("-" * 60)
    
    # Calculate statistics
    metrics = [
        ("Count", len(raw_scores), len(original_scores), len(sigmoid_scores)),
        ("Min", min(raw_scores), min(original_scores), min(sigmoid_scores)),
        ("Max", max(raw_scores), max(original_scores), max(sigmoid_scores)),
        ("Mean", np.mean(raw_scores), np.mean(original_scores), np.mean(sigmoid_scores)),
        ("Median", np.median(raw_scores), np.median(original_scores), np.median(sigmoid_scores)),
        ("Std Dev", np.std(raw_scores), np.std(original_scores), np.std(sigmoid_scores))
    ]
    
    # Print statistics
    for metric, raw, orig, sig in metrics:
        if metric == "Count":
            print(f"{metric:<15} | {raw:<15d} | {orig:<15d} | {sig:<15d}")
        else:
            print(f"{metric:<15} | {raw:<15.4f} | {orig:<15.4f} | {sig:<15.4f}")
    
    # Print percentiles
    print("\nPercentiles:")
    print("-" * 60)
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    
    for p in percentiles:
        raw_p = np.percentile(raw_scores, p)
        orig_p = np.percentile(original_scores, p)
        sig_p = np.percentile(sigmoid_scores, p)
        print(f"{p}th Percentile | {raw_p:<15.4f} | {orig_p:<15.4f} | {sig_p:<15.4f}")
    
    # Print threshold analysis
    print("\nThreshold Analysis:")
    print("-" * 60)
    
    # Calculate percentage of scores above thresholds
    thresholds = {
        "Excellent (>80%)": 80,
        "Good (60-80%)": 60,
        "Insufficient (<60%)": 0
    }
    
    for label, threshold in thresholds.items():
        orig_count = sum(1 for score in original_scores if score > threshold)
        sig_count = sum(1 for score in sigmoid_scores if score > threshold)
        
        orig_pct = orig_count / len(original_scores) * 100
        sig_pct = sig_count / len(sigmoid_scores) * 100
        
        print(f"{label:<20} | {'N/A':<15} | {orig_pct:<14.2f}% | {sig_pct:<14.2f}%")


def main():
    """Main function."""
    # Load raw scores
    raw_scores = load_raw_scores()
    if not raw_scores:
        print("No raw scores found. Run analyze_raw_scores.py first.")
        return
    
    # Apply transformations
    original_scores, sigmoid_scores = apply_transformations(raw_scores)
    
    # Create visualization
    visualize_distributions(raw_scores, original_scores, sigmoid_scores)
    
    # Print statistics
    print_distribution_statistics(raw_scores, original_scores, sigmoid_scores)
    
    # Print information about the updated sigmoid parameters
    print("\nUpdated Sigmoid Parameters:")
    print("=" * 60)
    print("The sigmoid function has been updated with new parameters:")
    print("- k = 13.0 (controls the slope of the curve)")
    print("- midpoint = 0.357 (center point of the transition)")
    print("\nWith these parameters:")
    print("- score = 0.0 → 99.04% (match eccellente)")
    print("- score = 0.1 → 96.58% (match eccellente)")
    print("- score = 0.25 → 80.08% (match eccellente)")
    print("- score = 0.3 → 67.72% (match buono)")
    print("- score = 0.4 → 36.38% (match insufficiente)")
    print("- score = 0.5 → 13.48% (match insufficiente)")
    print("\nThe midpoint parameter was adjusted to ensure that a raw score of 0.25")
    print("gives a matching percentage of 80%, as requested.")


if __name__ == "__main__":
    main()
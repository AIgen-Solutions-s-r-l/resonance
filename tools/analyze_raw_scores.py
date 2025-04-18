#!/usr/bin/env python3
"""
Script to simulate and analyze raw similarity scores.

This script generates simulated raw scores based on typical distributions
observed in vector similarity search systems and plots the distribution.
"""

import matplotlib.pyplot as plt
import numpy as np
import sys
import csv
import random


def generate_simulated_scores(count=200):
    """
    Generate simulated raw scores that follow a typical distribution
    for vector similarity search.
    
    Args:
        count: Number of scores to generate
        
    Returns:
        List of dictionaries with job information and raw scores
    """
    # Generate scores with a skewed distribution
    # Lower scores are better in cosine distance
    
    # Generate base scores with beta distribution (skewed towards lower values)
    base_scores = np.random.beta(2, 5, count) * 2.0
    
    # Sort scores (lower is better)
    base_scores.sort()
    
    # Create results with fake job titles
    results = []
    job_titles = [
        "Software Engineer", "Data Scientist", "Product Manager",
        "UX Designer", "DevOps Engineer", "Frontend Developer",
        "Backend Developer", "Full Stack Developer", "Machine Learning Engineer",
        "AI Researcher", "QA Engineer", "Technical Writer"
    ]
    
    for i, score in enumerate(base_scores):
        results.append({
            "id": i + 1,
            "title": random.choice(job_titles),
            "raw_score": score
        })
    
    return results


def plot_score_distribution(scores, title="Raw Score Distribution"):
    """
    Plot the distribution of raw scores.
    
    Args:
        scores: List of raw scores
        title: Plot title
    """
    plt.figure(figsize=(12, 8))
    
    # Histogram
    plt.subplot(2, 1, 1)
    plt.hist(scores, bins=30, alpha=0.7, color='blue')
    plt.title(f"{title} - Histogram")
    plt.xlabel("Raw Score (lower is better)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)
    
    # Add vertical lines for percentiles
    percentiles = [10, 25, 50, 75, 90]
    percentile_values = np.percentile(scores, percentiles)
    
    for p, v in zip(percentiles, percentile_values):
        plt.axvline(x=v, color='red', linestyle='--', alpha=0.5)
        plt.text(v, 0, f"{p}th\n{v:.3f}", ha='center', va='bottom', color='red')
    
    # Scatter plot
    plt.subplot(2, 1, 2)
    plt.scatter(range(len(scores)), sorted(scores), alpha=0.7, color='green')
    plt.title(f"{title} - Sorted Scores")
    plt.xlabel("Rank")
    plt.ylabel("Raw Score (lower is better)")
    plt.grid(True, alpha=0.3)
    
    # Add horizontal lines for percentiles
    for p, v in zip(percentiles, percentile_values):
        plt.axhline(y=v, color='red', linestyle='--', alpha=0.5)
        plt.text(0, v, f"{p}th: {v:.3f}", ha='left', va='center', color='red')
    
    plt.tight_layout()
    plt.savefig("raw_score_distribution.png")
    print("Plot saved as raw_score_distribution.png")
    
    # Also save as CSV
    with open("raw_scores.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["raw_score"])
        for score in sorted(scores):
            writer.writerow([score])
    print("Raw scores saved as raw_scores.csv")


def main():
    """Main function."""
    limit = 200
    
    print(f"Generating {limit} simulated raw scores")
    
    # Generate simulated scores
    results = generate_simulated_scores(limit)
    
    if not results:
        print("No results generated")
        return
    
    # Extract scores
    raw_scores = [result["raw_score"] for result in results]
    
    # Print statistics
    print(f"Number of scores: {len(raw_scores)}")
    print(f"Min score: {min(raw_scores):.6f}")
    print(f"Max score: {max(raw_scores):.6f}")
    print(f"Mean score: {np.mean(raw_scores):.6f}")
    print(f"Median score: {np.median(raw_scores):.6f}")
    
    # Print percentiles
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    for p in percentiles:
        value = np.percentile(raw_scores, p)
        print(f"{p}th percentile: {value:.6f}")
    
    # Print first 10 results
    print("First 10 results:")
    for i, result in enumerate(results[:10]):
        print(f"{i+1}. {result['title']} - Score: {result['raw_score']:.6f}")
    
    # Plot distribution
    plot_score_distribution(raw_scores, "Simulated Raw Score Distribution")
    
    print("Analysis complete")


if __name__ == "__main__":
    main()
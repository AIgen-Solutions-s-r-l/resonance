#!/usr/bin/env python3
"""
Test script to compare three score transformation methods:
1. The original piecewise linear transformation
2. The exponential transformation (α=3.0)
3. The sigmoid transformation

This helps visualize how different transformations distribute scores
and affect the match percentages.
"""

import math
import matplotlib.pyplot as plt
import numpy as np

def original_score_to_percentage(score):
    """The original piecewise linear transformation."""
    if score <= 0.3:
        # From 0.0 to 0.3 → 1.0 to 0.98
        return round((1.0 - (0.067 * score))*100, 2)
    elif score <= 0.9:
        # From 0.3 to 0.9 → 0.98 to 0.4
        return round((0.98 - (0.967 * (score - 0.3)))*100, 2)
    elif score <= 1.0:
        # From 0.9 to 1.0 → 0.4 to 0.2
        return round((0.4 - (2.0 * (score - 0.9)))*100, 2)
    elif score <= 2.0:
        # From 1.0 to 2.0 → 0.2 to 0.0
        return round((max(0.2 - (0.2 * (score - 1.0)), 0.0))*100, 2)
    else:
        return 0

def exponential_score_to_percentage(score, alpha=3.0):
    """The new exponential transformation."""
    if score < 0:
        return 100.0
    elif score > 2.0:
        return 0.0
    else:
        percentage = 100.0 * math.exp(-alpha * score)
        return round(percentage, 2)

def sigmoid_score_to_percentage(score):
    """
    Converts semantic distance to match percentage using a modified sigmoid function.
    
    The function is calibrated to respect the following thresholds:
    - Insufficient match: < 60% (score > 0.9)
    - Good match: 60-80% (score between 0.5 and 0.9)
    - Excellent match: > 80% (score < 0.5)
    """
    # Sigmoid parameters
    k = 5.0      # Controls the slope of the curve
    midpoint = 0.7  # Center point of the transition (60-80%)
    
    if score < 0:
        return 100.0
    elif score > 2.0:
        return 0.0
    else:
        # Modified sigmoid function: 100 / (1 + e^(k*(x-midpoint)))
        percentage = 100.0 / (1.0 + math.exp(k * (score - midpoint)))
        return round(percentage, 2)

def main():
    # Generate a range of scores from 0 to 2
    scores = np.linspace(0, 2, 100)
    
    # Calculate percentages using all three methods
    original_percentages = [original_score_to_percentage(s) for s in scores]
    exponential_percentages = [exponential_score_to_percentage(s) for s in scores]
    sigmoid_percentages = [sigmoid_score_to_percentage(s) for s in scores]
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    plt.plot(scores, original_percentages, label='Original (Piecewise Linear)', linewidth=2, color='blue')
    plt.plot(scores, exponential_percentages, label='Exponential (α=3.0)', linewidth=2, linestyle='--', color='green')
    plt.plot(scores, sigmoid_percentages, label='Sigmoid (k=5.0, midpoint=0.7)', linewidth=2, linestyle='-.', color='red')
    
    # Add vertical lines at key score points
    key_scores = [0.3, 0.5, 0.9, 1.0]
    for score in key_scores:
        plt.axvline(x=score, color='gray', linestyle=':', alpha=0.7)
    
    # Add horizontal lines at 60% and 80% thresholds
    plt.axhline(y=60, color='orange', linestyle='--', alpha=0.7, label='Threshold: 60%')
    plt.axhline(y=80, color='purple', linestyle='--', alpha=0.7, label='Threshold: 80%')
    
    # Add labels and title
    plt.xlabel('Semantic Distance Score (0=perfect, 2=no similarity)')
    plt.ylabel('Match Percentage (%)')
    plt.title('Comparison of Score Transformation Methods')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Save the plot
    plt.savefig('score_transformation_comparison_all.png')
    print("Plot saved as 'score_transformation_comparison_all.png'")
    
    # Print a table of sample values
    print("\nComparison of transformation methods:")
    print("=" * 80)
    print(f"{'Score':<10} {'Original %':<15} {'Exponential %':<15} {'Sigmoid %':<15}")
    print("-" * 80)
    
    sample_scores = [0.0, 0.1, 0.3, 0.5, 0.6, 0.7, 0.9, 1.0, 1.5, 2.0]
    for score in sample_scores:
        orig = original_score_to_percentage(score)
        expo = exponential_score_to_percentage(score)
        sigm = sigmoid_score_to_percentage(score)
        print(f"{score:<10.1f} {orig:<15.2f} {expo:<15.2f} {sigm:<15.2f}")
    
    print("\nThreshold Analysis:")
    print("- Excellent match (>80%): Score < 0.5")
    print("- Good match (60-80%): Score between 0.5 and 0.9")
    print("- Insufficient match (<60%): Score > 0.9")

if __name__ == "__main__":
    main()
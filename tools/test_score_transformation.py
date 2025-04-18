#!/usr/bin/env python3
"""
Test script to verify the sigmoid transformation function with the new parameters.

This script calculates the matching percentage for various raw scores to confirm
that the new parameters produce the expected results, particularly that a raw score
of 0.25 gives a matching percentage of 80%.
"""

import sys
import os
import math

# Add app directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the sigmoid transformation function
from app.libs.job_matcher.job_validator import JobValidator


def test_sigmoid_transformation():
    """Test the sigmoid transformation function with various raw scores."""
    print("Testing sigmoid transformation function with new parameters:")
    print("=" * 60)
    print(f"{'Raw Score':<10} | {'Match Percentage':<15} | {'Category':<15}")
    print("-" * 60)
    
    # Test various raw scores
    test_scores = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 0.9, 1.0, 1.5, 2.0]
    
    for score in test_scores:
        percentage = JobValidator.score_to_percentage(score)
        
        # Determine category
        if percentage >= 80:
            category = "Eccellente"
        elif percentage >= 60:
            category = "Buono"
        else:
            category = "Insufficiente"
        
        print(f"{score:<10.2f} | {percentage:<15.2f} | {category:<15}")


def calculate_midpoint_for_target(target_score, target_percentage, k=13.0):
    """
    Calculate the midpoint parameter needed to achieve a specific percentage at a given score.
    
    Args:
        target_score: The raw score at which we want to achieve the target percentage
        target_percentage: The desired percentage (0-100) at the target score
        k: The slope parameter of the sigmoid function
        
    Returns:
        float: The midpoint parameter value
    """
    # For the sigmoid function: percentage = 100.0 / (1.0 + math.exp(k * (score - midpoint)))
    # Solving for midpoint:
    # midpoint = target_score - ln((100/target_percentage) - 1) / k
    
    midpoint = target_score - math.log((100.0 / target_percentage) - 1.0) / k
    return midpoint


def main():
    """Main function."""
    # Test the sigmoid transformation
    test_sigmoid_transformation()
    
    print("\nCalculating midpoint parameters for different targets:")
    print("=" * 60)
    
    # Calculate midpoint for different target percentages at score 0.25
    targets = [60, 70, 75, 80, 85, 90]
    for target in targets:
        midpoint = calculate_midpoint_for_target(0.25, target)
        print(f"For {target}% at score 0.25: midpoint = {midpoint:.4f}")
    
    # Calculate midpoint for 80% at different scores
    scores = [0.2, 0.25, 0.3, 0.35, 0.4]
    print("\nCalculating midpoint for 80% at different scores:")
    print("=" * 60)
    for score in scores:
        midpoint = calculate_midpoint_for_target(score, 80)
        print(f"For 80% at score {score:.2f}: midpoint = {midpoint:.4f}")


if __name__ == "__main__":
    main()
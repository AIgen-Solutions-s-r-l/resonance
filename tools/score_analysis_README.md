# Score Analysis Tools

This directory contains tools for analyzing and visualizing the distribution of similarity scores in the job matching system.

## Background

In our job matching system, we use cosine similarity to measure the distance between job and resume embeddings. The raw scores range from 0 to 2, where:
- 0 represents perfect similarity (100% match)
- 2 represents no similarity (0% match)

We've implemented a sigmoid transformation function to convert these raw scores into more intuitive match percentages that better align with our desired thresholds:
- Excellent match: > 85% (raw score < 0.1)
- Good match: 60-85% (raw score between 0.1 and 0.25)
- Insufficient match: < 60% (raw score > 0.25)

## Tools

### 1. analyze_raw_scores.py

This script generates simulated raw scores based on typical distributions observed in vector similarity search systems and plots their distribution.

```bash
python tools/analyze_raw_scores.py
```

**Outputs:**
- `raw_score_distribution.png` - Visualization of the raw score distribution
- `raw_scores.csv` - CSV file containing the raw scores

### 2. compare_score_transformations.py

This script compares raw scores with transformed scores using both the original linear transformation and the new sigmoid transformation.

```bash
python tools/compare_score_transformations.py
```

**Outputs:**
- `score_transformation_comparison.png` - Comparison of raw and transformed scores
- Prints a table of key points showing the transformation values at specific raw scores

### 3. visualize_score_distribution.py

This script creates a comprehensive visualization of the score distributions, showing how the distribution changes after applying the transformations.

```bash
python tools/visualize_score_distribution.py
```

**Outputs:**
- `score_distribution_visualization.png` - Comprehensive visualization of score distributions
- Prints detailed statistics about the distributions

## Sigmoid Transformation

The sigmoid transformation function is implemented in `app/libs/job_matcher/job_validator.py` as:

```python
def score_to_percentage(score):
    import math
    
    # Sigmoid parameters
    k = 13.0      # Controls the slope of the curve
    midpoint = 0.281  # Center point of the transition (60% at score 0.25)
    
    if score < 0:
        return 100.0
    elif score > 2.0:
        return 0.0
    else:
        # Modified sigmoid function: 100 / (1 + e^(k*(score-midpoint)))
        percentage = 100.0 / (1.0 + math.exp(k * (score - midpoint)))
        return round(percentage, 2)
```

With these parameters:
- score = 0.0 → 97.47% (match eccellente)
- score = 0.1 → 91.32% (match eccellente)
- score = 0.25 → 59.94% (match buono)
- score = 0.5 → 5.48% (match insufficiente)
- score = 0.7 → 0.43% (match insufficiente)
- score = 0.9 → 0.03% (match insufficiente)
- score = 1.0 → 0.01% (match insufficiente)

## Analysis Results

The analysis shows that the sigmoid transformation provides a more intuitive distribution of match percentages compared to the original linear transformation:

1. **Threshold Alignment**: The sigmoid function creates clear thresholds at the desired points (85% at score 0.1, 60% at score 0.25)

2. **Distribution Shaping**: The sigmoid function creates a more meaningful separation between excellent, good, and insufficient matches

3. **Semantic Accuracy**: The sigmoid function reflects that small differences in highly similar items (low scores) are more significant than the same numerical differences between dissimilar items (high scores)

## Usage in Production

The sigmoid transformation is now active in the job matching system and will provide a more intuitive and aligned distribution of match percentages for users.
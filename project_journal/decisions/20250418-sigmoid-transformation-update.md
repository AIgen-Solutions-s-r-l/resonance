# Decision Record: Sigmoid Transformation Parameter Update

## Date
April 18, 2025

## Status
Accepted

## Context
The job matching system uses a sigmoid transformation function to convert raw similarity scores (0-2 range) into more intuitive match percentages (0-100% range). The original implementation was calibrated to provide:
- Excellent match: > 85% (raw score < 0.1)
- Good match: 60-85% (raw score between 0.1 and 0.25)
- Insufficient match: < 60% (raw score > 0.25)

With the original parameters (k=13.0, midpoint=0.281), a raw score of 0.25 resulted in approximately 60% match percentage, which was at the lower boundary of the "Good match" category.

A request was made to adjust the sigmoid function so that a raw score of 0.25 would result in an 80% match percentage instead of 60%, effectively making more jobs appear as better matches.

## Decision
We decided to update the sigmoid transformation function parameters to achieve the requested behavior. Specifically:

1. We kept the slope parameter (k) at 13.0 to maintain the general shape of the curve
2. We changed the midpoint parameter from 0.281 to 0.357 to ensure that a raw score of 0.25 results in an 80% match percentage

The updated sigmoid function now produces the following results:
- score = 0.0 → 99.04% (match eccellente)
- score = 0.1 → 96.58% (match eccellente)
- score = 0.25 → 80.08% (match eccellente)
- score = 0.3 → 67.72% (match buono)
- score = 0.4 → 36.38% (match insufficiente)
- score = 0.5 → 13.48% (match insufficiente)

This change effectively shifts the category thresholds:
- Excellent match: > 80% (raw score < 0.25)
- Good match: 60-80% (raw score between 0.25 and 0.3)
- Insufficient match: < 60% (raw score > 0.3)

## Consequences

### Positive
1. The system now meets the requirement of showing a raw score of 0.25 as an 80% match
2. More jobs will appear as "Excellent matches" to users, potentially increasing engagement
3. The transition between categories remains smooth and intuitive

### Negative
1. The change makes the system more lenient in its matching, which could lead to less relevant job matches being presented as high-quality matches
2. The "Good match" category is now narrower (raw scores between 0.25 and 0.3 instead of 0.1 and 0.25)
3. Historical match percentages will not be directly comparable to new ones without recalculation

### Neutral
1. The general shape of the sigmoid curve is preserved, maintaining the principle that small differences in highly similar items are more significant than the same numerical differences between dissimilar items
2. The implementation change is minimal, requiring only an update to a single parameter

## Implementation
The change was implemented by updating the midpoint parameter in the `score_to_percentage` method in `app/libs/job_matcher/job_validator.py`. The updated code was tested using the score analysis tools to verify the correct behavior.

## Related Documents
- [Score Analysis README](../../tools/score_analysis_README.md)
- [Test Score Transformation Script](../../tools/test_score_transformation.py)
- [Score Distribution Visualization](../../score_distribution_visualization.png)
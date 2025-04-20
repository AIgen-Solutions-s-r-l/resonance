# Decision Record: Sigmoid Transformation Parameter Update

## Date
April 18, 2025 (Updated April 20, 2025)

## Status
Accepted

## Context
The job matching system uses a sigmoid transformation function to convert raw similarity scores (0-2 range) into more intuitive match percentages (0-100% range). The original implementation was calibrated to provide:
- Excellent match: > 85% (raw score < 0.1)
- Good match: 60-85% (raw score between 0.1 and 0.25)
- Insufficient match: < 60% (raw score > 0.25)

With the original parameters (k=13.0, midpoint=0.281), a raw score of 0.25 resulted in approximately 60% match percentage, which was at the lower boundary of the "Good match" category.

A request was made to adjust the sigmoid function so that a raw score of 0.25 would result in an 80% match percentage instead of 60%, effectively making more jobs appear as better matches.

**Update (April 20, 2025)**: An additional request was made to further refine the sigmoid function to ensure that a raw score of 0.20 results in a 90% match percentage, and all scores below 0.20 have greater than 90% matching.

## Decision
We decided to update the sigmoid transformation function parameters to achieve the requested behavior. Specifically:

1. We kept the slope parameter (k) at 13.0 to maintain the general shape of the curve
2. We initially changed the midpoint parameter from 0.281 to 0.357 to ensure that a raw score of 0.25 results in an 80% match percentage
3. **Update (April 20, 2025)**: We further adjusted the midpoint parameter to 0.369 to ensure that a raw score of 0.20 results in a 90% match percentage while maintaining a high match percentage (~82%) at a raw score of 0.25

The updated sigmoid function now produces the following results:
- score = 0.0 → 99.18% (match eccellente)
- score = 0.1 → 97.06% (match eccellente)
- score = 0.2 → 90.00% (match eccellente)
- score = 0.25 → 82.45% (match eccellente)
- score = 0.3 → 71.03% (match buono)
- score = 0.4 → 40.06% (match insufficiente)
- score = 0.5 → 15.41% (match insufficiente)

This change effectively shifts the category thresholds:
- Excellent match: > 80% (raw score < 0.25)
- Good match: 60-80% (raw score between 0.25 and 0.3)
- Insufficient match: < 60% (raw score > 0.3)

With the additional refinement, we now ensure that:
- Scores of 0.20 get exactly 90% matching
- All scores below 0.20 get >90% matching
- Scores of 0.25 get ~82% matching (slightly higher than the original 80% target)

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

**Update (April 20, 2025)**: The midpoint parameter was further adjusted from 0.357 to 0.369 to meet the additional requirements. The change was tested using the `test_score_transformation.py` script, which confirmed that the new parameters produce the desired matching percentages.

## Related Documents
- [Score Analysis README](../../tools/score_analysis_README.md)
- [Test Score Transformation Script](../../tools/test_score_transformation.py)
- [Score Distribution Visualization](../../score_distribution_visualization.png)
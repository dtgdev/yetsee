from __future__ import annotations

from dataclasses import dataclass


PRIOR_STRENGTH = 4.0


@dataclass(frozen=True)
class ConfidenceComputation:
    prior: float
    supporting_weight: float
    contradicting_weight: float
    neutral_weight: float
    posterior: float


def calculate_confidence(
    *,
    prior: float,
    supporting_weight: float,
    contradicting_weight: float,
    neutral_weight: float = 0.0,
    prior_strength: float = PRIOR_STRENGTH,
) -> ConfidenceComputation:
    """Deterministic weighted Beta-style confidence update.

    The original hypothesis confidence is treated as the prior mean. Supporting
    and contradicting evidence add weighted pseudo-observations. Neutral evidence
    is preserved for audit/coverage but intentionally does not move confidence.
    """
    prior = max(0.001, min(0.999, float(prior)))
    supporting_weight = max(0.0, float(supporting_weight))
    contradicting_weight = max(0.0, float(contradicting_weight))
    neutral_weight = max(0.0, float(neutral_weight))
    prior_strength = max(0.001, float(prior_strength))

    alpha = prior * prior_strength + supporting_weight
    beta = (1.0 - prior) * prior_strength + contradicting_weight
    posterior = alpha / (alpha + beta)
    return ConfidenceComputation(
        prior=prior,
        supporting_weight=supporting_weight,
        contradicting_weight=contradicting_weight,
        neutral_weight=neutral_weight,
        posterior=max(0.0, min(1.0, posterior)),
    )

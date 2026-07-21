"""
TradeSense AI Decision Engine

Combines:
- Rule-based trading signals
- ML prediction
- Confidence score

Returns a detailed decision report.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List


@dataclass
class DecisionReport:
    recommendation: str
    risk: str
    agreement: bool
    score: int
    reasons: List[str]


class Recommendation(str, Enum):
    STRONG_BUY = "STRONG BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG SELL"
    WAIT = "WAIT"


def get_recommendation(rule_signal: str,
                       ml_prediction: int,
                       confidence: float) -> DecisionReport:
    """
    Combines Rule Engine + ML prediction.

    Parameters
    ----------
    rule_signal : BUY / SELL / NEUTRAL
    ml_prediction : 1 (UP), 0 (DOWN)
    confidence : Probability (0-100)

    Returns
    -------
    DecisionReport
    """

    bullish = ml_prediction == 1

    if rule_signal == "BUY":
        agreement = bullish

    elif rule_signal == "SELL":
        agreement = not bullish

    else:
        agreement = None

    reasons = []

    score = 50

    # ----------------------------
    # Rule Engine Reason
    # ----------------------------

    if rule_signal == "BUY":
        reasons.append("Rule engine generated BUY signal")

    elif rule_signal == "SELL":
        reasons.append("Rule engine generated SELL signal")

    else:
        reasons.append("Rule engine is NEUTRAL")

    # ----------------------------
    # ML Reason
    # ----------------------------

    if bullish:
        reasons.append("AI predicts upward movement")
    else:
        reasons.append("AI predicts downward movement")

    # ----------------------------
    # Confidence
    # ----------------------------

    if confidence >= 85:
        reasons.append("High confidence prediction")
        score += 30

    elif confidence >= 70:
        reasons.append("Moderate confidence prediction")
        score += 20

    else:
        reasons.append("Low confidence prediction")

    # ----------------------------
    # Agreement
    # ----------------------------

    if agreement is True:
        reasons.append("Rule engine and AI agree")
        score += 20

    elif agreement is False:
        reasons.append("Rule engine and AI disagree")
        score -= 20

    else:
        reasons.append("Rule engine is neutral")

    score = max(0, min(score, 100))

    # ----------------------------
    # Risk
    # ----------------------------

    if confidence >= 85 and agreement is True:
        risk = "LOW"

    elif confidence >= 70:
        risk = "MEDIUM"

    else:
        risk = "HIGH"

    # ----------------------------
    # Recommendation
    # ----------------------------

    if rule_signal == "BUY":

        if bullish:

            if confidence >= 85:
                recommendation = Recommendation.STRONG_BUY

            elif confidence >= 70:
                recommendation = Recommendation.BUY

            else:
                recommendation = Recommendation.HOLD

        else:
            recommendation = Recommendation.WAIT

    elif rule_signal == "SELL":

        if not bullish:

            if confidence >= 85:
                recommendation = Recommendation.STRONG_SELL

            elif confidence >= 70:
                recommendation = Recommendation.SELL

            else:
                recommendation = Recommendation.HOLD

        else:
            recommendation = Recommendation.WAIT

    else:

        if bullish:

            if confidence >= 90:
                recommendation = Recommendation.BUY
            else:
                recommendation = Recommendation.HOLD

        else:

            if confidence >= 90:
                recommendation = Recommendation.SELL
            else:
                recommendation = Recommendation.HOLD

    return DecisionReport(
        recommendation=recommendation.value,
        risk=risk,
        agreement=agreement,
        score=score,
        reasons=reasons
    )
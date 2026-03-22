from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouterThresholds:
    proceed_min_confidence: float = 0.85
    revise_min_confidence: float = 0.45


def route_decision(decision_record: dict[str, object], thresholds: RouterThresholds | None = None) -> str:
    active_thresholds = thresholds or RouterThresholds()
    decision = str(decision_record["decision"])
    confidence = float(decision_record["confidence"])
    required_human_review = bool(decision_record["required_human_review"])

    if decision == "stop" or confidence < active_thresholds.revise_min_confidence or required_human_review:
        return "stop"
    if decision == "revise" or confidence < active_thresholds.proceed_min_confidence:
        return "revise"
    return "proceed"

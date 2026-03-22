from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agent_chappie.validation import validate_job_result, validate_system_observation


@dataclass
class SourcePackage:
    project_id: str
    source_kind: str
    project_summary: str
    raw_text: str
    source_ref: str
    competitor: str | None = None
    region: str | None = None


SIGNAL_RULES: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("pricing_change", ("price", "pricing", "fee", "fees", "raised pricing", "discount", "voucher"), "high", "high"),
    ("opening", ("open", "opening", "launch", "new school", "new academy"), "medium", "high"),
    ("closure", ("close", "closure", "shut down", "for sale", "sale of school"), "high", "high"),
    ("staffing", ("coach", "staff", "hiring", "academy director"), "low", "medium"),
    ("offer", ("offer", "trial", "scholarship", "discount", "voucher", "free onboarding"), "medium", "high"),
    ("asset_sale", ("equipment sale", "sell equipment", "clearance", "liquidation", "sell-off"), "medium", "medium"),
    ("messaging_shift", ("testimonial", "testimonials", "customer logos", "above the fold", "no engineering required"), "medium", "high"),
    ("proof_signal", ("testimonial", "customer logos", "logos", "case study", "social proof"), "low", "medium"),
    ("vendor_adoption", ("sport-tech", "sports tech", "tracking", "gps", "video analysis", "platform"), "medium", "medium"),
)


def extract_observations(source: SourcePackage, observed_at: str | None = None) -> list[dict[str, Any]]:
    text = source.raw_text.strip()
    if not text:
        return []

    normalized = text.lower()
    competitor = source.competitor or infer_competitor(source.project_summary, text)
    region = source.region or infer_region(source.project_summary, text)
    timestamp = observed_at or utc_now_iso()
    observations: list[dict[str, Any]] = []

    for signal_type, keywords, impact, confidence_band in SIGNAL_RULES:
        if any(keyword in normalized for keyword in keywords):
            summary = build_summary(signal_type, text)
            observation = {
                "signal_id": build_signal_id(source.project_id, signal_type, competitor, summary, source.source_ref),
                "signal_type": signal_type,
                "competitor": competitor,
                "region": region,
                "summary": summary,
                "source_ref": source.source_ref,
                "observed_at": timestamp,
                "confidence": band_to_confidence(confidence_band),
                "business_impact": impact,
            }
            observations.append(validate_system_observation(observation))

    if not observations:
        observation = {
            "signal_id": build_signal_id(source.project_id, "messaging_shift", competitor, text[:120], source.source_ref),
            "signal_type": "messaging_shift",
            "competitor": competitor,
            "region": region,
            "summary": summarize_text(text),
            "source_ref": source.source_ref,
            "observed_at": timestamp,
            "confidence": 0.42,
            "business_impact": "low",
        }
        observations.append(validate_system_observation(observation))

    return observations


def generate_recommended_tasks(
    source: SourcePackage,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    scored = []
    for observation in observations:
        task = observation_to_task(observation)
        score = score_observation(observation)
        if task and score >= 7:
            scored.append((score, task))

    scored.sort(key=lambda item: item[0], reverse=True)
    tasks = []
    for index, (_, task) in enumerate(scored[:3], start=1):
        task["rank"] = index
        tasks.append(task)

    if not tasks:
        return validate_job_result(
            {
                "job_id": "placeholder",
                "app_id": "placeholder",
                "project_id": source.project_id,
                "status": "blocked",
                "completed_at": utc_now_iso(),
                "result_payload": {
                    "reason": "No strong competitive action was supported by the supplied evidence.",
                },
            }
        )["result_payload"]

    return {
        "recommended_tasks": tasks,
        "summary": "Three competitive actions were prioritized from current source input and stored market observations."
        if len(tasks) == 3
        else "High-confidence competitive actions were prioritized from current source input and stored market observations.",
    }


def observation_to_task(observation: dict[str, Any]) -> dict[str, Any] | None:
    signal_type = observation["signal_type"]
    evidence = [observation["signal_id"]]
    competitor = observation["competitor"]
    summary = observation["summary"]

    if signal_type == "pricing_change":
        return {
            "rank": 0,
            "title": f"Adjust academy pricing and offer positioning against {competitor}",
            "why_now": f"Pricing movement was detected for {competitor}: {summary}",
            "expected_advantage": "Protects enrollment and reduces parent switching risk caused by competitor price pressure.",
            "evidence_refs": evidence,
        }
    if signal_type == "closure":
        return {
            "rank": 0,
            "title": f"Investigate whether {competitor} is available for acquisition or player transfer capture",
            "why_now": f"Closure or distress signals were detected for {competitor}: {summary}",
            "expected_advantage": "Creates a faster path to growth through acquisition, player capture, or facility access.",
            "evidence_refs": evidence,
        }
    if signal_type == "asset_sale":
        return {
            "rank": 0,
            "title": "Check for discounted equipment or infrastructure purchase opportunities",
            "why_now": f"An asset-sale signal was detected: {summary}",
            "expected_advantage": "Improves margin and frees budget for coaching quality or promotion.",
            "evidence_refs": evidence,
        }
    if signal_type == "opening":
        return {
            "rank": 0,
            "title": f"Review local catchment messaging before {competitor} expands in the region",
            "why_now": f"A local opening or expansion signal was detected: {summary}",
            "expected_advantage": "Helps defend territory and pre-empt competitor momentum before the next intake cycle.",
            "evidence_refs": evidence,
        }
    if signal_type in {"offer", "proof_signal", "messaging_shift"}:
        return {
            "rank": 0,
            "title": f"Strengthen proof and onboarding messaging against {competitor}",
            "why_now": f"A competitor positioning signal was detected: {summary}",
            "expected_advantage": "Improves conversion and reduces hesitation around ease of joining your academy.",
            "evidence_refs": evidence,
        }
    if signal_type == "vendor_adoption":
        return {
            "rank": 0,
            "title": "Evaluate the new sport-tech signal for a fast competitive advantage test",
            "why_now": f"A sport-tech adoption signal was detected: {summary}",
            "expected_advantage": "Helps the academy adopt tools that improve development quality or parent trust before rivals do.",
            "evidence_refs": evidence,
        }
    return None


def score_observation(observation: dict[str, Any]) -> int:
    impact_score = {"low": 1, "medium": 2, "high": 3}[observation["business_impact"]]
    confidence_score = int(round(observation["confidence"] * 3))
    urgency_bonus = 3 if observation["signal_type"] in {"pricing_change", "closure", "offer"} else 1
    leverage_bonus = 3 if observation["signal_type"] in {"pricing_change", "closure", "asset_sale"} else 2
    return impact_score + confidence_score + urgency_bonus + leverage_bonus


def deduplicate_observations(
    incoming: list[dict[str, Any]],
    existing: list[dict[str, Any]],
    recent_window_hours: int = 168,
) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    cutoff = datetime.now(UTC).timestamp() - recent_window_hours * 3600

    for candidate in incoming:
        normalized_candidate = normalize_summary(candidate["summary"])
        duplicate = False
        for stored in existing:
            if stored["competitor"] != candidate["competitor"]:
                continue
            if stored["signal_type"] != candidate["signal_type"]:
                continue
            observed_at = datetime.fromisoformat(stored["observed_at"].replace("Z", "+00:00")).timestamp()
            if observed_at < cutoff:
                continue
            overlap = token_overlap(normalized_candidate, normalize_summary(stored["summary"]))
            if overlap >= 0.7:
                duplicate = True
                break
        if not duplicate:
            deduped.append(candidate)
    return deduped


def build_signal_id(project_id: str, signal_type: str, competitor: str, summary: str, source_ref: str) -> str:
    digest = hashlib.sha1(f"{project_id}|{signal_type}|{competitor}|{summary}|{source_ref}".encode("utf-8")).hexdigest()[:12]
    return f"sig_{digest}"


def build_source_hash(source: SourcePackage) -> str:
    digest = hashlib.sha1(
        (
            f"{source.project_id}|{source.source_kind}|{source.project_summary}|"
            f"{source.raw_text}|{source.source_ref}|{source.competitor}|{source.region}"
        ).encode("utf-8")
    ).hexdigest()
    return digest


def infer_competitor(project_summary: str, raw_text: str) -> str:
    for text in (raw_text, project_summary):
        matches = re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,2}\b", text)
        for match in matches:
            if match.lower() not in {"The", "Our", "Current", "Sales", "Context"}:
                return match
    return "regional_competitor_unknown"


def infer_region(project_summary: str, raw_text: str) -> str:
    match = re.search(r"\b(region|county|city|area)\s*[:\-]?\s*([A-Za-z0-9\s]+)", f"{project_summary}\n{raw_text}", re.IGNORECASE)
    if match:
        return match.group(2).strip().lower().replace(" ", "_")
    return "region_unknown"


def build_summary(signal_type: str, raw_text: str) -> str:
    prefix = signal_type.replace("_", " ")
    return f"{prefix}: {summarize_text(raw_text)}"


def summarize_text(raw_text: str) -> str:
    text = " ".join(raw_text.strip().split())
    return text[:180]


def normalize_summary(summary: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", summary.lower()))


def token_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    return intersection / union


def band_to_confidence(band: str) -> float:
    return {"high": 0.84, "medium": 0.67}.get(band, 0.48)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")

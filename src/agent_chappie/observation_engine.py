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


@dataclass
class TaskCandidate:
    task: dict[str, Any]
    total_score: int
    competitive_relevance: int
    urgency: int
    actionability_this_week: int
    strategic_leverage: int
    evidence_strength: int


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
    seen_keys: set[tuple[str, str]] = set()
    clauses = extract_clauses(text)

    for signal_type, keywords, impact, confidence_band in SIGNAL_RULES:
        matching_clause = first_matching_clause(clauses, keywords)
        if matching_clause:
            summary = build_summary(signal_type, matching_clause)
            dedupe_key = (signal_type, summary.lower())
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
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
    scored: list[TaskCandidate] = []
    for observation in observations:
        candidate = observation_to_task(source, observation)
        if candidate and candidate.total_score >= 15:
            scored.append(candidate)

    scored.sort(key=lambda item: item.total_score, reverse=True)
    tasks = []
    for index, candidate in enumerate(scored[:3], start=1):
        task = dict(candidate.task)
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


def observation_to_task(source: SourcePackage, observation: dict[str, Any]) -> TaskCandidate | None:
    signal_type = observation["signal_type"]
    evidence = [observation["signal_id"]]
    competitor = observation["competitor"]
    summary = observation["summary"]
    region = humanize_region(observation["region"])
    domain = infer_domain(source)
    signal_phrase = extract_signal_phrase(summary)

    task: dict[str, Any] | None = None

    if signal_type == "pricing_change":
        task = {
            "rank": 0,
            "title": f"Publish a 7-day comparison offer and update the pricing page against {competitor}'s latest fee change",
            "why_now": f"{competitor} changed pricing in {region}: {signal_phrase}. Launching a visible counter-offer this week addresses the exact comparison parents or buyers are making right now.",
            "expected_advantage": measurable_advantage(domain, "pricing"),
            "evidence_refs": evidence,
        }
    elif signal_type == "closure":
        task = {
            "rank": 0,
            "title": f"Contact {competitor}'s owner this week about acquiring released customers, staff, or equipment",
            "why_now": f"{competitor} is showing a closure or distress signal in {region}: {signal_phrase}. Direct outreach this week is time-sensitive before another operator captures the same assets.",
            "expected_advantage": measurable_advantage(domain, "acquisition"),
            "evidence_refs": evidence,
        }
    elif signal_type == "asset_sale":
        task = {
            "rank": 0,
            "title": "Request the asset list and place a bid on discounted equipment before the sell-off closes",
            "why_now": f"An asset-sale signal was detected in {region}: {signal_phrase}. Acting this week turns a competitor event into a fast cost-saving move instead of a missed bargain.",
            "expected_advantage": measurable_advantage(domain, "cost"),
            "evidence_refs": evidence,
        }
    elif signal_type == "opening":
        task = {
            "rank": 0,
            "title": f"Send a local comparison campaign before {competitor} opens in {region}",
            "why_now": f"{competitor} is signaling an opening or expansion in {region}: {signal_phrase}. A local comparison push this week helps lock in prospects before the new option gains momentum.",
            "expected_advantage": measurable_advantage(domain, "conversion"),
            "evidence_refs": evidence,
        }
    elif signal_type in {"offer", "proof_signal", "messaging_shift"}:
        task = {
            "rank": 0,
            "title": f"Rewrite the homepage hero and sales script this week to answer {competitor}'s latest claim",
            "why_now": f"{competitor} changed customer-facing messaging in {region}: {signal_phrase}. Rewriting the first impression now prevents the competitor narrative from owning the buying conversation.",
            "expected_advantage": measurable_advantage(domain, "positioning"),
            "evidence_refs": evidence,
        }
    elif signal_type == "vendor_adoption":
        task = {
            "rank": 0,
            "title": "Run a 7-day pilot of the surfaced sport-tech tool and decide buy-or-skip by Friday",
            "why_now": f"A vendor-adoption signal appeared in {region}: {signal_phrase}. A short pilot this week is enough to test whether the tool creates a real execution edge before competitors normalize it.",
            "expected_advantage": measurable_advantage(domain, "retention"),
            "evidence_refs": evidence,
        }
    if not task:
        return None

    scores = score_task_candidate(observation, task)
    return TaskCandidate(task=task, **scores)


def score_task_candidate(observation: dict[str, Any], task: dict[str, Any]) -> dict[str, int]:
    competitive_relevance = 5 if observation["signal_type"] in {"pricing_change", "closure", "offer", "asset_sale"} else 4
    urgency = 5 if observation["signal_type"] in {"pricing_change", "closure", "asset_sale"} else 3
    actionability_this_week = 5 if contains_week_specific_action(task["title"]) else 2
    strategic_leverage = 5 if observation["business_impact"] == "high" else 3 if observation["business_impact"] == "medium" else 2
    evidence_strength = max(2, min(5, int(round(observation["confidence"] * 5))))
    total_score = competitive_relevance + urgency + actionability_this_week + strategic_leverage + evidence_strength
    return {
        "total_score": total_score,
        "competitive_relevance": competitive_relevance,
        "urgency": urgency,
        "actionability_this_week": actionability_this_week,
        "strategic_leverage": strategic_leverage,
        "evidence_strength": evidence_strength,
    }


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


def extract_clauses(raw_text: str) -> list[str]:
    chunks = re.split(r"[.!?;\n]+", raw_text)
    clauses: list[str] = []
    for chunk in chunks:
        parts = re.split(r",|\band\b|\bbut\b", chunk, flags=re.IGNORECASE)
        for part in parts:
            cleaned = " ".join(part.strip().split())
            if cleaned:
                clauses.append(cleaned)
    return clauses


def first_matching_clause(clauses: list[str], keywords: tuple[str, ...]) -> str | None:
    for clause in clauses:
        normalized = clause.lower()
        if any(keyword in normalized for keyword in keywords):
            return clause
    return None


def humanize_region(region: str) -> str:
    return region.replace("_", " ")


def extract_signal_phrase(summary: str) -> str:
    if ":" in summary:
        return summary.split(":", 1)[1].strip()
    return summary


def infer_domain(source: SourcePackage) -> str:
    text = f"{source.project_summary} {source.raw_text}".lower()
    if any(term in text for term in {"academy", "soccer", "football school", "sport school", "parents", "players"}):
        return "academy"
    return "general"


def measurable_advantage(domain: str, advantage_type: str) -> str:
    academy_advantages = {
        "pricing": "Protects enrollment and improves intake conversion before the next sign-up cycle.",
        "acquisition": "Increases player capacity, local revenue, or facility access faster than organic growth.",
        "cost": "Reduces equipment cost this month and protects operating margin for coaching or promotion.",
        "conversion": "Improves inquiry-to-enrollment conversion before prospects compare the new entrant.",
        "positioning": "Improves parent conversion and reduces onboarding or proof objections in active conversations.",
        "retention": "Improves player-development quality or parent retention without waiting for a long rollout.",
    }
    general_advantages = {
        "pricing": "Protects revenue and conversion against a competitor price move in the current buying cycle.",
        "acquisition": "Creates a faster growth path through acquired customers, assets, or operating capacity.",
        "cost": "Reduces near-term operating cost and frees budget for higher-leverage growth moves.",
        "conversion": "Improves conversion before the competitor gains traction with the same audience.",
        "positioning": "Improves win rate by countering the competitor narrative with a stronger market-facing response.",
        "retention": "Improves delivery or retention fast enough to matter in the current decision window.",
    }
    lookup = academy_advantages if domain == "academy" else general_advantages
    return lookup[advantage_type]


def contains_week_specific_action(title: str) -> bool:
    normalized = title.lower()
    return any(
        phrase in normalized
        for phrase in (
            "7-day",
            "this week",
            "before",
            "by friday",
            "place a bid",
            "publish",
            "contact",
            "rewrite",
            "request",
            "send",
            "run a 7-day pilot",
        )
    )


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

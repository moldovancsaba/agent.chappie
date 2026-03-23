from __future__ import annotations

import hashlib
import re
import urllib.parse
import urllib.request
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
    ("opening", ("open", "opening", "opened", "new school", "new academy"), "medium", "high"),
    ("closure", ("close", "closure", "shut down", "for sale", "sale of school"), "high", "high"),
    ("staffing", ("coach", "staff", "hiring", "academy director"), "low", "medium"),
    ("offer", ("offer", "trial", "scholarship", "discount", "voucher", "free onboarding"), "medium", "high"),
    ("asset_sale", ("equipment sale", "sell equipment", "clearance", "liquidation", "sell-off"), "medium", "medium"),
    ("messaging_shift", ("testimonial", "testimonials", "customer logos", "above the fold", "no engineering required"), "medium", "high"),
    ("proof_signal", ("testimonial", "customer logos", "logos", "case study", "social proof"), "low", "medium"),
    ("vendor_adoption", ("sport-tech", "sports tech", "tracking", "gps", "video analysis", "platform"), "medium", "medium"),
)
SIGNAL_KEYWORDS = tuple({keyword for _, keywords, _, _ in SIGNAL_RULES for keyword in keywords})
URL_MIN_CONTENT_CHARS = 280
GENERIC_ENTITY_WORDS = {
    "The",
    "Our",
    "Current",
    "Sales",
    "Context",
    "Source",
    "URL",
    "Host",
    "Fetched",
    "Title",
    "Content",
    "Map",
    "Home",
    "Page",
}
REGION_TERMS = ("cluster", "region", "county", "city", "area", "district", "zone")


def extract_observations(source: SourcePackage, observed_at: str | None = None) -> list[dict[str, Any]]:
    text = source.raw_text.strip()
    if not text:
        return []

    if source.source_kind == "url" and not passes_url_signal_quality(text):
        return []

    inferred_context = infer_context(text, source.project_summary)
    competitor = source.competitor or inferred_context["competitor"] or "regional_competitor_unknown"
    region = source.region or inferred_context["region"] or "region_unknown"
    timestamp = observed_at or utc_now_iso()
    observations: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    clauses = extract_clauses(text)

    for signal_type, keywords, impact, confidence_band in SIGNAL_RULES:
        for clause in matching_clauses(clauses, keywords):
            clause_context = infer_context(clause, source.project_summary)
            clause_competitor = source.competitor or clause_context["competitor"] or competitor
            clause_region = source.region or clause_context["region"] or region
            summary = build_summary(signal_type, clause)
            dedupe_key = (signal_type, clause_competitor.lower(), summary.lower())
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            observation = {
                "signal_id": build_signal_id(source.project_id, signal_type, clause_competitor, summary, source.source_ref),
                "signal_type": signal_type,
                "competitor": clause_competitor,
                "region": clause_region,
                "summary": summary,
                "source_ref": source.source_ref,
                "observed_at": timestamp,
                "confidence": max(band_to_confidence(confidence_band), float(clause_context["confidence"])),
                "business_impact": impact,
            }
            observations.append(validate_system_observation(observation))

    return observations


def generate_recommended_tasks(
    source: SourcePackage,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    scored_by_title: dict[str, TaskCandidate] = {}
    for candidate in build_task_candidates(source, observations):
        if candidate and candidate.total_score >= 15:
            if not passes_task_quality_gate(candidate.task):
                continue
            key = normalize_task_title(candidate.task["title"])
            existing = scored_by_title.get(key)
            if existing is None or candidate.total_score > existing.total_score:
                scored_by_title[key] = candidate

    scored = list(scored_by_title.values())
    scored.sort(key=lambda item: item.total_score, reverse=True)
    tasks = []
    for index, candidate in enumerate(scored[:3], start=1):
        task = dict(candidate.task)
        task["rank"] = index
        tasks.append(task)

    if len(tasks) < 3:
        return validate_job_result(
            {
                "job_id": "placeholder",
                "app_id": "placeholder",
                "project_id": source.project_id,
                "status": "blocked",
                "completed_at": utc_now_iso(),
                "result_payload": {
                    "reason": "insufficient_signal_quality"
                    if source.source_kind == "url"
                    else "The worker could not derive three distinct, high-confidence actions from the supplied evidence.",
                },
            }
        )["result_payload"]

    return {
        "recommended_tasks": tasks,
        "summary": "Three competitive actions were prioritized from current source input and stored market observations."
        if len(tasks) == 3
        else "High-confidence competitive actions were prioritized from current source input and stored market observations.",
    }


def build_task_candidates(source: SourcePackage, observations: list[dict[str, Any]]) -> list[TaskCandidate]:
    candidates: list[TaskCandidate] = []
    candidates.extend(build_multi_signal_candidates(source, observations))
    for observation in observations:
        candidate = observation_to_task(source, observation)
        if candidate:
            candidates.append(candidate)
    return candidates


def build_multi_signal_candidates(source: SourcePackage, observations: list[dict[str, Any]]) -> list[TaskCandidate]:
    candidates: list[TaskCandidate] = []
    pricing_observations = [obs for obs in observations if obs["signal_type"] == "pricing_change"]
    offer_observations = [obs for obs in observations if obs["signal_type"] == "offer"]
    closure_observations = [obs for obs in observations if obs["signal_type"] == "closure"]
    asset_sale_observations = [obs for obs in observations if obs["signal_type"] == "asset_sale"]
    proof_observations = [obs for obs in observations if obs["signal_type"] in {"proof_signal", "messaging_shift"}]

    if pricing_observations and offer_observations:
        pricing = pricing_observations[0]
        offer = next(
            (
                candidate
                for candidate in offer_observations
                if candidate["region"] == pricing["region"] and candidate["competitor"] != pricing["competitor"]
            ),
            offer_observations[0],
        )
        candidates.append(build_pricing_offer_candidate(source, pricing, offer))

    if closure_observations and asset_sale_observations:
        closure = closure_observations[0]
        asset = next(
            (
                candidate
                for candidate in asset_sale_observations
                if candidate["region"] == closure["region"] or candidate["competitor"] == closure["competitor"]
            ),
            asset_sale_observations[0],
        )
        candidates.append(build_closure_asset_candidate(source, closure, asset))

    if proof_observations and offer_observations:
        proof = proof_observations[0]
        offer = next(
            (
                candidate
                for candidate in offer_observations
                if candidate["competitor"] == proof["competitor"] or candidate["region"] == proof["region"]
            ),
            offer_observations[0],
        )
        candidates.append(build_positioning_bundle_candidate(source, proof, offer))

    return candidates


def observation_to_task(source: SourcePackage, observation: dict[str, Any]) -> TaskCandidate | None:
    signal_type = observation["signal_type"]
    evidence = [observation["signal_id"]]
    competitor = observation["competitor"]
    summary = observation["summary"]
    region = humanize_region(observation["region"])
    domain = infer_domain(source)
    signal_phrase = extract_signal_phrase(summary)
    detail = extract_action_detail(signal_phrase)

    task: dict[str, Any] | None = None

    if signal_type == "pricing_change":
        task = {
            "rank": 0,
            "title": build_pricing_task_title(competitor, detail, domain),
            "why_now": f"{competitor} changed pricing in {region}: {signal_phrase}. Matching the move with a concrete offer this week gives buyers a direct alternative before the next comparison cycle closes.",
            "expected_advantage": measurable_advantage(domain, "pricing"),
            "evidence_refs": evidence,
        }
    elif signal_type == "closure":
        task = {
            "rank": 0,
            "title": build_closure_task_title(competitor, detail),
            "why_now": f"{competitor} is showing a closure or distress signal in {region}: {signal_phrase}. Direct outreach this week is time-sensitive before another operator captures the same families, staff, or assets.",
            "expected_advantage": measurable_advantage(domain, "acquisition"),
            "evidence_refs": evidence,
        }
    elif signal_type == "asset_sale":
        task = {
            "rank": 0,
            "title": build_asset_sale_task_title(detail),
            "why_now": f"An asset-sale signal was detected in {region}: {signal_phrase}. Acting this week turns a competitor event into a fast cost-saving move instead of a missed bargain.",
            "expected_advantage": measurable_advantage(domain, "cost"),
            "evidence_refs": evidence,
        }
    elif signal_type == "opening":
        task = {
            "rank": 0,
            "title": build_opening_task_title(competitor, region, detail),
            "why_now": f"{competitor} is signaling an opening or expansion in {region}: {signal_phrase}. A specific comparison push this week helps lock in prospects before the new option gains momentum.",
            "expected_advantage": measurable_advantage(domain, "conversion"),
            "evidence_refs": evidence,
        }
    elif signal_type in {"offer", "proof_signal", "messaging_shift"}:
        task = {
            "rank": 0,
            "title": build_positioning_task_title(competitor, signal_type, detail, domain),
            "why_now": f"{competitor} changed customer-facing messaging in {region}: {signal_phrase}. Updating the highest-exposure conversion touchpoint this week prevents the competitor narrative from owning the buying conversation.",
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


def score_multi_signal_candidate(observations: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, int]:
    strategic_signals = {observation["signal_type"] for observation in observations}
    competitive_relevance = min(5, 4 + int(len(strategic_signals) > 1))
    urgency = 5 if {"pricing_change", "closure", "asset_sale"} & strategic_signals else 4
    actionability_this_week = 5 if contains_week_specific_action(task["title"]) else 3
    highest_impact = 5 if any(observation["business_impact"] == "high" for observation in observations) else 4
    evidence_strength = min(
        5,
        max(3, int(round(sum(float(observation["confidence"]) for observation in observations) / max(len(observations), 1) * 5))),
    )
    total_score = competitive_relevance + urgency + actionability_this_week + highest_impact + evidence_strength + 2
    return {
        "total_score": total_score,
        "competitive_relevance": competitive_relevance,
        "urgency": urgency,
        "actionability_this_week": actionability_this_week,
        "strategic_leverage": highest_impact,
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


def build_pricing_offer_candidate(
    source: SourcePackage,
    pricing_observation: dict[str, Any],
    offer_observation: dict[str, Any],
) -> TaskCandidate:
    region = humanize_region(pricing_observation["region"])
    domain = infer_domain(source)
    pricing_detail = extract_action_detail(extract_signal_phrase(pricing_observation["summary"]))
    offer_detail = extract_action_detail(extract_signal_phrase(offer_observation["summary"]))
    tier = pricing_detail.get("tier") or "next intake"
    offer_name = offer_detail.get("offer") or "switch offer"
    title = (
        f"Launch a 7-day switch campaign with a {offer_name} for {tier} families before {offer_observation['competitor']} and {pricing_observation['competitor']} reset the {region} market"
        if domain == "academy"
        else f"Launch a 7-day switch offer before {offer_observation['competitor']} and {pricing_observation['competitor']} reset buyer expectations"
    )
    task = {
        "rank": 0,
        "title": title,
        "why_now": (
            f"{pricing_observation['competitor']} raised pricing while {offer_observation['competitor']} pushed {offer_name} messaging in {region}. "
            "A single switch campaign this week answers both price pressure and promotional pressure before families choose a competing path."
        ),
        "expected_advantage": (
            "Captures switching parents before the intake window by giving price-sensitive families one visible alternative instead of losing them to either discount-led or premium-led competitor moves."
            if domain == "academy"
            else "Captures price-sensitive buyers before the active buying window closes and competitors reset the comparison frame."
        ),
        "evidence_refs": [pricing_observation["signal_id"], offer_observation["signal_id"]],
    }
    return TaskCandidate(task=task, **score_multi_signal_candidate([pricing_observation, offer_observation], task))


def build_closure_asset_candidate(
    source: SourcePackage,
    closure_observation: dict[str, Any],
    asset_observation: dict[str, Any],
) -> TaskCandidate:
    region = humanize_region(closure_observation["region"])
    domain = infer_domain(source)
    title = (
        f"Call {closure_observation['competitor']}'s owner and submit one bundled offer for players, equipment, and facility access before the closure finalizes"
    )
    task = {
        "rank": 0,
        "title": title,
        "why_now": (
            f"{closure_observation['competitor']} is showing closure pressure and an asset-sale signal in {region}. "
            "A bundled offer this week turns two distress signals into one asymmetric expansion move before other operators react."
        ),
        "expected_advantage": (
            "Acquires players and equipment at low cost before closure finalizes, creating immediate growth capacity without waiting for organic expansion."
            if domain == "academy"
            else "Captures customers, assets, or operating capacity at low cost before the distressed competitor exits."
        ),
        "evidence_refs": [closure_observation["signal_id"], asset_observation["signal_id"]],
    }
    return TaskCandidate(task=task, **score_multi_signal_candidate([closure_observation, asset_observation], task))


def build_positioning_bundle_candidate(
    source: SourcePackage,
    proof_observation: dict[str, Any],
    offer_observation: dict[str, Any],
) -> TaskCandidate:
    region = humanize_region(proof_observation["region"])
    domain = infer_domain(source)
    offer_name = extract_action_detail(extract_signal_phrase(offer_observation["summary"])).get("offer") or "offer-led"
    title = (
        f"Add a {offer_name} response, two proof points, and one urgency strip to the enrollment page before the next {region} intake"
        if domain == "academy"
        else f"Add one {offer_name} response and proof-led conversion strip before the next campaign cycle"
    )
    task = {
        "rank": 0,
        "title": title,
        "why_now": (
            f"{proof_observation['competitor']} is pairing customer-facing proof with {offer_name} messaging in {region}. "
            "Updating the page this week lets you answer both trust and offer pressure with one conversion move."
        ),
        "expected_advantage": (
            "Raises conversion among undecided parents before the next intake by combining proof, urgency, and a direct answer to the competitor offer."
            if domain == "academy"
            else "Improves conversion before the next campaign window by answering both proof and offer pressure in one place."
        ),
        "evidence_refs": [proof_observation["signal_id"], offer_observation["signal_id"]],
    }
    return TaskCandidate(task=task, **score_multi_signal_candidate([proof_observation, offer_observation], task))


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


def detect_source_kind(raw_text: str) -> str:
    stripped = raw_text.strip()
    if stripped.startswith(("http://", "https://", "www.")):
        return "url"
    return "manual_text"


def normalize_source_package(source: SourcePackage) -> SourcePackage:
    source_kind = detect_source_kind(source.raw_text)
    if source_kind != "url":
        return source

    url = extract_first_url(source.raw_text)
    if not url:
        return source

    fetched = fetch_url_text(url)
    raw_text = format_fetched_source(url, fetched["title"], fetched["content"])
    return SourcePackage(
        project_id=source.project_id,
        source_kind="url",
        project_summary=source.project_summary,
        raw_text=raw_text,
        source_ref=source.source_ref,
        competitor=source.competitor,
        region=source.region,
    )


def recover_source_context(source: SourcePackage, knowledge_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> SourcePackage:
    competitor = source.competitor
    region = source.region
    project_summary = source.project_summary

    for row in knowledge_rows:
        if not competitor:
            competitor = row.get("competitor")
        if not region:
            region = row.get("region")
        if competitor and region:
            break

    for row in source_rows:
        if not competitor and row.get("competitor"):
            competitor = row["competitor"]
        if not region and row.get("region"):
            region = row["region"]
        if project_summary == "managed_on_worker" and row.get("project_summary") and row["project_summary"] != "managed_on_worker":
            project_summary = row["project_summary"]
        if competitor and region and project_summary != "managed_on_worker":
            break

    return SourcePackage(
        project_id=source.project_id,
        source_kind=source.source_kind,
        project_summary=project_summary,
        raw_text=source.raw_text,
        source_ref=source.source_ref,
        competitor=competitor,
        region=region,
    )


def infer_context(source_text: str, project_summary: str) -> dict[str, str | float | None]:
    competitor = infer_competitor(project_summary, source_text)
    region = infer_region(project_summary, source_text)
    confidence = 0.0
    if competitor != "regional_competitor_unknown":
        confidence += 0.5
    if region != "region_unknown":
        confidence += 0.4
    if project_summary and project_summary != "managed_on_worker":
        confidence += 0.1
    return {
        "competitor": None if competitor == "regional_competitor_unknown" else competitor,
        "region": None if region == "region_unknown" else region,
        "confidence": min(confidence, 1.0),
    }


def infer_competitor(project_summary: str, raw_text: str) -> str:
    explicit = extract_named_entity_after_labels(raw_text, ("competitor", "academy", "club", "school"))
    if explicit:
        return explicit

    host = extract_labeled_field(raw_text, "Source Host")
    if host:
        host_name = host_to_entity(host)
        if host_name:
            return host_name

    title = extract_labeled_field(raw_text, "Fetched Title")
    for text in (title, raw_text, project_summary):
        entity = first_viable_entity(extract_named_entities(text))
        if entity:
            return entity
    return "regional_competitor_unknown"


def infer_region(project_summary: str, raw_text: str) -> str:
    region_tail = r"(cluster|region|county|city|area|district|zone)"
    not_entity_suffix = r"(?!\s+(club|academy|school|fc|foundation)\b)"
    explicit_match = re.search(
        rf"\b(region|area|city|county|cluster|district|zone)\s*[:\-]\s*([A-Za-z0-9\s]+)",
        f"{project_summary}\n{raw_text}",
        re.IGNORECASE,
    )
    if explicit_match:
        return re.sub(r"^(in|at|near|for)_", "", explicit_match.group(2).strip().lower().replace(" ", "_"))

    project_summary_match = re.search(
        rf"\b([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)?)\s+{region_tail}\b{not_entity_suffix}",
        project_summary,
        re.IGNORECASE,
    )
    if project_summary_match:
        region_name = f"{project_summary_match.group(1)}_{project_summary_match.group(2)}".strip().lower().replace(" ", "_")
        return re.sub(r"^(in|at|near)_", "", region_name)

    raw_text_match = re.search(
        rf"\b(region|area|city|county|cluster|district|zone)\s*[:\-]\s*([A-Za-z0-9\s]+)",
        raw_text,
        re.IGNORECASE,
    )
    if raw_text_match:
        return re.sub(r"^(in|at|near|for)_", "", raw_text_match.group(2).strip().lower().replace(" ", "_"))
    region_phrase = re.search(
        rf"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+{region_tail}\b{not_entity_suffix}",
        raw_text,
        re.IGNORECASE,
    )
    if region_phrase:
        return re.sub(
            r"^(in|at|near|for)_",
            "",
            f"{region_phrase.group(1)}_{region_phrase.group(2)}".strip().lower().replace(" ", "_"),
        )
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


def matching_clauses(clauses: list[str], keywords: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for clause in clauses:
        normalized = clause.lower()
        if any(keyword in normalized for keyword in keywords):
            matches.append(clause)
    return matches


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


def normalize_task_title(title: str) -> str:
    return " ".join(title.lower().split())


def extract_first_url(raw_text: str) -> str | None:
    match = re.search(r"(https?://\S+|www\.\S+)", raw_text.strip())
    if not match:
        return None
    url = match.group(1).rstrip(".,)")
    if url.startswith("www."):
        return f"https://{url}"
    return url


def fetch_url_text(url: str) -> dict[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Agent.Chappie/1.0 (+https://agent-chappie.vercel.app)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="replace")

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = strip_html(title_match.group(1)) if title_match else url
    body = html
    body = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<style\b[^>]*>.*?</style>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = extract_primary_html_block(body)
    body = strip_html(body)
    body = remove_boilerplate_lines(body)
    body = " ".join(body.split())
    return {
        "title": title.strip()[:180],
        "content": body[:6000],
    }


def format_fetched_source(url: str, title: str, content: str) -> str:
    host = urllib.parse.urlparse(url).netloc or url
    parts = [
        f"Source URL: {url}",
        f"Source Host: {host}",
        f"Fetched Title: {title}",
        f"Fetched Content: {content}",
    ]
    return "\n".join(parts)


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def extract_primary_html_block(html: str) -> str:
    for pattern in (
        r"<main\b[^>]*>(.*?)</main>",
        r"<article\b[^>]*>(.*?)</article>",
        r"<body\b[^>]*>(.*?)</body>",
    ):
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    return html


def remove_boilerplate_lines(value: str) -> str:
    parts = [segment.strip() for segment in re.split(r"[\n\r\t]+", value)]
    kept: list[str] = []
    for part in parts:
        normalized = " ".join(part.split())
        if len(normalized) < 24:
            continue
        if normalized.lower().startswith(("skip to", "privacy", "cookie", "menu", "navigation", "search", "sign in", "log in")):
            continue
        if any(token in normalized.lower() for token in ("all rights reserved", "javascript", "enable cookies", "subscribe", "newsletter")):
            continue
        kept.append(normalized)
    return " ".join(kept)


def passes_url_signal_quality(value: str) -> bool:
    normalized = value.lower()
    if len(normalized) < URL_MIN_CONTENT_CHARS:
        return False
    if not any(keyword in normalized for keyword in SIGNAL_KEYWORDS):
        return False
    proper_nouns = re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,2}\b", value)
    return len(proper_nouns) >= 2


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


def extract_action_detail(signal_phrase: str) -> dict[str, str | None]:
    tier_match = re.search(r"\b(U\d{1,2}|under\s*\d{1,2})\b", signal_phrase, re.IGNORECASE)
    percent_match = re.search(r"\b(\d{1,2}(?:\.\d+)?\s?%)\b", signal_phrase)
    offer_match = re.search(r"\b(free[-\s]trial|trial offer|discount campaign|discount|voucher|scholarship)\b", signal_phrase, re.IGNORECASE)
    timeframe_match = re.search(r"\b(this week|this month|before the next intake|before next intake|before enrollment closes)\b", signal_phrase, re.IGNORECASE)
    return {
        "tier": tier_match.group(1).upper().replace(" ", "") if tier_match else None,
        "percent": percent_match.group(1).replace(" ", "") if percent_match else None,
        "offer": offer_match.group(1).lower().replace("-", " ") if offer_match else None,
        "timeframe": timeframe_match.group(1).lower() if timeframe_match else None,
    }


def build_pricing_task_title(competitor: str, detail: dict[str, str | None], domain: str) -> str:
    tier = detail.get("tier")
    percent = detail.get("percent")
    if domain == "academy" and tier and percent:
        return f"Update the {tier} pricing page and launch a 7-day comparison offer against {competitor}'s {percent} price move"
    if domain == "academy" and tier:
        return f"Update the {tier} pricing page and launch a 7-day comparison offer against {competitor}"
    return f"Publish a 7-day comparison offer and update the pricing page against {competitor}'s latest fee change"


def build_closure_task_title(competitor: str, detail: dict[str, str | None]) -> str:
    timeframe = detail.get("timeframe") or "this week"
    return f"Call {competitor}'s owner {timeframe} and ask for player, staff, and equipment availability"


def build_asset_sale_task_title(detail: dict[str, str | None]) -> str:
    return "Request the equipment inventory and submit a bid before the sell-off closes"


def build_opening_task_title(competitor: str, region: str, detail: dict[str, str | None]) -> str:
    offer = detail.get("offer")
    if offer:
        return f"Launch a local comparison campaign in {region} before {competitor} pushes its {offer}"
    return f"Launch a local comparison campaign in {region} before {competitor} opens"


def build_positioning_task_title(
    competitor: str,
    signal_type: str,
    detail: dict[str, str | None],
    domain: str,
) -> str:
    offer = detail.get("offer")
    tier = detail.get("tier")
    if domain == "academy" and offer and tier:
        return f"Add a {offer} response for {tier} to the enrollment page and sales script this week"
    if domain == "academy" and offer:
        return f"Add a {offer} response to the enrollment page and sales script this week"
    if signal_type == "proof_signal":
        return "Add two parent testimonials and one proof strip to the enrollment page this week"
    return f"Rewrite the enrollment-page hero and sales script this week to answer {competitor}'s latest claim"


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
            "launch",
            "update the",
            "call",
            "add a",
        )
    )


def passes_task_quality_gate(task: dict[str, Any]) -> bool:
    title = task["title"].strip().lower()
    why_now = task["why_now"].strip().lower()
    expected_advantage = task["expected_advantage"].strip().lower()

    generic_starts = (
        "adjust ",
        "improve ",
        "optimize ",
        "review ",
        "analyze ",
        "research ",
        "monitor ",
        "investigate ",
        "evaluate ",
    )
    if title.startswith(generic_starts):
        return False

    if not contains_week_specific_action(task["title"]) and not any(
        token in why_now for token in ("this week", "before", "next intake", "by friday", "7-day")
    ):
        return False

    competitive_tokens = (
        "competitor",
        "price",
        "pricing",
        "offer",
        "closure",
        "distress",
        "sell-off",
        "switch",
        "comparison",
        "intake",
    )
    if not any(token in why_now or token in expected_advantage for token in competitive_tokens):
        return False

    vague_advantage_phrases = ("improve positioning", "reduce churn", "improves conversion", "improves win rate")
    if any(expected_advantage == phrase for phrase in vague_advantage_phrases):
        return False

    if len(task["evidence_refs"]) < 1:
        return False

    return True


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


def extract_named_entity_after_labels(raw_text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        match = re.search(
            rf"\b{label}\b\s*[:\-]\s*([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){{0,2}})",
            raw_text,
            re.IGNORECASE,
        )
        if match:
            candidate = clean_entity(match.group(1))
            if candidate:
                return candidate
    return None


def extract_labeled_field(raw_text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*(.+)", raw_text)
    return match.group(1).strip() if match else ""


def host_to_entity(host: str) -> str | None:
    domain = host.strip().lower().split(":")[0]
    if not domain:
        return None
    base = domain.split(".")[0]
    words = [word for word in re.split(r"[-_]+", base) if word and word not in {"www", "app"}]
    if not words:
        return None
    return clean_entity(" ".join(word.capitalize() for word in words))


def extract_named_entities(text: str) -> list[str]:
    if not text:
        return []
    pattern = r"\b(?:[A-Z][a-zA-Z0-9]+|[A-Z]{2,}[a-zA-Z0-9]*)(?:\s+(?:[A-Z][a-zA-Z0-9]+|[A-Z]{2,}[a-zA-Z0-9]*)){0,2}\b"
    return [match.group(0) for match in re.finditer(pattern, text)]


def first_viable_entity(candidates: list[str]) -> str | None:
    for candidate in candidates:
        cleaned = clean_entity(candidate)
        if cleaned:
            return cleaned
    return None


def clean_entity(value: str) -> str | None:
    candidate = " ".join(value.strip().split())
    if not candidate or len(candidate) < 3:
        return None
    words = candidate.split()
    if any(word in GENERIC_ENTITY_WORDS for word in words):
        return None
    if words[-1].lower() in REGION_TERMS:
        return None
    return candidate


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")

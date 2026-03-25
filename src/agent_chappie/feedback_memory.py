"""
Shared generation_memory helpers: task feedback and intelligence-card teach use the same
normalization, comment parsing, and avoid_title token matching.
"""

from __future__ import annotations

import re
from typing import Any


def normalize_task_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def avoid_title_pattern_matches(candidate_normalized: str, pattern_key: str) -> bool:
    """Same token-overlap rule as generation_memory_adjustment for avoid_title."""
    if pattern_key == candidate_normalized:
        return True
    pw = set(pattern_key.split())
    tw = set(candidate_normalized.split())
    if not pw or not tw:
        return False
    return len(pw & tw) / len(pw | tw) > 0.6


def intel_card_text_fingerprint(
    insight: str | None,
    implication: str | None,
    potential_moves: list[Any] | None,
) -> str:
    parts: list[str] = []
    for x in (insight, implication):
        s = str(x or "").strip()
        if s:
            parts.append(s)
    for m in potential_moves or []:
        s = str(m).strip()
        if s:
            parts.append(s)
    return " ".join(parts)


def extract_comment_signals(comment: str, feedback_id: str) -> list[dict[str, Any]]:
    """
    Parse a free-text operator comment into structured generation_memory signals.
    Handles channel, segment, competitor, move-type, specificity preferences.
    """
    signals: list[dict[str, Any]] = []
    c = comment.strip().lower()

    # ---- CHANNEL preferences ----
    CHANNEL_PREFER: list[tuple[list[str], str]] = [
        (["pricing page", "on the pricing page", "about the pricing page", "price page"], "pricing_page"),
        (["landing page", "on the landing page"], "landing_page"),
        (["homepage", "on the homepage"], "homepage"),
        (["email", "onboarding email", "email campaign", "via email"], "email"),
        (["linkedin", "linkedin post"], "linkedin"),
        (["sales call", "call the", "phone call"], "sales_call"),
        (["in the app", "in-app", "app notification"], "in_app"),
        (["blog", "blog post", "article"], "blog"),
        (["webinar", "event", "live session"], "event"),
        (["case study", "case studies"], "case_study"),
        (["comparison page", "comparison section", "comparison block"], "comparison_page"),
        (["onboarding", "onboarding flow", "onboarding sequence"], "onboarding"),
    ]
    CHANNEL_AVOID: list[tuple[list[str], str]] = [
        (["not email", "no email", "avoid email"], "email"),
        (["not homepage", "not the homepage", "avoid homepage"], "homepage"),
        (["not pricing", "not a pricing", "away from pricing"], "pricing_page"),
        (["not onboarding", "not about onboarding"], "onboarding"),
        (["not linkedin", "avoid linkedin"], "linkedin"),
    ]
    for phrases, channel in CHANNEL_PREFER:
        if any(phrase in c for phrase in phrases):
            signals.append({
                "memory_kind": "prefer_channel",
                "pattern_key": "",
                "signal_value": channel,
                "weight": 5.0,
                "source_feedback_id": feedback_id,
            })
    for phrases, channel in CHANNEL_AVOID:
        if any(phrase in c for phrase in phrases):
            signals.append({
                "memory_kind": "avoid_channel",
                "pattern_key": channel,
                "signal_value": channel,
                "weight": 5.0,
                "source_feedback_id": feedback_id,
            })

    # ---- SEGMENT preferences ----
    SEGMENT_PREFER: list[tuple[list[str], str]] = [
        (["trial users", "free trial users", "people on trial"], "trial_users"),
        (["buyers", "active buyers", "paying buyers"], "buyers"),
        (["onboarders", "new users", "new signups", "people who just joined"], "new_users"),
        (["decision makers", "cto", "vp ", "executive", "c-suite"], "decision_makers"),
        (["enterprise", "large accounts", "enterprise buyers"], "enterprise"),
        (["smb", "small business", "small teams"], "smb"),
        (["churned", "lost customers", "at risk accounts"], "at_risk_accounts"),
        (["leads", "prospects", "top of funnel", "potential buyers"], "prospects"),
    ]
    SEGMENT_AVOID: list[tuple[list[str], str]] = [
        (["wrong audience", "not the right audience", "not our audience", "different audience"], "wrong_audience"),
        (["not enterprise", "not for enterprise"], "enterprise"),
        (["not smb", "not small business"], "smb"),
    ]
    for phrases, segment in SEGMENT_PREFER:
        if any(phrase in c for phrase in phrases):
            signals.append({
                "memory_kind": "prefer_segment",
                "pattern_key": segment,
                "signal_value": segment,
                "weight": 4.0,
                "source_feedback_id": feedback_id,
            })
    for phrases, segment in SEGMENT_AVOID:
        if any(phrase in c for phrase in phrases):
            signals.append({
                "memory_kind": "avoid_phrase",
                "pattern_key": segment,
                "signal_value": segment,
                "weight": 5.0,
                "source_feedback_id": feedback_id,
            })

    # ---- COMPETITOR preferences ----
    COMPETITOR_SIGNALS = [
        "answer ",
        "vs ",
        "versus ",
        "beat ",
        "respond to ",
        "called out by ",
        "mentioned by ",
        "benchmark against ",
    ]
    for sig in COMPETITOR_SIGNALS:
        idx = c.find(sig)
        if idx != -1:
            fragment = c[idx + len(sig):idx + len(sig) + 30].strip()
            competitor_name = fragment.split()[0].strip(".,\"'") if fragment.split() else ""
            if competitor_name and len(competitor_name) > 2:
                signals.append({
                    "memory_kind": "prefer_competitor",
                    "pattern_key": competitor_name,
                    "signal_value": competitor_name,
                    "weight": 4.0,
                    "source_feedback_id": feedback_id,
                })
                break

    # ---- MOVE TYPE preferences ----
    MOVE_PREFER: list[tuple[list[str], str]] = [
        (["trust move", "proof move", "we need a trust", "we need proof", "social proof", "concrete asset", "credibility"], "proof_or_trust_move"),
        (["pricing move", "offer move", "commercial response", "pricing response", "lower price", "better offer"], "pricing_or_offer_move"),
        (["capture move", "close the deal", "close this account", "win back", "intercept"], "intercept_or_capture_move"),
        (["messaging move", "positioning move", "reframe", "reposition", "messaging response"], "messaging_or_positioning_move"),
        (["partnership", "partner move", "referral move", "channel partner"], "partnership_or_distribution_move"),
    ]
    MOVE_AVOID: list[tuple[list[str], str]] = [
        (["not a messaging", "not messaging", "not a positioning", "not about messaging"], "messaging_or_positioning_move"),
        (["not a trust", "not about trust", "not a proof move"], "proof_or_trust_move"),
        (["not a pricing", "not a commercial", "not about pricing", "not an offer"], "pricing_or_offer_move"),
    ]
    for phrases, bucket in MOVE_PREFER:
        if any(phrase in c for phrase in phrases):
            signals.append({
                "memory_kind": "prefer_bucket",
                "pattern_key": bucket,
                "signal_value": bucket,
                "weight": 5.0,
                "source_feedback_id": feedback_id,
            })
    for phrases, bucket in MOVE_AVOID:
        if any(phrase in c for phrase in phrases):
            signals.append({
                "memory_kind": "avoid_bucket",
                "pattern_key": bucket,
                "signal_value": bucket,
                "weight": 5.0,
                "source_feedback_id": feedback_id,
            })

    # ---- SPECIFICITY preferences ----
    if any(token in c for token in ("too vague", "too broad", "too generic", "not specific enough", "be more specific", "needs specificity", "more precise")):
        signals.append({
            "memory_kind": "prefer_specificity",
            "pattern_key": "high_specificity",
            "signal_value": "high",
            "weight": 3.0,
            "source_feedback_id": feedback_id,
        })

    # ---- PHRASE avoidance (overlap/duplicate signals) ----
    if any(token in c for token in ("overlap", "duplicate", "same idea", "repeated idea", "too similar")):
        signals.append({
            "memory_kind": "avoid_phrase",
            "pattern_key": "duplicate_idea",
            "signal_value": "duplicate",
            "weight": 2.0,
            "source_feedback_id": feedback_id,
        })

    return signals

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.local_store import initialize_local_store
from agent_chappie.worker_bridge import WorkerBridgeConfig, build_workspace_payload, process_job_payload


GENERIC_PATTERNS = (
    "current competitor frame",
    "buyer-facing response",
    "comparison-stage buyers",
    "market frame already shaping decisions",
    "the worker drafted",
    "use the linked intelligence",
    "the current market leader",
    "the strongest visible competitor",
)
SPECIFIC_CHANNEL_HINTS = (
    "pricing page",
    "homepage",
    "hero section",
    "comparison section",
    "faq",
    "contact page",
    "landing page",
    "enrollment",
)
SPECIFIC_MECHANISM_HINTS = (
    "comparison block",
    "proof block",
    "free trial",
    "trial",
    "faq",
    "testimonial",
    "onboarding",
    "proof",
    "offer",
)


@dataclass(frozen=True)
class PressureCase:
    slug: str
    title: str
    prompt: str
    raw_text: str
    source_kind: str = "manual_text"
    file_name: str | None = None


def build_cases() -> list[PressureCase]:
    return [
        PressureCase(
            slug="fortitude_market_doc",
            title="Fortitude market analysis document",
            prompt="Analyze the uploaded market document and return the next three actions.",
            raw_text=(
                "Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. "
                "The document compares packaging models, AI-led positioning, service-led onboarding, "
                "customer testimonials, integration claims, trial offers, and buyer objections."
            ),
            file_name="competitive-analysis.docx",
        ),
        PressureCase(
            slug="explicit_claim_asset",
            title="Explicit claim and asset document",
            prompt="Analyze the uploaded market document and return the next three actions.",
            raw_text=(
                "Add a pricing comparison block and onboarding FAQ to the pricing page this week before Fortitude AI's free trial sets buyer expectations. "
                "Rewrite the homepage hero section to answer the no engineering required claim before buyers already comparing options default to Fortitude AI."
            ),
            file_name="competitive-analysis.docx",
        ),
        PressureCase(
            slug="diverse_pressure_mix",
            title="Diverse market pressure mix",
            prompt="Identify competitive signals and return exactly 3 actionable follow-up tasks.",
            raw_text=(
                "FlowOps raised onboarding and pricing friction in the SEO market. "
                "Competitors are using testimonials, proof blocks, integration claims, and comparison messaging. "
                "One exposed operator is reducing staff and may sell assets. "
                "Trial-led acquisition pressure is rising."
            ),
        ),
        PressureCase(
            slug="knowledge_heavy_noisy_doc",
            title="Knowledge-heavy noisy competitor doc",
            prompt="Analyze the uploaded market document and return actions only if the evidence supports them.",
            raw_text=(
                "Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. "
                "The document compares packaging, pricing bundles, trial offers, customer testimonials, "
                "and AI-led positioning across several vendors."
            ),
            file_name="competitive-analysis.docx",
        ),
        PressureCase(
            slug="multi_pressure_bundle",
            title="Multi-pressure comparison notes",
            prompt="Analyze the source and return the next three concrete moves.",
            raw_text=(
                "Fortitude AI is using free trial language and low-friction onboarding claims on the pricing page. "
                "Its homepage hero now promises no engineering required and features new customer proof blocks. "
                "Several buyer notes mention pricing comparison and integration hesitation."
            ),
        ),
        PressureCase(
            slug="messy_internal_notes",
            title="Messy internal notes",
            prompt="Turn these messy notes into the next three useful business moves.",
            raw_text=(
                "Notes: buyers keep asking if setup is heavy, two prospects mentioned Fortitude AI's free trial, "
                "pricing page doesn't answer onboarding objections, homepage proof is weak, sales calls keep rebuilding the same comparison manually."
            ),
        ),
    ]


def build_payload(case: PressureCase) -> dict[str, Any]:
    project_id = f"pressure_{case.slug}"
    source_ref = f"source_{case.slug}"
    return {
        "job_request": {
            "job_id": f"job_{case.slug}",
            "app_id": "consultant_followup_web",
            "project_id": project_id,
            "priority_class": "normal",
            "job_class": "light",
            "submitted_at": "2026-03-24T18:00:00+00:00",
            "requested_capability": "followup_task_recommendation",
            "input_payload": {
                "context_type": "working_document",
                "prompt": case.prompt,
                "artifacts": [{"type": "upload", "ref": source_ref}],
            },
            "source_refs": [source_ref],
        },
        "source_package": {
            "project_id": project_id,
            "source_kind": case.source_kind,
            "project_summary": "managed_on_worker",
            "raw_text": case.raw_text,
            "source_ref": source_ref,
            "file_name": case.file_name,
        },
    }


def title_word_set(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def task_specificity_score(task: dict[str, Any]) -> float:
    text = " ".join(
        [
            task.get("title", ""),
            task.get("why_now", ""),
            task.get("expected_advantage", ""),
            task.get("done_definition", ""),
        ]
    ).lower()
    score = 0.0
    if task.get("competitor_name"):
        score += 1.2
    if task.get("target_channel"):
        score += 1.0
    if task.get("target_segment"):
        score += 0.8
    if task.get("mechanism"):
        score += 0.8
    if any(hint in text for hint in SPECIFIC_CHANNEL_HINTS):
        score += 1.0
    if any(hint in text for hint in SPECIFIC_MECHANISM_HINTS):
        score += 0.8
    if task.get("strongest_evidence_excerpt"):
        score += 0.6
    if "this week" in text:
        score += 0.3
    return score


def find_failure_patterns(tasks: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    titles = [task.get("title", "") for task in tasks]
    buckets = [task.get("move_bucket", "") for task in tasks]
    combined = " ".join(
        [
            task.get("title", "") + " " + task.get("why_now", "") + " " + task.get("expected_advantage", "")
            for task in tasks
        ]
    ).lower()

    if any(pattern in combined for pattern in GENERIC_PATTERNS):
        failures.append("generic_wording")
    if len(set(buckets)) < 3:
        failures.append("low_bucket_diversity")
    if sum(task.get("task_type") == "information_request" for task in tasks) > 1:
        failures.append("too_many_information_requests")
    if tasks and tasks[-1].get("task_type") == "information_request":
        failures.append("fallback_third_task")
    if not any(task.get("competitor_name") for task in tasks):
        failures.append("missing_competitor_binding")
    if not any(task.get("target_channel") for task in tasks):
        failures.append("missing_channel_binding")
    if not any(task.get("done_definition") for task in tasks):
        failures.append("missing_done_definition")
    if len(titles) >= 2:
        word_sets = [title_word_set(title) for title in titles]
        overlap_pairs = 0
        for index, current in enumerate(word_sets):
            for other in word_sets[index + 1 :]:
                if current and other:
                    overlap = len(current & other) / max(1, len(current | other))
                    if overlap > 0.55:
                        overlap_pairs += 1
        if overlap_pairs >= 2:
            failures.append("overlapping_titles")
    if any(re.search(r"\bon the [^,]+ on the\b", task.get("title", "").lower()) for task in tasks):
        failures.append("duplicated_asset_location")
    if any("proof block in proof section" in task.get("title", "").lower() for task in tasks):
        failures.append("awkward_asset_phrase")
    if task_specificity_score(tasks[0]) < 2.8:
        failures.append("weak_rank1_specificity")
    return failures


def evaluate_case(case: PressureCase, db_path: str) -> dict[str, Any]:
    payload = build_payload(case)
    result = process_job_payload(payload, WorkerBridgeConfig(local_db_path=db_path))
    tasks = result["job_result"]["result_payload"]["recommended_tasks"]
    workspace = build_workspace_payload(payload["source_package"]["project_id"], WorkerBridgeConfig(local_db_path=db_path))

    failures = find_failure_patterns(tasks)
    distinct = len(set(task.get("move_bucket", "") for task in tasks))
    rank1 = tasks[0]
    score = 10.0
    score += min(2.0, task_specificity_score(rank1) / 2.0)
    score += min(1.5, distinct * 0.5)
    score += 1.0 if rank1.get("priority_label") == "critical" else 0.0
    score -= 1.2 * len(failures)

    return {
        "slug": case.slug,
        "title": case.title,
        "input_prompt": case.prompt,
        "input_excerpt": case.raw_text[:360],
        "tasks": tasks,
        "knowledge_cards": [
            {
                "knowledge_id": card["knowledge_id"],
                "title": card["title"],
                "summary": card["summary"],
            }
            for card in workspace["knowledge_cards"][:6]
        ],
        "snapshot": workspace["competitive_snapshot"],
        "score": round(score, 2),
        "distinct_move_buckets": distinct,
        "failures": failures,
        "would_operator_act": not failures,
    }


def render_markdown_report(cases: list[dict[str, Any]]) -> str:
    ordered = sorted(cases, key=lambda item: item["score"], reverse=True)
    strongest = ordered[:3]
    weakest = ordered[-3:]
    failure_counts = Counter(failure for case in cases for failure in case["failures"])

    lines: list[str] = []
    lines.append("# Phase 7 Pressure Test Report")
    lines.append("")
    lines.append(f"Cases run: {len(cases)}")
    lines.append("")
    lines.append("## Strongest Cases")
    lines.append("")
    for case in strongest:
        lines.append(f"### {case['title']} (`{case['slug']}`)")
        lines.append(f"- Score: {case['score']}")
        lines.append(f"- Distinct move buckets: {case['distinct_move_buckets']}")
        lines.append(f"- Operator would act: {'yes' if case['would_operator_act'] else 'no'}")
        lines.append("- Top 3 tasks:")
        for task in case["tasks"]:
            lines.append(f"  - {task['rank']}. {task['title']}")
        lines.append("")

    lines.append("## Weakest Cases")
    lines.append("")
    for case in weakest:
        lines.append(f"### {case['title']} (`{case['slug']}`)")
        lines.append(f"- Score: {case['score']}")
        lines.append(f"- Failures: {', '.join(case['failures']) if case['failures'] else 'none'}")
        lines.append("- Top 3 tasks:")
        for task in case["tasks"]:
            lines.append(f"  - {task['rank']}. {task['title']}")
        lines.append("")

    lines.append("## Failure Patterns")
    lines.append("")
    if failure_counts:
        for pattern, count in failure_counts.most_common():
            lines.append(f"- `{pattern}`: {count}")
    else:
        lines.append("- No repeated failure pattern detected in this run.")
    lines.append("")

    lines.append("## Per-Case Detail")
    lines.append("")
    for case in ordered:
        lines.append(f"### {case['title']} (`{case['slug']}`)")
        lines.append(f"- Score: {case['score']}")
        lines.append(f"- Distinct move buckets: {case['distinct_move_buckets']}")
        lines.append(f"- Failures: {', '.join(case['failures']) if case['failures'] else 'none'}")
        lines.append(f"- Input excerpt: {case['input_excerpt']}")
        lines.append("- Tasks:")
        for task in case["tasks"]:
            lines.append(
                "  - "
                f"{task['rank']}. {task['title']} "
                f"[bucket={task.get('move_bucket', 'n/a')}, priority={task.get('priority_label', 'n/a')}]"
            )
        lines.append("- Snapshot:")
        lines.append(
            "  - "
            f"Pricing: {case['snapshot'].get('pricing_position', 'n/a')} | "
            f"Acquisition: {case['snapshot'].get('acquisition_strategy_comparison', 'n/a')} | "
            f"Weakness: {case['snapshot'].get('current_weakness', 'n/a')}"
        )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pressure test Agent.Chappie's worker against messy real cases.")
    parser.add_argument(
        "--output-dir",
        default=os.path.join(ROOT, "runtime_status", "pressure_tests"),
        help="Directory for generated report artifacts.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "pressure_test.sqlite3")
        initialize_local_store(db_path)
        results = [evaluate_case(case, db_path) for case in build_cases()]

    report_path = output_dir / "phase7_pressure_report.md"
    json_path = output_dir / "phase7_pressure_report.json"
    report_path.write_text(render_markdown_report(results), encoding="utf-8")
    json_path.write_text(json.dumps({"cases": results}, indent=2), encoding="utf-8")

    print(str(report_path))
    print(str(json_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

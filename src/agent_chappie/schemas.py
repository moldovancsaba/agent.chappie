from __future__ import annotations

STRUCTURED_TASK_OBJECT_SCHEMA = {
    "task_id": str,
    "intent": {"design", "build", "analyse", "retrieve", "review", "execute"},
    "goal": str,
    "constraints": list,
    "priority": {"ideabank", "in_progress", "critical"},
    "risk_class": {"low", "moderate", "high"},
    "needs_memory": bool,
    "needs_rag": bool,
    "needs_human_approval": bool,
    "candidate_tools": list,
    "candidate_domains": list,
    "success_criteria": list,
    "draft_confidence": (int, float),
}


EXECUTION_PLAN_SCHEMA = {
    "task_id": str,
    "plan_id": str,
    "execution_mode": {"serial", "parallel", "hybrid"},
    "stages": list,
    "required_evidence": list,
    "acceptance_tests": list,
    "rollback_strategy": str,
    "writer_confidence": (int, float),
}


EXECUTION_STAGE_SCHEMA = {
    "stage_id": str,
    "objective": str,
    "agent_type": {"retriever", "developer", "qa", "ops", "annotator", "summariser"},
    "inputs": list,
    "outputs": list,
    "depends_on": list,
    "tool_calls_allowed": list,
    "max_iterations": int,
    "timeout_ms": int,
}


DECISION_RECORD_SCHEMA = {
    "task_id": str,
    "plan_id": str,
    "decision": {"proceed", "revise", "stop"},
    "confidence": (int, float),
    "confidence_components": dict,
    "risk_flags": list,
    "required_human_review": bool,
    "judge_rationale": list,
    "next_action": {"proceed", "revise", "stop"},
}


DECISION_COMPONENTS_SCHEMA = {
    "schema_integrity": (int, float),
    "policy_compliance": (int, float),
    "evidence_sufficiency": (int, float),
    "execution_feasibility": (int, float),
    "expected_value": (int, float),
}


OUTCOME_SCHEMA = {
    "status": {"complete", "revise", "stop", "error"},
    "result": str,
    "insights": list,
    "route": {"proceed", "revise", "stop"},
    "evidence": list,
}

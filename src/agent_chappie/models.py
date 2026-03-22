from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_SYSTEM_PROMPT = """
You are a deterministic local agent.

Rules:
- Always respond with valid JSON only
- Never include markdown fences
- Never invent fields that were not requested
- If the task cannot be completed, return a valid JSON object with a safe fallback
""".strip()


class ModelClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate a model response for the given prompt."""


@dataclass
class OllamaClient:
    model: str = os.environ.get("AGENT_MODEL", "llama3:latest")
    url: str = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    timeout: float = 30.0
    system_prompt: str = BASE_SYSTEM_PROMPT

    def generate(self, prompt: str) -> str:
        payload_bytes = json.dumps(
            {
                "model": self.model,
                "prompt": f"{self.system_prompt}\n\n{prompt}",
                "stream": False,
            }
        ).encode("utf-8")
        request = Request(
            self.url,
            data=payload_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Failed to reach Ollama at {self.url}: {exc}") from exc
        text = payload.get("response")
        if not isinstance(text, str):
            raise ValueError("Ollama response did not contain a string 'response' field")
        return text


class ModelAdapter(Protocol):
    def draft(self, task: str, url: str) -> str:
        """Produce a StructuredTaskObject JSON string."""

    def write(self, task: str, url: str, sto: dict[str, object], evidence: list[str]) -> str:
        """Produce an ExecutionPlan JSON string."""

    def judge(
        self,
        task: str,
        url: str,
        sto: dict[str, object],
        plan: dict[str, object],
        evidence: list[str],
    ) -> str:
        """Produce a DecisionRecord JSON string."""

    def summarize(
        self,
        task: str,
        url: str,
        sto: dict[str, object],
        plan: dict[str, object],
        evidence: list[str],
    ) -> str:
        """Produce an Outcome JSON string."""


@dataclass
class OllamaModelAdapter:
    client: OllamaClient
    drafter_model: str | None = os.environ.get("DRAFTER_MODEL")
    writer_model: str | None = os.environ.get("WRITER_MODEL")
    judge_model: str | None = os.environ.get("JUDGE_MODEL")

    def draft(self, task: str, url: str) -> str:
        prompt = (
            "Role: drafter\n"
            "Return JSON only.\n"
            "Allowed intent values: design, build, analyse, retrieve, review, execute.\n"
            "Allowed priority values: ideabank, in_progress, critical.\n"
            "Allowed risk_class values: low, moderate, high.\n"
            "Use exactly these keys: task_id, intent, goal, constraints, priority, risk_class, needs_memory, needs_rag, needs_human_approval, candidate_tools, candidate_domains, success_criteria, draft_confidence.\n"
            "Example: {\"task_id\":\"task-001\",\"intent\":\"analyse\",\"goal\":\"Summarise the target URL\",\"constraints\":[\"local-first\"],\"priority\":\"in_progress\",\"risk_class\":\"low\",\"needs_memory\":false,\"needs_rag\":true,\"needs_human_approval\":false,\"candidate_tools\":[\"fetch_url\"],\"candidate_domains\":[\"docs\"],\"success_criteria\":[\"return summary\"],\"draft_confidence\":0.9}\n"
            f"Task: {task}\n"
            f"URL: {url}\n"
        )
        return self._generate(prompt, model_override=self.drafter_model)

    def write(self, task: str, url: str, sto: dict[str, object], evidence: list[str]) -> str:
        prompt = (
            "Role: writer\n"
            "Return JSON only.\n"
            "Allowed execution_mode values: serial, parallel, hybrid.\n"
            "Allowed agent_type values per stage: retriever, developer, qa, ops, annotator, summariser.\n"
            "Use exactly these top-level keys: task_id, plan_id, execution_mode, stages, required_evidence, acceptance_tests, rollback_strategy, writer_confidence.\n"
            "Each stage must use exactly these keys: stage_id, objective, agent_type, inputs, outputs, depends_on, tool_calls_allowed, max_iterations, timeout_ms.\n"
            "Example: {\"task_id\":\"task-001\",\"plan_id\":\"plan-001\",\"execution_mode\":\"serial\",\"stages\":[{\"stage_id\":\"S1\",\"objective\":\"Fetch content\",\"agent_type\":\"retriever\",\"inputs\":[\"https://example.com\"],\"outputs\":[\"raw_article_text\"],\"depends_on\":[],\"tool_calls_allowed\":[\"fetch_url\"],\"max_iterations\":1,\"timeout_ms\":15000}],\"required_evidence\":[\"raw_article_text\"],\"acceptance_tests\":[\"content fetched\"],\"rollback_strategy\":\"Stop and preserve traces.\",\"writer_confidence\":0.9}\n"
            f"Task: {task}\n"
            f"URL: {url}\n"
            f"StructuredTaskObject: {json.dumps(sto)}\n"
            f"Retrieved evidence: {json.dumps(evidence)}\n"
        )
        return self._generate(prompt, model_override=self.writer_model)

    def judge(
        self,
        task: str,
        url: str,
        sto: dict[str, object],
        plan: dict[str, object],
        evidence: list[str],
    ) -> str:
        prompt = (
            "Role: judge\n"
            "Return JSON only.\n"
            "Allowed decision values: proceed, revise, stop.\n"
            "Allowed next_action values: proceed, revise, stop.\n"
            "Use exactly these keys: task_id, plan_id, decision, confidence, confidence_components, risk_flags, required_human_review, judge_rationale, next_action.\n"
            "confidence_components must contain exactly: schema_integrity, policy_compliance, evidence_sufficiency, execution_feasibility, expected_value.\n"
            "Example: {\"task_id\":\"task-001\",\"plan_id\":\"plan-001\",\"decision\":\"proceed\",\"confidence\":0.9,\"confidence_components\":{\"schema_integrity\":0.95,\"policy_compliance\":0.95,\"evidence_sufficiency\":0.85,\"execution_feasibility\":0.9,\"expected_value\":0.88},\"risk_flags\":[],\"required_human_review\":false,\"judge_rationale\":[\"bounded task\"],\"next_action\":\"proceed\"}\n"
            f"Task: {task}\n"
            f"URL: {url}\n"
            f"StructuredTaskObject: {json.dumps(sto)}\n"
            f"ExecutionPlan: {json.dumps(plan)}\n"
            f"Retrieved evidence: {json.dumps(evidence)}\n"
        )
        return self._generate(prompt, model_override=self.judge_model)

    def summarize(
        self,
        task: str,
        url: str,
        sto: dict[str, object],
        plan: dict[str, object],
        evidence: list[str],
    ) -> str:
        prompt = (
            "Role: summarizer\n"
            "Return JSON only.\n"
            "Allowed status values: complete, revise, stop, error.\n"
            "Allowed route values: proceed, revise, stop.\n"
            "Use exactly these keys: status, result, insights, route, evidence.\n"
            "Example: {\"status\":\"complete\",\"result\":\"Summary text\",\"insights\":[\"point one\",\"point two\"],\"route\":\"proceed\",\"evidence\":[\"source text\"]}\n"
            f"Task: {task}\n"
            f"URL: {url}\n"
            f"StructuredTaskObject: {json.dumps(sto)}\n"
            f"ExecutionPlan: {json.dumps(plan)}\n"
            f"Retrieved evidence: {json.dumps(evidence)}\n"
            "Set route to proceed when summarizing successful evidence.\n"
        )
        return self._generate(prompt, model_override=self.writer_model)

    def _generate(self, prompt: str, model_override: str | None = None) -> str:
        original_model = self.client.model
        if model_override:
            self.client.model = model_override
        try:
            return self.client.generate(prompt)
        finally:
            self.client.model = original_model


@dataclass
class DryRunModelAdapter:
    """Deterministic model stub for offline validation."""

    def draft(self, task: str, url: str) -> str:
        return json.dumps(
            {
                "task_id": "task-dry-run-001",
                "intent": "analyse",
                "goal": task,
                "constraints": ["local-first", "structured-output"],
                "priority": "in_progress",
                "risk_class": "low",
                "needs_memory": False,
                "needs_rag": True,
                "needs_human_approval": False,
                "candidate_tools": ["fetch_url"],
                "candidate_domains": ["docs", "local_kb"],
                "success_criteria": [
                    "fetch the target URL",
                    "return a concise summary",
                    "return machine-readable insights",
                ],
                "draft_confidence": 0.94,
            }
        )

    def write(self, task: str, url: str, sto: dict[str, object], evidence: list[str]) -> str:
        return json.dumps(
            {
                "task_id": sto["task_id"],
                "plan_id": "plan-dry-run-001",
                "execution_mode": "serial",
                "stages": [
                    {
                        "stage_id": "S1",
                        "objective": "Fetch article content",
                        "agent_type": "retriever",
                        "inputs": [url],
                        "outputs": ["raw_article_text"],
                        "depends_on": [],
                        "tool_calls_allowed": ["fetch_url"],
                        "max_iterations": 1,
                        "timeout_ms": 15000,
                    },
                    {
                        "stage_id": "S2",
                        "objective": "Summarise the fetched content",
                        "agent_type": "summariser",
                        "inputs": ["raw_article_text"],
                        "outputs": ["summary", "insights"],
                        "depends_on": ["S1"],
                        "tool_calls_allowed": [],
                        "max_iterations": 1,
                        "timeout_ms": 15000,
                    },
                ],
                "required_evidence": ["raw_article_text"],
                "acceptance_tests": [
                    "article content was fetched",
                    "summary is non-empty",
                    "insights list has at least two items",
                ],
                "rollback_strategy": "Stop execution and preserve traces for review.",
                "writer_confidence": 0.91,
            }
        )

    def judge(
        self,
        task: str,
        url: str,
        sto: dict[str, object],
        plan: dict[str, object],
        evidence: list[str],
    ) -> str:
        evidence_sufficiency = 0.92 if evidence else 0.30
        confidence = 0.90 if evidence else 0.40
        decision = "proceed" if evidence else "revise"
        return json.dumps(
            {
                "task_id": sto["task_id"],
                "plan_id": plan["plan_id"],
                "decision": decision,
                "confidence": confidence,
                "confidence_components": {
                    "schema_integrity": 0.98,
                    "policy_compliance": 0.97,
                    "evidence_sufficiency": evidence_sufficiency,
                    "execution_feasibility": 0.89,
                    "expected_value": 0.88,
                },
                "risk_flags": [],
                "required_human_review": False,
                "judge_rationale": [
                    "The task is low risk and reversible.",
                    "The plan includes a bounded fetch-and-summarise flow.",
                ],
                "next_action": decision,
            }
        )

    def summarize(
        self,
        task: str,
        url: str,
        sto: dict[str, object],
        plan: dict[str, object],
        evidence: list[str],
    ) -> str:
        return json.dumps(
            {
                "status": "complete",
                "result": "Summary generated from fetched content.",
                "insights": [
                    "The page is reachable.",
                    "A local-first workflow can chain fetch and summarise steps.",
                ],
                "route": "proceed",
                "evidence": evidence,
            }
        )


class StubSequenceClient:
    """Model stub backed by a fixed sequence of outputs."""

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.calls = 0

    def generate(self, prompt: str) -> str:
        if not self._outputs:
            raise RuntimeError("No more stub outputs available")
        self.calls += 1
        return self._outputs.pop(0)

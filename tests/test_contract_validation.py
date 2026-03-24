from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agent_chappie.validation import (
    ValidationError,
    validate_feedback,
    validate_job_request,
    validate_job_result,
    validate_system_observation,
)


class ContractValidationTests(unittest.TestCase):
    def test_job_request_accepts_valid_mvp_payload(self) -> None:
        payload = {
            "job_id": "job_mvp_0001",
            "app_id": "app_consultant_followup",
            "project_id": "client_acme_q2",
            "priority_class": "normal",
            "job_class": "heavy",
            "submitted_at": "2026-03-22T08:00:00+00:00",
            "requested_capability": "followup_task_recommendation",
            "input_payload": {
                "context_type": "meeting_notes",
                "prompt": "Recommend the next follow-up tasks for this client project.",
                "artifacts": [{"type": "upload", "ref": "upload_meeting_notes_001"}],
            },
            "requested_by": "consultant_001",
        }
        validated = validate_job_request(payload)
        self.assertEqual(validated["requested_capability"], "followup_task_recommendation")

    def test_job_result_accepts_valid_complete_payload(self) -> None:
        payload = {
            "job_id": "job_mvp_0001",
            "app_id": "app_consultant_followup",
            "project_id": "client_acme_q2",
            "status": "complete",
            "completed_at": "2026-03-22T08:02:00+00:00",
            "result_payload": {
                "recommended_tasks": [
                    {
                        "rank": 1,
                        "title": "Publish a 7-day comparison offer against the nearest academy price change",
                        "why_now": "A competitor pricing change was detected this week after the nearest academy raised fees.",
                        "expected_advantage": "Protects enrollment conversion against price pressure before the next intake cycle.",
                        "evidence_refs": ["sig_price_001"],
                    },
                    {
                        "rank": 2,
                        "title": "Contact the closing academy owner this week about acquiring released players and equipment",
                        "why_now": "A closure signal was detected this week and the window for a low-cost acquisition move is short.",
                        "expected_advantage": "Creates a faster route to enrollment and revenue growth through released players and assets.",
                        "evidence_refs": ["sig_close_001"],
                    },
                    {
                        "rank": 3,
                        "title": "Request one fresh competitor offer source this week before the next intake window closes",
                        "why_now": "A pricing and closure signal were detected this week, but one offer signal is still missing from the comparison set.",
                        "expected_advantage": "Improves conversion and win rate by filling the missing offer evidence before the next intake cycle.",
                        "evidence_refs": ["sig_offer_001"],
                    },
                ],
                "summary": "Three competitive actions were prioritized from stored market signals.",
            },
            "decision_summary": {"route": "proceed", "confidence": 0.86},
            "trace_run_id": "20260322T080200Z_mvp00001",
            "trace_refs": ["sig_price_001", "sig_close_001"],
        }
        validated = validate_job_result(payload)
        self.assertEqual(validated["status"], "complete")

    def test_system_observation_accepts_valid_signal(self) -> None:
        payload = {
            "signal_id": "sig_001",
            "signal_type": "pricing_change",
            "competitor": "FlowOps",
            "region": "north_cluster",
            "summary": "pricing change: FlowOps introduced a spring voucher",
            "source_ref": "source_001",
            "observed_at": "2026-03-22T08:02:00+00:00",
            "confidence": 0.84,
            "business_impact": "high",
        }
        validated = validate_system_observation(payload)
        self.assertEqual(validated["signal_type"], "pricing_change")

    def test_job_result_rejects_non_sequential_ranks(self) -> None:
        payload = {
            "job_id": "job_bad_0001",
            "app_id": "app_consultant_followup",
            "project_id": "client_acme_q2",
            "status": "complete",
            "completed_at": "2026-03-22T08:02:00+00:00",
            "result_payload": {
                "recommended_tasks": [
                    {
                        "rank": 2,
                        "title": "Late-ranked task",
                        "why_now": "A signal exists.",
                        "expected_advantage": "Still invalid because the ordering is wrong.",
                        "evidence_refs": ["sig_bad_001"],
                    },
                    {
                        "rank": 3,
                        "title": "Publish one competitor comparison block this week before the next intake closes",
                        "why_now": "A pricing signal changed this week and the comparison frame is moving.",
                        "expected_advantage": "Improves conversion in the next intake cycle by answering the changed competitor comparison frame.",
                        "evidence_refs": ["sig_bad_002"],
                    },
                    {
                        "rank": 4,
                        "title": "Request one pricing proof source this week before the next buyer decision",
                        "why_now": "A signal gap remains in the comparison set this week.",
                        "expected_advantage": "Improves win rate this week by filling the remaining pricing evidence gap before buyers decide.",
                        "evidence_refs": ["sig_bad_003"],
                    },
                ],
                "summary": "Bad ordering",
            },
        }
        with self.assertRaises(ValidationError) as context:
            validate_job_result(payload)
        self.assertIn("sequential", str(context.exception))

    def test_job_result_rejects_generic_task_titles(self) -> None:
        payload = {
            "job_id": "job_bad_0002",
            "app_id": "app_consultant_followup",
            "project_id": "client_acme_q2",
            "status": "complete",
            "completed_at": "2026-03-22T08:02:00+00:00",
            "result_payload": {
                "recommended_tasks": [
                    {
                        "rank": 1,
                        "title": "Adjust pricing strategy",
                        "why_now": "A competitor pricing change was detected this week.",
                        "expected_advantage": "Protects enrollment conversion against price pressure.",
                        "evidence_refs": ["sig_bad_002"],
                    },
                    {
                        "rank": 2,
                        "title": "Publish one comparison offer this week before the next intake cycle closes",
                        "why_now": "A competitor pricing change was detected this week.",
                        "expected_advantage": "Improves enrollment conversion before the next intake cycle.",
                        "evidence_refs": ["sig_bad_003"],
                    },
                    {
                        "rank": 3,
                        "title": "Request one competitor offer page this week before buyers lock their shortlist",
                        "why_now": "A competitor pricing change was detected this week.",
                        "expected_advantage": "Improves win rate this week by filling the missing competitor offer evidence.",
                        "evidence_refs": ["sig_bad_004"],
                    },
                ],
                "summary": "Bad task quality",
            },
        }
        with self.assertRaises(ValidationError) as context:
            validate_job_result(payload)
        self.assertIn("concrete action", str(context.exception))

    def test_feedback_accepts_done_vocabulary(self) -> None:
        payload = {
            "feedback_id": "feedback_mvp_0001",
            "job_id": "job_mvp_0001",
            "app_id": "app_consultant_followup",
            "project_id": "client_acme_q2",
            "feedback_type": "task_response",
            "submitted_at": "2026-03-22T08:10:00+00:00",
            "user_action": "edited",
            "feedback_payload": {
                "done": ["Send recap email to the client"],
                "edited": ["Draft the revised milestone plan with updated target dates"],
                "declined": ["Confirm ownership for the open action items"],
                "commented": [],
                "deleted_silent": [],
                "deleted_with_annotation": [],
                "held_for_later": [],
            },
            "actor_id": "consultant_001",
            "linked_result_status": "complete",
        }
        validated = validate_feedback(payload)
        self.assertEqual(validated["feedback_payload"]["done"][0], "Send recap email to the client")

    def test_feedback_rejects_old_accepted_vocabulary(self) -> None:
        payload = {
            "feedback_id": "feedback_bad_0001",
            "job_id": "job_mvp_0001",
            "app_id": "app_consultant_followup",
            "project_id": "client_acme_q2",
            "feedback_type": "task_response",
            "submitted_at": "2026-03-22T08:10:00+00:00",
            "user_action": "edited",
            "feedback_payload": {
                "accepted": ["Send recap email to the client"],
                "edited": [],
                "declined": [],
                "commented": [],
                "deleted_silent": [],
                "deleted_with_annotation": [],
                "held_for_later": [],
            },
        }
        with self.assertRaises(ValidationError) as context:
            validate_feedback(payload)
        self.assertIn("missing required field 'done'", str(context.exception))


if __name__ == "__main__":
    unittest.main()

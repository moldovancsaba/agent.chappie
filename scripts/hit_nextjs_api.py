import urllib.request
import json
import time
import uuid

url = "http://localhost:3010/api/feedback"

payload = {
    "feedback_id": f"api_proof_{uuid.uuid4().hex[:8]}",
    "job_id": "job_api_001",
    "app_id": "consultant_followup_web",
    "project_id": "project_api_proof_001",
    "feedback_type": "task_response",
    "submitted_at": "2026-03-25T12:00:00.000Z",
    "user_action": "declined",
    "feedback_payload": {
        "done": [],
        "edited": [],
        "declined": ["task_2"],
        "commented": [],
        "deleted_silent": [],
        "deleted_with_annotation": [],
        "held_for_later": []
    },
    "task_feedback_items": [
        {
            "feedback_id": f"task_2_{uuid.uuid4().hex[:8]}",
            "rank": 2,
            "original_title": "Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise before buyers default to it",
            "original_expected_advantage": "Increases conversion for active buyers this week by answering Fortitude AI's customer testimonials in the pricing page.",
            "feedback_type": "declined"
        }
    ],
    "current_tasks": [
        {
            "rank": 1,
            "title": "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers",
            "why_now": "Because the competitor launched a new pricing model.",
            "expected_advantage": "Increases conversion for new intake by answering expectations.",
            "evidence_refs": ["ref1"]
        },
        {
            "rank": 2,
            "title": "Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise before buyers default to it",
            "why_now": "The rival just launched a discount campaign.",
            "expected_advantage": "Increases conversion for active buyers this week by addressing competitors.",
            "evidence_refs": ["ref2"]
        },
        {
            "rank": 3,
            "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
            "why_now": "New pricing tier changes detected.",
            "expected_advantage": "Eliminates hesitation for buyers to protect our margin and revenue.",
            "evidence_refs": ["ref3"]
        }
    ]
}

print("POSTing feedback to NextJS API Boundary:", url)
print("Request Body:")
print(json.dumps(payload, indent=2))
print("\n---\n")

try:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        print("Response Status:", response.status)
        print("Response Body:")
        print(json.dumps(json.loads(response.read().decode('utf-8')), indent=2))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print(e.read().decode('utf-8'))
except Exception as e:
    print("Error hitting API:", e)

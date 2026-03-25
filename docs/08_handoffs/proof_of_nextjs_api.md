POSTing feedback to NextJS API Boundary: http://localhost:3010/api/feedback
Request Body:
{
  "feedback_id": "api_proof_77e5ac24",
  "job_id": "job_api_001",
  "app_id": "consultant_followup_web",
  "project_id": "project_api_proof_001",
  "feedback_type": "task_response",
  "submitted_at": "2026-03-25T12:00:00.000Z",
  "user_action": "declined",
  "feedback_payload": {
    "done": [],
    "edited": [],
    "declined": [
      "task_2"
    ],
    "commented": [],
    "deleted_silent": [],
    "deleted_with_annotation": [],
    "held_for_later": []
  },
  "task_feedback_items": [
    {
      "feedback_id": "task_2_805bda10",
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
      "evidence_refs": [
        "ref1"
      ]
    },
    {
      "rank": 2,
      "title": "Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise before buyers default to it",
      "why_now": "The rival just launched a discount campaign.",
      "expected_advantage": "Increases conversion for active buyers this week by addressing competitors.",
      "evidence_refs": [
        "ref2"
      ]
    },
    {
      "rank": 3,
      "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
      "why_now": "New pricing tier changes detected.",
      "expected_advantage": "Eliminates hesitation for buyers to protect our margin and revenue.",
      "evidence_refs": [
        "ref3"
      ]
    }
  ]
}

---

Response Status: 200
Response Body:
{
  "status": "saved",
  "feedback_id": "api_proof_77e5ac24",
  "regenerated": {
    "job_result": {
      "job_id": "job_api_001",
      "app_id": "consultant_followup_web",
      "project_id": "project_api_proof_001",
      "status": "complete",
      "completed_at": "2026-03-25T09:11:23.801963Z",
      "result_payload": {
        "recommended_tasks": [
          {
            "rank": 1,
            "title": "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers",
            "why_now": "Because the competitor launched a new pricing model.",
            "expected_advantage": "Increases conversion for new intake by answering expectations.",
            "evidence_refs": [
              "ref1"
            ],
            "is_next_best_action": true,
            "priority_label": "critical"
          },
          {
            "rank": 2,
            "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
            "why_now": "New pricing tier changes detected.",
            "expected_advantage": "Eliminates hesitation for buyers to protect our margin and revenue.",
            "evidence_refs": [
              "ref3"
            ],
            "is_next_best_action": false,
            "priority_label": "high"
          },
          {
            "rank": 3,
            "title": "Add pricing comparison block on pricing page this week before the competitor using pricing comparison sets expectations for buyers",
            "why_now": "We detected pricing or onboarding pressure tied to the competitor using pricing comparison: We still need stronger pricing evidence before we can recommend a tighter commercial response. If you do not answer it in the pricing page, buyers can adopt the competitor using pricing comparison's lower-friction commercial expectation first.",
            "expected_advantage": "Increases conversion for active buyers this week by answering the competitor using pricing comparison's its strongest visible claim in the pricing page.",
            "evidence_refs": [
              "segment::project_api_proof_001::segment:open_questions:3"
            ],
            "task_type": "direct_competitive_move",
            "move_bucket": "pricing_or_offer_move",
            "competitor_name": "the competitor using pricing comparison",
            "target_channel": "pricing page",
            "target_segment": "buyers",
            "mechanism": "Add a side-by-side pricing comparison and onboarding FAQ that lowers perceived adoption friction.",
            "done_definition": "The live pricing comparison block on the pricing page explicitly answers the competitor using pricing comparison's pricing or onboarding claim and is visible to active buyers.",
            "execution_steps": [
              "Pull the exact pricing, onboarding, and proof claims from the linked source set, especially the claim behind this excerpt: We still need stronger pricing evidence before we can recommend a tighter commercial response.",
              "Turn those claims into a live pricing comparison block on the pricing page using this mechanism: Add a side-by-side pricing comparison and onboarding FAQ that lowers perceived adoption friction..",
              "Publish the updated pricing comparison block on the pricing page this week so active buyers see it in the pricing page.",
              "Send the updated pricing comparison block on the pricing page into live comparisons and check whether the competitor using pricing comparison-style pricing or onboarding objections drop."
            ],
            "supporting_signal_refs": [],
            "supporting_segment_ids": [
              "project_api_proof_001::segment:open_questions:3"
            ],
            "supporting_signal_scores": [],
            "supporting_segment_scores": [
              {
                "segment_id": "project_api_proof_001::segment:open_questions:3",
                "relevance_score": 1.2
              }
            ],
            "supporting_source_refs": [],
            "supporting_source_scores": [],
            "strongest_evidence_excerpt": "We still need stronger pricing evidence before we can recommend a tighter commercial response.",
            "is_next_best_action": false,
            "priority_label": "normal",
            "confidence_class": "strong_action",
            "best_before": "2026-03-27"
          }
        ],
        "summary": "Merged retained tasks with generated replacements."
      },
      "decision_summary": {
        "route": "proceed",
        "confidence": 0.74
      }
    },
    "workspace": {
      "project_id": "project_api_proof_001",
      "recent_sources": [],
      "recent_activity": [],
      "market_summary": {
        "pricing_changes": 0,
        "closure_signals": 0,
        "offer_signals": 0
      },
      "fact_chips": [],
      "draft_segments": [
        {
          "segment_id": "project_api_proof_001::segment:open_questions",
          "segment_kind": "open_questions",
          "title": "Open Questions",
          "segment_text": "Region is still weakly inferred. Add one source with explicit geography or local market scope.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.99,
          "confidence": 0.55
        },
        {
          "segment_id": "project_api_proof_001::segment:open_questions:2",
          "segment_kind": "open_questions",
          "title": "Open Questions",
          "segment_text": "No clear named competitors were extracted. A denser market source would improve competitor confidence.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.93,
          "confidence": 0.55
        },
        {
          "segment_id": "project_api_proof_001::segment:open_questions:3",
          "segment_kind": "open_questions",
          "title": "Open Questions",
          "segment_text": "We still need stronger pricing evidence before we can recommend a tighter commercial response.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.93,
          "confidence": 0.55
        },
        {
          "segment_id": "project_api_proof_001::segment:open_questions:4",
          "segment_kind": "open_questions",
          "title": "Open Questions",
          "segment_text": "We still need a clearer buyer-facing offer or positioning signal before we can sharpen the response channel.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.93,
          "confidence": 0.55
        },
        {
          "segment_id": "project_api_proof_001::segment:competitors_detected",
          "segment_kind": "competitors_detected",
          "title": "Competitors Detected",
          "segment_text": "No named competitors have been extracted with enough confidence yet.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.73,
          "confidence": 0.28
        },
        {
          "segment_id": "project_api_proof_001::segment:offer_positioning",
          "segment_kind": "offer_positioning",
          "title": "Offer / Positioning",
          "segment_text": "No clear positioning or offer observations have been extracted yet.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.7,
          "confidence": 0.25
        },
        {
          "segment_id": "project_api_proof_001::segment:pricing_packaging",
          "segment_kind": "pricing_packaging",
          "title": "Pricing / Packaging",
          "segment_text": "No pricing or packaging observations are strong enough yet.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.69,
          "confidence": 0.24
        },
        {
          "segment_id": "project_api_proof_001::segment:market_summary",
          "segment_kind": "market_summary",
          "title": "Market Summary",
          "segment_text": "No market synthesis has been derived yet.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.67,
          "confidence": 0.22
        },
        {
          "segment_id": "project_api_proof_001::segment:proof_signals",
          "segment_kind": "proof_signals",
          "title": "Proof Signals",
          "segment_text": "No proof signals have been extracted yet.",
          "source_refs": [],
          "evidence_refs": [],
          "importance": 0.66,
          "confidence": 0.21
        }
      ],
      "competitive_snapshot": {
        "pricing_position": "No pricing pressure detected yet.",
        "acquisition_strategy_comparison": "No competitor is clearly winning on low-friction acquisition yet.",
        "current_weakness": "No dominant weakness is strongly evidenced yet.",
        "active_threats": [
          "No immediate competitive threats are strongly evidenced yet."
        ],
        "immediate_opportunities": [
          "Confirm or edit the cards above if any inference is wrong.",
          "Add one source that resolves the highest-confidence gap first."
        ],
        "reference_competitor": "Comparison set still forming",
        "risk_level": "low"
      },
      "knowledge_summary": [],
      "monitor_jobs": [
        {
          "job_name": "continuous_observation_loop",
          "status": "idle",
          "last_run_at": "2026-03-25T09:11:22.696Z",
          "last_source_ref": null
        }
      ],
      "knowledge_cards": [
        {
          "knowledge_id": "market_summary",
          "title": "Market Summary",
          "summary": "What the system currently knows about this market or project from the ingested sources.",
          "items": [
            "No market synthesis has been derived yet."
          ],
          "insight": "We have only a thin market picture so far, so the strongest pattern is still forming.",
          "implication": "Add one denser source if you want the next recommendation cycle to rely on something stronger than broad context.",
          "potential_moves": [
            "Compare your current positioning against the strongest pattern in the source set.",
            "Add one denser source if the market story still feels incomplete."
          ],
          "source_refs": [],
          "evidence_refs": [],
          "confidence": 0.22,
          "support_count": 0,
          "strongest_excerpt": null,
          "annotation_status": "pending",
          "confidence_source": "extracted",
          "audit": {
            "original_value": {
              "title": "Market Summary",
              "summary": "What the system currently knows about this market or project from the ingested sources.",
              "items": [
                "No market synthesis has been derived yet."
              ],
              "insight": "We have only a thin market picture so far, so the strongest pattern is still forming.",
              "implication": "Add one denser source if you want the next recommendation cycle to rely on something stronger than broad context.",
              "potential_moves": [
                "Compare your current positioning against the strongest pattern in the source set.",
                "Add one denser source if the market story still feels incomplete."
              ]
            },
            "user_modification": null,
            "timestamp": null
          }
        },
        {
          "knowledge_id": "competitors_detected",
          "title": "Competitors Detected",
          "summary": "Named companies, schools, clubs, or products we extracted from the current source set.",
          "items": [
            "No named competitors have been extracted with enough confidence yet."
          ],
          "insight": "The source set points to the competitors most likely shaping the current comparison set.",
          "implication": "These names should anchor who you benchmark, monitor, and position against first.",
          "potential_moves": [
            "Verify whether the top named competitor is truly in your comparison set.",
            "Add one competitor-specific source if the detected list feels too thin."
          ],
          "source_refs": [],
          "evidence_refs": [],
          "confidence": 0.28,
          "support_count": 0,
          "strongest_excerpt": null,
          "annotation_status": "pending",
          "confidence_source": "extracted",
          "audit": {
            "original_value": {
              "title": "Competitors Detected",
              "summary": "Named companies, schools, clubs, or products we extracted from the current source set.",
              "items": [
                "No named competitors have been extracted with enough confidence yet."
              ],
              "insight": "The source set points to the competitors most likely shaping the current comparison set.",
              "implication": "These names should anchor who you benchmark, monitor, and position against first.",
              "potential_moves": [
                "Verify whether the top named competitor is truly in your comparison set.",
                "Add one competitor-specific source if the detected list feels too thin."
              ]
            },
            "user_modification": null,
            "timestamp": null
          }
        },
        {
          "knowledge_id": "pricing_packaging",
          "title": "Pricing / Packaging",
          "summary": "Commercial packaging and pricing observations we extracted from the current source material.",
          "items": [
            "No pricing or packaging observations are strong enough yet."
          ],
          "insight": "Packaging and onboarding language are the strongest commercial signals currently visible in the source set.",
          "implication": "If these signals keep appearing, your offer may need a clearer pricing or packaging response before buyers compare options.",
          "potential_moves": [
            "Check whether your current package framing is weaker than the source set suggests.",
            "Prepare one pricing-page adjustment if a competitor pattern keeps repeating."
          ],
          "source_refs": [],
          "evidence_refs": [],
          "confidence": 0.24,
          "support_count": 0,
          "strongest_excerpt": null,
          "annotation_status": "pending",
          "confidence_source": "extracted",
          "audit": {
            "original_value": {
              "title": "Pricing / Packaging",
              "summary": "Commercial packaging and pricing observations we extracted from the current source material.",
              "items": [
                "No pricing or packaging observations are strong enough yet."
              ],
              "insight": "Packaging and onboarding language are the strongest commercial signals currently visible in the source set.",
              "implication": "If these signals keep appearing, your offer may need a clearer pricing or packaging response before buyers compare options.",
              "potential_moves": [
                "Check whether your current package framing is weaker than the source set suggests.",
                "Prepare one pricing-page adjustment if a competitor pattern keeps repeating."
              ]
            },
            "user_modification": null,
            "timestamp": null
          }
        },
        {
          "knowledge_id": "offer_positioning",
          "title": "Offer / Positioning",
          "summary": "Offer language, positioning claims, and tactical market signals found in the sources.",
          "items": [
            "No clear positioning or offer observations have been extracted yet."
          ],
          "insight": "We can see which offer, proof, and positioning angles competitors are using to shape buyer expectations right now.",
          "implication": "If you do not answer the strongest angle in the right channel, your offer can lose urgency during live comparisons.",
          "potential_moves": [
            "Draft one response angle that answers the strongest positioning claim.",
            "Check whether your enrollment or landing-page copy reflects the same buyer pressure."
          ],
          "source_refs": [],
          "evidence_refs": [],
          "confidence": 0.25,
          "support_count": 0,
          "strongest_excerpt": null,
          "annotation_status": "pending",
          "confidence_source": "extracted",
          "audit": {
            "original_value": {
              "title": "Offer / Positioning",
              "summary": "Offer language, positioning claims, and tactical market signals found in the sources.",
              "items": [
                "No clear positioning or offer observations have been extracted yet."
              ],
              "insight": "We can see which offer, proof, and positioning angles competitors are using to shape buyer expectations right now.",
              "implication": "If you do not answer the strongest angle in the right channel, your offer can lose urgency during live comparisons.",
              "potential_moves": [
                "Draft one response angle that answers the strongest positioning claim.",
                "Check whether your enrollment or landing-page copy reflects the same buyer pressure."
              ]
            },
            "user_modification": null,
            "timestamp": null
          }
        },
        {
          "knowledge_id": "proof_signals",
          "title": "Proof Signals",
          "summary": "Trust cues, proof points, and credibility patterns extracted from the current source set.",
          "items": [
            "No proof signals have been extracted yet."
          ],
          "insight": "The source set contains proof language that may shape trust and buyer confidence.",
          "implication": "If competitors are using stronger proof than you are, they can win comparison-stage buyers even without a better product.",
          "potential_moves": [
            "Review whether your best proof matches the strongest proof signal in the market.",
            "Add a stronger proof source if the current evidence is still weak."
          ],
          "source_refs": [],
          "evidence_refs": [],
          "confidence": 0.21,
          "support_count": 0,
          "strongest_excerpt": null,
          "annotation_status": "pending",
          "confidence_source": "extracted",
          "audit": {
            "original_value": {
              "title": "Proof Signals",
              "summary": "Trust cues, proof points, and credibility patterns extracted from the current source set.",
              "items": [
                "No proof signals have been extracted yet."
              ],
              "insight": "The source set contains proof language that may shape trust and buyer confidence.",
              "implication": "If competitors are using stronger proof than you are, they can win comparison-stage buyers even without a better product.",
              "potential_moves": [
                "Review whether your best proof matches the strongest proof signal in the market.",
                "Add a stronger proof source if the current evidence is still weak."
              ]
            },
            "user_modification": null,
            "timestamp": null
          }
        },
        {
          "knowledge_id": "open_questions",
          "title": "Open Questions",
          "summary": "Weak-confidence areas and unresolved questions the operator may want to confirm or correct.",
          "items": [
            "Region is still weakly inferred. Add one source with explicit geography or local market scope.",
            "No clear named competitors were extracted. A denser market source would improve competitor confidence.",
            "We still need stronger pricing evidence before we can recommend a tighter commercial response.",
            "We still need a clearer buyer-facing offer or positioning signal before we can sharpen the response channel."
          ],
          "insight": "The system still has unresolved areas that could change recommendation quality.",
          "implication": "Correcting these gaps will improve future task precision and reduce weak inference.",
          "potential_moves": [
            "Confirm or edit the cards above if any inference is wrong.",
            "Add one source that resolves the highest-confidence gap first."
          ],
          "source_refs": [],
          "evidence_refs": [],
          "confidence": 0.55,
          "support_count": 4,
          "strongest_excerpt": null,
          "annotation_status": "pending",
          "confidence_source": "extracted",
          "audit": {
            "original_value": {
              "title": "Open Questions",
              "summary": "Weak-confidence areas and unresolved questions the operator may want to confirm or correct.",
              "items": [
                "Region is still weakly inferred. Add one source with explicit geography or local market scope.",
                "No clear named competitors were extracted. A denser market source would improve competitor confidence.",
                "We still need stronger pricing evidence before we can recommend a tighter commercial response.",
                "We still need a clearer buyer-facing offer or positioning signal before we can sharpen the response channel."
              ],
              "insight": "The system still has unresolved areas that could change recommendation quality.",
              "implication": "Correcting these gaps will improve future task precision and reduce weak inference.",
              "potential_moves": [
                "Confirm or edit the cards above if any inference is wrong.",
                "Add one source that resolves the highest-confidence gap first."
              ]
            },
            "user_modification": null,
            "timestamp": null
          }
        }
      ],
      "source_cards": [],
      "managed_sources": [],
      "managed_jobs": []
    }
  }
}

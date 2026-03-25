# LIVE SYSTEM PROOF: Task Learning Loop
## CASE 1 — Decline and replace
### 1. Real job result with 3 tasks (Before Task Array)
```json
[
  {
    "rank": 1,
    "title": "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers",
    "task_type": "direct_competitive_move"
  },
  {
    "rank": 2,
    "title": "Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise before buyers default to it",
    "task_type": "tactical_response"
  },
  {
    "rank": 3,
    "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
    "task_type": "general_business_value"
  }
]
```
### 2. Decline task #2
Declining: `Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise before buyers default to it`
### 3 & 4. Updated checklist (After Task Array), Exactly 3 tasks, Not a near-duplicate
```json
[
  {
    "rank": 1,
    "title": "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers",
    "task_type": "direct_competitive_move"
  },
  {
    "rank": 2,
    "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
    "task_type": "general_business_value"
  },
  {
    "rank": 3,
    "title": "Request one sharper source this week that resolves the strongest Market Summary gap before the next buyer decision window",
    "task_type": "exploratory_action"
  }
]
```
**Raw API Response:**
```json
{
  "job_result": {
    "job_id": "job_proof_001",
    "app_id": "consultant_followup_web",
    "project_id": "project_proof_001",
    "status": "complete",
    "completed_at": "2026-03-25T08:30:00.821863Z",
    "result_payload": {
      "recommended_tasks": [
        {
          "rank": 1,
          "title": "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers",
          "why_now": "We detected a pricing change signal in your sources tied to Fortitude AI: pricing change: pricing bundles If you do not answer that specific pressure in the pricing page, buyers can keep comparing you through Fortitude AI's claim.",
          "expected_advantage": "Increases conversion for active buyers this week by answering Fortitude AI's customer testimonials in the pricing page.",
          "evidence_refs": [
            "sig_5513eea5e597",
            "sig_d7e2ab5819fa",
            "sig_9d90880f3552",
            "sig_d25a6672bd89"
          ],
          "task_type": "direct_competitive_move",
          "move_bucket": "pricing_or_offer_move",
          "competitor_name": "Fortitude AI",
          "target_channel": "pricing page",
          "target_segment": "buyers",
          "mechanism": "Add a side-by-side pricing comparison and onboarding FAQ that lowers perceived adoption friction.",
          "done_definition": "The live pricing comparison block and onboarding FAQ on the pricing page explicitly answers Fortitude AI's pricing or onboarding claim and is visible to active buyers.",
          "execution_steps": [
            "Pull the exact pricing, onboarding, and proof claims from source_proof_001, especially the claim behind this excerpt: customer testimonials",
            "Turn those claims into a live pricing comparison block and onboarding FAQ on the pricing page using this mechanism: Add a side-by-side pricing comparison and onboarding FAQ that lowers perceived adoption friction..",
            "Publish the updated pricing comparison block and onboarding FAQ on the pricing page this week so active buyers see it in the pricing page.",
            "Send the updated pricing comparison block and onboarding FAQ on the pricing page into live comparisons and check whether Fortitude AI-style pricing or onboarding objections drop."
          ],
          "supporting_signal_refs": [
            "sig_5513eea5e597",
            "sig_d7e2ab5819fa",
            "sig_9d90880f3552"
          ],
          "supporting_segment_ids": [
            "project_proof_001::segment:market_summary"
          ],
          "supporting_signal_scores": [
            {
              "signal_id": "sig_5513eea5e597",
              "relevance_score": 2.24
            },
            {
              "signal_id": "sig_d7e2ab5819fa",
              "relevance_score": 2.24
            },
            {
              "signal_id": "sig_9d90880f3552",
              "relevance_score": 1.24
            }
          ],
          "supporting_segment_scores": [
            {
              "segment_id": "project_proof_001::segment:market_summary",
              "relevance_score": 1.8
            }
          ],
          "supporting_source_refs": [
            "source_proof_001"
          ],
          "supporting_source_scores": [
            {
              "source_ref": "source_proof_001",
              "relevance_score": 3.98,
              "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
            }
          ],
          "strongest_evidence_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "is_next_best_action": true,
          "priority_label": "critical",
          "confidence_class": "strong_action",
          "best_before": "2026-03-27"
        },
        {
          "rank": 2,
          "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
          "why_now": "We detected a messaging shift signal in your sources tied to the competitor using customer testimonials: messaging shift: customer testimonials If you do not answer that specific pressure in the pricing page, buyers can keep comparing you through the competitor using customer testimonials's claim.",
          "expected_advantage": "Increases conversion and win rate for hesitant buyers this week by strengthening trust signals in the pricing page before the competitor using customer testimonials hardens its customer testimonials.",
          "evidence_refs": [
            "unit::project_proof_001::134489541665258043"
          ],
          "task_type": "general_business_value",
          "move_bucket": "proof_or_trust_move",
          "competitor_name": "the competitor using customer testimonials",
          "target_channel": "pricing page",
          "target_segment": "buyers",
          "mechanism": "Add concrete proof blocks where hesitant buyers compare trust and implementation confidence.",
          "done_definition": "The live proof block in the comparison section on the pricing page contains at least two concrete proof elements that answer the trust pressure behind this task.",
          "execution_steps": [
            "Pull the strongest trust and proof patterns from source_proof_001, especially what makes the competitor using customer testimonials more credible to buyers: customer testimonials",
            "Add the planned proof block in the comparison section on the pricing page using this mechanism: Add concrete proof blocks where hesitant buyers compare trust and implementation confidence..",
            "Publish the proof block in the comparison section on the pricing page this week where hesitant buyers see it first on the pricing page.",
            "Check whether trust objections drop when buyers compare you against the competitor using customer testimonials."
          ],
          "supporting_signal_refs": [
            "sig_d25a6672bd89",
            "sig_9d90880f3552"
          ],
          "supporting_segment_ids": [
            "project_proof_001::project_proof_001::unit-cluster::1348214143625061833"
          ],
          "supporting_signal_scores": [
            {
              "signal_id": "sig_d25a6672bd89",
              "relevance_score": 2.07
            },
            {
              "signal_id": "sig_9d90880f3552",
              "relevance_score": 1.64
            }
          ],
          "supporting_segment_scores": [
            {
              "segment_id": "project_proof_001::project_proof_001::unit-cluster::1348214143625061833",
              "relevance_score": 1.2
            }
          ],
          "supporting_source_refs": [
            "source_proof_001"
          ],
          "supporting_source_scores": [
            {
              "source_ref": "source_proof_001",
              "relevance_score": 1.57,
              "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
            }
          ],
          "strongest_evidence_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "is_next_best_action": false,
          "priority_label": "high",
          "confidence_class": "moderate_action",
          "best_before": "2026-03-31"
        },
        {
          "rank": 3,
          "title": "Request one sharper source this week that resolves the strongest Market Summary gap before the next buyer decision window",
          "why_now": "We only have partial evidence from this source set, and the strongest drafted segment is still below the confident-action threshold: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "expected_advantage": "Improves conversion and task quality this week by turning a partial market picture into an evidence-backed move before the next decision window closes.",
          "evidence_refs": [
            "sig_5513eea5e597",
            "sig_d7e2ab5819fa",
            "sig_9d90880f3552",
            "sig_d25a6672bd89"
          ],
          "task_type": "exploratory_action",
          "move_bucket": "information_request",
          "is_next_best_action": false,
          "priority_label": "normal",
          "confidence_class": "exploratory_action",
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
    "project_id": "project_proof_001",
    "recent_sources": [
      {
        "source_ref": "source_proof_001",
        "source_kind": "manual_text",
        "created_at": "2026-03-25T08:30:00.794Z",
        "preview": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
      }
    ],
    "recent_activity": [
      {
        "signal_id": "sig_5513eea5e597",
        "signal_type": "pricing_change",
        "summary": "pricing change: pricing bundles",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_d7e2ab5819fa",
        "signal_type": "offer",
        "summary": "offer: trial offers",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_9d90880f3552",
        "signal_type": "messaging_shift",
        "summary": "messaging shift: customer testimonials",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_d25a6672bd89",
        "signal_type": "proof_signal",
        "summary": "proof signal: customer testimonials",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      }
    ],
    "market_summary": {
      "pricing_changes": 1,
      "closure_signals": 0,
      "offer_signals": 1
    },
    "fact_chips": [
      {
        "fact_id": "pricing:1",
        "category": "pricing",
        "label": "Fortitude AI changed pricing or packaging terms in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ]
      },
      {
        "fact_id": "offer:2",
        "category": "offer",
        "label": "Fortitude AI is using offer-led acquisition pressure in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa"
        ]
      },
      {
        "fact_id": "positioning:3",
        "category": "positioning",
        "label": "Fortitude AI is shifting buyer-facing positioning in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_9d90880f3552"
        ]
      },
      {
        "fact_id": "proof:4",
        "category": "proof",
        "label": "Fortitude AI is leaning on proof signals to win comparison-stage buyers.",
        "confidence": 0.67,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ]
      },
      {
        "fact_id": "competitor:5",
        "category": "competitor",
        "label": "Fortitude AI.",
        "confidence": 0.74,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "pricing:6",
        "category": "pricing",
        "label": "Onboarding terms are part of the commercial comparison set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "positioning:7",
        "category": "positioning",
        "label": "AI or automation-led positioning appears in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:8",
        "category": "proof",
        "label": "Proof language like testimonials or customer examples appears in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:9",
        "category": "proof",
        "label": "Integration claims are being used as proof in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "pricing:10",
        "category": "pricing",
        "label": "Pricing bundles, packaging terms, or onboarding friction appear in the source set.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "offer:11",
        "category": "offer",
        "label": "Offer-led acquisition pressure appears in the source set.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:12",
        "category": "proof",
        "label": "Proof language appears in the source set and may shape buyer trust.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      }
    ],
    "draft_segments": [
      {
        "segment_id": "project_proof_001::segment:market_summary",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:offer_positioning",
        "segment_kind": "offer_positioning",
        "title": "Offer / Positioning",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "importance": 0.99,
        "confidence": 0.73
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.99,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::segment:open_questions",
        "segment_kind": "open_questions",
        "title": "Open Questions",
        "segment_text": "Region is still weakly inferred. Add one source with explicit geography or local market scope.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa"
        ],
        "importance": 0.99,
        "confidence": 0.55
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::5383985053033446201",
        "segment_kind": "pricing",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::641951966098855969"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::5852167938226779011",
        "segment_kind": "offer",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8878751836415055745",
          "unit::project_proof_001::3875988506588741544"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::3883122624185337083",
        "segment_kind": "positioning",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::1168531468853054372",
          "unit::project_proof_001::1422392661991471609"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2380215096829055025",
        "segment_kind": "pricing_change",
        "title": "Pricing Page move",
        "segment_text": "pricing change: pricing bundles",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::4400791477287718107"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::736575020236149819",
        "segment_kind": "offer",
        "title": "Homepage Comparison Section move",
        "segment_text": "offer: trial offers",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::3893769257179263308"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::1348214143625061833",
        "segment_kind": "messaging_shift",
        "title": "Proof Block on Homepage Comparison Section",
        "segment_text": "messaging shift: customer testimonials",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::134489541665258043"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2377628532808287105",
        "segment_kind": "competitor",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8211504938006529767"
        ],
        "importance": 0.97,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::1586898657738614715",
        "segment_kind": "proof",
        "title": "Comparison Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::7758437512965692673"
        ],
        "importance": 0.97,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2240546210450344208",
        "segment_kind": "proof_signal",
        "title": "Proof Block on Homepage Comparison Section",
        "segment_text": "proof signal: customer testimonials",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8788776240143824059"
        ],
        "importance": 0.97,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::8423934417481757919",
        "segment_kind": "pricing",
        "title": "Comparison Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::3888137783271425249"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2249912470706123175",
        "segment_kind": "proof",
        "title": "Proof Block on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8047142767914109873"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::6880175130638987156",
        "segment_kind": "proof",
        "title": "Proof Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::7510327209811218106"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::6599538769777884571",
        "segment_kind": "pricing",
        "title": "Onboarding Friction pressure",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::2466290138736625818"
        ],
        "importance": 0.97,
        "confidence": 0.59
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:1",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Integration is reinforcing integration claims as a live comparison claim.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:2",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Proof is changing expectations through proof block on the pricing page.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:3",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Fortitude AI is contributing to proof pressure in the active market.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:4",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Onboarding is contributing to pricing pressure in the active market.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:1",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Fortitude AI",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:2",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Onboarding",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:3",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Proof",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:4",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Integration",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:5",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Offer",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:offer_positioning:1",
        "segment_kind": "offer_positioning",
        "title": "Offer / Positioning",
        "segment_text": "Homepage Comparison Section move: offer: trial offers",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "importance": 0.95,
        "confidence": 0.73
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:1",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:2",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:3",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals:1",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals:2",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::fact:pricing:1",
        "segment_kind": "pricing",
        "title": "Pricing",
        "segment_text": "Fortitude AI changed pricing or packaging terms in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:offer:2",
        "segment_kind": "offer",
        "title": "Offer",
        "segment_text": "Fortitude AI is using offer-led acquisition pressure in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:positioning:3",
        "segment_kind": "positioning",
        "title": "Positioning",
        "segment_text": "Fortitude AI is shifting buyer-facing positioning in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_9d90880f3552"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:competitor:5",
        "segment_kind": "competitor",
        "title": "Competitor",
        "segment_text": "Fortitude AI.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [],
        "importance": 0.92,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::fact:proof:4",
        "segment_kind": "proof",
        "title": "Proof",
        "segment_text": "Fortitude AI is leaning on proof signals to win comparison-stage buyers.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.92,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::fact:pricing:6",
        "segment_kind": "pricing",
        "title": "Pricing",
        "segment_text": "Onboarding terms are part of the commercial comparison set.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [],
        "importance": 0.92,
        "confidence": 0.61
      }
    ],
    "competitive_snapshot": {
      "pricing_position": "Fortitude AI is resetting buyer price expectations in region unknown, which exposes any weaker entry offer you still show.",
      "acquisition_strategy_comparison": "Fortitude AI is lowering switching friction in region unknown through offer-led acquisition.",
      "current_weakness": "Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.",
      "active_threats": [
        "Fortitude AI is shaping live comparisons through this visible pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "Fortitude AI is changing pricing pressure in region unknown.",
        "Fortitude AI is using a direct offer to win buyers in region unknown."
      ],
      "immediate_opportunities": [
        "Answer both Fortitude AI's offer pressure and Fortitude AI's pricing move with one visible comparison response.",
        "Confirm or edit the cards above if any inference is wrong.",
        "Add one source that resolves the highest-confidence gap first."
      ],
      "reference_competitor": "Fortitude AI",
      "risk_level": "high"
    },
    "knowledge_summary": [
      {
        "competitor": "Fortitude AI",
        "region": "region_unknown",
        "latest_observed_at": "2026-03-25T08:30:00.796421Z"
      }
    ],
    "monitor_jobs": [
      {
        "job_name": "continuous_observation_loop",
        "status": "processed",
        "last_run_at": "2026-03-25T08:30:00.801Z",
        "last_source_ref": "source_proof_001"
      }
    ],
    "knowledge_cards": [
      {
        "knowledge_id": "market_summary",
        "title": "Market Summary",
        "summary": "What the system currently knows about this market or project from the ingested sources.",
        "items": [
          "Integration is reinforcing integration claims as a live comparison claim.",
          "Proof is changing expectations through proof block on the pricing page.",
          "Fortitude AI is contributing to proof pressure in the active market.",
          "Onboarding is contributing to pricing pressure in the active market."
        ],
        "insight": "We can already see the market leaning on pricing pressure, with Fortitude AI helping set buyer expectations.",
        "implication": "If you do not answer the current pricing and onboarding comparison directly, buyers can adopt the competitor's lower-friction frame before you respond.",
        "potential_moves": [
          "Compare your current positioning against the strongest pattern in the source set.",
          "Add one denser source if the market story still feels incomplete."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "confidence": 0.78,
        "support_count": 12,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Market Summary",
            "summary": "What the system currently knows about this market or project from the ingested sources.",
            "items": [
              "Integration is reinforcing integration claims as a live comparison claim.",
              "Proof is changing expectations through proof block on the pricing page.",
              "Fortitude AI is contributing to proof pressure in the active market.",
              "Onboarding is contributing to pricing pressure in the active market."
            ],
            "insight": "We can already see the market leaning on pricing pressure, with Fortitude AI helping set buyer expectations.",
            "implication": "If you do not answer the current pricing and onboarding comparison directly, buyers can adopt the competitor's lower-friction frame before you respond.",
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
          "Fortitude AI",
          "Onboarding",
          "Proof",
          "Integration",
          "Offer"
        ],
        "insight": "The source set points to the competitors most likely shaping the current comparison set.",
        "implication": "These names should anchor who you benchmark, monitor, and position against first.",
        "potential_moves": [
          "Verify whether the top named competitor is truly in your comparison set.",
          "Add one competitor-specific source if the detected list feels too thin."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "confidence": 0.74,
        "support_count": 5,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Competitors Detected",
            "summary": "Named companies, schools, clubs, or products we extracted from the current source set.",
            "items": [
              "Fortitude AI",
              "Onboarding",
              "Proof",
              "Integration",
              "Offer"
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
          "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
        ],
        "insight": "Packaging and onboarding language are the strongest commercial signals currently visible in the source set.",
        "implication": "If these signals keep appearing, your offer may need a clearer pricing or packaging response before buyers compare options.",
        "potential_moves": [
          "Check whether your current package framing is weaker than the source set suggests.",
          "Prepare one pricing-page adjustment if a competitor pattern keeps repeating."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "confidence": 0.71,
        "support_count": 3,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Pricing / Packaging",
            "summary": "Commercial packaging and pricing observations we extracted from the current source material.",
            "items": [
              "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
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
          "Homepage Comparison Section move: offer: trial offers"
        ],
        "insight": "We can see which offer, proof, and positioning angles competitors are using to shape buyer expectations right now.",
        "implication": "If you do not answer the strongest angle in the right channel, your offer can lose urgency during live comparisons.",
        "potential_moves": [
          "Draft one response angle that answers the strongest positioning claim.",
          "Check whether your enrollment or landing-page copy reflects the same buyer pressure."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "confidence": 0.73,
        "support_count": 5,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Offer / Positioning",
            "summary": "Offer language, positioning claims, and tactical market signals found in the sources.",
            "items": [
              "Homepage Comparison Section move: offer: trial offers"
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
          "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
        ],
        "insight": "The source set contains proof language that may shape trust and buyer confidence.",
        "implication": "If competitors are using stronger proof than you are, they can win comparison-stage buyers even without a better product.",
        "potential_moves": [
          "Review whether your best proof matches the strongest proof signal in the market.",
          "Add a stronger proof source if the current evidence is still weak."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "confidence": 0.69,
        "support_count": 4,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Proof Signals",
            "summary": "Trust cues, proof points, and credibility patterns extracted from the current source set.",
            "items": [
              "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
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
          "Region is still weakly inferred. Add one source with explicit geography or local market scope."
        ],
        "insight": "The system still has unresolved areas that could change recommendation quality.",
        "implication": "Correcting these gaps will improve future task precision and reduce weak inference.",
        "potential_moves": [
          "Confirm or edit the cards above if any inference is wrong.",
          "Add one source that resolves the highest-confidence gap first."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa"
        ],
        "confidence": 0.55,
        "support_count": 1,
        "strongest_excerpt": null,
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Open Questions",
            "summary": "Weak-confidence areas and unresolved questions the operator may want to confirm or correct.",
            "items": [
              "Region is still weakly inferred. Add one source with explicit geography or local market scope."
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
    "source_cards": [
      {
        "source_ref": "source_proof_001",
        "label": "Competitive Analysis with Fortitude AI Focus",
        "source_kind": "manual_text",
        "status": "processed",
        "processing_summary": "We wrote three judged actions from the drafted knowledge segments and available evidence.",
        "last_used_in_checklist": true,
        "signal_count": 4,
        "key_takeaway": "A competitor is pressing on homepage comparison section with proof block shaped around the customer testimonials claim.",
        "business_impact": "If you do not answer a competitor's customer testimonials claim in the homepage comparison section, your current proof block can look weaker in live comparisons.",
        "linked_tasks": [
          "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers"
        ],
        "confidence": 0.78,
        "created_at": "2026-03-25T08:30:00.794Z",
        "preview": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
      }
    ],
    "managed_sources": [],
    "managed_jobs": []
  }
}
```
---
## CASE 2 — Delete and teach
### 1 & 2. Take a task and apply 'delete and teach'
Deleting: `Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers`
### 3 & 4. Run a new job, similar task NOT generated, scoring changed
```json
[
  {
    "rank": 1,
    "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first"
  },
  {
    "rank": 2,
    "title": "Request one sharper source this week that resolves the strongest Market Summary gap before the next buyer decision window"
  },
  {
    "rank": 3,
    "title": "Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move"
  }
]
```
**Raw API Response:**
```json
{
  "job_result": {
    "job_id": "job_proof_001",
    "app_id": "consultant_followup_web",
    "project_id": "project_proof_001",
    "status": "complete",
    "completed_at": "2026-03-25T08:30:00.838052Z",
    "result_payload": {
      "recommended_tasks": [
        {
          "rank": 1,
          "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
          "why_now": "We detected a messaging shift signal in your sources tied to the competitor using customer testimonials: messaging shift: customer testimonials If you do not answer that specific pressure in the pricing page, buyers can keep comparing you through the competitor using customer testimonials's claim.",
          "expected_advantage": "Increases conversion and win rate for hesitant buyers this week by strengthening trust signals in the pricing page before the competitor using customer testimonials hardens its customer testimonials.",
          "evidence_refs": [
            "unit::project_proof_001::134489541665258043"
          ],
          "task_type": "general_business_value",
          "move_bucket": "proof_or_trust_move",
          "competitor_name": "the competitor using customer testimonials",
          "target_channel": "pricing page",
          "target_segment": "buyers",
          "mechanism": "Add concrete proof blocks where hesitant buyers compare trust and implementation confidence.",
          "done_definition": "The live proof block in the comparison section on the pricing page contains at least two concrete proof elements that answer the trust pressure behind this task.",
          "execution_steps": [
            "Pull the strongest trust and proof patterns from source_proof_001, especially what makes the competitor using customer testimonials more credible to buyers: customer testimonials",
            "Add the planned proof block in the comparison section on the pricing page using this mechanism: Add concrete proof blocks where hesitant buyers compare trust and implementation confidence..",
            "Publish the proof block in the comparison section on the pricing page this week where hesitant buyers see it first on the pricing page.",
            "Check whether trust objections drop when buyers compare you against the competitor using customer testimonials."
          ],
          "supporting_signal_refs": [
            "sig_d25a6672bd89",
            "sig_9d90880f3552"
          ],
          "supporting_segment_ids": [
            "project_proof_001::project_proof_001::unit-cluster::1348214143625061833"
          ],
          "supporting_signal_scores": [
            {
              "signal_id": "sig_d25a6672bd89",
              "relevance_score": 2.07
            },
            {
              "signal_id": "sig_9d90880f3552",
              "relevance_score": 1.64
            }
          ],
          "supporting_segment_scores": [
            {
              "segment_id": "project_proof_001::project_proof_001::unit-cluster::1348214143625061833",
              "relevance_score": 1.2
            }
          ],
          "supporting_source_refs": [
            "source_proof_001"
          ],
          "supporting_source_scores": [
            {
              "source_ref": "source_proof_001",
              "relevance_score": 1.57,
              "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
            }
          ],
          "strongest_evidence_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "is_next_best_action": true,
          "priority_label": "critical",
          "confidence_class": "moderate_action",
          "best_before": "2026-03-31"
        },
        {
          "rank": 2,
          "title": "Request one sharper source this week that resolves the strongest Market Summary gap before the next buyer decision window",
          "why_now": "We only have partial evidence from this source set, and the strongest drafted segment is still below the confident-action threshold: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "expected_advantage": "Improves conversion and task quality this week by turning a partial market picture into an evidence-backed move before the next decision window closes.",
          "evidence_refs": [
            "sig_5513eea5e597",
            "sig_d7e2ab5819fa",
            "sig_9d90880f3552",
            "sig_d25a6672bd89"
          ],
          "task_type": "exploratory_action",
          "move_bucket": "information_request",
          "is_next_best_action": false,
          "priority_label": "high",
          "confidence_class": "exploratory_action",
          "best_before": "2026-03-27"
        },
        {
          "rank": 3,
          "title": "Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move",
          "why_now": "We detected a pricing change signal in your sources tied to the competitor using onboarding promise: pricing change: pricing bundles If you do not answer that specific pressure in the same workspace, buyers can keep comparing you through the competitor using onboarding promise's claim.",
          "expected_advantage": "Improves conversion and win rate this week by resolving the missing competitor, pricing, or buyer-pressure fact that is limiting the next best action.",
          "evidence_refs": [
            "sig_5513eea5e597",
            "sig_d7e2ab5819fa"
          ],
          "task_type": "information_request",
          "move_bucket": "information_request",
          "target_segment": "buyers",
          "execution_steps": [
            "Review source_proof_001 and isolate the one missing proprietary fact we still cannot collect automatically from this evidence: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
            "Request that specific missing input in one message, not a broad research ask.",
            "Add the new evidence back into this same workspace this week so the checklist can regenerate from it.",
            "Check that the next regeneration replaces the exploratory task with a stronger action move."
          ],
          "done_definition": "The missing proprietary fact is added to this workspace and the checklist regenerates from it.",
          "supporting_signal_refs": [
            "sig_5513eea5e597",
            "sig_d7e2ab5819fa",
            "sig_9d90880f3552"
          ],
          "supporting_segment_ids": [
            "project_proof_001::segment:open_questions"
          ],
          "supporting_signal_scores": [
            {
              "signal_id": "sig_5513eea5e597",
              "relevance_score": 1.84
            },
            {
              "signal_id": "sig_d7e2ab5819fa",
              "relevance_score": 1.84
            },
            {
              "signal_id": "sig_9d90880f3552",
              "relevance_score": 1.84
            }
          ],
          "supporting_segment_scores": [
            {
              "segment_id": "project_proof_001::segment:open_questions",
              "relevance_score": 1.2
            }
          ],
          "supporting_source_refs": [
            "source_proof_001"
          ],
          "supporting_source_scores": [
            {
              "source_ref": "source_proof_001",
              "relevance_score": 0.75,
              "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
            }
          ],
          "strongest_evidence_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "is_next_best_action": false,
          "priority_label": "normal",
          "confidence_class": "moderate_action",
          "best_before": "2026-03-29"
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
    "project_id": "project_proof_001",
    "recent_sources": [
      {
        "source_ref": "source_proof_001",
        "source_kind": "manual_text",
        "created_at": "2026-03-25T08:30:00.794Z",
        "preview": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
      }
    ],
    "recent_activity": [
      {
        "signal_id": "sig_5513eea5e597",
        "signal_type": "pricing_change",
        "summary": "pricing change: pricing bundles",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_d7e2ab5819fa",
        "signal_type": "offer",
        "summary": "offer: trial offers",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_9d90880f3552",
        "signal_type": "messaging_shift",
        "summary": "messaging shift: customer testimonials",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_d25a6672bd89",
        "signal_type": "proof_signal",
        "summary": "proof signal: customer testimonials",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      }
    ],
    "market_summary": {
      "pricing_changes": 1,
      "closure_signals": 0,
      "offer_signals": 1
    },
    "fact_chips": [
      {
        "fact_id": "pricing:1",
        "category": "pricing",
        "label": "Fortitude AI changed pricing or packaging terms in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ]
      },
      {
        "fact_id": "offer:2",
        "category": "offer",
        "label": "Fortitude AI is using offer-led acquisition pressure in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa"
        ]
      },
      {
        "fact_id": "positioning:3",
        "category": "positioning",
        "label": "Fortitude AI is shifting buyer-facing positioning in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_9d90880f3552"
        ]
      },
      {
        "fact_id": "proof:4",
        "category": "proof",
        "label": "Fortitude AI is leaning on proof signals to win comparison-stage buyers.",
        "confidence": 0.67,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ]
      },
      {
        "fact_id": "competitor:5",
        "category": "competitor",
        "label": "Fortitude AI.",
        "confidence": 0.74,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "pricing:6",
        "category": "pricing",
        "label": "Onboarding terms are part of the commercial comparison set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "positioning:7",
        "category": "positioning",
        "label": "AI or automation-led positioning appears in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:8",
        "category": "proof",
        "label": "Proof language like testimonials or customer examples appears in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:9",
        "category": "proof",
        "label": "Integration claims are being used as proof in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "pricing:10",
        "category": "pricing",
        "label": "Pricing bundles, packaging terms, or onboarding friction appear in the source set.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "offer:11",
        "category": "offer",
        "label": "Offer-led acquisition pressure appears in the source set.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:12",
        "category": "proof",
        "label": "Proof language appears in the source set and may shape buyer trust.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      }
    ],
    "draft_segments": [
      {
        "segment_id": "project_proof_001::segment:market_summary",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:offer_positioning",
        "segment_kind": "offer_positioning",
        "title": "Offer / Positioning",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "importance": 0.99,
        "confidence": 0.73
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.99,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::segment:open_questions",
        "segment_kind": "open_questions",
        "title": "Open Questions",
        "segment_text": "Region is still weakly inferred. Add one source with explicit geography or local market scope.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa"
        ],
        "importance": 0.99,
        "confidence": 0.55
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::5383985053033446201",
        "segment_kind": "pricing",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::641951966098855969"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::5852167938226779011",
        "segment_kind": "offer",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8878751836415055745",
          "unit::project_proof_001::3875988506588741544"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::3883122624185337083",
        "segment_kind": "positioning",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::1168531468853054372",
          "unit::project_proof_001::1422392661991471609"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2380215096829055025",
        "segment_kind": "pricing_change",
        "title": "Pricing Page move",
        "segment_text": "pricing change: pricing bundles",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::4400791477287718107"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::736575020236149819",
        "segment_kind": "offer",
        "title": "Homepage Comparison Section move",
        "segment_text": "offer: trial offers",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::3893769257179263308"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::1348214143625061833",
        "segment_kind": "messaging_shift",
        "title": "Proof Block on Homepage Comparison Section",
        "segment_text": "messaging shift: customer testimonials",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::134489541665258043"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2377628532808287105",
        "segment_kind": "competitor",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8211504938006529767"
        ],
        "importance": 0.97,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::1586898657738614715",
        "segment_kind": "proof",
        "title": "Comparison Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::7758437512965692673"
        ],
        "importance": 0.97,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2240546210450344208",
        "segment_kind": "proof_signal",
        "title": "Proof Block on Homepage Comparison Section",
        "segment_text": "proof signal: customer testimonials",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8788776240143824059"
        ],
        "importance": 0.97,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::8423934417481757919",
        "segment_kind": "pricing",
        "title": "Comparison Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::3888137783271425249"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2249912470706123175",
        "segment_kind": "proof",
        "title": "Proof Block on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8047142767914109873"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::6880175130638987156",
        "segment_kind": "proof",
        "title": "Proof Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::7510327209811218106"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::6599538769777884571",
        "segment_kind": "pricing",
        "title": "Onboarding Friction pressure",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::2466290138736625818"
        ],
        "importance": 0.97,
        "confidence": 0.59
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:1",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Integration is reinforcing integration claims as a live comparison claim.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:2",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Proof is changing expectations through proof block on the pricing page.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:3",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Fortitude AI is contributing to proof pressure in the active market.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:4",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Onboarding is contributing to pricing pressure in the active market.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:1",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Fortitude AI",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:2",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Onboarding",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:3",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Proof",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:4",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Integration",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:5",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Offer",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:offer_positioning:1",
        "segment_kind": "offer_positioning",
        "title": "Offer / Positioning",
        "segment_text": "Homepage Comparison Section move: offer: trial offers",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "importance": 0.95,
        "confidence": 0.73
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:1",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:2",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:3",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals:1",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals:2",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::fact:pricing:1",
        "segment_kind": "pricing",
        "title": "Pricing",
        "segment_text": "Fortitude AI changed pricing or packaging terms in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:offer:2",
        "segment_kind": "offer",
        "title": "Offer",
        "segment_text": "Fortitude AI is using offer-led acquisition pressure in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:positioning:3",
        "segment_kind": "positioning",
        "title": "Positioning",
        "segment_text": "Fortitude AI is shifting buyer-facing positioning in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_9d90880f3552"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:competitor:5",
        "segment_kind": "competitor",
        "title": "Competitor",
        "segment_text": "Fortitude AI.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [],
        "importance": 0.92,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::fact:proof:4",
        "segment_kind": "proof",
        "title": "Proof",
        "segment_text": "Fortitude AI is leaning on proof signals to win comparison-stage buyers.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.92,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::fact:pricing:6",
        "segment_kind": "pricing",
        "title": "Pricing",
        "segment_text": "Onboarding terms are part of the commercial comparison set.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [],
        "importance": 0.92,
        "confidence": 0.61
      }
    ],
    "competitive_snapshot": {
      "pricing_position": "Fortitude AI is resetting buyer price expectations in region unknown, which exposes any weaker entry offer you still show.",
      "acquisition_strategy_comparison": "Fortitude AI is lowering switching friction in region unknown through offer-led acquisition.",
      "current_weakness": "Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.",
      "active_threats": [
        "Fortitude AI is shaping live comparisons through this visible pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "Fortitude AI is changing pricing pressure in region unknown.",
        "Fortitude AI is using a direct offer to win buyers in region unknown."
      ],
      "immediate_opportunities": [
        "Answer both Fortitude AI's offer pressure and Fortitude AI's pricing move with one visible comparison response.",
        "Confirm or edit the cards above if any inference is wrong.",
        "Add one source that resolves the highest-confidence gap first."
      ],
      "reference_competitor": "Fortitude AI",
      "risk_level": "high"
    },
    "knowledge_summary": [
      {
        "competitor": "Fortitude AI",
        "region": "region_unknown",
        "latest_observed_at": "2026-03-25T08:30:00.796421Z"
      }
    ],
    "monitor_jobs": [
      {
        "job_name": "continuous_observation_loop",
        "status": "processed",
        "last_run_at": "2026-03-25T08:30:00.801Z",
        "last_source_ref": "source_proof_001"
      }
    ],
    "knowledge_cards": [
      {
        "knowledge_id": "market_summary",
        "title": "Market Summary",
        "summary": "What the system currently knows about this market or project from the ingested sources.",
        "items": [
          "Integration is reinforcing integration claims as a live comparison claim.",
          "Proof is changing expectations through proof block on the pricing page.",
          "Fortitude AI is contributing to proof pressure in the active market.",
          "Onboarding is contributing to pricing pressure in the active market."
        ],
        "insight": "We can already see the market leaning on pricing pressure, with Fortitude AI helping set buyer expectations.",
        "implication": "If you do not answer the current pricing and onboarding comparison directly, buyers can adopt the competitor's lower-friction frame before you respond.",
        "potential_moves": [
          "Compare your current positioning against the strongest pattern in the source set.",
          "Add one denser source if the market story still feels incomplete."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "confidence": 0.78,
        "support_count": 12,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Market Summary",
            "summary": "What the system currently knows about this market or project from the ingested sources.",
            "items": [
              "Integration is reinforcing integration claims as a live comparison claim.",
              "Proof is changing expectations through proof block on the pricing page.",
              "Fortitude AI is contributing to proof pressure in the active market.",
              "Onboarding is contributing to pricing pressure in the active market."
            ],
            "insight": "We can already see the market leaning on pricing pressure, with Fortitude AI helping set buyer expectations.",
            "implication": "If you do not answer the current pricing and onboarding comparison directly, buyers can adopt the competitor's lower-friction frame before you respond.",
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
          "Fortitude AI",
          "Onboarding",
          "Proof",
          "Integration",
          "Offer"
        ],
        "insight": "The source set points to the competitors most likely shaping the current comparison set.",
        "implication": "These names should anchor who you benchmark, monitor, and position against first.",
        "potential_moves": [
          "Verify whether the top named competitor is truly in your comparison set.",
          "Add one competitor-specific source if the detected list feels too thin."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "confidence": 0.74,
        "support_count": 5,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Competitors Detected",
            "summary": "Named companies, schools, clubs, or products we extracted from the current source set.",
            "items": [
              "Fortitude AI",
              "Onboarding",
              "Proof",
              "Integration",
              "Offer"
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
          "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
        ],
        "insight": "Packaging and onboarding language are the strongest commercial signals currently visible in the source set.",
        "implication": "If these signals keep appearing, your offer may need a clearer pricing or packaging response before buyers compare options.",
        "potential_moves": [
          "Check whether your current package framing is weaker than the source set suggests.",
          "Prepare one pricing-page adjustment if a competitor pattern keeps repeating."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "confidence": 0.71,
        "support_count": 3,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Pricing / Packaging",
            "summary": "Commercial packaging and pricing observations we extracted from the current source material.",
            "items": [
              "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
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
          "Homepage Comparison Section move: offer: trial offers"
        ],
        "insight": "We can see which offer, proof, and positioning angles competitors are using to shape buyer expectations right now.",
        "implication": "If you do not answer the strongest angle in the right channel, your offer can lose urgency during live comparisons.",
        "potential_moves": [
          "Draft one response angle that answers the strongest positioning claim.",
          "Check whether your enrollment or landing-page copy reflects the same buyer pressure."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "confidence": 0.73,
        "support_count": 5,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Offer / Positioning",
            "summary": "Offer language, positioning claims, and tactical market signals found in the sources.",
            "items": [
              "Homepage Comparison Section move: offer: trial offers"
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
          "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
        ],
        "insight": "The source set contains proof language that may shape trust and buyer confidence.",
        "implication": "If competitors are using stronger proof than you are, they can win comparison-stage buyers even without a better product.",
        "potential_moves": [
          "Review whether your best proof matches the strongest proof signal in the market.",
          "Add a stronger proof source if the current evidence is still weak."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "confidence": 0.69,
        "support_count": 4,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Proof Signals",
            "summary": "Trust cues, proof points, and credibility patterns extracted from the current source set.",
            "items": [
              "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
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
          "Region is still weakly inferred. Add one source with explicit geography or local market scope."
        ],
        "insight": "The system still has unresolved areas that could change recommendation quality.",
        "implication": "Correcting these gaps will improve future task precision and reduce weak inference.",
        "potential_moves": [
          "Confirm or edit the cards above if any inference is wrong.",
          "Add one source that resolves the highest-confidence gap first."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa"
        ],
        "confidence": 0.55,
        "support_count": 1,
        "strongest_excerpt": null,
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Open Questions",
            "summary": "Weak-confidence areas and unresolved questions the operator may want to confirm or correct.",
            "items": [
              "Region is still weakly inferred. Add one source with explicit geography or local market scope."
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
    "source_cards": [
      {
        "source_ref": "source_proof_001",
        "label": "Competitive Analysis with Fortitude AI Focus",
        "source_kind": "manual_text",
        "status": "processed",
        "processing_summary": "We wrote three judged actions from the drafted knowledge segments and available evidence.",
        "last_used_in_checklist": true,
        "signal_count": 4,
        "key_takeaway": "A competitor is pressing on homepage comparison section with proof block shaped around the customer testimonials claim.",
        "business_impact": "If you do not answer a competitor's customer testimonials claim in the homepage comparison section, your current proof block can look weaker in live comparisons.",
        "linked_tasks": [
          "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers"
        ],
        "confidence": 0.78,
        "created_at": "2026-03-25T08:30:00.794Z",
        "preview": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
      }
    ],
    "managed_sources": [],
    "managed_jobs": []
  }
}
```
---
## CASE 3 — Comment-driven regeneration
### 1 & 2. Take a task, add comment
Commenting on: `Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move` with *'we need a trust move, not a pricing move'*
### 3 & 4. Regenerate, new task reflects constraint, comment persisted
**Updated Task Array:**
```json
[
  {
    "rank": 1,
    "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
    "move_bucket": "proof_or_trust_move"
  },
  {
    "rank": 2,
    "title": "Request one sharper source this week that resolves the strongest Market Summary gap before the next buyer decision window",
    "move_bucket": "information_request"
  },
  {
    "rank": 3,
    "title": "Add pricing comparison block and onboarding FAQ on pricing page this week before the competitor using onboarding promise sets expectations for buyers",
    "move_bucket": "pricing_or_offer_move"
  }
]
```
**Raw API Response:**
```json
{
  "job_result": {
    "job_id": "job_proof_001",
    "app_id": "consultant_followup_web",
    "project_id": "project_proof_001",
    "status": "complete",
    "completed_at": "2026-03-25T08:30:00.853619Z",
    "result_payload": {
      "recommended_tasks": [
        {
          "rank": 1,
          "title": "Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first",
          "why_now": "We detected a messaging shift signal in your sources tied to the competitor using customer testimonials: messaging shift: customer testimonials If you do not answer that specific pressure in the pricing page, buyers can keep comparing you through the competitor using customer testimonials's claim.",
          "expected_advantage": "Increases conversion and win rate for hesitant buyers this week by strengthening trust signals in the pricing page before the competitor using customer testimonials hardens its customer testimonials.",
          "evidence_refs": [
            "unit::project_proof_001::134489541665258043"
          ],
          "task_type": "general_business_value",
          "move_bucket": "proof_or_trust_move",
          "competitor_name": "the competitor using customer testimonials",
          "target_channel": "pricing page",
          "target_segment": "buyers",
          "mechanism": "Add concrete proof blocks where hesitant buyers compare trust and implementation confidence.",
          "done_definition": "The live proof block in the comparison section on the pricing page contains at least two concrete proof elements that answer the trust pressure behind this task.",
          "execution_steps": [
            "Pull the strongest trust and proof patterns from source_proof_001, especially what makes the competitor using customer testimonials more credible to buyers: customer testimonials",
            "Add the planned proof block in the comparison section on the pricing page using this mechanism: Add concrete proof blocks where hesitant buyers compare trust and implementation confidence..",
            "Publish the proof block in the comparison section on the pricing page this week where hesitant buyers see it first on the pricing page.",
            "Check whether trust objections drop when buyers compare you against the competitor using customer testimonials."
          ],
          "supporting_signal_refs": [
            "sig_d25a6672bd89",
            "sig_9d90880f3552"
          ],
          "supporting_segment_ids": [
            "project_proof_001::project_proof_001::unit-cluster::1348214143625061833"
          ],
          "supporting_signal_scores": [
            {
              "signal_id": "sig_d25a6672bd89",
              "relevance_score": 2.07
            },
            {
              "signal_id": "sig_9d90880f3552",
              "relevance_score": 1.64
            }
          ],
          "supporting_segment_scores": [
            {
              "segment_id": "project_proof_001::project_proof_001::unit-cluster::1348214143625061833",
              "relevance_score": 1.2
            }
          ],
          "supporting_source_refs": [
            "source_proof_001"
          ],
          "supporting_source_scores": [
            {
              "source_ref": "source_proof_001",
              "relevance_score": 1.57,
              "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
            }
          ],
          "strongest_evidence_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "is_next_best_action": true,
          "priority_label": "critical",
          "confidence_class": "moderate_action",
          "best_before": "2026-03-31"
        },
        {
          "rank": 2,
          "title": "Request one sharper source this week that resolves the strongest Market Summary gap before the next buyer decision window",
          "why_now": "We only have partial evidence from this source set, and the strongest drafted segment is still below the confident-action threshold: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "expected_advantage": "Improves conversion and task quality this week by turning a partial market picture into an evidence-backed move before the next decision window closes.",
          "evidence_refs": [
            "sig_5513eea5e597",
            "sig_d7e2ab5819fa",
            "sig_9d90880f3552",
            "sig_d25a6672bd89"
          ],
          "task_type": "exploratory_action",
          "move_bucket": "information_request",
          "is_next_best_action": false,
          "priority_label": "high",
          "confidence_class": "exploratory_action",
          "best_before": "2026-03-27"
        },
        {
          "rank": 3,
          "title": "Add pricing comparison block and onboarding FAQ on pricing page this week before the competitor using onboarding promise sets expectations for buyers",
          "why_now": "We detected a pricing change signal in your sources tied to the competitor using onboarding promise: pricing change: pricing bundles If you do not answer that specific pressure in the pricing page, buyers can keep comparing you through the competitor using onboarding promise's claim.",
          "expected_advantage": "Increases conversion for active buyers this week by answering the competitor using onboarding promise's its strongest visible claim in the pricing page.",
          "evidence_refs": [
            "unit::project_proof_001::4400791477287718107"
          ],
          "task_type": "direct_competitive_move",
          "move_bucket": "pricing_or_offer_move",
          "competitor_name": "the competitor using onboarding promise",
          "target_channel": "pricing page",
          "target_segment": "buyers",
          "mechanism": "Add a side-by-side pricing comparison and onboarding FAQ that lowers perceived adoption friction.",
          "done_definition": "The live pricing comparison block and onboarding FAQ on the pricing page explicitly answers the competitor using onboarding promise's pricing or onboarding claim and is visible to active buyers.",
          "execution_steps": [
            "Pull the exact pricing, onboarding, and proof claims from source_proof_001, especially the claim behind this excerpt: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
            "Turn those claims into a live pricing comparison block and onboarding FAQ on the pricing page using this mechanism: Add a side-by-side pricing comparison and onboarding FAQ that lowers perceived adoption friction..",
            "Publish the updated pricing comparison block and onboarding FAQ on the pricing page this week so active buyers see it in the pricing page.",
            "Send the updated pricing comparison block and onboarding FAQ on the pricing page into live comparisons and check whether the competitor using onboarding promise-style pricing or onboarding objections drop."
          ],
          "supporting_signal_refs": [
            "sig_5513eea5e597",
            "sig_d7e2ab5819fa"
          ],
          "supporting_segment_ids": [
            "project_proof_001::project_proof_001::unit-cluster::2380215096829055025"
          ],
          "supporting_signal_scores": [
            {
              "signal_id": "sig_5513eea5e597",
              "relevance_score": 2.44
            },
            {
              "signal_id": "sig_d7e2ab5819fa",
              "relevance_score": 1.84
            }
          ],
          "supporting_segment_scores": [
            {
              "segment_id": "project_proof_001::project_proof_001::unit-cluster::2380215096829055025",
              "relevance_score": 1.2
            }
          ],
          "supporting_source_refs": [
            "source_proof_001"
          ],
          "supporting_source_scores": [
            {
              "source_ref": "source_proof_001",
              "relevance_score": 1.67,
              "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
            }
          ],
          "strongest_evidence_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "is_next_best_action": false,
          "priority_label": "normal",
          "confidence_class": "moderate_action",
          "best_before": "2026-03-29"
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
    "project_id": "project_proof_001",
    "recent_sources": [
      {
        "source_ref": "source_proof_001",
        "source_kind": "manual_text",
        "created_at": "2026-03-25T08:30:00.794Z",
        "preview": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
      }
    ],
    "recent_activity": [
      {
        "signal_id": "sig_5513eea5e597",
        "signal_type": "pricing_change",
        "summary": "pricing change: pricing bundles",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_d7e2ab5819fa",
        "signal_type": "offer",
        "summary": "offer: trial offers",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_9d90880f3552",
        "signal_type": "messaging_shift",
        "summary": "messaging shift: customer testimonials",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      },
      {
        "signal_id": "sig_d25a6672bd89",
        "signal_type": "proof_signal",
        "summary": "proof signal: customer testimonials",
        "observed_at": "2026-03-25T08:30:00.796421Z",
        "source_ref": "source_proof_001"
      }
    ],
    "market_summary": {
      "pricing_changes": 1,
      "closure_signals": 0,
      "offer_signals": 1
    },
    "fact_chips": [
      {
        "fact_id": "pricing:1",
        "category": "pricing",
        "label": "Fortitude AI changed pricing or packaging terms in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ]
      },
      {
        "fact_id": "offer:2",
        "category": "offer",
        "label": "Fortitude AI is using offer-led acquisition pressure in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa"
        ]
      },
      {
        "fact_id": "positioning:3",
        "category": "positioning",
        "label": "Fortitude AI is shifting buyer-facing positioning in region unknown.",
        "confidence": 0.84,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_9d90880f3552"
        ]
      },
      {
        "fact_id": "proof:4",
        "category": "proof",
        "label": "Fortitude AI is leaning on proof signals to win comparison-stage buyers.",
        "confidence": 0.67,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ]
      },
      {
        "fact_id": "competitor:5",
        "category": "competitor",
        "label": "Fortitude AI.",
        "confidence": 0.74,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "pricing:6",
        "category": "pricing",
        "label": "Onboarding terms are part of the commercial comparison set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "positioning:7",
        "category": "positioning",
        "label": "AI or automation-led positioning appears in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:8",
        "category": "proof",
        "label": "Proof language like testimonials or customer examples appears in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:9",
        "category": "proof",
        "label": "Integration claims are being used as proof in the source set.",
        "confidence": 0.61,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "pricing:10",
        "category": "pricing",
        "label": "Pricing bundles, packaging terms, or onboarding friction appear in the source set.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "offer:11",
        "category": "offer",
        "label": "Offer-led acquisition pressure appears in the source set.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      },
      {
        "fact_id": "proof:12",
        "category": "proof",
        "label": "Proof language appears in the source set and may shape buyer trust.",
        "confidence": 0.59,
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": []
      }
    ],
    "draft_segments": [
      {
        "segment_id": "project_proof_001::segment:market_summary",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:offer_positioning",
        "segment_kind": "offer_positioning",
        "title": "Offer / Positioning",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "importance": 0.99,
        "confidence": 0.73
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.99,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.99,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::segment:open_questions",
        "segment_kind": "open_questions",
        "title": "Open Questions",
        "segment_text": "Region is still weakly inferred. Add one source with explicit geography or local market scope.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa"
        ],
        "importance": 0.99,
        "confidence": 0.55
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::5383985053033446201",
        "segment_kind": "pricing",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::641951966098855969"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::5852167938226779011",
        "segment_kind": "offer",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8878751836415055745",
          "unit::project_proof_001::3875988506588741544"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::3883122624185337083",
        "segment_kind": "positioning",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::1168531468853054372",
          "unit::project_proof_001::1422392661991471609"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2380215096829055025",
        "segment_kind": "pricing_change",
        "title": "Pricing Page move",
        "segment_text": "pricing change: pricing bundles",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::4400791477287718107"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::736575020236149819",
        "segment_kind": "offer",
        "title": "Homepage Comparison Section move",
        "segment_text": "offer: trial offers",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::3893769257179263308"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::1348214143625061833",
        "segment_kind": "messaging_shift",
        "title": "Proof Block on Homepage Comparison Section",
        "segment_text": "messaging shift: customer testimonials",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::134489541665258043"
        ],
        "importance": 0.97,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2377628532808287105",
        "segment_kind": "competitor",
        "title": "Pricing Page move",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8211504938006529767"
        ],
        "importance": 0.97,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::1586898657738614715",
        "segment_kind": "proof",
        "title": "Comparison Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::7758437512965692673"
        ],
        "importance": 0.97,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2240546210450344208",
        "segment_kind": "proof_signal",
        "title": "Proof Block on Homepage Comparison Section",
        "segment_text": "proof signal: customer testimonials",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8788776240143824059"
        ],
        "importance": 0.97,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::8423934417481757919",
        "segment_kind": "pricing",
        "title": "Comparison Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::3888137783271425249"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::2249912470706123175",
        "segment_kind": "proof",
        "title": "Proof Block on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::8047142767914109873"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::6880175130638987156",
        "segment_kind": "proof",
        "title": "Proof Section on Pricing Page",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::7510327209811218106"
        ],
        "importance": 0.97,
        "confidence": 0.61
      },
      {
        "segment_id": "project_proof_001::project_proof_001::unit-cluster::6599538769777884571",
        "segment_kind": "pricing",
        "title": "Onboarding Friction pressure",
        "segment_text": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "unit::project_proof_001::2466290138736625818"
        ],
        "importance": 0.97,
        "confidence": 0.59
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:1",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Integration is reinforcing integration claims as a live comparison claim.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:2",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Proof is changing expectations through proof block on the pricing page.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:3",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Fortitude AI is contributing to proof pressure in the active market.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:market_summary:4",
        "segment_kind": "market_summary",
        "title": "Market Summary",
        "segment_text": "Onboarding is contributing to pricing pressure in the active market.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.78
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:1",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Fortitude AI",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:2",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Onboarding",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:3",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Proof",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:4",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Integration",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:competitors_detected:5",
        "segment_kind": "competitors_detected",
        "title": "Competitors Detected",
        "segment_text": "Offer",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::segment:offer_positioning:1",
        "segment_kind": "offer_positioning",
        "title": "Offer / Positioning",
        "segment_text": "Homepage Comparison Section move: offer: trial offers",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "importance": 0.95,
        "confidence": 0.73
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:1",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:2",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:pricing_packaging:3",
        "segment_kind": "pricing_packaging",
        "title": "Pricing / Packaging",
        "segment_text": "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.95,
        "confidence": 0.71
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals:1",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::segment:proof_signals:2",
        "segment_kind": "proof_signals",
        "title": "Proof Signals",
        "segment_text": "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.95,
        "confidence": 0.69
      },
      {
        "segment_id": "project_proof_001::fact:pricing:1",
        "segment_kind": "pricing",
        "title": "Pricing",
        "segment_text": "Fortitude AI changed pricing or packaging terms in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:offer:2",
        "segment_kind": "offer",
        "title": "Offer",
        "segment_text": "Fortitude AI is using offer-led acquisition pressure in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:positioning:3",
        "segment_kind": "positioning",
        "title": "Positioning",
        "segment_text": "Fortitude AI is shifting buyer-facing positioning in region unknown.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_9d90880f3552"
        ],
        "importance": 0.92,
        "confidence": 0.84
      },
      {
        "segment_id": "project_proof_001::fact:competitor:5",
        "segment_kind": "competitor",
        "title": "Competitor",
        "segment_text": "Fortitude AI.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [],
        "importance": 0.92,
        "confidence": 0.74
      },
      {
        "segment_id": "project_proof_001::fact:proof:4",
        "segment_kind": "proof",
        "title": "Proof",
        "segment_text": "Fortitude AI is leaning on proof signals to win comparison-stage buyers.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "importance": 0.92,
        "confidence": 0.67
      },
      {
        "segment_id": "project_proof_001::fact:pricing:6",
        "segment_kind": "pricing",
        "title": "Pricing",
        "segment_text": "Onboarding terms are part of the commercial comparison set.",
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [],
        "importance": 0.92,
        "confidence": 0.61
      }
    ],
    "competitive_snapshot": {
      "pricing_position": "Fortitude AI is resetting buyer price expectations in region unknown, which exposes any weaker entry offer you still show.",
      "acquisition_strategy_comparison": "Fortitude AI is lowering switching friction in region unknown through offer-led acquisition.",
      "current_weakness": "Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.",
      "active_threats": [
        "Fortitude AI is shaping live comparisons through this visible pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "Fortitude AI is changing pricing pressure in region unknown.",
        "Fortitude AI is using a direct offer to win buyers in region unknown."
      ],
      "immediate_opportunities": [
        "Answer both Fortitude AI's offer pressure and Fortitude AI's pricing move with one visible comparison response.",
        "Confirm or edit the cards above if any inference is wrong.",
        "Add one source that resolves the highest-confidence gap first."
      ],
      "reference_competitor": "Fortitude AI",
      "risk_level": "high"
    },
    "knowledge_summary": [
      {
        "competitor": "Fortitude AI",
        "region": "region_unknown",
        "latest_observed_at": "2026-03-25T08:30:00.796421Z"
      }
    ],
    "monitor_jobs": [
      {
        "job_name": "continuous_observation_loop",
        "status": "processed",
        "last_run_at": "2026-03-25T08:30:00.801Z",
        "last_source_ref": "source_proof_001"
      }
    ],
    "knowledge_cards": [
      {
        "knowledge_id": "market_summary",
        "title": "Market Summary",
        "summary": "What the system currently knows about this market or project from the ingested sources.",
        "items": [
          "Integration is reinforcing integration claims as a live comparison claim.",
          "Proof is changing expectations through proof block on the pricing page.",
          "Fortitude AI is contributing to proof pressure in the active market.",
          "Onboarding is contributing to pricing pressure in the active market."
        ],
        "insight": "We can already see the market leaning on pricing pressure, with Fortitude AI helping set buyer expectations.",
        "implication": "If you do not answer the current pricing and onboarding comparison directly, buyers can adopt the competitor's lower-friction frame before you respond.",
        "potential_moves": [
          "Compare your current positioning against the strongest pattern in the source set.",
          "Add one denser source if the market story still feels incomplete."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "confidence": 0.78,
        "support_count": 12,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Market Summary",
            "summary": "What the system currently knows about this market or project from the ingested sources.",
            "items": [
              "Integration is reinforcing integration claims as a live comparison claim.",
              "Proof is changing expectations through proof block on the pricing page.",
              "Fortitude AI is contributing to proof pressure in the active market.",
              "Onboarding is contributing to pricing pressure in the active market."
            ],
            "insight": "We can already see the market leaning on pricing pressure, with Fortitude AI helping set buyer expectations.",
            "implication": "If you do not answer the current pricing and onboarding comparison directly, buyers can adopt the competitor's lower-friction frame before you respond.",
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
          "Fortitude AI",
          "Onboarding",
          "Proof",
          "Integration",
          "Offer"
        ],
        "insight": "The source set points to the competitors most likely shaping the current comparison set.",
        "implication": "These names should anchor who you benchmark, monitor, and position against first.",
        "potential_moves": [
          "Verify whether the top named competitor is truly in your comparison set.",
          "Add one competitor-specific source if the detected list feels too thin."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552",
          "sig_d25a6672bd89"
        ],
        "confidence": 0.74,
        "support_count": 5,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Competitors Detected",
            "summary": "Named companies, schools, clubs, or products we extracted from the current source set.",
            "items": [
              "Fortitude AI",
              "Onboarding",
              "Proof",
              "Integration",
              "Offer"
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
          "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
        ],
        "insight": "Packaging and onboarding language are the strongest commercial signals currently visible in the source set.",
        "implication": "If these signals keep appearing, your offer may need a clearer pricing or packaging response before buyers compare options.",
        "potential_moves": [
          "Check whether your current package framing is weaker than the source set suggests.",
          "Prepare one pricing-page adjustment if a competitor pattern keeps repeating."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597"
        ],
        "confidence": 0.71,
        "support_count": 3,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Pricing / Packaging",
            "summary": "Commercial packaging and pricing observations we extracted from the current source material.",
            "items": [
              "Pricing Page move: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Comparison Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Onboarding Friction pressure: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
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
          "Homepage Comparison Section move: offer: trial offers"
        ],
        "insight": "We can see which offer, proof, and positioning angles competitors are using to shape buyer expectations right now.",
        "implication": "If you do not answer the strongest angle in the right channel, your offer can lose urgency during live comparisons.",
        "potential_moves": [
          "Draft one response angle that answers the strongest positioning claim.",
          "Check whether your enrollment or landing-page copy reflects the same buyer pressure."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d7e2ab5819fa",
          "sig_9d90880f3552"
        ],
        "confidence": 0.73,
        "support_count": 5,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Offer / Positioning",
            "summary": "Offer language, positioning claims, and tactical market signals found in the sources.",
            "items": [
              "Homepage Comparison Section move: offer: trial offers"
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
          "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
          "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
        ],
        "insight": "The source set contains proof language that may shape trust and buyer confidence.",
        "implication": "If competitors are using stronger proof than you are, they can win comparison-stage buyers even without a better product.",
        "potential_moves": [
          "Review whether your best proof matches the strongest proof signal in the market.",
          "Add a stronger proof source if the current evidence is still weak."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_d25a6672bd89"
        ],
        "confidence": 0.69,
        "support_count": 4,
        "strongest_excerpt": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Proof Signals",
            "summary": "Trust cues, proof points, and credibility patterns extracted from the current source set.",
            "items": [
              "Proof Block on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction.",
              "Proof Section on Pricing Page: Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
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
          "Region is still weakly inferred. Add one source with explicit geography or local market scope."
        ],
        "insight": "The system still has unresolved areas that could change recommendation quality.",
        "implication": "Correcting these gaps will improve future task precision and reduce weak inference.",
        "potential_moves": [
          "Confirm or edit the cards above if any inference is wrong.",
          "Add one source that resolves the highest-confidence gap first."
        ],
        "source_refs": [
          "source_proof_001"
        ],
        "evidence_refs": [
          "sig_5513eea5e597",
          "sig_d7e2ab5819fa"
        ],
        "confidence": 0.55,
        "support_count": 1,
        "strongest_excerpt": null,
        "annotation_status": "pending",
        "confidence_source": "extracted",
        "audit": {
          "original_value": {
            "title": "Open Questions",
            "summary": "Weak-confidence areas and unresolved questions the operator may want to confirm or correct.",
            "items": [
              "Region is still weakly inferred. Add one source with explicit geography or local market scope."
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
    "source_cards": [
      {
        "source_ref": "source_proof_001",
        "label": "Competitive Analysis with Fortitude AI Focus",
        "source_kind": "manual_text",
        "status": "processed",
        "processing_summary": "We wrote three judged actions from the drafted knowledge segments and available evidence.",
        "last_used_in_checklist": true,
        "signal_count": 4,
        "key_takeaway": "A competitor is pressing on homepage comparison section with proof block shaped around the customer testimonials claim.",
        "business_impact": "If you do not answer a competitor's customer testimonials claim in the homepage comparison section, your current proof block can look weaker in live comparisons.",
        "linked_tasks": [
          "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers"
        ],
        "confidence": 0.78,
        "created_at": "2026-03-25T08:30:00.794Z",
        "preview": "Competitive Analysis with Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, integration claims, and onboarding friction."
      }
    ],
    "managed_sources": [],
    "managed_jobs": []
  }
}
```
---
## CASE 4 — Persistence proof
### Show local DB entries for task feedback and generation memory
**Task Feedback Table Rows:**
```json
[
  {
    "feedback_id": "feedback_003",
    "task_id": "3",
    "job_id": "job_proof_001",
    "project_id": "project_proof_001",
    "original_title": "Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move",
    "original_expected_advantage": "Improves conversion and win rate this week by resolving the missing competitor, pricing, or buyer-pressure fact that is limiting the next best action.",
    "feedback_type": "commented",
    "feedback_comment": "We need a trust move, not a pricing move.",
    "adjusted_text": null,
    "replacement_generated": 1,
    "created_at": "2026-03-25T08:30:00.845Z"
  },
  {
    "feedback_id": "feedback_002",
    "task_id": "1",
    "job_id": "job_proof_001",
    "project_id": "project_proof_001",
    "original_title": "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers",
    "original_expected_advantage": "Increases conversion for active buyers this week by answering Fortitude AI's customer testimonials in the pricing page.",
    "feedback_type": "deleted_with_annotation",
    "feedback_comment": "Avoid this entirely.",
    "adjusted_text": null,
    "replacement_generated": 1,
    "created_at": "2026-03-25T08:30:00.829Z"
  },
  {
    "feedback_id": "feedback_001",
    "task_id": "2",
    "job_id": "job_proof_001",
    "project_id": "project_proof_001",
    "original_title": "Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise before buyers default to it",
    "original_expected_advantage": "Increases shortlist conversion for buyers this week by replacing the competitor using onboarding promise's its strongest visible claim with a stronger response in the pricing page.",
    "feedback_type": "declined",
    "feedback_comment": "Not relevant right now.",
    "adjusted_text": null,
    "replacement_generated": 1,
    "created_at": "2026-03-25T08:30:00.813Z"
  }
]
```
**Generation Memory Table Rows:**
```json
[
  {
    "memory_id": "memory_project_proof_001_4162010191814250565",
    "project_id": "project_proof_001",
    "memory_kind": "avoid_title",
    "pattern_key": "request the missing proprietary pricing offer or buyer proof fact this week before making the wrong response move",
    "signal_value": "Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move",
    "weight": 2.0,
    "source_feedback_id": "feedback_003",
    "created_at": "2026-03-25T08:30:00.846Z",
    "updated_at": "2026-03-25T08:30:00.846Z"
  },
  {
    "memory_id": "memory_project_proof_001_456216910407999945",
    "project_id": "project_proof_001",
    "memory_kind": "prefer_bucket",
    "pattern_key": "proof_or_trust_move",
    "signal_value": "trust",
    "weight": 5.0,
    "source_feedback_id": "feedback_003",
    "created_at": "2026-03-25T08:30:00.846Z",
    "updated_at": "2026-03-25T08:30:00.846Z"
  },
  {
    "memory_id": "memory_project_proof_001_9188308736589434552",
    "project_id": "project_proof_001",
    "memory_kind": "prefer_bucket",
    "pattern_key": "pricing_or_offer_move",
    "signal_value": "pricing",
    "weight": 5.0,
    "source_feedback_id": "feedback_003",
    "created_at": "2026-03-25T08:30:00.846Z",
    "updated_at": "2026-03-25T08:30:00.846Z"
  },
  {
    "memory_id": "memory_project_proof_001_2222547631103734940",
    "project_id": "project_proof_001",
    "memory_kind": "avoid_title",
    "pattern_key": "add pricing comparison block and onboarding faq on pricing page this week before fortitude ai s customer testimonials sets expectations for buyers",
    "signal_value": "Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers",
    "weight": 3.0,
    "source_feedback_id": "feedback_002",
    "created_at": "2026-03-25T08:30:00.830Z",
    "updated_at": "2026-03-25T08:30:00.830Z"
  },
  {
    "memory_id": "memory_project_proof_001_7532395099868577636",
    "project_id": "project_proof_001",
    "memory_kind": "avoid_title",
    "pattern_key": "rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise before buyers default to it",
    "signal_value": "Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise before buyers default to it",
    "weight": 3.0,
    "source_feedback_id": "feedback_001",
    "created_at": "2026-03-25T08:30:00.814Z",
    "updated_at": "2026-03-25T08:30:00.814Z"
  }
]
```
---
## CASE 5 — No regression
- **checklist always returns exactly 3 tasks:** Demonstrated in every phase above.
- **evidence_refs are still valid:** Demonstrated in raw API responses (`supporting_signal_refs` remains populated).
- **no fallback to generic tasks:** Replaced tasks continue pulling from specific strategic buckets (`move_bucket`) and feature competitor-specific logic.

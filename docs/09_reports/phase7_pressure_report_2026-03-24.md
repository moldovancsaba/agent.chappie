# Phase 7 Pressure Test Report

Cases run: 6

## Strongest Cases

### Fortitude market analysis document (`fortitude_market_doc`)
- Score: 14.5
- Distinct move buckets: 3
- Operator would act: yes
- Top 3 tasks:
  - 1. Add pricing comparison block and onboarding FAQ on homepage comparison section this week before Fortitude AI's customer testimonials sets expectations for buyers
  - 2. Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move
  - 3. Add proof block in comparison section on homepage comparison section this week so hesitant buyers do not trust the competitor using customer testimonials first

### Diverse market pressure mix (`diverse_pressure_mix`)
- Score: 14.5
- Distinct move buckets: 3
- Operator would act: yes
- Top 3 tasks:
  - 1. Add pricing comparison block and onboarding FAQ on pricing page this week before FlowOps' integration claims sets expectations for buyers
  - 2. Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise trial before buyers default to it
  - 3. Add proof block in comparison section on pricing page this week so hesitant buyers do not trust Competitors first

### Knowledge-heavy noisy competitor doc (`knowledge_heavy_noisy_doc`)
- Score: 14.5
- Distinct move buckets: 3
- Operator would act: yes
- Top 3 tasks:
  - 1. Add pricing comparison block on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers
  - 2. Rewrite comparison section copy on pricing page this week to answer the competitor using pricing comparison trial before buyers default to it
  - 3. Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first

## Weakest Cases

### Explicit claim and asset document (`explicit_claim_asset`)
- Score: 12.8
- Failures: low_bucket_diversity
- Top 3 tasks:
  - 1. Add pricing comparison block in hero section on pricing page this week before Fortitude AI's free trial sets expectations for buyers
  - 2. Add proof blocks on homepage comparison section this week so hesitant buyers do not trust Fortitude AI first
  - 3. Add pricing comparison block on pricing page this week before the competitor using free trial free trial sets expectations for buyers

### Multi-pressure comparison notes (`multi_pressure_bundle`)
- Score: 12.8
- Failures: low_bucket_diversity
- Top 3 tasks:
  - 1. Add hero section copy on pricing page this week before Fortitude AI's free trial sets expectations for buyers
  - 2. Add proof blocks on homepage comparison section this week so hesitant buyers do not trust the competitor using no engineering required first
  - 3. Add pricing comparison block in hero section on pricing page this week before Fortitude AI's free trial sets expectations for buyers

### Messy internal notes (`messy_internal_notes`)
- Score: 12.8
- Failures: low_bucket_diversity
- Top 3 tasks:
  - 1. Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's free trial sets expectations for buyers
  - 2. Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move
  - 3. Add pricing comparison block and onboarding FAQ on pricing page this week before the competitor using free trial free trial sets expectations for buyers

## Failure Patterns

- `low_bucket_diversity`: 3

## Per-Case Detail

### Fortitude market analysis document (`fortitude_market_doc`)
- Score: 14.5
- Distinct move buckets: 3
- Failures: none
- Input excerpt: Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. The document compares packaging models, AI-led positioning, service-led onboarding, customer testimonials, integration claims, trial offers, and buyer objections.
- Tasks:
  - 1. Add pricing comparison block and onboarding FAQ on homepage comparison section this week before Fortitude AI's customer testimonials sets expectations for buyers [bucket=pricing_or_offer_move, priority=critical]
  - 2. Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move [bucket=information_request, priority=high]
  - 3. Add proof block in comparison section on homepage comparison section this week so hesitant buyers do not trust the competitor using customer testimonials first [bucket=proof_or_trust_move, priority=normal]
- Snapshot:
  - Pricing: Onboarding is shaping live comparisons through this visible pressure: Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. The document compares packaging models, AI-led positioning, service-led onboarding, cus | Acquisition: Fortitude AI is lowering switching friction in region unknown through offer-led acquisition. | Weakness: Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.

### Diverse market pressure mix (`diverse_pressure_mix`)
- Score: 14.5
- Distinct move buckets: 3
- Failures: none
- Input excerpt: FlowOps raised onboarding and pricing friction in the SEO market. Competitors are using testimonials, proof blocks, integration claims, and comparison messaging. One exposed operator is reducing staff and may sell assets. Trial-led acquisition pressure is rising.
- Tasks:
  - 1. Add pricing comparison block and onboarding FAQ on pricing page this week before FlowOps' integration claims sets expectations for buyers [bucket=pricing_or_offer_move, priority=critical]
  - 2. Rewrite comparison section copy on pricing page this week to answer the competitor using onboarding promise trial before buyers default to it [bucket=messaging_or_positioning_move, priority=high]
  - 3. Add proof block in comparison section on pricing page this week so hesitant buyers do not trust Competitors first [bucket=proof_or_trust_move, priority=normal]
- Snapshot:
  - Pricing: FlowOps is resetting buyer price expectations in region unknown, which exposes any weaker entry offer you still show. | Acquisition: FlowOps is lowering switching friction in region unknown through offer-led acquisition. | Weakness: Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.

### Knowledge-heavy noisy competitor doc (`knowledge_heavy_noisy_doc`)
- Score: 14.5
- Distinct move buckets: 3
- Failures: none
- Input excerpt: Competitive Analysis in the Marketing and SEO Intelligence Market with a Fortitude AI Focus. The document compares packaging, pricing bundles, trial offers, customer testimonials, and AI-led positioning across several vendors.
- Tasks:
  - 1. Add pricing comparison block on pricing page this week before Fortitude AI's customer testimonials sets expectations for buyers [bucket=pricing_or_offer_move, priority=critical]
  - 2. Rewrite comparison section copy on pricing page this week to answer the competitor using pricing comparison trial before buyers default to it [bucket=messaging_or_positioning_move, priority=high]
  - 3. Add proof block in comparison section on pricing page this week so hesitant buyers do not trust the competitor using customer testimonials first [bucket=proof_or_trust_move, priority=normal]
- Snapshot:
  - Pricing: Fortitude AI is resetting buyer price expectations in region unknown, which exposes any weaker entry offer you still show. | Acquisition: Fortitude AI is lowering switching friction in region unknown through offer-led acquisition. | Weakness: Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.

### Explicit claim and asset document (`explicit_claim_asset`)
- Score: 12.8
- Distinct move buckets: 2
- Failures: low_bucket_diversity
- Input excerpt: Add a pricing comparison block and onboarding FAQ to the pricing page this week before Fortitude AI's free trial sets buyer expectations. Rewrite the homepage hero section to answer the no engineering required claim before buyers already comparing options default to Fortitude AI.
- Tasks:
  - 1. Add pricing comparison block in hero section on pricing page this week before Fortitude AI's free trial sets expectations for buyers [bucket=pricing_or_offer_move, priority=critical]
  - 2. Add proof blocks on homepage comparison section this week so hesitant buyers do not trust Fortitude AI first [bucket=messaging_or_positioning_move, priority=high]
  - 3. Add pricing comparison block on pricing page this week before the competitor using free trial free trial sets expectations for buyers [bucket=pricing_or_offer_move, priority=normal]
- Snapshot:
  - Pricing: Fortitude AI is resetting buyer price expectations in region unknown, which exposes any weaker entry offer you still show. | Acquisition: Fortitude AI is lowering switching friction in region unknown through offer-led acquisition. | Weakness: Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.

### Multi-pressure comparison notes (`multi_pressure_bundle`)
- Score: 12.8
- Distinct move buckets: 2
- Failures: low_bucket_diversity
- Input excerpt: Fortitude AI is using free trial language and low-friction onboarding claims on the pricing page. Its homepage hero now promises no engineering required and features new customer proof blocks. Several buyer notes mention pricing comparison and integration hesitation.
- Tasks:
  - 1. Add hero section copy on pricing page this week before Fortitude AI's free trial sets expectations for buyers [bucket=pricing_or_offer_move, priority=critical]
  - 2. Add proof blocks on homepage comparison section this week so hesitant buyers do not trust the competitor using no engineering required first [bucket=messaging_or_positioning_move, priority=high]
  - 3. Add pricing comparison block in hero section on pricing page this week before Fortitude AI's free trial sets expectations for buyers [bucket=pricing_or_offer_move, priority=normal]
- Snapshot:
  - Pricing: Fortitude AI is resetting buyer price expectations in region unknown, which exposes any weaker entry offer you still show. | Acquisition: Fortitude AI is lowering switching friction in region unknown through offer-led acquisition. | Weakness: Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.

### Messy internal notes (`messy_internal_notes`)
- Score: 12.8
- Distinct move buckets: 2
- Failures: low_bucket_diversity
- Input excerpt: Notes: buyers keep asking if setup is heavy, two prospects mentioned Fortitude AI's free trial, pricing page doesn't answer onboarding objections, homepage proof is weak, sales calls keep rebuilding the same comparison manually.
- Tasks:
  - 1. Add pricing comparison block and onboarding FAQ on pricing page this week before Fortitude AI's free trial sets expectations for buyers [bucket=pricing_or_offer_move, priority=critical]
  - 2. Request the missing proprietary pricing, offer, or buyer-proof fact this week before making the wrong response move [bucket=information_request, priority=high]
  - 3. Add pricing comparison block and onboarding FAQ on pricing page this week before the competitor using free trial free trial sets expectations for buyers [bucket=pricing_or_offer_move, priority=normal]
- Snapshot:
  - Pricing: Fortitude AI is resetting buyer price expectations in region unknown, which exposes any weaker entry offer you still show. | Acquisition: Fortitude AI is lowering switching friction in region unknown through offer-led acquisition. | Weakness: Weakness: no lower-friction entry offer is visible while a competitor is using offer-led acquisition.

import { z } from "zod";

export const priorityClassSchema = z.enum(["critical", "normal", "low"]);
export const jobClassSchema = z.enum(["heavy", "light"]);
export const resultStatusSchema = z.enum(["complete", "failed", "blocked"]);
export const contextTypeSchema = z.enum(["meeting_notes", "call_summary", "working_document"]);
export const inputSourceKindSchema = z.enum(["url", "manual_text", "uploaded_file"]);
export const artifactTypeSchema = z.enum(["upload"]);
export const decisionRouteSchema = z.enum(["proceed", "revise", "stop"]);
export const businessImpactSchema = z.enum(["low", "medium", "high"]);
export const signalTypeSchema = z.enum([
  "pricing_change",
  "opening",
  "closure",
  "staffing",
  "offer",
  "asset_sale",
  "messaging_shift",
  "proof_signal",
  "vendor_adoption",
]);

export const jobRequestArtifactSchema = z.object({
  type: artifactTypeSchema,
  ref: z.string().min(1),
});

export const jobRequestInputPayloadSchema = z.object({
  context_type: contextTypeSchema,
  prompt: z.string().min(1),
  artifacts: z.array(jobRequestArtifactSchema).min(1),
});

export const jobRequestSchema = z.object({
  job_id: z.string().min(1),
  app_id: z.string().min(1),
  project_id: z.string().min(1),
  priority_class: priorityClassSchema,
  job_class: jobClassSchema,
  submitted_at: z.string().datetime({ offset: true }),
  requested_capability: z.string().min(1),
  input_payload: jobRequestInputPayloadSchema,
  requested_by: z.string().min(1).optional(),
  deadline_at: z.string().datetime({ offset: true }).optional(),
  source_refs: z.array(z.string()).optional(),
  trace_parent_id: z.string().min(1).optional(),
  policy_tags: z.array(z.string()).optional(),
});

export const decisionSummarySchema = z.object({
  route: decisionRouteSchema,
  confidence: z.number().min(0).max(1),
});

export const systemObservationSchema = z.object({
  signal_id: z.string().min(1),
  signal_type: signalTypeSchema,
  competitor: z.string().min(1),
  region: z.string().min(1),
  summary: z.string().min(1),
  source_ref: z.string().min(1),
  observed_at: z.string().datetime({ offset: true }),
  confidence: z.number().min(0).max(1),
  business_impact: businessImpactSchema,
});

export const recommendedTaskSchema = z.object({
  rank: z.number().int().min(1).max(3),
  title: z.string().min(1),
  why_now: z.string().min(1),
  expected_advantage: z.string().min(1),
  evidence_refs: z.array(z.string().min(1)).min(1),
});

export const jobResultCompletePayloadSchema = z.object({
  recommended_tasks: z
    .array(recommendedTaskSchema)
    .min(1)
    .max(3)
    .superRefine((tasks, ctx) => {
      const ranks = tasks.map((task) => task.rank);
      if (new Set(ranks).size !== ranks.length) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "recommended_tasks ranks must be unique",
        });
      }
      for (const expected of ranks.map((_, index) => index + 1)) {
        if (!ranks.includes(expected)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "recommended_tasks ranks must be sequential starting at 1",
          });
          break;
        }
      }
    }),
  summary: z.string().min(1),
});

export const jobResultBlockedPayloadSchema = z.object({
  reason: z.string().min(1),
});

export const jobResultSchema = z.object({
  job_id: z.string().min(1),
  app_id: z.string().min(1),
  project_id: z.string().min(1),
  status: resultStatusSchema,
  completed_at: z.string().datetime({ offset: true }),
  result_payload: z.union([jobResultCompletePayloadSchema, jobResultBlockedPayloadSchema, z.record(z.string(), z.unknown())]),
  decision_summary: decisionSummarySchema.optional(),
  trace_run_id: z.string().min(1).optional(),
  trace_refs: z.array(z.string()).optional(),
  error_code: z.string().min(1).optional(),
  error_detail: z.string().min(1).optional(),
});

export const feedbackPayloadSchema = z.object({
  done: z.array(z.string()),
  edited: z.array(z.string()),
  declined: z.array(z.string()),
});

export const feedbackSchema = z.object({
  feedback_id: z.string().min(1),
  job_id: z.string().min(1),
  app_id: z.string().min(1),
  project_id: z.string().min(1),
  feedback_type: z.literal("task_response"),
  submitted_at: z.string().datetime({ offset: true }),
  user_action: z.enum(["done", "edited", "declined"]),
  feedback_payload: feedbackPayloadSchema,
  actor_id: z.string().min(1).optional(),
  linked_result_status: resultStatusSchema.optional(),
});

export const demoJobSubmissionSchema = z.object({
  contextNotes: z.string().min(1),
  contextType: contextTypeSchema,
  sourceKind: inputSourceKindSchema,
  sessionId: z.string().min(1),
  projectId: z.string().min(1).optional(),
});

export type JobRequest = z.infer<typeof jobRequestSchema>;
export type JobResult = z.infer<typeof jobResultSchema>;
export type Feedback = z.infer<typeof feedbackSchema>;
export type SystemObservation = z.infer<typeof systemObservationSchema>;
export type RecommendedTask = z.infer<typeof recommendedTaskSchema>;

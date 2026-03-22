import { z } from "zod";

export const priorityClassSchema = z.enum(["critical", "normal", "low"]);
export const jobClassSchema = z.enum(["heavy", "light"]);
export const resultStatusSchema = z.enum(["complete", "failed", "blocked"]);
export const contextTypeSchema = z.enum(["meeting_notes", "call_summary", "working_document"]);
export const artifactTypeSchema = z.enum(["upload"]);
export const decisionRouteSchema = z.enum(["proceed", "revise", "stop"]);

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

export const jobResultCompletePayloadSchema = z.object({
  recommended_tasks: z.array(z.string()).min(1),
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
  projectSummary: z.string().min(1),
  contextNotes: z.string().min(1),
  contextType: contextTypeSchema,
  sessionId: z.string().min(1),
  projectId: z.string().min(1).optional(),
});

export type JobRequest = z.infer<typeof jobRequestSchema>;
export type JobResult = z.infer<typeof jobResultSchema>;
export type Feedback = z.infer<typeof feedbackSchema>;

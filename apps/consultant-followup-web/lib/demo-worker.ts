import { env } from "@/lib/env";

function includesOneOf(value: string, needles: string[]) {
  return needles.some((needle) => value.includes(needle));
}

export function createDemoRecommendation(input: { projectSummary: string; contextNotes: string }) {
  const haystack = `${input.projectSummary}\n${input.contextNotes}`.toLowerCase();
  const tasks: string[] = [];

  if (includesOneOf(haystack, ["recap", "summary", "meeting notes", "meeting"])) {
    tasks.push("Send recap email to the client");
  }
  if (includesOneOf(haystack, ["milestone", "plan", "timeline", "dates"])) {
    tasks.push("Draft the revised milestone plan");
  }
  if (includesOneOf(haystack, ["owner", "ownership", "action items", "open actions"])) {
    tasks.push("Confirm ownership for the open action items");
  }
  if (includesOneOf(haystack, ["vendor", "dependency", "risk"])) {
    tasks.push("Document the dependency risk in the client update");
  }

  return {
    tasks: Array.from(new Set(tasks)).slice(0, 4).length
      ? Array.from(new Set(tasks)).slice(0, 4)
      : ["Review uploaded context and draft a focused follow-up task list"],
    summary:
      env.agentBridgeMode === "demo"
        ? "Demo bridge generated a deterministic follow-up recommendation from the submitted context."
        : "Worker bridge returned a follow-up recommendation result.",
  };
}

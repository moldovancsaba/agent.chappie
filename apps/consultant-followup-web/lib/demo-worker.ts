import { env } from "@/lib/env";
import type { RecommendedTask } from "@/lib/contracts";

function includesOneOf(value: string, needles: string[]) {
  return needles.some((needle) => value.includes(needle));
}

export function createDemoRecommendation(input: { contextNotes: string }) {
  const haystack = input.contextNotes.toLowerCase();
  const tasks: RecommendedTask[] = [];

  if (includesOneOf(haystack, ["recap", "summary", "meeting notes", "meeting"])) {
    tasks.push({
      rank: 1,
      title: "Send a recap update to the client and parents",
      why_now: "The submitted context references a meeting-style update that needs a clear written follow-up.",
      expected_advantage: "Keeps stakeholders aligned and reduces confusion after a competitive or operational change.",
      evidence_refs: ["source_inline_context"],
    });
  }
  if (includesOneOf(haystack, ["milestone", "plan", "timeline", "dates"])) {
    tasks.push({
      rank: 1,
      title: "Revise the delivery timeline or academy plan before the next intake decision",
      why_now: "The supplied context references milestones, plans, or dates that may influence parent confidence.",
      expected_advantage: "Improves trust by showing clear next steps and timing.",
      evidence_refs: ["source_inline_context"],
    });
  }
  if (includesOneOf(haystack, ["owner", "ownership", "action items", "open actions"])) {
    tasks.push({
      rank: 1,
      title: "Assign ownership to the open follow-up actions",
      why_now: "The context includes open actions that need a named owner to move quickly.",
      expected_advantage: "Increases execution speed and reduces dropped follow-ups.",
      evidence_refs: ["source_inline_context"],
    });
  }
  if (includesOneOf(haystack, ["vendor", "dependency", "risk"])) {
    tasks.push({
      rank: 1,
      title: "Document the competitive or delivery risk in the project update",
      why_now: "The context mentions vendor, dependency, or risk factors that need visible handling.",
      expected_advantage: "Prevents avoidable surprises and gives the client a clearer plan of response.",
      evidence_refs: ["source_inline_context"],
    });
  }

  const uniqueTasks = Array.from(new Map(tasks.map((task) => [task.title, task])).values())
    .slice(0, 3)
    .map((task, index) => ({ ...task, rank: index + 1 }));

  return {
    tasks: uniqueTasks.length
      ? uniqueTasks
      : [
          {
            rank: 1,
            title: "Review the submitted context and prepare one concrete next move",
            why_now: "The demo bridge could not identify stronger competitive signals from the input.",
            expected_advantage: "Keeps the demo flow moving without inventing unsupported advice.",
            evidence_refs: ["source_inline_context"],
          },
        ],
    summary:
      env.agentBridgeMode === "demo"
        ? "Demo bridge generated a deterministic follow-up recommendation from the submitted context."
        : "Worker bridge returned a follow-up recommendation result.",
  };
}

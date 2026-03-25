import { NextResponse } from "next/server";
import path from "path";
import fs from "fs";

type TailEntry = { [k: string]: unknown } | { line: string };

function envEnabled() {
  return process.env.LOCAL_ADMIN_ENABLED === "1" || process.env.LOCAL_ADMIN_ENABLED === "true";
}

function resolveStatusDir() {
  if (process.env.AGENT_RUNTIME_STATUS_DIR && process.env.AGENT_RUNTIME_STATUS_DIR.trim()) {
    return process.env.AGENT_RUNTIME_STATUS_DIR.trim();
  }
  // When running Next.js from apps/consultant-followup-web, repo root is ../../
  return path.resolve(process.cwd(), "../../runtime_status");
}

function tailJsonLines(filePath: string, maxLines: number): TailEntry[] {
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, "utf-8");
  if (!raw.trim()) return [];
  const lines = raw.split("\n").filter(Boolean);
  const sliced = lines.slice(Math.max(0, lines.length - maxLines));
  const parsed: TailEntry[] = [];
  for (const line of sliced) {
    try {
      parsed.push(JSON.parse(line) as TailEntry);
    } catch {
      parsed.push({ line });
    }
  }
  return parsed;
}

function tailText(filePath: string, maxLines: number): TailEntry[] {
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, "utf-8");
  if (!raw.trim()) return [];
  const lines = raw.split("\n");
  const sliced = lines.slice(Math.max(0, lines.length - maxLines));
  return sliced.map((line) => ({ line }));
}

export async function GET() {
  if (!envEnabled()) {
    return NextResponse.json({ error: "not_enabled" }, { status: 404 });
  }

  const statusDir = resolveStatusDir();
  const heartbeatPath = path.join(statusDir, "heartbeat.json");
  const watchdogStatePath = path.join(statusDir, "watchdog_state.json");

  let heartbeat: unknown = null;
  let watchdog_state: unknown = null;
  try {
    if (fs.existsSync(heartbeatPath)) {
      heartbeat = JSON.parse(fs.readFileSync(heartbeatPath, "utf-8"));
    }
  } catch {
    heartbeat = null;
  }
  try {
    if (fs.existsSync(watchdogStatePath)) {
      watchdog_state = JSON.parse(fs.readFileSync(watchdogStatePath, "utf-8"));
    }
  } catch {
    watchdog_state = null;
  }

  return NextResponse.json({
    statusDir,
    heartbeat,
    watchdog_state,
    queue_consumer_health_tail: tailJsonLines(path.join(statusDir, "queue_consumer_health.jsonl"), 80),
    watchdog_log_tail: tailJsonLines(path.join(statusDir, "watchdog_log.jsonl"), 120),
    worker_runtime_stdout_tail: tailText(path.join(statusDir, "runtime_stdout.log"), 120),
    worker_runtime_stderr_tail: tailText(path.join(statusDir, "runtime_stderr.log"), 80),
  });
}


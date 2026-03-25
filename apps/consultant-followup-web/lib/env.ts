export const env = {
  appId: process.env.APP_ID ?? "app_consultant_followup",
  agentBridgeMode: process.env.AGENT_BRIDGE_MODE ?? "worker",
  demoStorageMode: process.env.DEMO_STORAGE_MODE ?? "memory",
  databaseUrl: process.env.DATABASE_URL,
  agentApiBaseUrl: process.env.AGENT_API_BASE_URL,
  agentSharedSecret: process.env.AGENT_SHARED_SECRET,
  workerQueueSecret: process.env.WORKER_QUEUE_SHARED_SECRET ?? process.env.AGENT_SHARED_SECRET,
  appUrl: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
  appName: process.env.NEXT_PUBLIC_APP_NAME ?? "Agent.Chappie Demo",
};

/**
 * When false, the Next.js server must not call AGENT_API_BASE_URL (no Cloudflare tunnel, no inbound Mac).
 * Use AGENT_BRIDGE_MODE=queue on Vercel: jobs and results stay in Neon; the Mac Mini polls /api/worker/jobs/claim.
 */
export function isDirectWorkerEnabled(): boolean {
  const mode = env.agentBridgeMode;
  if (mode === "demo" || mode === "queue") {
    return false;
  }
  return Boolean(env.agentApiBaseUrl?.trim());
}

/** User-facing explanation when workspace-management routes cannot call the Mac over HTTP. */
export function describeDirectWorkerBlock(): string {
  const mode = env.agentBridgeMode;
  if (mode === "queue") {
    return (
      "Queue mode (AGENT_BRIDGE_MODE=queue): Sources & Jobs and similar controls need a direct Mac HTTP bridge, which is intentionally off on the hosted app. " +
      "Use the main context submission flow; the Mac Mini should run scripts/worker_queue_consumer.py. " +
      "For full management UI, run locally with AGENT_BRIDGE_MODE=worker and AGENT_API_BASE_URL pointing at worker_bridge.py."
    );
  }
  if (mode === "demo") {
    return "Demo mode (AGENT_BRIDGE_MODE=demo): worker management APIs are disabled.";
  }
  if (!env.agentApiBaseUrl?.trim()) {
    return (
      "AGENT_API_BASE_URL is unset while AGENT_BRIDGE_MODE=worker. " +
      "Either switch to AGENT_BRIDGE_MODE=queue (with DEMO_STORAGE_MODE=neon) for hosted queue + Mac consumer, " +
      "or set AGENT_API_BASE_URL (e.g. http://127.0.0.1:8787) and run scripts/worker_bridge.py for management features."
    );
  }
  return "Direct worker access is disabled.";
}

export const env = {
  appId: process.env.APP_ID ?? "app_consultant_followup",
  agentBridgeMode: process.env.AGENT_BRIDGE_MODE ?? "worker",
  demoStorageMode: process.env.DEMO_STORAGE_MODE ?? "memory",
  databaseUrl: process.env.DATABASE_URL,
  agentApiBaseUrl: process.env.AGENT_API_BASE_URL,
  agentSharedSecret: process.env.AGENT_SHARED_SECRET,
  appUrl: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
  appName: process.env.NEXT_PUBLIC_APP_NAME ?? "Agent.Chappie Demo",
};

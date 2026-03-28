# Agent.Chappie + agent.meimei (LLM gateway)

[agent.meimei](https://github.com/moldovancsaba/agent.meimei) is the operator dashboard on your Mac. **Model calls** from this repo’s Python stack can go through MeiMei’s Ollama routing instead of calling `127.0.0.1:11434` directly.

There is **no** Checklist miniapp or `/727/Checklist` route in MeiMei anymore. Run the Next.js UI here (`apps/consultant-followup-web`) on its own port (e.g. 3000) or deploy to Vercel as before.

## 1. MeiMei endpoint

- **URL:** `POST http://127.0.0.1:3030/api/llm/gateway/generate`  
  (or `https://meimei.localhost:8443/dashboard/api/llm/gateway/generate` through the HTTPS proxy — same path after `/dashboard`.)
- **Body:** Ollama-compatible JSON: `{ "model": "...", "prompt": "...", "stream": false }` (optional: `format`, `system`, `options`).
- **Response:** Ollama `/api/generate` JSON (includes `response` string). Same shape `OllamaClient` in `src/agent_chappie/models.py` already expects.

## 2. Auth

- **Default:** only **loopback** clients may call the gateway (no secret).
- **Optional:** set `MEIMEI_LLM_GATEWAY_SECRET` in the **MeiMei** dashboard environment, then send header **`x-meimei-llm-secret`** with the same value from this repo (`MEIMEI_LLM_GATEWAY_SECRET` in `.env` / worker env).

## 3. Configure this repo

In the **repository root** `.env` or `.env.local` (see `.env.example`):

```bash
OLLAMA_URL=http://127.0.0.1:3030/api/llm/gateway/generate
# MEIMEI_LLM_GATEWAY_SECRET=...   # if MeiMei requires it
```

Worker / scripts that construct `OllamaClient` will then use the gateway automatically.

## 4. Ollama must be reachable from MeiMei

MeiMei’s `dashboard/lib/llm.mjs` talks to Ollama at `http://localhost:11434`. Ensure Ollama is running when using the gateway.

## 5. Next.js app

The web app does not need MeiMei for static hosting. Configure `DATABASE_URL`, `AGENT_BRIDGE_MODE`, worker URLs, etc. per existing checklist docs.

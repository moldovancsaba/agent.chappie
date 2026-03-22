import { DemoWorkspace } from "@/components/demo-workspace";
import { env } from "@/lib/env";

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <div className="panel hero-copy">
          <div className="eyebrow">Public test MVP · no login</div>
          <h1>Competitive action engine, without app-layer sprawl.</h1>
          <p>
            This app stays intentionally narrow: submit one messy competitive context package, let the private worker
            accumulate internal observations, and expose only the top three ranked actions back to the user.
          </p>
          <div className="hero-points">
            <div className="hero-point">
              <strong>What this proves</strong>
              <span>We can exercise the accepted Job Request, Job Result, and Feedback contracts without leaking observation logic into the UI.</span>
            </div>
            <div className="hero-point">
              <strong>What is intentionally missing</strong>
              <span>No auth, no scheduler implementation, no chat interface, and no attempt to expose internal system observations to the user.</span>
            </div>
            <div className="hero-point">
              <strong>What happens next</strong>
              <span>The user loop stays simple while the private worker learns continuously from stored competitor signals in the background.</span>
            </div>
          </div>
        </div>

        <aside className="panel hero-card">
          <div className="demo-chip">Phase 4 · thin app layer</div>
          <h2>{env.appName}</h2>
          <div className="demo-meta">
            <span>
              <strong>App ID:</strong> {env.appId}
            </span>
            <span>
              <strong>Bridge mode:</strong> {env.agentBridgeMode}
            </span>
            <span>
              <strong>Storage mode:</strong> {env.demoStorageMode}
            </span>
            <span>
              <strong>Deploy target:</strong> Vercel app layer only
            </span>
          </div>
        </aside>
      </section>

      <DemoWorkspace />
    </main>
  );
}

import { DemoWorkspace } from "@/components/demo-workspace";
import { env } from "@/lib/env";

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <div className="panel hero-copy">
          <div className="eyebrow">Public test MVP · no login</div>
          <h1>Client follow-up, without platform drag.</h1>
          <p>
            This first app layer is intentionally narrow: paste a client project summary, drop in meeting notes, and
            send one contract-shaped job through the demo boundary. The core remains private. The app stays thin.
          </p>
          <div className="hero-points">
            <div className="hero-point">
              <strong>What this proves</strong>
              <span>We can exercise the accepted Job Request, Job Result, and Feedback contracts without leaking UI logic into the core.</span>
            </div>
            <div className="hero-point">
              <strong>What is intentionally missing</strong>
              <span>No auth, no scheduler implementation, no model calls in the app, and no attempt to expose the Mac mini worker publicly.</span>
            </div>
            <div className="hero-point">
              <strong>What happens next</strong>
              <span>After the public test loop is stable, auth and the real worker bridge can be added without breaking the contract layer.</span>
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

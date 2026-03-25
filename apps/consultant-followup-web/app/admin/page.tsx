"use client";

import { useEffect, useState } from "react";

type AdminRuntimePayload = {
  statusDir?: string;
  heartbeat?: unknown;
  watchdog_state?: unknown;
  queue_consumer_health_tail?: Array<{ [k: string]: unknown } | { line: string }>;
  watchdog_log_tail?: Array<{ [k: string]: unknown } | { line: string }>;
  worker_runtime_stdout_tail?: Array<{ line: string }>;
  worker_runtime_stderr_tail?: Array<{ line: string }>;
  error?: string;
};

export default function AdminPage() {
  const [data, setData] = useState<AdminRuntimePayload | null>(null);
  const [err, setErr] = useState<string>("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        setErr("");
        const res = await fetch("/api/admin/runtime", { cache: "no-store" });
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.error ? String(body.error) : `HTTP ${res.status}`);
        }
        const json = (await res.json()) as AdminRuntimePayload;
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      }
    };
    void run();
    const id = window.setInterval(() => {
      setTick((t) => t + 1);
    }, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (!tick) return;
    // The interval only increments tick; fetch on each tick.
    (async () => {
      try {
        setErr("");
        const res = await fetch("/api/admin/runtime", { cache: "no-store" });
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.error ? String(body.error) : `HTTP ${res.status}`);
        }
        const json = (await res.json()) as AdminRuntimePayload;
        setData(json);
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e));
      }
    })();
  }, [tick]);

  const asLines = (items: Array<{ [k: string]: unknown } | { line: string }> | undefined) =>
    (items ?? []).slice(-12).map((x) => ("line" in x ? x.line : JSON.stringify(x)));

  return (
    <main className="page-shell app-main">
      <section className="panel section-card">
        <div className="section-head">
          <div>
            <span className="section-kicker">Local Admin Monitor</span>
            <h2>Follow local worker + queue health</h2>
            <p className="section-subcopy">
              Shows the latest state from <code>runtime_status</code> files on this host.
            </p>
          </div>
          <div className="section-head-badges">
            <span className="status-pill">Local only</span>
          </div>
        </div>

        {err ? (
          <div className="notice error" style={{ marginTop: "1rem" }}>
            <strong>Admin API error</strong>
            <p>{err}</p>
          </div>
        ) : null}

        {data ? (
          <div style={{ marginTop: "1rem" }}>
            <div className="summary-row">
              <span>Status dir</span>
              <strong style={{ fontFamily: "monospace" }}>{data.statusDir ?? "—"}</strong>
            </div>

            <div className="task-block">
              <span>Heartbeat</span>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{data.heartbeat ? JSON.stringify(data.heartbeat, null, 2) : "—"}</pre>
            </div>

            <div className="task-block">
              <span>Watchdog state</span>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{data.watchdog_state ? JSON.stringify(data.watchdog_state, null, 2) : "—"}</pre>
            </div>

            <div className="task-block">
              <span>Queue consumer health (tail)</span>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{asLines(data.queue_consumer_health_tail).join("\n") || "—"}</pre>
            </div>

            <div className="task-block">
              <span>Watchdog log (tail)</span>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{asLines(data.watchdog_log_tail).join("\n") || "—"}</pre>
            </div>

            <div className="task-block">
              <span>Runtime stdout (tail)</span>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                {(data.worker_runtime_stdout_tail ?? []).slice(-20).map((x) => x.line).join("\n") || "—"}
              </pre>
            </div>

            <div className="task-block">
              <span>Runtime stderr (tail)</span>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                {(data.worker_runtime_stderr_tail ?? []).slice(-20).map((x) => x.line).join("\n") || "—"}
              </pre>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}


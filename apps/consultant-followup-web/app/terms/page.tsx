import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms & conditions · Agent.Chappie Demo",
};

export default function TermsPage() {
  return (
    <main className="page-shell legal-page">
      <p className="legal-back">
        <Link href="/">← Back to workspace</Link>
      </p>
      <article className="panel section-card legal-article">
        <h1>Terms &amp; conditions</h1>
        <p className="section-subcopy">
          This public demo is provided for evaluation only. It is not legal advice. By using the demo you agree that
          outputs may be incomplete or incorrect, and that you will not rely on them as the sole basis for business or
          legal decisions.
        </p>
        <p className="section-subcopy">
          We may change or discontinue the demo at any time. Contact your own counsel for binding terms if you move to a
          production agreement.
        </p>
      </article>
    </main>
  );
}

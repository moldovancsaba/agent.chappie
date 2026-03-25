import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy policy · Agent.Chappie Demo",
};

export default function PrivacyPage() {
  return (
    <main className="page-shell legal-page">
      <p className="legal-back">
        <Link href="/">← Back to workspace</Link>
      </p>
      <article className="panel section-card legal-article">
        <h1>Privacy policy</h1>
        <p className="section-subcopy">
          This demo may process text and files you submit so we can show how the product works. Do not upload
          confidential, personal health, or regulated data you are not allowed to share.
        </p>
        <p className="section-subcopy">
          Operational logs and hosted storage follow the deployment configuration of whoever runs this instance. For a
          production deployment, a dedicated privacy notice and data processing agreement should replace this summary.
        </p>
      </article>
    </main>
  );
}

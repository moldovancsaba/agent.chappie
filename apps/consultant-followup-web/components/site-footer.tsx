import Link from "next/link";

const version = process.env.NEXT_PUBLIC_APP_VERSION ?? "0.1.1";
const deploySha = (process.env.NEXT_PUBLIC_DEPLOY_SHA ?? "").trim();

export function SiteFooter() {
  const buildLabel =
    deploySha && deploySha !== "local" ? ` · build ${deploySha}` : deploySha === "local" ? " · dev" : "";

  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <span className="site-footer-version" title={deploySha && deploySha !== "local" ? `Git ${deploySha}` : undefined}>
          Agent.Chappie demo · v{version}
          {buildLabel}
        </span>
        <nav className="site-footer-links" aria-label="Legal">
          <Link href="/terms">Terms &amp; conditions</Link>
          <span aria-hidden className="site-footer-sep">
            ·
          </span>
          <Link href="/privacy">Privacy policy</Link>
        </nav>
      </div>
    </footer>
  );
}

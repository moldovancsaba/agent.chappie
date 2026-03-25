import Link from "next/link";

const version = process.env.NEXT_PUBLIC_APP_VERSION ?? "0.1.0";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <span className="site-footer-version">Agent.Chappie demo · v{version}</span>
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

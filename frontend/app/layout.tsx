import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "FSC", template: "%s · FSC" },
  description: "Quellenübergreifende Story- und Debattenanalyse",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de">
      <body>
        <header className="site-header">
          <div className="shell nav">
            <Link className="brand" href="/">
              <span className="brand-mark">FSC</span>
              <span className="brand-text">Story Intelligence</span>
            </Link>
            <nav className="nav-links" aria-label="Hauptnavigation">
              <Link href="/">Suche</Link>
              <Link href="/stories">Stories</Link>
            </nav>
          </div>
        </header>
        <main className="shell">{children}</main>
        <footer className="shell footer">
          FSC zeigt Quellen, Aussagen und beobachtbare Unterschiede. Keine Truth- oder Glaubwürdigkeits-Scores.
        </footer>
      </body>
    </html>
  );
}

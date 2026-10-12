import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "FSC", template: "%s · FSC" },
  description: "Nachrichten vergleichen, Aussagen prüfen und unterschiedliche Perspektiven verstehen.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de">
      <body>
        <header className="site-header">
          <div className="shell nav">
            <Link className="brand" href="/">
              <span className="brand-mark">FSC</span>
              <span className="brand-text">Nachrichten im Vergleich</span>
            </Link>
            <nav className="nav-links" aria-label="Hauptnavigation">
              <Link href="/">Startseite</Link>
              <Link href="/stories">Ereignisse</Link>
            </nav>
          </div>
        </header>
        <main className="shell">{children}</main>
        <footer className="shell footer">
          FSC · Deutschsprachige Nachrichten im Vergleich. Aussagen und Quellen transparent einordnen – ohne Wahrheits- oder Glaubwürdigkeitsurteile.
        </footer>
      </body>
    </html>
  );
}

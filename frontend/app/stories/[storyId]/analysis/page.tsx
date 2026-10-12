import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getStory, getStoryAnalysis } from "@/lib/api";
import { formatDate, label, safeExternalUrl } from "@/lib/format";
import {
  germanClaimGroups,
  germanDifferences,
  germanStoryArticles,
  type GermanClaimGroup,
} from "@/lib/public-content";

export const metadata: Metadata = {
  title: "Aussagen im Vergleich",
  description: "Deutschsprachige Aussagen aus mehreren Medien einordnen, vergleichen und anhand der Originalberichte nachvollziehen.",
};
export const dynamic = "force-dynamic";
type Props = { params: Promise<{ storyId: string }> };

function StatementCard({ group, index }: { group: GermanClaimGroup; index: number }) {
  const sourceNames = Array.from(
    new Set(group.members.map((member) => member.source_name)),
  );
  const labelText = group.visibleSourceCount > 1
    ? "In mehreren Medien berichtet"
    : "In einem Medium berichtet";
  return (
    <article className="statement-card">
      <div className="statement-heading">
        <span className="statement-number">{String(index).padStart(2, "0")}</span>
        <span className="statement-status">{labelText}</span>
      </div>
      <h3>{group.title}</h3>
      <p className="statement-byline">
        {sourceNames.join(" · ")}
      </p>
      <details className="statement-details">
        <summary>Originalaussagen und Belege ansehen <span aria-hidden="true">↓</span></summary>
        <div className="statement-source-list">
          {group.members.map((member) => {
            const url = safeExternalUrl(member.article_url);
            return (
              <div className="statement-source" key={member.claim_id}>
                <strong>{member.source_name}</strong>
                <p>{member.claim_text}</p>
                {url ? <a href={url} target="_blank" rel="noopener noreferrer">Zum Originalartikel ↗</a> : null}
              </div>
            );
          })}
          {group.evidence.length > 0 ? (
            <div className="statement-evidence">
              <h4>Belege und Kontext</h4>
              {group.evidence.map((item) => (
                <blockquote key={item.id}>
                  <span>{item.source_name} · {label(item.evidence_kind)}</span>
                  <p>{item.evidence_text}</p>
                </blockquote>
              ))}
            </div>
          ) : null}
        </div>
      </details>
    </article>
  );
}

export default async function AnalysisPage({ params }: Props) {
  const { storyId } = await params;
  let story;
  try {
    story = await getStory(storyId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  const germanArticles = germanStoryArticles(story);
  // This applies even when the underlying multilingual analysis exists.
  if (germanArticles.length === 0) notFound();

  const title = germanArticles.find((article) => article.title?.trim())?.title ?? "Ereignis";
  const germanSources = new Set(germanArticles.map((article) => article.source_id));

  const analysis = await getStoryAnalysis(storyId);
  if (!analysis) {
    return (
      <>
        <nav className="article-breadcrumb" aria-label="Pfadnavigation">
          <Link href="/">Startseite</Link><span aria-hidden="true">/</span>
          <Link href="/stories">Ereignisse</Link><span aria-hidden="true">/</span>
          <Link href={`/stories/${storyId}`}>Originalberichte</Link>
        </nav>
        <section className="empty-state top-space">
          <p className="eyebrow">AUSSAGENVERGLEICH</p>
          <h1>Die Auswertung wird vorbereitet</h1>
          <p>Es liegt noch kein vollständig abgeglichener Stand vor. FSC zeigt deshalb keine unvollständigen Zwischenergebnisse.</p>
          <Link className="button" href={`/stories/${storyId}`}>Zu den Originalberichten</Link>
        </section>
      </>
    );
  }

  const articleIds = new Set(germanArticles.map((article) => article.article_id));
  const visibleGroups = germanClaimGroups(analysis, articleIds);
  const shared = visibleGroups.filter((group) => group.visibleSourceCount >= 2)
    .sort((left, right) => right.visibleSourceCount - left.visibleSourceCount || right.members.length - left.members.length);
  const single = visibleGroups.filter((group) => group.visibleSourceCount < 2);
  const differences = germanDifferences(analysis, visibleGroups);
  const featuredShared = shared.slice(0, 6);
  const additionalShared = shared.slice(6);
  const newest = germanArticles.reduce<string | null>((latest, article) => {
    const date = article.published_at ?? article.article_time;
    return !latest || Date.parse(date) > Date.parse(latest) ? date : latest;
  }, null);

  return (
    <>
      <nav className="article-breadcrumb" aria-label="Pfadnavigation">
        <Link href="/">Startseite</Link><span aria-hidden="true">/</span>
        <Link href="/stories">Ereignisse</Link><span aria-hidden="true">/</span>
        <Link href={`/stories/${storyId}`}>Originalberichte</Link><span aria-hidden="true">/</span>
        <span>Vergleich</span>
      </nav>

      <header className="analysis-hero">
        <p className="eyebrow">DER AUSSAGENVERGLEICH</p>
        <h1>Wo die Berichte übereinstimmen – und wo nicht.</h1>
        <p className="analysis-subject">{title}</p>
        <div className="reading-meta">
          <span><strong>{germanSources.size}</strong> deutschsprachige Medien</span>
          <span><strong>{germanArticles.length}</strong> Artikel</span>
          <span>Zuletzt berichtet: {formatDate(newest)}</span>
        </div>
        <p className="analysis-intro">
          Wir ordnen Aussagen aus den sichtbaren Originalberichten ein. Mehrere
          Berichte sind nicht automatisch unabhängige Bestätigungen. Hier gibt
          es keine Wahrheitswerte und keine künstliche Gewissheit.
        </p>
      </header>

      <nav className="analysis-anchor-nav" aria-label="Abschnitte der Analyse">
        <a href="#gemeinsame-aussagen">Gemeinsame Aussagen <span>{shared.length}</span></a>
        <a href="#unterschiede">Unterschiede <span>{differences.length}</span></a>
        <a href="#einzelberichte">Weitere Aussagen <span>{single.length}</span></a>
      </nav>

      <div className="analysis-layout">
        <div className="analysis-main">
          <section className="analysis-section" id="gemeinsame-aussagen" aria-labelledby="shared-heading">
            <div className="analysis-section-header">
              <div>
                <p className="eyebrow">MEHRFACH BERICHTET</p>
                <h2 id="shared-heading">Was mehrere Medien berichten</h2>
              </div>
              <span className="analysis-count">{shared.length} {shared.length === 1 ? "Aussage" : "Aussagen"}</span>
            </div>
            <p className="section-description">
              Ähnlich formulierte Aussagen aus mindestens zwei hier sichtbaren deutschsprachigen Medien.
              Die Zahl der Medien ist kein Unabhängigkeitsnachweis.
            </p>
            {shared.length > 0 ? (
              <div className="statement-stack">
                {featuredShared.map((group, index) => <StatementCard group={group} index={index + 1} key={group.id} />)}
                {additionalShared.length > 0 ? (
                  <details className="more-statements">
                    <summary>{additionalShared.length} weitere mehrfach berichtete Aussagen anzeigen</summary>
                    <div className="statement-stack">
                      {additionalShared.map((group, index) => <StatementCard group={group} index={featuredShared.length + index + 1} key={group.id} />)}
                    </div>
                  </details>
                ) : null}
              </div>
            ) : (
              <p className="analysis-empty">Zu diesem Ereignis sind noch keine gemeinsamen Aussagen aus mindestens zwei sichtbaren deutschsprachigen Medien erfasst.</p>
            )}
          </section>

          <section className="analysis-section" id="unterschiede" aria-labelledby="difference-heading">
            <div className="analysis-section-header">
              <div>
                <p className="eyebrow">ABWEICHENDE DARSTELLUNGEN</p>
                <h2 id="difference-heading">Wo Aussagen auseinandergehen</h2>
              </div>
              <span className="analysis-count">{differences.length}</span>
            </div>
            {differences.length > 0 ? (
              <div className="analysis-differences">
                {differences.map((difference) => (
                  <article className="analysis-difference" key={difference.id}>
                    <p className="difference-type">{label(difference.kind)}</p>
                    <div className="difference-columns">
                      <div><span>Darstellung 1</span><p>{difference.left.title}</p><small>{Array.from(new Set(difference.left.members.map((member) => member.source_name))).join(" · ")}</small></div>
                      <div><span>Darstellung 2</span><p>{difference.right.title}</p><small>{Array.from(new Set(difference.right.members.map((member) => member.source_name))).join(" · ")}</small></div>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="analysis-empty">Aktuell wurden keine belastbar vergleichbaren abweichenden Aussagen zwischen den sichtbaren deutschsprachigen Gruppen gefunden. Das bedeutet nicht, dass alle Quellen vollständig übereinstimmen.</p>
            )}
          </section>

          <section className="analysis-section" id="einzelberichte" aria-labelledby="single-heading">
            <div className="analysis-section-header">
              <div>
                <p className="eyebrow">ERGÄNZENDE EINZELAUSSAGEN</p>
                <h2 id="single-heading">Was bislang nur ein Medium berichtet</h2>
              </div>
              <span className="analysis-count">{single.length}</span>
            </div>
            {single.length > 0 ? (
              <details className="more-statements">
                <summary>{single.length} {single.length === 1 ? "Einzelaussage" : "Einzelaussagen"} mit Originalquellen ansehen</summary>
                <div className="statement-stack">
                  {single.map((group, index) => <StatementCard group={group} index={index + 1} key={group.id} />)}
                </div>
              </details>
            ) : (
              <p className="analysis-empty">Derzeit keine weiteren Einzelaussagen vorhanden.</p>
            )}
          </section>
        </div>

        <aside className="analysis-sidebar" aria-label="Hintergrund zur Einordnung">
          <div className="reading-aside-card">
            <p className="eyebrow">WIE FSC ARBEITET</p>
            <h2>Was diese Analyse zeigt</h2>
            <p>FSC vergleicht dokumentierte Aussagen und verweist auf die Originalberichte. Ob eine Aussage zutrifft, wird nicht durch eine einfache Kennzahl bewertet.</p>
            <ul className="method-list">
              <li><strong>Deutsch sichtbar</strong><span>Berichte aus allen Ländern, sofern sie auf Deutsch verfasst sind.</span></li>
              <li><strong>Quellen nachvollziehbar</strong><span>Die Originaltexte und ihre Herkunft bleiben zugänglich.</span></li>
              <li><strong>Grenzen transparent</strong><span>Fehlende Unterschiede oder Belege sind kein Wahrheitsbeweis.</span></li>
            </ul>
          </div>
          <div className="reading-aside-card reading-aside-note">
            <h2>Originalberichte ansehen</h2>
            <p>Vergleiche die Aussagen mit dem Wortlaut der Nachrichtenmedien.</p>
            <Link className="text-link" href={`/stories/${storyId}`}>Zu den {germanArticles.length} deutschsprachigen Artikeln →</Link>
          </div>
        </aside>
      </div>
    </>
  );
}

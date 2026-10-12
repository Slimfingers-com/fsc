import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getStory } from "@/lib/api";
import { formatDate, safeExternalUrl } from "@/lib/format";
import { germanStoryArticles } from "@/lib/public-content";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ storyId: string }> };

async function load(storyId: string) {
  let story;
  try {
    story = await getStory(storyId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  // Do not expose foreign-only Stories via a direct bookmarked URL.
  if (germanStoryArticles(story).length === 0) notFound();
  return story;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const story = await load((await params).storyId);
  const germanArticles = germanStoryArticles(story);
  const title = germanArticles.find((article) => article.title?.trim())?.title ?? "Ereignis";
  return {
    title,
    description: "Deutschsprachige Originalberichte aus verschiedenen Ländern zu einem Ereignis vergleichen.",
  };
}

export default async function StoryPage({ params }: Props) {
  const { storyId } = await params;
  const story = await load(storyId);
  const articles = germanStoryArticles(story).sort(
    (left, right) => Date.parse(right.article_time) - Date.parse(left.article_time),
  );
  const title = articles.find((article) => article.title?.trim())?.title ?? "Ereignis";
  const sources = Array.from(
    articles.reduce((items, article) => {
      const previous = items.get(article.source_id);
      items.set(article.source_id, {
        name: article.source_name,
        count: (previous?.count ?? 0) + 1,
      });
      return items;
    }, new Map<string, { name: string; count: number }>()),
  ).map(([id, data]) => ({ id, ...data }))
    .sort((left, right) => right.count - left.count || left.name.localeCompare(right.name, "de"));
  const newest = articles[0]?.published_at ?? articles[0]?.article_time ?? null;
  const oldest = articles[articles.length - 1]?.published_at
    ?? articles[articles.length - 1]?.article_time ?? null;

  return (
    <>
      <nav className="article-breadcrumb" aria-label="Pfadnavigation">
        <Link href="/">Startseite</Link><span aria-hidden="true">/</span>
        <Link href="/stories">Ereignisse</Link><span aria-hidden="true">/</span>
        <span>Quellenvergleich</span>
      </nav>

      <header className="reading-hero">
        <p className="eyebrow">EIN EREIGNIS · MEHRERE MEDIEN</p>
        <h1>{title}</h1>
        <p className="reading-intro">
          Wie verschiedene Medien über dieses Ereignis berichten – mit Links zu den Originalen.
          Sichtbar sind ausschließlich deutschsprachige Beiträge, unabhängig vom Herkunftsland.
        </p>
        <div className="reading-meta">
          <span><strong>{sources.length}</strong> {sources.length === 1 ? "Medium" : "Medien"}</span>
          <span><strong>{articles.length}</strong> {articles.length === 1 ? "Bericht" : "Berichte"}</span>
          <span>Zuletzt berichtet: {formatDate(newest)}</span>
        </div>
        <div className="reading-actions">
          <Link href={`/stories/${storyId}/analysis`} className="button">Aussagen vergleichen <span aria-hidden="true">→</span></Link>
          <a className="button secondary" href="#originalberichte">Originalberichte ansehen <span aria-hidden="true">↓</span></a>
        </div>
      </header>

      <div className="reading-layout">
        <div className="reading-content" id="originalberichte">
          <section aria-labelledby="original-heading">
            <p className="eyebrow">DIE QUELLEN IM ÜBERBLICK</p>
            <h2 id="original-heading">So berichten die Medien</h2>
            <p className="section-description">
              Jede Meldung ist mit dem Original verlinkt. Mehrere Artikel bedeuten nicht
              automatisch mehrere unabhängige Bestätigungen.
            </p>
            <div className="reading-report-list">
              {articles.map((article, index) => {
                const externalUrl = safeExternalUrl(article.url);
                return (
                  <article className="reading-report" key={article.membership_id}>
                    <div className="reading-report-index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</div>
                    <div className="reading-report-body">
                      <div className="reading-report-meta">
                        <strong>{article.source_name}</strong>
                        <span>{formatDate(article.published_at ?? article.article_time)}</span>
                      </div>
                      <h3>{article.title || "Bericht ohne Titel"}</h3>
                      {externalUrl ? (
                        <a className="text-link" href={externalUrl} target="_blank" rel="noopener noreferrer">
                          Originalbericht lesen <span aria-hidden="true">↗</span>
                        </a>
                      ) : <span className="section-description">Kein öffentlicher Artikellink verfügbar</span>}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        </div>

        <aside className="reading-sidebar" aria-label="Quellen und Einordnung">
          <section className="reading-aside-card">
            <p className="eyebrow">BETEILIGTE MEDIEN</p>
            <h2>Diese Medien berichten</h2>
            <ul className="source-overview">
              {sources.map((source) => (
                <li key={source.id}><span>{source.name}</span><small>{source.count} {source.count === 1 ? "Bericht" : "Berichte"}</small></li>
              ))}
            </ul>
          </section>
          <section className="reading-aside-card reading-aside-note">
            <h2>Was lässt sich vergleichen?</h2>
            <p>Welche Aussagen tauchen in mehreren Berichten auf? Wo gibt es Unterschiede – und wo fehlen Belege?</p>
            <Link className="text-link" href={`/stories/${storyId}/analysis`}>Zur Aussagenanalyse <span aria-hidden="true">→</span></Link>
          </section>
          <p className="reading-footnote">
            Beobachtungszeitraum: {formatDate(oldest)} bis {formatDate(newest)}.
            Für die technische Zusammenführung können auch fremdsprachige Quellen berücksichtigt werden.
          </p>
        </aside>
      </div>
    </>
  );
}

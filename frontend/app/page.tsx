import type { Metadata } from "next";
import Link from "next/link";
import { Pagination } from "@/components/pagination";
import { listStories, searchArticles } from "@/lib/api";
import {
  allowedSearchParam,
  cleanSearchParam,
  formatDate,
  positivePage,
  safeExternalUrl,
} from "@/lib/format";

export const metadata: Metadata = {
  title: "Nachrichten verstehen",
  description: "Deutschsprachige Nachrichten aus mehreren Quellen. Themen entdecken, Aussagen vergleichen und Hintergründe nachvollziehen.",
};
export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function HomePage({ searchParams }: Props) {
  const raw = await searchParams;
  const q = cleanSearchParam(raw.q);
  const sort = allowedSearchParam(
    raw.sort, ["relevance", "newest", "oldest"], "newest",
  );
  const page = positivePage(cleanSearchParam(raw.page));
  // Featured stories are not displayed for searches or later result pages.
  // Avoid an expensive, otherwise-unused second backend query on those routes.
  const [result, stories] = await Promise.all([
    searchArticles({ q, sort, page }),
    !q && page === 1
      ? listStories({ sort: "newest", page: 1, minSources: 2 })
      : Promise.resolve(null),
  ]);

  return (
    <>
      <section className="front-hero" aria-labelledby="home-title">
        <div className="front-hero-main">
          <p className="eyebrow"><span className="eyebrow-dot" /> NACHRICHTEN IM VERGLEICH</p>
          <h1 id="home-title">Ein Ereignis.<br /><em>Mehrere Perspektiven.</em></h1>
          <p className="lead">
            Was ist passiert – und wie berichten unterschiedliche Medien darüber?
            Entdecke deutschsprachige Nachrichten, gemeinsame Aussagen und offene Fragen.
          </p>
          <form className="search-form" action="/" method="get" role="search">
            <label className="sr-only" htmlFor="home-query">Deutschsprachige Nachrichten durchsuchen</label>
            <input id="home-query" name="q" defaultValue={q} placeholder="Thema, Person oder Nachricht suchen" maxLength={500} />
            <input type="hidden" name="sort" value={sort} />
            <button type="submit">Nachrichten suchen <span aria-hidden="true">→</span></button>
          </form>
          <p className="hero-hint">Auf Deutsch · Mit Originalquellen · Ohne Wahrheitswertung</p>
        </div>
      </section>

      {stories ? (
        <section className="section featured-section" aria-labelledby="featured-heading">
          <div className="section-heading">
            <div><p className="eyebrow">DAS BEWEGT DIE NACHRICHTEN</p><h2 id="featured-heading">Mehrere Medien, ein Thema</h2></div>
            <Link href="/stories?min_sources=2" className="text-link">Alle Ereignisse <span aria-hidden="true">↗</span></Link>
          </div>
          <div className="featured-grid">
            {stories.items.slice(0, 4).map((story, index) => (
              <Link key={story.story_id} href={"/stories/" + story.story_id} className={"featured-story featured-story-" + index}>
                <div className="featured-topline"><span>EREIGNIS {String(index + 1).padStart(2, "0")}</span><span>{formatDate(story.last_article_at)}</span></div>
                <h3>{story.title ?? "Ereignis ohne Titel"}</h3>
                <div className="featured-bottomline"><span>{story.source_count} Quellen · {story.article_count} Artikel</span><span aria-hidden="true">↗</span></div>
              </Link>
            ))}
            {stories.items.length === 0 ? <p className="empty">Derzeit keine quellenübergreifenden deutschsprachigen Ereignisse verfügbar.</p> : null}
          </div>
        </section>
      ) : null}

      <section className="section news-section" aria-labelledby="news-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">WEITERE MELDUNGEN</p>
            <h2 id="news-heading">{q ? "Suchergebnisse" : "Die neuesten Berichte"}</h2>
            <p className="section-description">{q ? result.total + " Treffer für „" + q + "“" : "Deutschsprachige Originalmeldungen, mit Links zu den Quellen."}</p>
          </div>
          <div className="sort-actions">
            <form method="get" action="/">
              {q ? <input type="hidden" name="q" value={q} /> : null}
              <label htmlFor="news-sort">Sortieren</label>
              <select id="news-sort" name="sort" defaultValue={sort}>
                <option value="newest">Neueste zuerst</option>
                <option value="relevance">Relevanz</option>
                <option value="oldest">Älteste zuerst</option>
              </select>
              <button type="submit" className="button secondary">Anwenden</button>
            </form>
          </div>
        </div>

        <div className="news-list">
          {result.items.map((hit) => {
            const externalUrl = safeExternalUrl(hit.url);
            return (
              <article className="news-item" key={hit.document_id}>
                <div className="news-item-meta"><span className="source-indicator" /> <strong>{hit.source_name}</strong><span>{formatDate(hit.published_at)}</span></div>
                <h3>{hit.story_id ? <Link href={"/stories/" + hit.story_id}>{hit.title}</Link> : hit.title}</h3>
                <p>{hit.excerpt}</p>
                <div className="news-item-links">
                  {hit.story_id ? <Link href={"/stories/" + hit.story_id}>Einordnung ansehen <span aria-hidden="true">→</span></Link> : null}
                  {externalUrl ? <a href={externalUrl} target="_blank" rel="noopener noreferrer">Originalartikel <span aria-hidden="true">↗</span></a> : null}
                </div>
              </article>
            );
          })}
          {result.items.length === 0 ? <div className="empty">Keine deutschsprachigen Treffer gefunden. Versuche einen anderen Suchbegriff.</div> : null}
        </div>
        <Pagination page={result.page} pages={result.pages} pathname="/" searchParams={{ q, sort }} />
      </section>
    </>
  );
}

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
  const [result, stories] = await Promise.all([
    searchArticles({ q, sort, page }),
    listStories({ sort: "newest", page: 1, minSources: 2 }),
  ]);

  return (
    <>
      <section className="front-hero" aria-labelledby="home-title">
        <div className="front-hero-main">
          <p className="eyebrow"><span className="eyebrow-dot" /> DIE NACHRICHTEN. MEHR ALS EINE SICHT.</p>
          <h1 id="home-title">Was passiert.<br /><em>Wer berichtet.</em><br />Was dahintersteckt.</h1>
          <p className="lead">
            FSC ordnet Berichte verschiedener Medien zu gemeinsamen Ereignissen.
            Entdecke, was mehrere unabhängige Quellen sagen – und wo Informationen fehlen.
          </p>
          <form className="search-form" action="/" method="get" role="search">
            <label className="sr-only" htmlFor="home-query">Nachrichten durchsuchen</label>
            <input id="home-query" name="q" defaultValue={q} placeholder="Nachrichten, Personen oder Themen suchen" maxLength={500} />
            <input type="hidden" name="sort" value={sort} />
            <button type="submit">Suchen <span aria-hidden="true">↗</span></button>
          </form>
          <p className="hero-hint">Deutschsprachige Nachrichten · Nachvollziehbare Quellen · Keine Wahrheits-Scores</p>
        </div>
        <aside className="front-hero-aside" aria-label="So funktioniert FSC">
          <div className="aside-heading"><span className="aside-index">01 — 03</span><span>WAS FSC UNTERSCHEIDET</span></div>
          <div className="aside-step"><span>01</span><div><strong>Berichte bündeln</strong><p>Mehrere Artikel zum selben Ereignis werden einer Story zugeordnet.</p></div></div>
          <div className="aside-step"><span>02</span><div><strong>Aussagen vergleichen</strong><p>Gemeinsame Aussagen, Belege und Unterschiede transparent einordnen.</p></div></div>
          <div className="aside-step"><span>03</span><div><strong>Grenzen zeigen</strong><p>Nur belegbare Ergebnisse; Unsicherheit wird nicht versteckt.</p></div></div>
          <Link href="/stories" className="aside-link">Alle Ereignisse erkunden <span aria-hidden="true">→</span></Link>
        </aside>
      </section>

      {!q && page === 1 ? (
        <section className="section featured-section" aria-labelledby="featured-heading">
          <div className="section-heading">
            <div><p className="eyebrow">MEDIEN IM VERGLEICH</p><h2 id="featured-heading">Aktuelle Ereignisse</h2></div>
            <Link href="/stories?min_sources=2" className="text-link">Alle Ereignisse <span aria-hidden="true">↗</span></Link>
          </div>
          <div className="featured-grid">
            {stories.items.slice(0, 4).map((story, index) => (
              <Link key={story.story_id} href={"/stories/" + story.story_id} className={"featured-story featured-story-" + index}>
                <div className="featured-topline"><span>STORY {String(index + 1).padStart(2, "0")}</span><span>{formatDate(story.last_article_at)}</span></div>
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
            <p className="eyebrow">ORIGINALBERICHTE</p>
            <h2 id="news-heading">{q ? "Suchergebnisse" : "Neueste Meldungen"}</h2>
            <p className="section-description">{q ? result.total + " Treffer für „" + q + "“" : "Aktuelle deutschsprachige Beiträge aus dem Quellenverzeichnis."}</p>
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

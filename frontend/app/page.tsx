import type { Metadata } from "next";
import Link from "next/link";
import { Pagination } from "@/components/pagination";
import { searchArticles } from "@/lib/api";
import { cleanSearchParam, formatDate, positivePage } from "@/lib/format";

export const metadata: Metadata = { title: "Suche" };
export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function SearchPage({ searchParams }: Props) {
  const raw = await searchParams;
  const q = cleanSearchParam(raw.q);
  const sort = cleanSearchParam(raw.sort) ?? "relevance";
  const page = positivePage(cleanSearchParam(raw.page));
  const result = await searchArticles({ q, sort, page });

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Quellenübergreifend recherchieren</p>
        <h1>Artikel finden. Story verstehen. Unterschiede nachvollziehen.</h1>
        <p className="lead">
          Durchsuche Artikel und springe direkt in die zugehörige Story und ihre generationenkonsistente Analyse.
        </p>
        <form className="search-form" action="/" method="get">
          <input aria-label="Suchbegriff" name="q" defaultValue={q} placeholder="Thema, Person oder Begriff …" maxLength={500} />
          <select aria-label="Sortierung" name="sort" defaultValue={sort}>
            <option value="relevance">Relevanz</option>
            <option value="newest">Neueste zuerst</option>
            <option value="oldest">Älteste zuerst</option>
          </select>
          <button type="submit">Suchen</button>
        </form>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{q ? "Suchergebnisse" : "Neueste Artikel"}</p>
            <h2>{result.total} Treffer</h2>
          </div>
          <Link className="text-link" href="/stories">Alle Stories →</Link>
        </div>
        <div className="stack">
          {result.items.map((hit) => (
            <article className="card search-hit" key={hit.document_id}>
              <div className="meta-row">
                <span>{hit.source_name}</span>
                <span>{formatDate(hit.published_at)}</span>
                {hit.language_code ? <span>{hit.language_code.toUpperCase()}</span> : null}
              </div>
              <h3>{hit.title}</h3>
              <p>{hit.excerpt}</p>
              <div className="card-actions">
                {hit.story_id ? <Link className="button" href={`/stories/${hit.story_id}`}>Story öffnen</Link> : null}
                {hit.url ? <a className="button secondary" href={hit.url} target="_blank" rel="noreferrer">Originalquelle ↗</a> : null}
              </div>
            </article>
          ))}
          {result.items.length === 0 ? <div className="empty">Keine Treffer für diese Suche.</div> : null}
        </div>
        <Pagination page={result.page} pages={result.pages} pathname="/" searchParams={{ q, sort }} />
      </section>
    </>
  );
}

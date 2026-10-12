import type { Metadata } from "next";
import Link from "next/link";
import { Pagination } from "@/components/pagination";
import { listStories } from "@/lib/api";
import {
  allowedSearchParam,
  cleanSearchParam,
  formatDate,
  positivePage,
} from "@/lib/format";

export const metadata: Metadata = {
  title: "Ereignisse",
  description: "Deutschsprachige Nachrichten nach Ereignissen geordnet – mit transparentem Quellenvergleich.",
};
export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function StoriesPage({ searchParams }: Props) {
  const raw = await searchParams;
  const sort = allowedSearchParam(raw.sort, ["newest", "oldest", "largest"], "newest");
  const page = positivePage(cleanSearchParam(raw.page));
  const minSourcesRaw = allowedSearchParam(raw.min_sources, ["1", "2", "3", "5"], "2");
  const minSources = Number(minSourcesRaw);
  const result = await listStories({ sort, page, minSources });

  return (
    <section className="section top-space">
      <div className="section-heading">
        <div>
          <p className="eyebrow">DIE NACHRICHTEN IM ZUSAMMENHANG</p>
          <h1>Ereignisse im Überblick</h1>
          <p className="lead compact">
            Verschiedene deutschsprachige Berichte, nach gemeinsamen Ereignissen geordnet.
            Ein Ereignis ist nicht automatisch eine unabhängige Bestätigung.
          </p>
        </div>
        <Link href="/" className="text-link">← Zur Startseite</Link>
      </div>
      <form className="filters" method="get" action="/stories">
        <label htmlFor="story-sort">Sortierung
          <select id="story-sort" name="sort" defaultValue={sort}>
            <option value="newest">Zuletzt berichtet</option>
            <option value="oldest">Älteste zuerst</option>
            <option value="largest">Meiste Artikel</option>
          </select>
        </label>
        <label htmlFor="story-sources">Mindestens Quellen
          <select id="story-sources" name="min_sources" defaultValue={minSourcesRaw}>
            <option value="1">Eine</option><option value="2">Zwei</option><option value="3">Drei</option><option value="5">Fünf</option>
          </select>
        </label>
        <button type="submit">Ansicht aktualisieren</button>
        <span className="section-description">{result.total} Ereignisse</span>
      </form>
      <div className="story-grid" style={{ marginTop: "1.6rem" }}>
        {result.items.map((story, index) => (
          <Link className="card story-card" href={"/stories/" + story.story_id} key={story.story_id}>
            <div className="meta-row"><span>{String((page - 1) * result.page_size + index + 1).padStart(2, "0")}</span><span>{formatDate(story.last_article_at)}</span></div>
            <h2>{story.title ?? "Ereignis ohne Titel"}</h2>
            <p>{story.source_count} Quellen · {story.article_count} Artikel</p>
            <span className="text-link">Berichte vergleichen <span aria-hidden="true">↗</span></span>
          </Link>
        ))}
        {result.items.length === 0 ? <div className="empty">Keine deutschsprachigen Ereignisse für diese Filter gefunden.</div> : null}
      </div>
      <Pagination page={result.page} pages={result.pages} pathname="/stories" searchParams={{ sort, min_sources: minSourcesRaw }} />
    </section>
  );
}

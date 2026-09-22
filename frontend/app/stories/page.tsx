import type { Metadata } from "next";
import Link from "next/link";
import { Pagination } from "@/components/pagination";
import { listStories } from "@/lib/api";
import { cleanSearchParam, formatDate, positivePage } from "@/lib/format";

export const metadata: Metadata = { title: "Stories" };
export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function StoriesPage({ searchParams }: Props) {
  const raw = await searchParams;
  const sort = cleanSearchParam(raw.sort) ?? "newest";
  const page = positivePage(cleanSearchParam(raw.page));
  const minSources = positivePage(cleanSearchParam(raw.min_sources));
  const result = await listStories({ sort, page, minSources });

  return (
    <section className="section top-space">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Story-Cluster</p>
          <h1>{result.total} Stories</h1>
          <p className="lead compact">Artikel werden quellenübergreifend zu Ereignissen und Themenverläufen zusammengeführt.</p>
        </div>
        <form className="filters" method="get">
          <label>Sortierung
            <select name="sort" defaultValue={sort}>
              <option value="newest">Neueste</option>
              <option value="oldest">Älteste</option>
              <option value="largest">Größte</option>
            </select>
          </label>
          <label>Mind. Quellen
            <select name="min_sources" defaultValue={String(minSources)}>
              <option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="5">5</option>
            </select>
          </label>
          <button type="submit">Anwenden</button>
        </form>
      </div>
      <div className="story-grid">
        {result.items.map((story) => (
          <Link className="card story-card" href={`/stories/${story.story_id}`} key={story.story_id}>
            <div className="meta-row"><span>{story.source_count} Quellen</span><span>{story.article_count} Artikel</span></div>
            <h2>{story.title ?? "Story ohne Titel"}</h2>
            <p>{formatDate(story.first_article_at)} – {formatDate(story.last_article_at)}</p>
            <span className="text-link">Story öffnen →</span>
          </Link>
        ))}
      </div>
      <Pagination page={result.page} pages={result.pages} pathname="/stories" searchParams={{ sort, min_sources: String(minSources) }} />
    </section>
  );
}

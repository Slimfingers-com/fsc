import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getStory } from "@/lib/api";
import { formatDate, percent, safeExternalUrl } from "@/lib/format";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ storyId: string }> };

async function load(storyId: string) {
  try {
    const story = await getStory(storyId);
    if (!story.articles.some((article) =>
      article.language_code?.toLowerCase().startsWith("de")
    )) {
      notFound();
    }
    return story;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { storyId } = await params;
  const story = await load(storyId);
  return {
    title: story.articles.find((article) => article.language_code?.toLowerCase().startsWith("de") && article.title)?.title
      ?? "Ereignis",
  };
}

export default async function StoryPage({ params }: Props) {
  const { storyId } = await params;
  const story = await load(storyId);
  const germanArticles = story.articles.filter(
    (article) => article.language_code?.toLowerCase().startsWith("de"),
  );
  const germanSourceCount = new Set(germanArticles.map((article) => article.source_id)).size;
  const displayTitle = germanArticles.find((article) => article.title)?.title
    ?? "Ereignis ohne Titel";

  return (
    <>
      <section className="story-hero top-space">
        <div>
          <p className="eyebrow">NACHRICHTEN IM VERGLEICH</p>
          <h1>{displayTitle}</h1>
          <div className="meta-row large">
            <span>{germanArticles.length} deutschsprachige Artikel</span><span>{germanSourceCount} Quellen</span>
            <span>{formatDate(story.first_article_at)} – {formatDate(story.last_article_at)}</span>
          </div>
        </div>
        <Link className="button primary-large" href={`/stories/${storyId}/analysis`}>Aussagen vergleichen ↗</Link>
      </section>
      <section className="metric-grid">
        <div className="metric"><strong>{germanSourceCount}</strong><span>Deutschsprachige Quellen</span></div>
        <div className="metric"><strong>{germanArticles.length}</strong><span>Deutschsprachige Artikel</span></div>
        <div className="metric"><strong>{story.entities.length}</strong><span>Entitäten</span></div>
        <div className="metric"><strong>{story.topics.length}</strong><span>Themen</span></div>
      </section>
      {(story.entities.length > 0 || story.topics.length > 0) ? (
        <section className="card section-card">
          <h2>Kontext</h2>
          <div className="tag-row">
            {story.entities.map((entity) => <span className="tag" key={entity.entity_id}>{entity.canonical_name}</span>)}
            {story.topics.map((topic) => <span className="tag" key={topic.topic_id}>{topic.name}</span>)}
          </div>
        </section>
      ) : null}
      <section className="section">
        <p className="eyebrow">DIE ORIGINALBERICHTE</p><h2>So berichten die Quellen</h2><p className="section-description">Die Ansicht zeigt nur deutschsprachige Artikel. Internationale Berichte bleiben für die Hintergrundanalyse erhalten.</p>
        <div className="stack">
          {germanArticles.map((article) => {
            const externalUrl = safeExternalUrl(article.url);
            return (
            <article className="card article-row" key={article.membership_id}>
              <div>
                <div className="meta-row"><span>{article.source_name}</span><span>{formatDate(article.published_at)}</span><span>Zuordnung: {percent(article.similarity_score)}</span></div>
                <h3>{article.title ?? "Artikel ohne Titel"}</h3>
              </div>
              {externalUrl ? <a className="text-link" href={externalUrl} target="_blank" rel="noopener noreferrer">Quelle ↗</a> : null}
            </article>
            );
          })}
        </div>
      </section>
    </>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getStory } from "@/lib/api";
import { formatDate, percent, safeExternalUrl } from "@/lib/format";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ storyId: string }> };

async function load(storyId: string) {
  try {
    return await getStory(storyId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { storyId } = await params;
  const story = await load(storyId);
  return { title: story.title ?? "Story" };
}

export default async function StoryPage({ params }: Props) {
  const { storyId } = await params;
  const story = await load(storyId);

  return (
    <>
      <section className="story-hero top-space">
        <div>
          <p className="eyebrow">Story</p>
          <h1>{story.title ?? "Story ohne Titel"}</h1>
          <div className="meta-row large">
            <span>{story.article_count} Artikel</span><span>{story.source_count} Quellen</span>
            <span>{formatDate(story.first_article_at)} – {formatDate(story.last_article_at)}</span>
          </div>
        </div>
        <Link className="button primary-large" href={`/stories/${storyId}/analysis`}>Analyse öffnen →</Link>
      </section>
      <section className="metric-grid">
        <div className="metric"><strong>{story.source_count}</strong><span>Quellen</span></div>
        <div className="metric"><strong>{story.article_count}</strong><span>Artikel</span></div>
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
        <p className="eyebrow">Quellenlage</p><h2>Artikel in dieser Story</h2>
        <div className="stack">
          {story.articles.map((article) => {
            const externalUrl = safeExternalUrl(article.url);
            return (
            <article className="card article-row" key={article.membership_id}>
              <div>
                <div className="meta-row"><span>{article.source_name}</span><span>{formatDate(article.published_at)}</span><span>{percent(article.similarity_score)} Cluster-Match</span></div>
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

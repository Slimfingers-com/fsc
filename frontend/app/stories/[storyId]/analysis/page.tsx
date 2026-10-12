import type { Metadata } from "next";
import Link from "next/link";
import { ApiError, getStory, getStoryAnalysis } from "@/lib/api";
import { label, percent, safeExternalUrl } from "@/lib/format";
import { notFound } from "next/navigation";

export const metadata: Metadata = { title: "Analyse" };
export const dynamic = "force-dynamic";
type Props = { params: Promise<{ storyId: string }> };

export default async function AnalysisPage({ params }: Props) {
  const { storyId } = await params;
  let story;
  try {
    story = await getStory(storyId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  // A direct link must follow the same German-language rule as
  // public search and discovery, even for a wholly foreign Story.
  if (!story.articles.some((article) =>
    article.language_code?.toLowerCase().startsWith("de")
  )) {
    notFound();
  }
  const analysis = await getStoryAnalysis(storyId);

  if (!analysis) {
    return (
      <section className="empty-state top-space">
        <p className="eyebrow">Analyse</p>
        <h1>Analyse wird noch aufgebaut</h1>
        <p>Für diese Story liegt noch keine vollständige, generationenkonsistente Analyse vor. FSC zeigt bewusst keine Teilstände.</p>
        <Link className="button" href={`/stories/${storyId}`}>Zur Story</Link>
      </section>
    );
  }

  const germanArticleIds = new Set(
    story.articles.filter((article) => article.language_code?.toLowerCase().startsWith("de")).map((article) => article.article_id),
  );
  const germanArticles = story.articles.filter((article) => germanArticleIds.has(article.article_id));
  const title = germanArticles.find((article) => article.title)?.title
    ?? "Ereignis im Überblick";
  const visibleGroups = analysis.claim_groups.filter((group) =>
    group.members.some((member) => germanArticleIds.has(member.article_id)),
  );
  const groupTitles = new Map(visibleGroups.map((group) => [
    group.id,
    group.members.find((member) => germanArticleIds.has(member.article_id))?.claim_text
      ?? group.representative_claim_text,
  ]));
  const visibleDifferences = analysis.differences.filter(
    (difference) => groupTitles.has(difference.left_group_id) && groupTitles.has(difference.right_group_id),
  );

  return (
    <>
      <section className="story-hero top-space">
        <div>
          <p className="eyebrow">AUSSAGEN UND QUELLEN</p>
          <h1>{title}</h1>
          <p className="lead compact">Aussagen, Belege und Unterschiede transparent nebeneinanderstellen. Sichtbar sind hier nur deutschsprachige Textbeiträge; die integrierte Berechnung berücksichtigt weiterhin alle zugehörigen Quellen.</p>
        </div>
        <Link className="button secondary" href={`/stories/${storyId}`}>← Story</Link>
      </section>

      <section className="metric-grid">
        <div className="metric"><strong>{analysis.coverage.claim_group_count}</strong><span>Aussagegruppen</span></div>
        <div className="metric"><strong>{analysis.coverage.shared_group_count}</strong><span>Geteilte Aussagen</span></div>
        <div className="metric"><strong>{analysis.coverage.difference_count}</strong><span>Unterschiede</span></div>
        <div className="metric"><strong>{analysis.coverage.independent_content_source_count}</strong><span>Unabh. Quellen</span></div>
      </section>

      {analysis.coverage_gaps.length > 0 ? (
        <section className="section">
          <p className="eyebrow">ABDECKUNG</p><h2>Beobachtbare Abdeckungslücken</h2>
          <div className="notice-grid">
            {analysis.coverage_gaps.map((gap) => (
              <div className="notice" key={gap.id}>
                <strong>{label(gap.gap_kind)}</strong>
                <span>Beobachtet: {gap.observed_count}{gap.minimum_expected !== null ? ` · Schwelle: ${gap.minimum_expected}` : ""}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {visibleDifferences.length > 0 ? (
        <section className="section">
          <p className="eyebrow">Differences</p><h2>Unterschiedliche Aussagen</h2>
          <div className="stack">
            {visibleDifferences.map((difference) => (
              <article className="difference" key={difference.id}>
                <div><span className={difference.difference_kind === "contradiction" ? "badge danger" : "badge warning"}>{label(difference.difference_kind)}</span><p>{groupTitles.get(difference.left_group_id)}</p><small>{difference.left_independent_source_count} unabhängige Quellenverbünde</small></div>
                <span className="versus">↔</span>
                <div><span className={difference.difference_kind === "contradiction" ? "badge danger" : "badge warning"}>{label(difference.difference_kind)}</span><p>{groupTitles.get(difference.right_group_id)}</p><small>{difference.right_independent_source_count} unabhängige Quellenverbünde</small></div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="section">
        <p className="eyebrow">NACHVOLLZIEHBARE AUSSAGEN</p><h2>Aussagen und Belege</h2>
        <div className="stack">
          {visibleGroups.map((group) => (
            <article className="claim-card" key={group.id}>
              <div className="claim-header">
                <div>
                  <div className="badge-row">
                    <span className={group.consensus.consensus_kind === "shared" ? "badge success" : "badge"}>{label(group.consensus.consensus_kind)}</span>
                    {group.missing_perspective ? <span className="badge warning">{label(group.missing_perspective.missing_kind)}</span> : null}
                  </div>
                  <h3>{groupTitles.get(group.id)}</h3>
                </div>
                <span className="confidence">
                  Gruppierungs-Konfidenz {percent(group.confidence)}
                </span>
              </div>
              <div className="mini-metrics">
                <span>{group.consensus.independent_source_count} unabh. Quellenverbünde</span>
                <span>{group.consensus.evidence_item_count} Evidenzen</span>
                <span>{group.consensus.attributed_perspective_count} attribuierte Perspektiven</span>
              </div>
              {group.evidence.some((evidence) => germanArticleIds.has(evidence.article_id)) ? (
                <div className="evidence-list">
                  <h4>Evidenz</h4>
                  {group.evidence.filter((evidence) => germanArticleIds.has(evidence.article_id)).map((evidence) => (
                    <blockquote key={evidence.id}>
                      <div className="meta-row"><span>{evidence.source_name}</span><span>{label(evidence.evidence_kind)}</span><span>{label(evidence.relation_kind)}</span></div>
                      <p>{evidence.evidence_text}</p>
                    </blockquote>
                  ))}
                </div>
              ) : null}
              <details>
                <summary>{group.members.filter((member) => germanArticleIds.has(member.article_id)).length} zugrunde liegende deutschsprachige Aussagen</summary>
                <div className="member-list">
                  {group.members.filter((member) => germanArticleIds.has(member.article_id)).map((member) => {
                    const externalUrl = safeExternalUrl(member.article_url);
                    return (
                    <div key={member.claim_id}>
                      <strong>{member.source_name}</strong><span>{member.claim_text}</span>
                      {externalUrl ? <a href={externalUrl} target="_blank" rel="noopener noreferrer">Artikel ↗</a> : null}
                    </div>
                    );
                  })}
                </div>
              </details>
            </article>
          ))}
        </div>
      </section>

      <details className="generation-details">
        <summary>Analyse-Generationen</summary>
        <dl>{Object.entries(analysis.generations).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>
      </details>
    </>
  );
}

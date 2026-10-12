import type { StoryAnalysis, StoryDetail } from "./types";

/**
 * Public FSC is German-language first, independent of the country
 * where a publisher is based. Analysis and ingestion remain multilingual.
 */
export function isGermanLanguage(language: string | null | undefined): boolean {
  return /^de(?:-|$)/i.test(language?.trim() ?? "");
}

export function germanStoryArticles(story: StoryDetail): StoryDetail["articles"] {
  return story.articles.filter((article) => isGermanLanguage(article.language_code));
}

export type GermanClaimGroup = {
  id: string;
  title: string;
  visibleSourceCount: number;
  members: StoryAnalysis["claim_groups"][number]["members"];
  evidence: StoryAnalysis["claim_groups"][number]["evidence"];
};

/** Never fall back to a non-German representative claim. */
export function germanClaimGroups(
  analysis: StoryAnalysis,
  germanArticleIds: ReadonlySet<string>,
): GermanClaimGroup[] {
  return analysis.claim_groups.flatMap((group) => {
    const members = group.members.filter((member) => germanArticleIds.has(member.article_id));
    if (!members.length) return [];
    const title = members.find((member) => member.claim_text?.trim())?.claim_text?.trim();
    if (!title) return [];
    const evidence = group.evidence.filter((item) => germanArticleIds.has(item.article_id));
    return [{
      id: group.id,
      title,
      members,
      evidence,
      visibleSourceCount: new Set(members.map((member) => member.source_id)).size,
    }];
  });
}

export type GermanDifference = {
  id: string;
  kind: StoryAnalysis["differences"][number]["difference_kind"];
  left: GermanClaimGroup;
  right: GermanClaimGroup;
};

/** A difference is visible only when both claims have German wording. */
export function germanDifferences(
  analysis: StoryAnalysis,
  visibleGroups: readonly GermanClaimGroup[],
): GermanDifference[] {
  const groups = new Map(visibleGroups.map((group) => [group.id, group]));
  return analysis.differences.flatMap((difference) => {
    const left = groups.get(difference.left_group_id);
    const right = groups.get(difference.right_group_id);
    return left && right ? [{
      id: difference.id,
      kind: difference.difference_kind,
      left,
      right,
    }] : [];
  });
}

import { describe, expect, it } from "vitest";
import {
  germanClaimGroups,
  germanDifferences,
  germanStoryArticles,
  isGermanLanguage,
} from "./public-content";
import type { StoryAnalysis, StoryDetail } from "./types";

function germanDetail(): StoryDetail {
  return {
    story_id: "event", title: "English backend title", language_code: "mul",
    article_count: 3, source_count: 3,
    first_article_at: "2026-10-10T09:00:00Z",
    last_article_at: "2026-10-10T12:00:00Z",
    sources: [], entities: [], topics: [],
    articles: [
      { membership_id: "a", article_id: "de-ch", language_code: "de-CH", title: "Deutsch aus der Schweiz", url: null, published_at: null, article_time: "2026-10-10T09:00:00Z", source_id: "ch", source_name: "Schweizer Medium", source_slug: "ch", match_kind: "matched", similarity_score: 0.9, match_details: null, clustered_at: "2026-10-10T10:00:00Z" },
      { membership_id: "b", article_id: "en-us", language_code: "en", title: "English article", url: null, published_at: null, article_time: "2026-10-10T10:00:00Z", source_id: "us", source_name: "US Medium", source_slug: "us", match_kind: "matched", similarity_score: 0.9, match_details: null, clustered_at: "2026-10-10T10:00:00Z" },
      { membership_id: "c", article_id: "de-at", language_code: "de-AT", title: "Deutsch aus Österreich", url: null, published_at: null, article_time: "2026-10-10T12:00:00Z", source_id: "at", source_name: "Österreichisches Medium", source_slug: "at", match_kind: "matched", similarity_score: 0.9, match_details: null, clustered_at: "2026-10-10T12:00:00Z" },
    ],
  };
}

function germanAnalysis(): StoryAnalysis {
  const group = (id: string, members: Array<{ article: string; source: string; text: string }>) => ({
    id, representative_claim_id: "id", representative_claim_text: "Foreign representative claim", confidence: .87,
    members: members.map((member) => ({
      claim_id: member.article + id, claim_text: member.text,
      article_id: member.article, article_title: null, article_url: null, published_at: null,
      source_id: member.source, source_name: member.source, source_slug: member.source,
      similarity_score: .92, match_kind: "lexical" as const,
    })),
    evidence: members.map((member) => ({
      id: member.article + id, claim_id: member.article + id, article_id: member.article,
      source_id: member.source, source_name: member.source, source_slug: member.source,
      evidence_kind: "independent_reporting", relation_kind: "supports" as const,
      evidence_text: member.text, evidence_confidence: .95, relation_confidence: .95,
    })),
    consensus: { consensus_kind: "shared" as const, claim_count: members.length,
      article_count: members.length, independent_source_count: members.length,
      evidence_item_count: members.length, evidence_source_count: members.length, attributed_perspective_count: 0 },
    missing_perspective: null,
  });
  return {
    story_id: "event", language_code: "mul",
    generations: { claim_relations_run_id: "c", evidence_run_id: "e", consensus_run_id: "x", coverage_run_id: "v" },
    claim_groups: [
      group("both", [{ article: "de-ch", source: "ch", text: "Behauptung aus der Schweiz" }, { article: "en-us", source: "us", text: "English claim" }]),
      group("foreign", [{ article: "en-us", source: "us", text: "English only" }]),
      group("austrian", [{ article: "de-at", source: "at", text: "Behauptung aus Österreich" }]),
    ],
    differences: [
      { id: "hide", claim_relation_id: "r1", left_group_id: "both", right_group_id: "foreign", left_claim_text: "English left", right_claim_text: "English right", difference_kind: "dispute", left_independent_source_count: 1, right_independent_source_count: 1, left_evidence_source_count: 1, right_evidence_source_count: 1 },
      { id: "show", claim_relation_id: "r2", left_group_id: "both", right_group_id: "austrian", left_claim_text: "English left", right_claim_text: "English right", difference_kind: "dispute", left_independent_source_count: 1, right_independent_source_count: 1, left_evidence_source_count: 1, right_evidence_source_count: 1 },
    ],
    coverage: { article_count: 3, source_count: 3, content_source_count: 3, signal_source_count: 0, independent_content_source_count: 3, claim_group_count: 3, shared_group_count: 1, difference_count: 2, attributed_group_count: 0, source_type_counts: {}, coverage_scope_counts: {}, country_counts: {} },
    coverage_gaps: [],
  };
}

describe("German-language public presentation", () => {
  it("includes German-language publishers regardless of country", () => {
    const visible = germanStoryArticles(germanDetail());
    expect(visible.map((article) => article.source_id)).toEqual(["ch", "at"]);
    expect(isGermanLanguage("DE")).toBe(true);
    expect(isGermanLanguage("de-CH")).toBe(true);
    expect(isGermanLanguage("de-AT")).toBe(true);
    expect(isGermanLanguage("en")).toBe(false);
    expect(isGermanLanguage("den")).toBe(false);
    expect(isGermanLanguage(null)).toBe(false);
  });

  it("does not leak foreign-language claims, excerpts or global consensus", () => {
    const visible = germanClaimGroups(germanAnalysis(), new Set(["de-ch", "de-at"]));
    expect(visible.map((group) => group.id)).toEqual(["both", "austrian"]);
    expect(visible[0].title).toBe("Behauptung aus der Schweiz");
    expect(visible[0].visibleSourceCount).toBe(1);
    expect(visible[0].members).toHaveLength(1);
    expect(visible[0].evidence).toHaveLength(1);
    expect(JSON.stringify(visible)).not.toContain("English");
    const differences = germanDifferences(germanAnalysis(), visible);
    expect(differences).toHaveLength(1);
    expect(differences[0].id).toBe("show");
    expect(JSON.stringify(differences)).not.toContain("English");
  });

  it("does not expose any claim groups without German articles", () => {
    expect(germanClaimGroups(germanAnalysis(), new Set())).toEqual([]);
    expect(germanDifferences(germanAnalysis(), [])).toEqual([]);
  });
});

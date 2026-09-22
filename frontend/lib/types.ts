export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type SearchHit = {
  document_id: string;
  article_id: string;
  title: string;
  excerpt: string;
  url: string | null;
  source_id: string;
  source_name: string;
  source_slug: string;
  language_code: string | null;
  published_at: string | null;
  relevance: number;
  story_id: string | null;
};

export type StorySummary = {
  story_id: string;
  title: string | null;
  language_code: string | null;
  article_count: number;
  source_count: number;
  first_article_at: string;
  last_article_at: string;
};

export type StoryDetail = StorySummary & {
  sources: {
    source_id: string;
    name: string;
    slug: string;
    article_count: number;
  }[];
  articles: {
    membership_id: string;
    article_id: string;
    title: string | null;
    url: string | null;
    published_at: string | null;
    article_time: string;
    source_id: string;
    source_name: string;
    source_slug: string;
    match_kind: "created" | "matched" | "retained";
    similarity_score: number;
    match_details: Record<string, unknown> | null;
    clustered_at: string;
  }[];
  entities: {
    entity_id: string;
    canonical_name: string;
    entity_type: string;
    article_count: number;
  }[];
  topics: {
    topic_id: string;
    name: string;
    slug: string;
    article_count: number;
  }[];
};

export type StoryAnalysis = {
  story_id: string;
  language_code: string | null;
  generations: {
    claim_relations_run_id: string;
    evidence_run_id: string;
    consensus_run_id: string;
    coverage_run_id: string;
  };
  claim_groups: {
    id: string;
    representative_claim_id: string;
    representative_claim_text: string;
    confidence: number;
    members: {
      claim_id: string;
      claim_text: string;
      article_id: string;
      article_title: string | null;
      article_url: string | null;
      published_at: string | null;
      source_id: string;
      source_name: string;
      source_slug: string;
      similarity_score: number;
      match_kind: "exact" | "lexical";
    }[];
    evidence: {
      id: string;
      claim_id: string;
      article_id: string;
      source_id: string;
      source_name: string;
      source_slug: string;
      evidence_kind: string;
      relation_kind: "supports" | "context";
      evidence_text: string;
      evidence_confidence: number;
      relation_confidence: number;
    }[];
    consensus: {
      consensus_kind: "single_source" | "shared";
      claim_count: number;
      article_count: number;
      independent_source_count: number;
      evidence_item_count: number;
      evidence_source_count: number;
      attributed_perspective_count: number;
    };
    missing_perspective: {
      missing_kind: "no_attributed_perspective";
      contradiction_relation_ids: string[];
    } | null;
  }[];
  differences: {
    id: string;
    claim_relation_id: string;
    left_group_id: string;
    right_group_id: string;
    left_claim_text: string;
    right_claim_text: string;
    difference_kind: "contradiction";
    left_independent_source_count: number;
    right_independent_source_count: number;
    left_evidence_source_count: number;
    right_evidence_source_count: number;
  }[];
  coverage: {
    article_count: number;
    source_count: number;
    content_source_count: number;
    signal_source_count: number;
    independent_content_owner_count: number;
    claim_group_count: number;
    shared_group_count: number;
    difference_count: number;
    attributed_group_count: number;
    source_type_counts: Record<string, number>;
    coverage_scope_counts: Record<string, number>;
    country_counts: Record<string, number>;
  };
  coverage_gaps: {
    id: string;
    gap_kind: string;
    observed_count: number;
    minimum_expected: number | null;
  }[];
};

with active_sa as (
  select sa.story_id, sa.article_id, a.feed_id, f.source_id
  from story_articles sa
  join articles a on a.id = sa.article_id
  join feeds f on f.id = a.feed_id
  where sa.deleted_at is null
    and a.deleted_at is null
    and f.deleted_at is null
),
story_sizes as (
  select
    story_id,
    count(*) as article_count,
    count(distinct feed_id) as feed_count,
    count(distinct source_id) as source_count
  from active_sa
  group by story_id
)
select 'articles', count(*)::text from articles where deleted_at is null
union all select 'normalized_articles', count(*)::text from articles where deleted_at is null and normalized_at is not null
union all select 'search_documents', count(*)::text from search_documents where deleted_at is null
union all select 'entity_topic_processed', count(*)::text from article_processing_states where deleted_at is null and pipeline='entity_topic' and processed_input_hash is not null
union all select 'claim_extraction_processed', count(*)::text from article_processing_states where deleted_at is null and pipeline='claim_extraction' and processed_input_hash is not null
union all select 'perspective_processed', count(*)::text from article_processing_states where deleted_at is null and pipeline='perspective_analysis' and processed_input_hash is not null
union all select 'story_clustering_processed', count(*)::text from article_processing_states where deleted_at is null and pipeline='story_clustering' and processed_input_hash is not null
union all select 'active_stories', count(*)::text from stories where deleted_at is null
union all select 'active_story_assignments', count(*)::text from story_articles where deleted_at is null
union all select 'singleton_stories', count(*)::text from story_sizes where article_count=1
union all select 'multi_article_stories', count(*)::text from story_sizes where article_count>=2
union all select 'multi_feed_stories', count(*)::text from story_sizes where feed_count>=2
union all select 'multi_source_stories', count(*)::text from story_sizes where source_count>=2
union all select 'active_sources', count(*)::text from sources where deleted_at is null and active is true
union all select 'active_feeds', count(*)::text from feeds where deleted_at is null and active is true
union all select 'active_sources_with_active_feed', count(distinct s.id)::text
  from sources s
  join feeds f on f.source_id = s.id
  where s.deleted_at is null and s.active is true
    and f.deleted_at is null and f.active is true
union all select 'active_editorial_sources_with_active_feed', count(distinct s.id)::text
  from sources s
  join feeds f on f.source_id = s.id
  where s.deleted_at is null and s.active is true
    and f.deleted_at is null and f.active is true
    and s.source_type in ('NEWS', 'REGIONAL')
union all select 'active_editorial_feed_sources_de', count(distinct s.id)::text
  from sources s join feeds f on f.source_id = s.id
  where s.deleted_at is null and s.active is true
    and f.deleted_at is null and f.active is true
    and s.source_type in ('NEWS', 'REGIONAL') and s.country = 'DE'
union all select 'active_editorial_feed_sources_at', count(distinct s.id)::text
  from sources s join feeds f on f.source_id = s.id
  where s.deleted_at is null and s.active is true
    and f.deleted_at is null and f.active is true
    and s.source_type in ('NEWS', 'REGIONAL') and s.country = 'AT'
union all select 'active_editorial_feed_sources_ch', count(distinct s.id)::text
  from sources s join feeds f on f.source_id = s.id
  where s.deleted_at is null and s.active is true
    and f.deleted_at is null and f.active is true
    and s.source_type in ('NEWS', 'REGIONAL') and s.country = 'CH'
union all select 'active_editorial_feed_sources_gb', count(distinct s.id)::text
  from sources s join feeds f on f.source_id = s.id
  where s.deleted_at is null and s.active is true
    and f.deleted_at is null and f.active is true
    and s.source_type in ('NEWS', 'REGIONAL') and s.country = 'GB'
union all select 'active_editorial_feed_sources_us', count(distinct s.id)::text
  from sources s join feeds f on f.source_id = s.id
  where s.deleted_at is null and s.active is true
    and f.deleted_at is null and f.active is true
    and s.source_type in ('NEWS', 'REGIONAL') and s.country = 'US'
union all select 'sources_with_ownership_metadata', count(*)::text
  from sources
  where deleted_at is null and active is true
    and nullif(btrim(ownership), '') is not null
union all select 'active_source_relations', count(*)::text
  from source_relations where deleted_at is null
union all select 'active_collapsing_source_relations', count(*)::text
  from source_relations
  where deleted_at is null
    and relation_kind in ('editorial_parent', 'shared_newsroom', 'joint_editorial_operation')
union all select 'pending_article_provenance', count(*)::text
  from article_provenance
  where deleted_at is null and review_status = 'pending'
union all select 'verified_article_provenance', count(*)::text
  from article_provenance
  where deleted_at is null and review_status = 'verified'
union all select 'rejected_article_provenance', count(*)::text
  from article_provenance
  where deleted_at is null and review_status = 'rejected'
union all select 'active_claim_groups', count(*)::text from story_claim_groups where deleted_at is null
union all select 'active_claim_relations', count(*)::text from story_claim_relations where deleted_at is null
union all select 'active_contradictions', count(*)::text from story_claim_relations where deleted_at is null and relation_kind='contradicts'
union all select 'active_disputes', count(*)::text from story_claim_relations where deleted_at is null and relation_kind='disputes'
union all select 'active_evidence', count(*)::text from story_evidence where deleted_at is null
union all select 'active_consensus', count(*)::text from story_consensus_summaries where deleted_at is null
union all select 'active_differences', count(*)::text from story_difference_summaries where deleted_at is null
union all select 'active_contradiction_differences', count(*)::text from story_difference_summaries where deleted_at is null and difference_kind='contradiction'
union all select 'active_dispute_differences', count(*)::text from story_difference_summaries where deleted_at is null and difference_kind='dispute'
union all select 'active_coverage', count(*)::text from story_coverage_summaries where deleted_at is null
union all select 'article_states_with_error', count(*)::text
  from article_processing_states aps
  join articles a on a.id = aps.article_id
  where aps.deleted_at is null
    and a.deleted_at is null
    and aps.last_error_at is not null
    and (aps.last_processed_at is null or aps.last_error_at > aps.last_processed_at)
union all select 'story_states_with_error', count(*)::text
  from story_processing_states sps
  join stories s on s.id = sps.story_id
  where sps.deleted_at is null
    and s.deleted_at is null
    and sps.last_error_at is not null
    and (sps.last_processed_at is null or sps.last_error_at > sps.last_processed_at)
order by 1;

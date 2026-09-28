# ADR 0026: Signal sources are origin identities, not platforms

## Status

Accepted.

## Context

FSC already has `SourceType.SIGNAL` and the article-level
`confirmation_role=signal`. Signal content must not create independent
journalistic consensus merely because it is visible on a large platform or is
repeated by multiple accounts.

A static country catalog of platforms such as X, Reddit, Bluesky, Mastodon,
Telegram or similar services would model the wrong identity. A platform is a
distribution environment containing many unrelated originators. Treating the
platform itself as one Source would collapse unrelated authors, while treating
every platform appearance as an independent Source would inflate confirmation.

The same real-world institution can also publish both ordinary institutional
content and attention signals through different channels. Creating a second
SIGNAL Source for the same institution would violate FSC's one-institution /
one-editorial-identity Source rule.

## Decision

### 1. Source identity

A SIGNAL Source represents the **origin identity that is known only as a
signal-producing origin**, not the hosting platform.

Examples include a pseudonymous public account, a community-origin identity or
another signal-only origin that does not already map to an FSC Source of a more
specific type.

The platform, account URL, channel or profile is represented as an Outlet /
distribution surface of that Source.

### 2. Existing Sources are reused

If the real-world origin already exists as an FSC Source, do not create a
duplicate SIGNAL Source merely because an item was published on a social,
community or messaging platform.

Instead, reuse the existing Source and assign the concrete item
`confirmation_role=signal` when the item is only an attention/OSINT signal.

This applies equally to NEWS, PRIMARY_SOURCE, NGO, INTEREST_GROUP, COMPANY,
ACADEMIC and THINK_TANK Sources.

### 3. Platforms are not signal Sources

Hosting or discovery services are not SIGNAL Sources for all content they
carry.

A platform company can still be represented as a COMPANY Source for its own
corporate statements. Platform-derived trend or attention data can be an item
from that existing provider Source with `confirmation_role=signal` when
appropriate.

Hashtags, search queries, trending-topic labels and algorithmic clusters are
not Source identities.

### 4. Identity linking is conservative

Accounts or profiles on different platforms are combined into one Source only
when they can be reliably tied to the same origin identity.

Uncertain pseudonymous identities remain separate. FSC must not infer that two
accounts belong to the same person or organization merely from similar names,
content or behavior.

Country metadata describes the origin identity when reliably known. It is not
derived from platform headquarters, server location or the apparent location
of a single post.

### 5. Reposts and upstream origin

A repost, quote, forward or copied signal is not independent confirmation of
the upstream assertion.

When a reliable upstream origin can be established, the existing provenance
model should represent the relationship to the origin. Repetition alone does
not create additional independence.

### 6. Confirmation semantics

`SourceType.SIGNAL` defaults to `confirmation_role=signal`.

`confirmation_role=signal`:

- may contribute attention and coverage signal counts;
- does not count as independent confirmation;
- cannot by itself create multi-source journalistic consensus.

The article-level role remains the shared eligibility mechanism used by both
Consensus and Coverage. If a previously signal-only origin is later established
as a durable editorial, institutional or expert Source, its canonical Source
identity should be reclassified or reconciled rather than proliferating
parallel SIGNAL identities.

## Catalog policy

There is **no static DE/AT/CH/GB/US SIGNAL candidate core** analogous to the
curated media and organization catalogs.

Signal identities are discovered and reconciled at ingestion/review time
because the relevant population is dynamic and event-dependent.

This is an intentional catalog decision, not an unfilled coverage gap.

## Consequences

No database migration or new SourceType is required.

No new media category is required: social/community/channel surfaces can use
the existing digital/other outlet metadata until a later product need justifies
a more detailed distribution taxonomy.

The existing article-level confirmation-role architecture remains the single
source of truth for independent-confirmation eligibility.

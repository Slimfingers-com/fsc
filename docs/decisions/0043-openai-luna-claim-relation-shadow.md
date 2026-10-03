# ADR 0043: OpenAI Luna for Claim-Relation Shadow Evaluation

## Status

Accepted

## Context

ADR 0042 introduced a provider-neutral two-stage claim-relation architecture.
The second stage needs a concrete semantic classifier before FSC can evaluate
whether automatic `disputes` relations improve recall without unacceptable
false positives.

The classifier is a narrow, high-volume task:

- compare two claims plus bounded article context;
- classify exactly one relation from a fixed enum;
- return a confidence score and short reason;
- never decide which source is factually true.

Cost is not the primary constraint, but low per-request cost makes broad shadow
evaluation practical.

## Decision

FSC selects OpenAI `gpt-6-luna` as the first semantic claim-relation adapter.

The adapter uses the OpenAI Responses API with:

- model `gpt-6-luna`;
- the global OpenAI endpoint `https://api.openai.com/v1`;
- `store: false`;
- strict Structured Outputs through `text.format`;
- low reasoning effort by default;
- no tools or web access;
- a bounded output budget.

The provider returns exactly one of:

- `equivalent`;
- `contradicts`;
- `disputes`;
- `unrelated`;
- `insufficient`.

The prompt is conservative and explicitly requires the model to prefer
`insufficient` or `unrelated` instead of inventing a dispute. Prompt version
2 further requires an actual incompatible point between the claims: compatible
differences in detail, specificity, granularity, emphasis, wording, scope, or
attribution are not disputes. A broad headline and a more specific claim about
the same event remain non-disputing unless they make incompatible assertions
about the same aspect. The prompt also treats article content as untrusted quoted
data and instructs the model not to follow instructions embedded in source text.

The adapter records token usage returned by the API, but never includes the API
key in provider configuration or processing identity. Shadow evaluation also
paces requests and retries temporary HTTP 429 rate limits using server-provided
retry/reset headers where available. Shadow candidates are classified in bounded
request batches so a single large story cannot exhaust the structured-output
budget while still requiring every candidate to receive a validated decision.
Spend/quota-limit 429 responses remain fatal and are never retried blindly.

## Shadow-only activation

The first production evaluation is shadow-only.

A dedicated evaluator:

- reads recent active multi-source stories;
- builds candidates using the deterministic Stage-1 logic from ADR 0042;
- calls Luna only for locally plausible candidate pairs;
- writes JSONL audit output containing the candidate, decision, confidence and
  short reason;
- does not persist any claim relation, difference, consensus or coverage change.

Shadow evaluation is deliberately bounded to 16 semantic candidates per story
and 3000 output tokens per response. When candidates have the same overall
score because article-title similarity dominates, claim-level similarity is
used as the secondary ranking signal before deterministic group-key ordering.
This keeps the bounded candidate window focused on materially comparable claims.

Conflict-rich evaluation uses two balanced lanes inside the bounded
16-candidate window: up to eight candidates with local disagreement hints such
as negation or differing numeric values, and up to eight strongest non-hint
candidates ranked by claim similarity. Unused capacity in either lane is filled
from the other lane. This recall lane is important for role-reversal disputes
that use compatible vocabulary without an explicit negation token, such as two
accounts that disagree over which vehicle rammed the other.

Story selection uses the same principle. Half of the bounded story window is
reserved for stories with explicit local conflict hints; the other half is
reserved for stories whose strongest candidates have no hint but high claim
similarity. Unused slots flow to the other lane. This prevents hint-heavy stories
from crowding zero-hint semantic disputes out of the shadow sample before Luna
is called.

The normal claim-relation worker remains configured with
`RuleBasedClaimRelationAnalyzer`. Merely deploying the Luna adapter therefore
does not cause model calls, new processing identity, reprocessing or API cost.

A later decision is required before the normal worker may use the hybrid analyzer
with Luna and persist `disputes`.

## Data handling

The default endpoint is the global OpenAI API endpoint. Requests use
`store: false`. FSC does not claim EU data residency for this integration path.
The input is restricted to representative claim text, article title and the
already bounded claim-adjacent context created by the hybrid architecture.

Shadow JSONL output is an operational evaluation artifact and is not committed to
Git.

## Failure behavior

Missing `OPENAI_API_KEY` prevents only the explicit shadow evaluator from
running. It does not affect production workers.

HTTP errors, refusals, invalid structured output or incomplete classifications
cause the semantic provider call to fail. The hybrid architecture continues to
fail closed to the deterministic Stage-1 result when used in normal processing.

## Consequences

FSC can evaluate Luna against real production claims without changing user-visible
analysis.

The same provider-neutral contract remains available for later comparison with a
different model or vendor if Luna quality is insufficient.

The next decision is not another infrastructure choice. It is a quality decision
based on reviewed shadow results: whether Luna's `disputes` precision is high
enough to permit persisted relations.

from concurrent.futures import (
    ThreadPoolExecutor,
)
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.story import Story
from app.models.story_processing import (
    StoryProcessingRun,
)
from app.repositories.story_processing import (
    StoryProcessingCandidate,
    StoryProcessingRepository,
)
from tests.conftest import (
    TestSessionLocal,
)


def create_stories(
    count: int,
):
    with TestSessionLocal.begin() as db:
        stories = [
            Story(
                language_code="en"
            )
            for _ in range(
                count
            )
        ]
        db.add_all(
            stories
        )
        db.flush()
        return [
            story.id
            for story in stories
        ]


def make_candidate(
    story_id,
    *,
    input_hash=None,
):
    return StoryProcessingCandidate(
        story_id=story_id,
        input_hash=(
            input_hash
            or uuid4().hex * 2
        ),
        provider="test",
        provider_version="1",
        configuration_version="1",
    )


def test_parallel_workers_claim_different_story_states():
    story_ids = create_stories(
        6
    )
    candidates = [
        make_candidate(
            story_id
        )
        for story_id in story_ids
    ]
    now = datetime.now(UTC)

    def run(worker):
        with TestSessionLocal.begin() as db:
            return (
                StoryProcessingRepository()
                .claim_candidates(
                    db,
                    pipeline=(
                        "claim_relations"
                    ),
                    candidates=candidates,
                    worker_id=worker,
                    now=now,
                    claim_expires_at=(
                        now
                        + timedelta(
                            minutes=5
                        )
                    ),
                    limit=3,
                )
            )

    with ThreadPoolExecutor(
        max_workers=2
    ) as pool:
        results = list(
            pool.map(
                run,
                (
                    "a",
                    "b",
                ),
            )
        )

    claimed = [
        item
        for batch in results
        for item in batch
    ]

    assert len(claimed) == 6
    assert len(
        {
            item.story_id
            for item in claimed
        }
    ) == 6


def test_expired_lease_is_marked_lost_on_reclaim():
    story_id = create_stories(
        1
    )[0]
    first_time = datetime.now(
        UTC
    )

    with TestSessionLocal.begin() as db:
        first = (
            StoryProcessingRepository()
            .claim_candidates(
                db,
                pipeline=(
                    "claim_relations"
                ),
                candidates=[
                    make_candidate(
                        story_id,
                        input_hash=(
                            "a" * 64
                        ),
                    )
                ],
                worker_id="first",
                now=first_time,
                claim_expires_at=(
                    first_time
                    + timedelta(
                        seconds=1
                    )
                ),
                limit=1,
            )[0]
        )

    with TestSessionLocal.begin() as db:
        second = (
            StoryProcessingRepository()
            .claim_candidates(
                db,
                pipeline=(
                    "claim_relations"
                ),
                candidates=[
                    make_candidate(
                        story_id,
                        input_hash=(
                            "b" * 64
                        ),
                    )
                ],
                worker_id="second",
                now=(
                    first_time
                    + timedelta(
                        seconds=2
                    )
                ),
                claim_expires_at=(
                    first_time
                    + timedelta(
                        minutes=5
                    )
                ),
                limit=1,
            )[0]
        )

        old_run = db.get(
            StoryProcessingRun,
            first.run_id,
        )

        assert old_run is not None
        assert (
            old_run.outcome
            == "lease_lost"
        )
        assert (
            second.attempt_number
            == 2
        )

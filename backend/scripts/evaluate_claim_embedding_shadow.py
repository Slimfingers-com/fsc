from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.semantic.provider import OpenAIEmbeddingProvider, cosine_similarity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare OpenAI embedding dimensions on Luna shadow claim pairs without persistence."
    )
    parser.add_argument("input", type=Path, help="Luna shadow JSONL input")
    parser.add_argument(
        "--dimensions",
        default="256,512,1536",
        help="Comma-separated embedding dimensions",
    )
    parser.add_argument(
        "--model",
        default="text-embedding-3-small",
    )
    parser.add_argument(
        "--min-request-interval-seconds",
        type=float,
        default=61.0,
        help="Delay between dimension requests for conservative project rate limits",
    )
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * q)
    return ordered[index]


def summarize(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "p10": percentile(values, 0.10),
        "median": statistics.median(values) if values else None,
        "p90": percentile(values, 0.90),
        "max": max(values) if values else None,
    }


def threshold_metrics(
    rows: list[dict[str, object]],
    threshold: float,
) -> dict[str, float | int]:
    positive = [row for row in rows if row["label"] == "equivalent"]
    negative = [
        row
        for row in rows
        if row["label"] in {"unrelated", "insufficient", "disputes", "contradicts"}
    ]
    tp = sum(float(row["similarity"]) >= threshold for row in positive)
    fn = len(positive) - tp
    fp = sum(float(row["similarity"]) >= threshold for row in negative)
    tn = len(negative) - fp
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / len(positive) if positive else 0.0
    return {
        "threshold": threshold,
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "precision": precision,
        "recall": recall,
    }


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")

    records: list[dict[str, object]] = []
    texts: dict[str, int] = {}
    unique_texts: list[str] = []
    with args.input.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            left = item["left"]["claim"]
            right = item["right"]["claim"]
            for value in (left, right):
                if value not in texts:
                    texts[value] = len(unique_texts)
                    unique_texts.append(value)
            records.append(
                {
                    "label": item["relation_kind"],
                    "left": left,
                    "right": right,
                }
            )

    dimensions = [int(value) for value in args.dimensions.split(",") if value.strip()]
    print(json.dumps({
        "pairs": len(records),
        "unique_claims": len(unique_texts),
        "labels": {
            label: sum(row["label"] == label for row in records)
            for label in sorted({str(row["label"]) for row in records})
        },
    }, sort_keys=True))

    for index, dimension in enumerate(dimensions):
        if index and args.min_request_interval_seconds > 0:
            time.sleep(args.min_request_interval_seconds)
        provider = OpenAIEmbeddingProvider(
            api_key=api_key,
            model=args.model,
            dimensions=dimension,
        )
        vectors = provider.embed(tuple(unique_texts))
        scored: list[dict[str, object]] = []
        by_label: dict[str, list[float]] = defaultdict(list)
        for row in records:
            similarity = cosine_similarity(
                vectors[texts[str(row["left"])]],
                vectors[texts[str(row["right"])]],
            )
            scored.append({"label": row["label"], "similarity": similarity})
            by_label[str(row["label"])].append(similarity)

        payload = {
            "dimension": dimension,
            "labels": {
                label: summarize(values)
                for label, values in sorted(by_label.items())
            },
            "thresholds": [
                threshold_metrics(scored, threshold)
                for threshold in (0.75, 0.78, 0.80, 0.82, 0.84, 0.86, 0.88, 0.90)
            ],
        }
        print(json.dumps(payload, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

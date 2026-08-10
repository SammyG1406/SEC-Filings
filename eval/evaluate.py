"""Evaluates retrieval quality against eval/qa_eval_set.json.

Computes Recall@k, Precision@k, MRR@k, and NDCG@k for k in {1, 3, 5, 10},
overall and broken down by question tier (simple_lookup / filtered_lookup /
computed_comparative). Retrieval is unfiltered — every question is searched
across all five filing indexes, the same way an end user would ask it —
so filtered_lookup questions genuinely test whether the right document
surfaces on its own, and the scores are directly comparable to whatever
retrieval strategy (metadata filtering, reranking, etc.) you add later.

Refusal-tier questions have no retrievable answer chunk by design, so
they're excluded from these metrics — they belong to a separate
generation/guardrail evaluation (does the system correctly decline to
answer), which this script does not attempt.

A chunk counts as "relevant" to a question if it contains the question's
`answer_anchor` text. A few computed_comparative anchors in the eval set
join two source lines with " ... " (the question needs both facts); for
those, a chunk is relevant if it contains at least one of the fragments —
documented here because it makes precision/recall slightly lenient for
that subset.

Usage (from the project root):
    python eval/evaluate.py
    python eval/evaluate.py --k 1 3 5 10 --eval-set eval/qa_eval_set.json
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402
from pinecone import Pinecone  # noqa: E402
from query import retrieve  # noqa: E402  (reuses the app's own cross-index search)

load_dotenv()

DEFAULT_EVAL_SET = Path(__file__).resolve().parent / "qa_eval_set.json"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"
DEFAULT_K_VALUES = (1, 3, 5, 10)
METRIC_ORDER = ["recall", "precision", "mrr", "ndcg"]
METRIC_LABELS = {"recall": "Recall@k", "precision": "Precision@k", "mrr": "MRR@k", "ndcg": "NDCG@k"}


def anchor_fragments(anchor: str) -> list[str]:
    return [p.strip() for p in anchor.split("...") if p.strip()]


def score_question(anchor: str, candidates: list[dict], k_values: tuple[int, ...]) -> dict:
    fragments = anchor_fragments(anchor)
    relevance = [1 if any(f in c["text"] for f in fragments) else 0 for c in candidates]
    total_relevant = sum(relevance)
    first_hit_rank = next((i + 1 for i, r in enumerate(relevance) if r), None)

    per_k = {}
    for k in k_values:
        top_k = relevance[:k]
        hits_in_k = sum(top_k)

        recall = hits_in_k / total_relevant if total_relevant else 0.0
        precision = hits_in_k / k
        mrr = 1 / first_hit_rank if first_hit_rank and first_hit_rank <= k else 0.0

        dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(top_k))
        ideal_hits = min(k, total_relevant)
        idcg = sum(1 / math.log2(i + 2) for i in range(ideal_hits))
        ndcg = dcg / idcg if idcg else 0.0

        per_k[k] = {"recall": recall, "precision": precision, "mrr": mrr, "ndcg": ndcg}

    return {"total_relevant_found": total_relevant, "first_hit_rank": first_hit_rank, "per_k": per_k}


def run_evaluation(questions: list[dict], pc: Pinecone, k_values: tuple[int, ...]) -> tuple[list[dict], list[dict]]:
    max_k = max(k_values)
    results = []
    excluded = []

    for q in questions:
        if q["answer_type"] == "refusal" or not q.get("answer_anchor"):
            excluded.append(q)
            continue

        try:
            candidates = retrieve(pc, q["question"], filing=None, top_k=max_k)
        except Exception as exc:  # keep the run going even if one query fails
            print(f"  ! {q['id']} retrieval failed: {exc}", file=sys.stderr)
            candidates = []

        scored = score_question(q["answer_anchor"], candidates, k_values)
        results.append(
            {
                "id": q["id"],
                "tier": q["tier"],
                "source_doc": q["source_doc"],
                "question": q["question"],
                "found": scored["total_relevant_found"] > 0,
                "first_hit_rank": scored["first_hit_rank"],
                "num_candidates": len(candidates),
                "scores": scored["per_k"],
            }
        )

    return results, excluded


def aggregate(results: list[dict], k_values: tuple[int, ...]) -> dict:
    if not results:
        return {k: {m: 0.0 for m in METRIC_ORDER} for k in k_values}

    agg = {k: {m: [] for m in METRIC_ORDER} for k in k_values}
    for r in results:
        for k in k_values:
            for m in METRIC_ORDER:
                agg[k][m].append(r["scores"][k][m])

    return {k: {m: sum(vals) / len(vals) for m, vals in agg[k].items()} for k in k_values}


def format_table(agg: dict, k_values: tuple[int, ...], n: int) -> str:
    header = "Metric".ljust(14) + "".join(f"k={k}".rjust(10) for k in k_values)
    lines = [header, "-" * len(header)]
    for m in METRIC_ORDER:
        row = METRIC_LABELS[m].ljust(14) + "".join(f"{agg[k][m]:.3f}".rjust(10) for k in k_values)
        lines.append(row)
    lines.append(f"(n={n})")
    return "\n".join(lines)


def format_markdown_table(agg: dict, k_values: tuple[int, ...]) -> str:
    header = "| Metric | " + " | ".join(f"k={k}" for k in k_values) + " |"
    sep = "|---|" + "|".join("---" for _ in k_values) + "|"
    rows = [header, sep]
    for m in METRIC_ORDER:
        row = "| " + METRIC_LABELS[m] + " | " + " | ".join(f"{agg[k][m]:.3f}" for k in k_values) + " |"
        rows.append(row)
    return "\n".join(rows)


def build_markdown_report(
    results: list[dict],
    excluded: list[dict],
    overall: dict,
    by_tier: dict[str, dict],
    tier_counts: dict[str, int],
    k_values: tuple[int, ...],
    timestamp: str,
) -> str:
    misses = [r for r in results if not r["found"]]

    lines = [
        f"# Retrieval evaluation report — {timestamp}",
        "",
        f"Evaluated {len(results)} questions ({', '.join(f'{count} {tier}' for tier, count in tier_counts.items())}). "
        f"{len(excluded)} refusal-tier questions excluded (no retrievable answer by design).",
        "",
        "## Overall",
        "",
        format_markdown_table(overall, k_values),
        "",
    ]

    for tier, tier_results in sorted(by_tier.items()):
        agg = aggregate(tier_results, k_values)
        lines += [f"## {tier} (n={len(tier_results)})", "", format_markdown_table(agg, k_values), ""]

    lines += [f"## Misses ({len(misses)}/{len(results)})", ""]
    if misses:
        lines.append("Answer chunk not found in the top-{} retrieved candidates for any index:".format(max(k_values)))
        lines.append("")
        for r in misses:
            lines.append(f"- `{r['id']}` [{r['tier']}, {r['source_doc']}]: {r['question']}")
    else:
        lines.append("None — every evaluated question's answer chunk was retrieved.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_SET)
    parser.add_argument("--k", type=int, nargs="+", default=list(DEFAULT_K_VALUES))
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args()

    k_values = tuple(sorted(args.k))
    questions = json.loads(args.eval_set.read_text(encoding="utf-8"))

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

    print(f"Evaluating {len(questions)} questions from {args.eval_set} ...")
    results, excluded = run_evaluation(questions, pc, k_values)

    tier_counts = defaultdict(int)
    by_tier = defaultdict(list)
    for r in results:
        tier_counts[r["tier"]] += 1
        by_tier[r["tier"]].append(r)

    overall = aggregate(results, k_values)

    print()
    print("=== Overall ===")
    print(format_table(overall, k_values, len(results)))
    for tier, tier_results in sorted(by_tier.items()):
        print()
        print(f"=== {tier} ===")
        print(format_table(aggregate(tier_results, k_values), k_values, len(tier_results)))

    misses = [r for r in results if not r["found"]]
    print()
    print(f"Misses: {len(misses)}/{len(results)} (answer chunk not found in top-{max(k_values)})")
    for r in misses:
        print(f"  - {r['id']} [{r['tier']}, {r['source_doc']}]: {r['question']}")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report_json = {
        "timestamp": timestamp,
        "eval_set": str(args.eval_set),
        "k_values": list(k_values),
        "overall": overall,
        "by_tier": {tier: aggregate(tier_results, k_values) for tier, tier_results in by_tier.items()},
        "tier_counts": dict(tier_counts),
        "excluded_refusal_count": len(excluded),
        "results": results,
    }
    markdown = build_markdown_report(results, excluded, overall, by_tier, dict(tier_counts), k_values, timestamp)

    for stem in (timestamp, "latest"):
        (args.output_dir / f"{stem}.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")
        (args.output_dir / f"{stem}.md").write_text(markdown, encoding="utf-8")

    print()
    print(f"Report saved to {args.output_dir / f'{timestamp}.md'} (and latest.md / latest.json)")


if __name__ == "__main__":
    main()

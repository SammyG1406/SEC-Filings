"""Evaluates retrieval quality against eval/qa_eval_set.json.

Computes Recall@k, Precision@k, MRR@k, and NDCG@k for k in {1, 3, 5, 10},
overall and broken down by question tier (simple_lookup / filtered_lookup /
computed_comparative). Retrieval is unfiltered — every question is searched
across all five filing indexes, the same way an end user would ask it —
so filtered_lookup questions genuinely test whether the right document
surfaces on its own, and the scores are directly comparable to whatever
retrieval strategy (metadata filtering, reranking, etc.) you add later.

Refusal-tier questions have no retrievable answer chunk by design, so they're
excluded from Recall/Precision/MRR/NDCG — there's no "correct" chunk to score
against. But they are still run through the retriever: Pinecone always
returns its nearest neighbors regardless of whether anything actually
answers the question, so "the system returns nothing" isn't something
retrieval can do on its own — that has to be a downstream guardrail (e.g.
refuse below a similarity threshold). What this script CAN measure is
whether refusal-tier top-hit scores are meaningfully weaker than answerable
questions' — that gap is what such a threshold would be calibrated against.
See "Refusal-tier diagnostics" in the report. Whether the system eventually
*generates* a correct refusal is a separate generation/guardrail evaluation,
which this script does not attempt.

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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from pinecone import Pinecone  # noqa: E402
from query import (  # noqa: E402  (reuses the app's own retrieval)
    NUM_QUERY_VARIATIONS,
    RERANK_POOL_SIZE,
    rerank,
    retrieve,
    retrieve_with_fusion,
    route_filing,
)

load_dotenv()

DEFAULT_EVAL_SET = Path(__file__).resolve().parent / "qa_eval_set.json"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"
DEFAULT_K_VALUES = (1, 3, 5, 10)
DEFAULT_MAX_WORKERS = 5  # each question already fans out internally (up to 5x, or 20x under --rag-fusion)
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


def safe_retrieve(
    pc: Pinecone,
    question: str,
    top_k: int,
    client: anthropic.Anthropic | None = None,
    num_variations: int = NUM_QUERY_VARIATIONS,
    use_fusion: bool = False,
    use_rerank: bool = False,
    use_route: bool = False,
) -> list[dict]:
    try:
        filing = route_filing(client, question) if use_route else None
        pool_k = max(RERANK_POOL_SIZE, top_k) if use_rerank else top_k
        if use_fusion:
            hits, _variations = retrieve_with_fusion(pc, client, question, filing, pool_k, num_variations)
        else:
            hits = retrieve(pc, question, filing=filing, top_k=pool_k)
        return rerank(pc, question, hits, top_k) if use_rerank else hits
    except Exception as exc:  # keep the run going even if one query fails
        print(f"  ! retrieval failed for {question!r}: {exc}", file=sys.stderr)
        return []


def top1_score(candidates: list[dict]) -> float | None:
    """Prefers the rerank score (the actually-used relevance signal when
    reranking is on) over the raw embedding-similarity score."""
    if not candidates:
        return None
    return candidates[0].get("rerank_score", candidates[0].get("score"))


def run_evaluation(
    questions: list[dict],
    pc: Pinecone,
    k_values: tuple[int, ...],
    client: anthropic.Anthropic | None = None,
    num_variations: int = NUM_QUERY_VARIATIONS,
    max_workers: int = DEFAULT_MAX_WORKERS,
    use_fusion: bool = False,
    use_rerank: bool = False,
    use_route: bool = False,
) -> tuple[list[dict], list[dict]]:
    max_k = max(k_values)
    scoreable = [q for q in questions if q["answer_type"] != "refusal" and q.get("answer_anchor")]
    skipped = [q for q in questions if q["answer_type"] != "refusal" and not q.get("answer_anchor")]

    def process(q: dict) -> dict:
        candidates = safe_retrieve(pc, q["question"], max_k, client, num_variations, use_fusion, use_rerank, use_route)
        scored = score_question(q["answer_anchor"], candidates, k_values)
        return {
            "id": q["id"],
            "tier": q["tier"],
            "source_doc": q["source_doc"],
            "question": q["question"],
            "found": scored["total_relevant_found"] > 0,
            "first_hit_rank": scored["first_hit_rank"],
            "num_candidates": len(candidates),
            "top1_score": top1_score(candidates),
            "scores": scored["per_k"],
        }

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(process, scoreable))

    return results, skipped


def run_refusal_diagnostics(
    questions: list[dict],
    pc: Pinecone,
    k_values: tuple[int, ...],
    client: anthropic.Anthropic | None = None,
    num_variations: int = NUM_QUERY_VARIATIONS,
    max_workers: int = DEFAULT_MAX_WORKERS,
    use_fusion: bool = False,
    use_rerank: bool = False,
    use_route: bool = False,
) -> list[dict]:
    """Retrieves for refusal-tier questions and records how confident the
    top hits look, without scoring them against any ground-truth chunk."""
    max_k = max(k_values)
    refusal_qs = [q for q in questions if q["answer_type"] == "refusal"]

    def process(q: dict) -> dict:
        candidates = safe_retrieve(pc, q["question"], max_k, client, num_variations, use_fusion, use_rerank, use_route)
        scores = [c.get("rerank_score", c.get("score")) for c in candidates]
        top3 = scores[:3]
        return {
            "id": q["id"],
            "source_doc": q["source_doc"],
            "question": q["question"],
            "top1_score": scores[0] if scores else None,
            "top3_avg_score": sum(top3) / len(top3) if top3 else None,
            "top1_source_doc": candidates[0]["source"] if candidates else None,
            "top1_matches_named_doc": (candidates[0]["source"] == q["source_doc"]) if candidates else None,
        }

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(process, refusal_qs))


def score_gap_summary(results: list[dict], refusal_diagnostics: list[dict]) -> dict:
    answerable_scores = [r["top1_score"] for r in results if r["top1_score"] is not None]
    refusal_scores = [d["top1_score"] for d in refusal_diagnostics if d["top1_score"] is not None]

    def stats(vals: list[float]) -> dict:
        if not vals:
            return {"n": 0, "mean": None, "min": None, "max": None}
        return {"n": len(vals), "mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}

    return {"answerable_top1": stats(answerable_scores), "refusal_top1": stats(refusal_scores)}


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
    skipped: list[dict],
    refusal_diagnostics: list[dict],
    gap: dict,
    overall: dict,
    by_tier: dict[str, dict],
    tier_counts: dict[str, int],
    k_values: tuple[int, ...],
    timestamp: str,
    method_label: str,
) -> str:
    misses = [r for r in results if not r["found"]]

    lines = [
        f"# Retrieval evaluation report — {method_label} — {timestamp}",
        "",
        f"Evaluated {len(results)} answerable questions ({', '.join(f'{count} {tier}' for tier, count in tier_counts.items())}) "
        f"against Recall/Precision/MRR/NDCG, plus {len(refusal_diagnostics)} refusal-tier questions run through "
        f"retrieval for score diagnostics only (no ground-truth chunk to score against).",
    ]
    if skipped:
        lines.append(f"{len(skipped)} question(s) skipped entirely (missing `answer_anchor`).")
    lines += ["", "## Overall", "", format_markdown_table(overall, k_values), ""]

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

    def fmt(v):
        return f"{v:.3f}" if v is not None else "—"

    a, ref = gap["answerable_top1"], gap["refusal_top1"]
    lines += [
        "## Refusal-tier diagnostics",
        "",
        "Refusal questions have no correct chunk, so there's nothing to score them against directly. "
        "What matters is whether their top-hit similarity scores run lower than answerable questions' — "
        "that gap is what a similarity-threshold refusal guardrail would be calibrated on.",
        "",
        "| Group | n | mean top-1 score | min | max |",
        "|---|---|---|---|---|",
        f"| Answerable questions | {a['n']} | {fmt(a['mean'])} | {fmt(a['min'])} | {fmt(a['max'])} |",
        f"| Refusal questions | {ref['n']} | {fmt(ref['mean'])} | {fmt(ref['min'])} | {fmt(ref['max'])} |",
        "",
    ]
    if a["mean"] is not None and ref["mean"] is not None:
        gap_val = a["mean"] - ref["mean"]
        verdict = (
            "there's a usable gap — a similarity threshold could plausibly separate them."
            if gap_val > 0.02
            else "the gap is small — a bare similarity threshold likely won't reliably separate them; "
            "the guardrail will need more than top-score alone."
        )
        lines.append(f"Mean gap: {gap_val:.3f} ({verdict})")
        lines.append("")

    lines += ["### Per-question detail", "", "| id | question | top-1 score | top-1 doc | matches named company? |", "|---|---|---|---|---|"]
    for d in refusal_diagnostics:
        score_str = f"{d['top1_score']:.3f}" if d["top1_score"] is not None else "—"
        match_str = "yes" if d["top1_matches_named_doc"] else ("n/a" if d["top1_matches_named_doc"] is None else "no")
        lines.append(f"| `{d['id']}` | {d['question']} | {score_str} | {d['top1_source_doc']} | {match_str} |")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_SET)
    parser.add_argument("--k", type=int, nargs="+", default=list(DEFAULT_K_VALUES))
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument(
        "--rag-fusion",
        action="store_true",
        help="Evaluate RAG Fusion (query translation + RRF) instead of baseline single-query retrieval. "
        "Adds one Claude call per question and writes to separate '-fusion' report files.",
    )
    parser.add_argument("--num-variations", type=int, default=NUM_QUERY_VARIATIONS)
    parser.add_argument(
        "--route",
        action="store_true",
        help="Logical routing: extract the named company from the question and restrict retrieval "
        "to its filing (no-op for questions that don't name a single company). "
        "Writes to separate '-routed' report files.",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="Rerank retrieved candidates against the actual question text before scoring. "
        "Widens the candidate pool to RERANK_POOL_SIZE first, then reranks down to k. "
        "Writes to separate '-rerank' report files.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help="Questions evaluated concurrently. Each question already fans out internally "
        "(5x, or ~20x under --rag-fusion), so keep this modest to avoid API rate limits.",
    )
    args = parser.parse_args()

    k_values = tuple(sorted(args.k))
    questions = json.loads(args.eval_set.read_text(encoding="utf-8"))

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    needs_client = args.rag_fusion or args.route
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]) if needs_client else None
    method_label = (
        ("RAG Fusion" if args.rag_fusion else "baseline")
        + (" + routing" if args.route else "")
        + (" + rerank" if args.rerank else "")
    )

    print(f"Evaluating {len(questions)} questions from {args.eval_set} [{method_label}] ...")
    results, skipped = run_evaluation(
        questions, pc, k_values, client, args.num_variations, args.max_workers, args.rag_fusion, args.rerank, args.route
    )
    refusal_diagnostics = run_refusal_diagnostics(
        questions, pc, k_values, client, args.num_variations, args.max_workers, args.rag_fusion, args.rerank, args.route
    )
    gap = score_gap_summary(results, refusal_diagnostics)

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

    a, ref = gap["answerable_top1"], gap["refusal_top1"]
    print()
    print("=== Refusal-tier diagnostics ===")
    if a["mean"] is not None and ref["mean"] is not None:
        print(f"Answerable top-1 score: mean={a['mean']:.3f} min={a['min']:.3f} max={a['max']:.3f} (n={a['n']})")
        print(f"Refusal    top-1 score: mean={ref['mean']:.3f} min={ref['min']:.3f} max={ref['max']:.3f} (n={ref['n']})")
        print(f"Gap: {a['mean'] - ref['mean']:.3f}")
    for d in refusal_diagnostics:
        score_str = f"{d['top1_score']:.3f}" if d["top1_score"] is not None else "n/a"
        print(f"  - {d['id']} [{d['source_doc']}] top1={score_str} top1_doc={d['top1_source_doc']}: {d['question']}")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report_json = {
        "timestamp": timestamp,
        "method": "rag_fusion" if args.rag_fusion else "baseline",
        "num_variations": args.num_variations if args.rag_fusion else None,
        "routed": args.route,
        "reranked": args.rerank,
        "eval_set": str(args.eval_set),
        "k_values": list(k_values),
        "overall": overall,
        "by_tier": {tier: aggregate(tier_results, k_values) for tier, tier_results in by_tier.items()},
        "tier_counts": dict(tier_counts),
        "skipped_missing_anchor_count": len(skipped),
        "results": results,
        "refusal_diagnostics": refusal_diagnostics,
        "score_gap_summary": gap,
    }
    markdown = build_markdown_report(
        results, skipped, refusal_diagnostics, gap, overall, by_tier, dict(tier_counts), k_values, timestamp, method_label
    )

    suffix = ("-fusion" if args.rag_fusion else "") + ("-routed" if args.route else "") + ("-rerank" if args.rerank else "")
    for stem in (f"{timestamp}{suffix}", f"latest{suffix}"):
        (args.output_dir / f"{stem}.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")
        (args.output_dir / f"{stem}.md").write_text(markdown, encoding="utf-8")

    print()
    print(f"Report saved to {args.output_dir / f'{timestamp}{suffix}.md'} (and latest{suffix}.md / latest{suffix}.json)")


if __name__ == "__main__":
    main()

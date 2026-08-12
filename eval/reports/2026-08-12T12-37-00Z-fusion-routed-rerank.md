# Retrieval evaluation report — RAG Fusion + routing + rerank — 2026-08-12T12-37-00Z

Evaluated 40 answerable questions (15 simple_lookup, 10 filtered_lookup, 15 computed_comparative) against Recall/Precision/MRR/NDCG, plus 10 refusal-tier questions run through retrieval for score diagnostics only (no ground-truth chunk to score against).

## Overall

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.625 | 0.775 | 0.775 | 0.775 |
| Precision@k | 0.625 | 0.258 | 0.155 | 0.077 |
| MRR@k | 0.625 | 0.692 | 0.692 | 0.692 |
| NDCG@k | 0.625 | 0.713 | 0.713 | 0.713 |

## computed_comparative (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.400 | 0.800 | 0.800 | 0.800 |
| Precision@k | 0.400 | 0.267 | 0.160 | 0.080 |
| MRR@k | 0.400 | 0.578 | 0.578 | 0.578 |
| NDCG@k | 0.400 | 0.635 | 0.635 | 0.635 |

## filtered_lookup (n=10)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.700 | 0.700 | 0.700 | 0.700 |
| Precision@k | 0.700 | 0.233 | 0.140 | 0.070 |
| MRR@k | 0.700 | 0.700 | 0.700 | 0.700 |
| NDCG@k | 0.700 | 0.700 | 0.700 | 0.700 |

## simple_lookup (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.800 | 0.800 | 0.800 | 0.800 |
| Precision@k | 0.800 | 0.267 | 0.160 | 0.080 |
| MRR@k | 0.800 | 0.800 | 0.800 | 0.800 |
| NDCG@k | 0.800 | 0.800 | 0.800 | 0.800 |

## Misses (9/40)

Answer chunk not found in the top-10 retrieved candidates for any index:

- `q001` [simple_lookup, castellum-10q]: What was Castellum's total revenue for the three months ended June 30, 2026?
- `q002` [simple_lookup, castellum-10q]: What was Castellum's total assets as of June 30, 2026?
- `q003` [simple_lookup, castellum-10q]: What was Castellum's cash balance as of June 30, 2026?
- `q004` [filtered_lookup, castellum-10q]: What was Castellum's total revenue for the three months ended June 30, 2025 (the prior-year comparative quarter, not 2026)?
- `q005` [filtered_lookup, castellum-10q]: What was Castellum's total assets as of December 31, 2025 (not June 30, 2026)?
- `q006` [computed_comparative, castellum-10q]: What was Castellum's gross margin (gross profit divided by revenue), as a percentage, for the three months ended June 30, 2026?
- `q007` [computed_comparative, castellum-10q]: By how many dollars did Castellum's total revenue grow for the six months ended June 30, 2026 compared to the six months ended June 30, 2025?
- `q008` [computed_comparative, castellum-10q]: By what percentage did Castellum's total operating expenses increase for the three months ended June 30, 2026 compared to the same period in 2025?
- `q035` [filtered_lookup, xerian-10q]: What was Xeriant's net loss for the three months ended December 31, 2024 (the prior-year comparative quarter, not 2025)?

## Refusal-tier diagnostics

Refusal questions have no correct chunk, so there's nothing to score them against directly. What matters is whether their top-hit similarity scores run lower than answerable questions' — that gap is what a similarity-threshold refusal guardrail would be calibrated on.

| Group | n | mean top-1 score | min | max |
|---|---|---|---|---|
| Answerable questions | 32 | 0.663 | 0.105 | 0.966 |
| Refusal questions | 8 | 0.171 | 0.050 | 0.295 |

Mean gap: 0.492 (there's a usable gap — a similarity threshold could plausibly separate them.)

### Per-question detail

| id | question | top-1 score | top-1 doc | matches named company? |
|---|---|---|---|---|
| `q009` | What was Castellum's total revenue for the three months ended June 30, 2027? | — | None | n/a |
| `q010` | What dividend per share did Castellum pay on its common stock during the six months ended June 30, 2026? | — | None | n/a |
| `q019` | What was Ironstone Properties' total revenue for the three months ended March 31, 2026? | 0.182 | ironstone-properties-10q | yes |
| `q020` | What was Ironstone Properties' total assets as of March 31, 2027? | 0.204 | ironstone-properties-10q | yes |
| `q029` | What was Regen BioPharma's total revenue for the full fiscal year ended September 30, 2026? | 0.154 | regen-bio-pharma-10q | yes |
| `q030` | How many full-time employees did Regen BioPharma have as of December 31, 2025? | 0.050 | regen-bio-pharma-10q | yes |
| `q039` | What was Xeriant's total revenue for the six months ended December 31, 2025? | 0.266 | xerian-10q | yes |
| `q040` | What was Xeriant's total assets as of December 31, 2026? | 0.295 | xerian-10q | yes |
| `q049` | What was Alternus Clean Energy's total revenue for the three months ended March 31, 2027? | 0.088 | alternus-10q | yes |
| `q050` | What was Alternus Clean Energy's cost of goods sold for the three months ended March 31, 2026? | 0.129 | alternus-10q | yes |

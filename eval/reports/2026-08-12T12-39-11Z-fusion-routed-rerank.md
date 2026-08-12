# Retrieval evaluation report — RAG Fusion + routing + rerank — 2026-08-12T12-39-11Z

Evaluated 40 answerable questions (15 simple_lookup, 10 filtered_lookup, 15 computed_comparative) against Recall/Precision/MRR/NDCG, plus 10 refusal-tier questions run through retrieval for score diagnostics only (no ground-truth chunk to score against).

## Overall

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.700 | 0.875 | 0.875 | 0.875 |
| Precision@k | 0.700 | 0.292 | 0.175 | 0.087 |
| MRR@k | 0.700 | 0.779 | 0.779 | 0.779 |
| NDCG@k | 0.700 | 0.804 | 0.804 | 0.804 |

## computed_comparative (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.467 | 0.933 | 0.933 | 0.933 |
| Precision@k | 0.467 | 0.311 | 0.187 | 0.093 |
| MRR@k | 0.467 | 0.678 | 0.678 | 0.678 |
| NDCG@k | 0.467 | 0.744 | 0.744 | 0.744 |

## filtered_lookup (n=10)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.800 | 0.800 | 0.800 | 0.800 |
| Precision@k | 0.800 | 0.267 | 0.160 | 0.080 |
| MRR@k | 0.800 | 0.800 | 0.800 | 0.800 |
| NDCG@k | 0.800 | 0.800 | 0.800 | 0.800 |

## simple_lookup (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.867 | 0.867 | 0.867 | 0.867 |
| Precision@k | 0.867 | 0.289 | 0.173 | 0.087 |
| MRR@k | 0.867 | 0.867 | 0.867 | 0.867 |
| NDCG@k | 0.867 | 0.867 | 0.867 | 0.867 |

## Misses (5/40)

Answer chunk not found in the top-10 retrieved candidates for any index:

- `q002` [simple_lookup, castellum-10q]: What was Castellum's total assets as of June 30, 2026?
- `q003` [simple_lookup, castellum-10q]: What was Castellum's cash balance as of June 30, 2026?
- `q005` [filtered_lookup, castellum-10q]: What was Castellum's total assets as of December 31, 2025 (not June 30, 2026)?
- `q007` [computed_comparative, castellum-10q]: By how many dollars did Castellum's total revenue grow for the six months ended June 30, 2026 compared to the six months ended June 30, 2025?
- `q035` [filtered_lookup, xerian-10q]: What was Xeriant's net loss for the three months ended December 31, 2024 (the prior-year comparative quarter, not 2025)?

## Refusal-tier diagnostics

Refusal questions have no correct chunk, so there's nothing to score them against directly. What matters is whether their top-hit similarity scores run lower than answerable questions' — that gap is what a similarity-threshold refusal guardrail would be calibrated on.

| Group | n | mean top-1 score | min | max |
|---|---|---|---|---|
| Answerable questions | 40 | 0.610 | 0.070 | 0.966 |
| Refusal questions | 10 | 0.166 | 0.050 | 0.295 |

Mean gap: 0.444 (there's a usable gap — a similarity threshold could plausibly separate them.)

### Per-question detail

| id | question | top-1 score | top-1 doc | matches named company? |
|---|---|---|---|---|
| `q009` | What was Castellum's total revenue for the three months ended June 30, 2027? | 0.146 | castellum-10q | yes |
| `q010` | What dividend per share did Castellum pay on its common stock during the six months ended June 30, 2026? | 0.147 | castellum-10q | yes |
| `q019` | What was Ironstone Properties' total revenue for the three months ended March 31, 2026? | 0.182 | ironstone-properties-10q | yes |
| `q020` | What was Ironstone Properties' total assets as of March 31, 2027? | 0.204 | ironstone-properties-10q | yes |
| `q029` | What was Regen BioPharma's total revenue for the full fiscal year ended September 30, 2026? | 0.154 | regen-bio-pharma-10q | yes |
| `q030` | How many full-time employees did Regen BioPharma have as of December 31, 2025? | 0.050 | regen-bio-pharma-10q | yes |
| `q039` | What was Xeriant's total revenue for the six months ended December 31, 2025? | 0.266 | xerian-10q | yes |
| `q040` | What was Xeriant's total assets as of December 31, 2026? | 0.295 | xerian-10q | yes |
| `q049` | What was Alternus Clean Energy's total revenue for the three months ended March 31, 2027? | 0.088 | alternus-10q | yes |
| `q050` | What was Alternus Clean Energy's cost of goods sold for the three months ended March 31, 2026? | 0.129 | alternus-10q | yes |

# Retrieval evaluation report — RAG Fusion — 2026-08-12T05-04-52Z

Evaluated 40 answerable questions (15 simple_lookup, 10 filtered_lookup, 15 computed_comparative) against Recall/Precision/MRR/NDCG, plus 10 refusal-tier questions run through retrieval for score diagnostics only (no ground-truth chunk to score against).

## Overall

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.725 | 0.825 | 0.825 | 0.875 |
| Precision@k | 0.725 | 0.275 | 0.165 | 0.087 |
| MRR@k | 0.725 | 0.767 | 0.767 | 0.774 |
| NDCG@k | 0.725 | 0.782 | 0.782 | 0.798 |

## computed_comparative (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.667 | 0.800 | 0.800 | 0.933 |
| Precision@k | 0.667 | 0.267 | 0.160 | 0.093 |
| MRR@k | 0.667 | 0.711 | 0.711 | 0.730 |
| NDCG@k | 0.667 | 0.733 | 0.733 | 0.777 |

## filtered_lookup (n=10)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.600 | 0.800 | 0.800 | 0.800 |
| Precision@k | 0.600 | 0.267 | 0.160 | 0.080 |
| MRR@k | 0.600 | 0.700 | 0.700 | 0.700 |
| NDCG@k | 0.600 | 0.726 | 0.726 | 0.726 |

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
| Answerable questions | 40 | 0.583 | 0.442 | 0.684 |
| Refusal questions | 10 | 0.545 | 0.451 | 0.589 |

Mean gap: 0.038 (there's a usable gap — a similarity threshold could plausibly separate them.)

### Per-question detail

| id | question | top-1 score | top-1 doc | matches named company? |
|---|---|---|---|---|
| `q009` | What was Castellum's total revenue for the three months ended June 30, 2027? | 0.550 | castellum-10q | yes |
| `q010` | What dividend per share did Castellum pay on its common stock during the six months ended June 30, 2026? | 0.589 | castellum-10q | yes |
| `q019` | What was Ironstone Properties' total revenue for the three months ended March 31, 2026? | 0.586 | ironstone-properties-10q | yes |
| `q020` | What was Ironstone Properties' total assets as of March 31, 2027? | 0.577 | ironstone-properties-10q | yes |
| `q029` | What was Regen BioPharma's total revenue for the full fiscal year ended September 30, 2026? | 0.580 | regen-bio-pharma-10q | yes |
| `q030` | How many full-time employees did Regen BioPharma have as of December 31, 2025? | 0.498 | regen-bio-pharma-10q | yes |
| `q039` | What was Xeriant's total revenue for the six months ended December 31, 2025? | 0.494 | xerian-10q | yes |
| `q040` | What was Xeriant's total assets as of December 31, 2026? | 0.451 | xerian-10q | yes |
| `q049` | What was Alternus Clean Energy's total revenue for the three months ended March 31, 2027? | 0.561 | alternus-10q | yes |
| `q050` | What was Alternus Clean Energy's cost of goods sold for the three months ended March 31, 2026? | 0.564 | alternus-10q | yes |

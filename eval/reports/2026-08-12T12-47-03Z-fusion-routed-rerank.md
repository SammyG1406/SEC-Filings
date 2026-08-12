# Retrieval evaluation report — RAG Fusion + routing + rerank — 2026-08-12T12-47-03Z

Evaluated 40 answerable questions (15 simple_lookup, 10 filtered_lookup, 15 computed_comparative) against Recall/Precision/MRR/NDCG, plus 10 refusal-tier questions run through retrieval for score diagnostics only (no ground-truth chunk to score against).

## Overall

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.475 | 0.575 | 0.575 | 0.575 |
| Precision@k | 0.475 | 0.192 | 0.115 | 0.058 |
| MRR@k | 0.475 | 0.521 | 0.521 | 0.521 |
| NDCG@k | 0.475 | 0.535 | 0.535 | 0.535 |

## computed_comparative (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.267 | 0.533 | 0.533 | 0.533 |
| Precision@k | 0.267 | 0.178 | 0.107 | 0.053 |
| MRR@k | 0.267 | 0.389 | 0.389 | 0.389 |
| NDCG@k | 0.267 | 0.426 | 0.426 | 0.426 |

## filtered_lookup (n=10)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.500 | 0.500 | 0.500 | 0.500 |
| Precision@k | 0.500 | 0.167 | 0.100 | 0.050 |
| MRR@k | 0.500 | 0.500 | 0.500 | 0.500 |
| NDCG@k | 0.500 | 0.500 | 0.500 | 0.500 |

## simple_lookup (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.667 | 0.667 | 0.667 | 0.667 |
| Precision@k | 0.667 | 0.222 | 0.133 | 0.067 |
| MRR@k | 0.667 | 0.667 | 0.667 | 0.667 |
| NDCG@k | 0.667 | 0.667 | 0.667 | 0.667 |

## Misses (17/40)

Answer chunk not found in the top-10 retrieved candidates for any index:

- `q002` [simple_lookup, castellum-10q]: What was Castellum's total assets as of June 30, 2026?
- `q003` [simple_lookup, castellum-10q]: What was Castellum's cash balance as of June 30, 2026?
- `q005` [filtered_lookup, castellum-10q]: What was Castellum's total assets as of December 31, 2025 (not June 30, 2026)?
- `q007` [computed_comparative, castellum-10q]: By how many dollars did Castellum's total revenue grow for the six months ended June 30, 2026 compared to the six months ended June 30, 2025?
- `q013` [simple_lookup, ironstone-properties-10q]: What was Ironstone Properties' net operating loss for the three months ended March 31, 2026?
- `q014` [filtered_lookup, ironstone-properties-10q]: What was Ironstone Properties' total liabilities as of December 31, 2025 (not March 31, 2026)?
- `q017` [computed_comparative, ironstone-properties-10q]: By how many dollars did Ironstone Properties' total stockholders' equity deficit widen (become more negative) from December 31, 2025 to March 31, 2026?
- `q018` [computed_comparative, ironstone-properties-10q]: By what percentage did Ironstone Properties' net operating loss increase for the three months ended March 31, 2026 compared to the same period in 2025?
- `q022` [simple_lookup, regen-bio-pharma-10q]: What was Regen BioPharma's net loss for the three months ended December 31, 2025?
- `q025` [filtered_lookup, regen-bio-pharma-10q]: What was Regen BioPharma's net loss for the three months ended December 31, 2024 (the prior-year comparative period, not 2025)?
- `q033` [simple_lookup, xerian-10q]: What was Xeriant's net cash used in operating activities for the six months ended December 31, 2025?
- `q035` [filtered_lookup, xerian-10q]: What was Xeriant's net loss for the three months ended December 31, 2024 (the prior-year comparative quarter, not 2025)?
- `q036` [computed_comparative, xerian-10q]: By how many dollars did Xeriant's net loss decrease for the three months ended December 31, 2025 compared to the same period in 2024?
- `q038` [computed_comparative, xerian-10q]: What was the total dollar swing in Xeriant's six-month net income (loss) attributable to common stockholders, from a loss in the prior year to income in the current year (six months ended December 31, 2025 vs. 2024)?
- `q045` [filtered_lookup, alternus-10q]: What was Alternus Clean Energy's net cash used in operating activities for the three months ended March 31, 2025 (the prior-year comparative period, not 2026), in thousands of dollars as reported?
- `q046` [computed_comparative, alternus-10q]: By how many thousands of dollars did Alternus Clean Energy's net cash used in operating activities increase for the three months ended March 31, 2026 compared to the same period in 2025?
- `q048` [computed_comparative, alternus-10q]: By how many thousands of dollars did Alternus Clean Energy's total liabilities change from December 31, 2025 to March 31, 2026?

## Refusal-tier diagnostics

Refusal questions have no correct chunk, so there's nothing to score them against directly. What matters is whether their top-hit similarity scores run lower than answerable questions' — that gap is what a similarity-threshold refusal guardrail would be calibrated on.

| Group | n | mean top-1 score | min | max |
|---|---|---|---|---|
| Answerable questions | 40 | 0.566 | 0.022 | 0.974 |
| Refusal questions | 10 | 0.164 | 0.046 | 0.381 |

Mean gap: 0.402 (there's a usable gap — a similarity threshold could plausibly separate them.)

### Per-question detail

| id | question | top-1 score | top-1 doc | matches named company? |
|---|---|---|---|---|
| `q009` | What was Castellum's total revenue for the three months ended June 30, 2027? | 0.197 | castellum-10q | yes |
| `q010` | What dividend per share did Castellum pay on its common stock during the six months ended June 30, 2026? | 0.124 | castellum-10q | yes |
| `q019` | What was Ironstone Properties' total revenue for the three months ended March 31, 2026? | 0.159 | ironstone-properties-10q | yes |
| `q020` | What was Ironstone Properties' total assets as of March 31, 2027? | 0.194 | ironstone-properties-10q | yes |
| `q029` | What was Regen BioPharma's total revenue for the full fiscal year ended September 30, 2026? | 0.057 | regen-bio-pharma-10q | yes |
| `q030` | How many full-time employees did Regen BioPharma have as of December 31, 2025? | 0.046 | regen-bio-pharma-10q | yes |
| `q039` | What was Xeriant's total revenue for the six months ended December 31, 2025? | 0.306 | xerian-10q | yes |
| `q040` | What was Xeriant's total assets as of December 31, 2026? | 0.381 | xerian-10q | yes |
| `q049` | What was Alternus Clean Energy's total revenue for the three months ended March 31, 2027? | 0.080 | alternus-10q | yes |
| `q050` | What was Alternus Clean Energy's cost of goods sold for the three months ended March 31, 2026? | 0.099 | alternus-10q | yes |

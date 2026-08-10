# Retrieval evaluation report — 2026-08-10T13-09-07Z

Evaluated 40 questions (15 simple_lookup, 10 filtered_lookup, 15 computed_comparative). 10 refusal-tier questions excluded (no retrievable answer by design).

## Overall

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.650 | 0.775 | 0.825 | 0.875 |
| Precision@k | 0.650 | 0.258 | 0.165 | 0.087 |
| MRR@k | 0.650 | 0.708 | 0.721 | 0.729 |
| NDCG@k | 0.650 | 0.726 | 0.747 | 0.765 |

## computed_comparative (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.533 | 0.667 | 0.800 | 0.933 |
| Precision@k | 0.533 | 0.222 | 0.160 | 0.093 |
| MRR@k | 0.533 | 0.589 | 0.622 | 0.644 |
| NDCG@k | 0.533 | 0.609 | 0.666 | 0.714 |

## filtered_lookup (n=10)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.700 | 0.800 | 0.800 | 0.800 |
| Precision@k | 0.700 | 0.267 | 0.160 | 0.080 |
| MRR@k | 0.700 | 0.750 | 0.750 | 0.750 |
| NDCG@k | 0.700 | 0.763 | 0.763 | 0.763 |

## simple_lookup (n=15)

| Metric | k=1 | k=3 | k=5 | k=10 |
|---|---|---|---|---|
| Recall@k | 0.733 | 0.867 | 0.867 | 0.867 |
| Precision@k | 0.733 | 0.289 | 0.173 | 0.087 |
| MRR@k | 0.733 | 0.800 | 0.800 | 0.800 |
| NDCG@k | 0.733 | 0.817 | 0.817 | 0.817 |

## Misses (5/40)

Answer chunk not found in the top-10 retrieved candidates for any index:

- `q002` [simple_lookup, castellum-10q]: What was Castellum's total assets as of June 30, 2026?
- `q003` [simple_lookup, castellum-10q]: What was Castellum's cash balance as of June 30, 2026?
- `q005` [filtered_lookup, castellum-10q]: What was Castellum's total assets as of December 31, 2025 (not June 30, 2026)?
- `q007` [computed_comparative, castellum-10q]: By how many dollars did Castellum's total revenue grow for the six months ended June 30, 2026 compared to the six months ended June 30, 2025?
- `q035` [filtered_lookup, xerian-10q]: What was Xeriant's net loss for the three months ended December 31, 2024 (the prior-year comparative quarter, not 2025)?

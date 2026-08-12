"""Answers a question about the SEC filings using Pinecone (retrieval) + Claude (generation).

Usage (from the project root):
    python src/query.py "What was the change in revenue?"
    python src/query.py "What was the change in revenue?" --filing castellum
    python src/query.py "Compare gross profit across filings" --top-k 8
"""

import argparse
import os
import re
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv
from pinecone import Pinecone

from config import NAMESPACE

load_dotenv()

MODEL = "claude-sonnet-5"
TOP_K_PER_INDEX = 5

INDEXES = {
    "castellum": "castellum-10q",
    "ironstone": "ironstone-properties-10q",
    "regen-bio-pharma": "regen-bio-pharma-10q",
    "xerian": "xerian-10q",
    "alternus": "alternus-10q",
}

# --- RAG Fusion (query translation) ---
NUM_QUERY_VARIATIONS = 3
FUSION_TOP_K_PER_QUERY = 10
RRF_K = 60

# --- Reranking ---
RERANK_MODEL = "bge-reranker-v2-m3"
RERANK_POOL_SIZE = 20

QUERY_VARIATION_SYSTEM_PROMPT = """You are a search query generator for a retrieval system over SEC 10-Q filings.
Given a user's question, write {n} alternative search queries that could each surface the relevant \
passage, by varying phrasing, terminology (e.g. "net loss" vs "net income (loss)"), and specificity. \
Keep each query self-contained and focused on the same underlying information need - do not invent \
new facts or change what is being asked.

Respond with exactly {n} lines, one query per line, and nothing else (no numbering, bullets, or \
commentary)."""


def _search_index(pc: Pinecone, index_name: str, question: str) -> list[dict]:
    index = pc.Index(index_name)
    res = index.search(
        namespace=NAMESPACE,
        query={"inputs": {"text": question}, "top_k": TOP_K_PER_INDEX},
    )
    return [
        {
            "score": hit["score_"],
            "source": hit["fields"]["source"],
            "page": hit["fields"]["page"],
            "text": hit["fields"]["chunk_text"],
        }
        for hit in res["result"]["hits"]
    ]


def retrieve(pc: Pinecone, question: str, filing: str | None, top_k: int) -> list[dict]:
    index_names = [INDEXES[filing]] if filing else list(INDEXES.values())

    with ThreadPoolExecutor(max_workers=len(index_names)) as pool:
        results = pool.map(lambda name: _search_index(pc, name, question), index_names)

    hits = [hit for result in results for hit in result]
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:top_k]


def generate_query_variations(
    client: anthropic.Anthropic, question: str, n: int = NUM_QUERY_VARIATIONS
) -> list[str]:
    """Query translation step: asks Claude to rephrase the question into `n`
    alternative search queries covering the same information need."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=QUERY_VARIATION_SYSTEM_PROMPT.format(n=n),
        messages=[{"role": "user", "content": question}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    lines = [re.sub(r"^[\-\d.)\s]+", "", line).strip() for line in text.splitlines()]
    return [line for line in lines if line][:n]


def reciprocal_rank_fusion(ranked_lists: list[list[dict]], k: int = RRF_K) -> list[dict]:
    """Combines several ranked hit lists into one via Reciprocal Rank Fusion:
    score(chunk) = sum over lists of 1 / (k + rank_in_list). Chunks are
    deduped on (source, page, text) since Pinecone hits don't carry the
    original record id back through `retrieve`."""
    scores: dict[tuple, float] = {}
    best_hit: dict[tuple, dict] = {}

    for hits in ranked_lists:
        for rank, hit in enumerate(hits, start=1):
            key = (hit["source"], hit["page"], hit["text"])
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in best_hit or hit["score"] > best_hit[key]["score"]:
                best_hit[key] = hit

    fused = [{**best_hit[key], "rrf_score": score} for key, score in scores.items()]
    fused.sort(key=lambda h: h["rrf_score"], reverse=True)
    return fused


def retrieve_with_fusion(
    pc: Pinecone,
    client: anthropic.Anthropic,
    question: str,
    filing: str | None,
    top_k: int,
    num_variations: int = NUM_QUERY_VARIATIONS,
) -> tuple[list[dict], list[str]]:
    """RAG Fusion: translates the question into several query variations,
    retrieves for each independently, and fuses the ranked results with RRF."""
    variations = generate_query_variations(client, question, num_variations)
    queries = [question] + variations

    per_query_k = max(FUSION_TOP_K_PER_QUERY, top_k)
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        ranked_lists = list(pool.map(lambda q: retrieve(pc, q, filing, per_query_k), queries))
    fused = reciprocal_rank_fusion(ranked_lists)
    return fused[:top_k], variations


def rerank(pc: Pinecone, question: str, hits: list[dict], top_n: int) -> list[dict]:
    """Reads each candidate's actual text against the actual question (a joint,
    cross-attention read, unlike the independently-computed embeddings behind
    `retrieve`) and reorders by true relevance rather than rank consensus."""
    if not hits:
        return hits
    result = pc.inference.rerank(
        model=RERANK_MODEL,
        query=question,
        documents=[{"text": h["text"]} for h in hits],
        rank_fields=["text"],
        top_n=min(top_n, len(hits)),
        return_documents=False,
    )
    reranked = []
    for item in result.data:
        hit = dict(hits[item.index])
        hit["rerank_score"] = item.score
        reranked.append(hit)
    return reranked


def build_context(hits: list[dict]) -> str:
    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{i}] Source: {hit['source']}, page {int(hit['page'])}\n{hit['text']}"
        )
    return "\n\n".join(blocks)


def answer(client: anthropic.Anthropic, question: str, context: str) -> str:
    system = (
        "You answer questions about SEC 10-Q filings using only the provided excerpts. "
        "Cite the source and page for every claim, like this: (castellum-10q, p.33). "
        "If the excerpts don't contain the answer, say so directly instead of guessing."
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n\n{context}\n\nQuestion: {question}",
            }
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--filing", choices=list(INDEXES), default=None)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument(
        "--rag-fusion",
        dest="rag_fusion",
        action="store_true",
        default=True,
        help="Translate the question into multiple query variations and fuse retrieval "
        "across them with RRF (default: on).",
    )
    parser.add_argument(
        "--no-rag-fusion", dest="rag_fusion", action="store_false", help="Use plain single-query retrieval."
    )
    parser.add_argument("--num-variations", type=int, default=NUM_QUERY_VARIATIONS)
    parser.add_argument(
        "--rerank",
        dest="rerank",
        action="store_true",
        default=True,
        help="Rerank retrieved candidates against the actual question text before answering (default: on).",
    )
    parser.add_argument("--no-rerank", dest="rerank", action="store_false", help="Skip reranking.")
    args = parser.parse_args()

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    pool_k = RERANK_POOL_SIZE if args.rerank else args.top_k

    if args.rag_fusion:
        hits, variations = retrieve_with_fusion(pc, client, args.question, args.filing, pool_k, args.num_variations)
        print("Query variations:")
        for v in variations:
            print(f"  - {v}")
        print()
    else:
        hits = retrieve(pc, args.question, args.filing, pool_k)

    if args.rerank:
        hits = rerank(pc, args.question, hits, args.top_k)

    if not hits:
        print("No relevant chunks found.")
        return

    context = build_context(hits)
    print(answer(client, args.question, context))


if __name__ == "__main__":
    main()

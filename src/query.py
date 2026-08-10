"""Answers a question about the SEC filings using Pinecone (retrieval) + Claude (generation).

Usage (from the project root):
    python src/query.py "What was the change in revenue?"
    python src/query.py "What was the change in revenue?" --filing castellum
    python src/query.py "Compare gross profit across filings" --top-k 8
"""

import argparse
import os

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


def retrieve(pc: Pinecone, question: str, filing: str | None, top_k: int) -> list[dict]:
    index_names = [INDEXES[filing]] if filing else list(INDEXES.values())

    hits = []
    for index_name in index_names:
        index = pc.Index(index_name)
        res = index.search(
            namespace=NAMESPACE,
            query={"inputs": {"text": question}, "top_k": TOP_K_PER_INDEX},
        )
        for hit in res["result"]["hits"]:
            hits.append(
                {
                    "score": hit["score_"],
                    "source": hit["fields"]["source"],
                    "page": hit["fields"]["page"],
                    "text": hit["fields"]["chunk_text"],
                }
            )

    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:top_k]


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
    args = parser.parse_args()

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    hits = retrieve(pc, args.question, args.filing, args.top_k)
    if not hits:
        print("No relevant chunks found.")
        return

    context = build_context(hits)
    print(answer(client, args.question, context))


if __name__ == "__main__":
    main()

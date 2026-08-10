"""Connects to Pinecone and creates the SEC filings index if it doesn't exist yet.

Uses Pinecone's integrated (hosted) embedding model, so no separate
embedding API key is required — you upsert raw text and Pinecone embeds it.
"""

import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

INDEX_NAME = "sec-filings"
EMBEDDING_MODEL = "llama-text-embed-v2"


def main() -> None:
    api_key = os.environ["PINECONE_API_KEY"]
    pc = Pinecone(api_key=api_key)

    if pc.has_index(INDEX_NAME):
        print(f"Index '{INDEX_NAME}' already exists.")
    else:
        pc.create_index_for_model(
            name=INDEX_NAME,
            cloud="aws",
            region="us-east-1",
            embed={
                "model": EMBEDDING_MODEL,
                "field_map": {"text": "chunk_text"},
            },
        )
        print(f"Created index '{INDEX_NAME}' with embedding model '{EMBEDDING_MODEL}'.")

    desc = pc.describe_index(INDEX_NAME)
    print(f"Status: {desc.status}")
    print(f"Host: {desc.host}")


if __name__ == "__main__":
    main()

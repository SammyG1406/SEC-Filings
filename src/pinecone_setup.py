"""Creates one Pinecone index per SEC filing.

Uses Pinecone's integrated (hosted) embedding model, so no separate
embedding API key is required — you upsert raw text and Pinecone embeds it.
"""

import os

from dotenv import load_dotenv
from pinecone import Pinecone

from config import EMBEDDING_MODEL, FILINGS

load_dotenv()


def main() -> None:
    api_key = os.environ["PINECONE_API_KEY"]
    pc = Pinecone(api_key=api_key)

    for index_name, filename in FILINGS.items():
        if pc.has_index(index_name):
            print(f"Index '{index_name}' already exists.")
        else:
            pc.create_index_for_model(
                name=index_name,
                cloud="aws",
                region="us-east-1",
                embed={
                    "model": EMBEDDING_MODEL,
                    "field_map": {"text": "chunk_text"},
                },
            )
            print(f"Created index '{index_name}' (source: {filename}).")

    print()
    print("Current indexes:")
    for idx in pc.list_indexes():
        print(f"  - {idx.name}  [{idx.status.state}]  {idx.host}")


if __name__ == "__main__":
    main()

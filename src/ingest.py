"""Extracts text from each 10-Q PDF, chunks it, and upserts the chunks into
its matching Pinecone index (created by pinecone_setup.py).

Embeddings are generated server-side by Pinecone (integrated inference),
so we upsert raw text under the `chunk_text` field, not vectors.
"""

import os
import re

from dotenv import load_dotenv
from pinecone import Pinecone
from pypdf import PdfReader

from config import FILINGS, FILINGS_DIR, NAMESPACE

load_dotenv()

MAX_CHARS = 700
OVERLAP = 100
BATCH_SIZE = 90


def chunk_page(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Packs paragraphs into ~max_chars chunks, carrying a bit of overlap between them."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    raw_chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_chars:
            raw_chunks.append(current)
            current = ""
        if len(para) > max_chars:
            if current:
                raw_chunks.append(current)
                current = ""
            for i in range(0, len(para), max_chars - overlap):
                raw_chunks.append(para[i : i + max_chars])
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        raw_chunks.append(current)

    chunks = []
    for i, c in enumerate(raw_chunks):
        if i == 0:
            chunks.append(c)
        else:
            tail = raw_chunks[i - 1][-overlap:]
            chunks.append(f"{tail}\n\n{c}")
    return chunks


def extract_records(pdf_path: str, source: str) -> list[dict]:
    reader = PdfReader(pdf_path)
    records = []
    chunk_index = 0
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        for chunk in chunk_page(text):
            records.append(
                {
                    "_id": f"{source}-p{page_num:03d}-c{chunk_index:04d}",
                    "chunk_text": chunk,
                    "source": source,
                    "page": page_num,
                }
            )
            chunk_index += 1
    return records


def upsert_in_batches(index, records: list[dict]) -> None:
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        index.upsert_records(namespace=NAMESPACE, records=batch)
        print(f"    upserted {i + len(batch)}/{len(records)}")


def main() -> None:
    api_key = os.environ["PINECONE_API_KEY"]
    pc = Pinecone(api_key=api_key)

    for index_name, filename in FILINGS.items():
        print(f"{filename} -> {index_name}")
        pdf_path = FILINGS_DIR / filename
        records = extract_records(str(pdf_path), source=index_name)
        print(f"  {len(records)} chunks extracted")

        index = pc.Index(index_name)
        try:
            index.delete(delete_all=True, namespace=NAMESPACE)
        except Exception:
            pass  # namespace doesn't exist yet on a fresh index
        upsert_in_batches(index, records)

        stats = index.describe_index_stats()
        print(f"  index now has {stats.total_vector_count} vectors\n")


if __name__ == "__main__":
    main()

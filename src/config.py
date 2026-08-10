"""Shared constants for the Pinecone/Claude pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILINGS_DIR = ROOT / "filings"

EMBEDDING_MODEL = "llama-text-embed-v2"
NAMESPACE = "chunks"

# index_name -> PDF filename (relative to FILINGS_DIR)
FILINGS = {
    "castellum-10q": "Castellum 10Q.pdf",
    "ironstone-properties-10q": "Ironstone Properties 10Q.pdf",
    "regen-bio-pharma-10q": "Regen Bio Pharma 10Q.pdf",
    "xerian-10q": "Xerian 10Q.pdf",
    "alternus-10q": "Alternus 10Q.pdf",
}

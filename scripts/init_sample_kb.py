"""Initialize sample knowledge base documents."""

import asyncio
from pathlib import Path

from src.services.kb_ingestion import kb_ingestion_service

SAMPLE_DOCS_DIR = Path("knowledge_base/sample_docs")
DEFAULT_TENANT_ID = "default"


async def init_sample_kb():
    """Initialize sample knowledge base with default documents."""
    if not SAMPLE_DOCS_DIR.exists():
        print(f"Sample docs directory not found: {SAMPLE_DOCS_DIR}")
        return

    doc_files = list(SAMPLE_DOCS_DIR.glob("*.md"))

    if not doc_files:
        print(f"No markdown files found in {SAMPLE_DOCS_DIR}")
        return

    print(f"Found {len(doc_files)} sample documents to ingest")

    for doc_file in doc_files:
        category = doc_file.stem.split("_")[0] if "_" in doc_file.stem else "general"
        print(f"Ingesting: {doc_file.name} (category: {category})")

        try:
            result = await kb_ingestion_service.ingest_document(
                tenant_id=DEFAULT_TENANT_ID,
                file_path=doc_file,
                category=category,
                tags=["sample", "initial"],
            )
            print(f"✓ Ingested: {result['document_name']} ({result['chunks_count']} chunks)")
        except Exception as e:
            print(f"✗ Failed to ingest {doc_file.name}: {e}")

    print(f"\nSample knowledge base initialized for tenant: {DEFAULT_TENANT_ID}")


if __name__ == "__main__":
    asyncio.run(init_sample_kb())


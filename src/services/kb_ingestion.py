"""Knowledge base document ingestion service."""

import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from pypdf import PdfReader
from docx import Document

from src.core.config import settings
from src.core.logging import get_logger
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import vector_store

logger = get_logger(__name__)


class KBIngestionService:
    """Service for ingesting documents into the knowledge base."""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.chunk_size = settings.KB_CHUNK_SIZE
        self.chunk_overlap = settings.KB_CHUNK_OVERLAP

    def _read_text_file(self, file_path: Path) -> str:
        """Read text from a .txt file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_pdf(self, file_path: Path) -> str:
        """Extract text from a PDF file."""
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n".join(text_parts)

    def _read_docx(self, file_path: Path) -> str:
        """Extract text from a DOCX file."""
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs]
        return "\n".join(paragraphs)

    def _read_markdown(self, file_path: Path) -> str:
        """Read text from a Markdown file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def read_document(self, file_path: Path) -> str:
        """
        Read text from a document file.

        Args:
            file_path: Path to the document file

        Returns:
            Extracted text content
        """
        suffix = file_path.suffix.lower()

        if suffix == ".txt":
            return self._read_text_file(file_path)
        elif suffix == ".pdf":
            return self._read_pdf(file_path)
        elif suffix == ".docx":
            return self._read_docx(file_path)
        elif suffix in [".md", ".markdown"]:
            return self._read_markdown(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def chunk_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to chunk
            chunk_size: Size of each chunk (defaults to config)
            overlap: Overlap between chunks (defaults to config)

        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.chunk_overlap

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            if end < len(text):
                chunk = chunk.rstrip()

            chunks.append(chunk)
            start = end - overlap

        return chunks

    async def ingest_document(
        self,
        tenant_id: str,
        file_path: Path,
        category: str = "general",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest a document into the knowledge base.

        Args:
            tenant_id: Tenant identifier
            file_path: Path to the document file
            category: Document category (e.g., "hardware", "software", "network")
            tags: Optional list of tags
            metadata: Optional additional metadata

        Returns:
            Dictionary with ingestion results
        """
        try:
            logger.info("Ingesting document", tenant_id=tenant_id, file_path=str(file_path), category=category)

            text = self.read_document(file_path)
            chunks = self.chunk_text(text)

            document_id = str(uuid.uuid4())
            document_hash = hashlib.md5(text.encode()).hexdigest()

            embeddings = await self.embedding_service.embed_batch(chunks)

            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                chunk_metadata = {
                    "document_id": document_id,
                    "document_path": str(file_path),
                    "document_name": file_path.name,
                    "category": category,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "document_hash": document_hash,
                    "tags": ", ".join(tags) if tags else "",  # ChromaDB doesn't support lists in metadata
                    **(metadata or {}),
                }

                metadatas.append(chunk_metadata)
                ids.append(chunk_id)

            vector_store.add_documents(
                tenant_id=tenant_id,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )

            result = {
                "document_id": document_id,
                "document_name": file_path.name,
                "chunks_count": len(chunks),
                "category": category,
                "tags": tags or [],
            }

            logger.info("Document ingested successfully", tenant_id=tenant_id, **result)
            return result

        except Exception as e:
            logger.error("Failed to ingest document", tenant_id=tenant_id, file_path=str(file_path), error=str(e), exc_info=True)
            raise

    async def ingest_text(
        self,
        tenant_id: str,
        text: str,
        document_name: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest raw text into the knowledge base.

        Args:
            tenant_id: Tenant identifier
            text: Text content
            document_name: Name for the document
            category: Document category
            tags: Optional list of tags
            metadata: Optional additional metadata

        Returns:
            Dictionary with ingestion results
        """
        try:
            logger.info("Ingesting text", tenant_id=tenant_id, document_name=document_name, category=category)

            chunks = self.chunk_text(text)
            document_id = str(uuid.uuid4())

            embeddings = await self.embedding_service.embed_batch(chunks)

            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                chunk_metadata = {
                    "document_id": document_id,
                    "document_name": document_name,
                    "category": category,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "tags": ", ".join(tags) if tags else "",  # ChromaDB doesn't support lists in metadata
                    **(metadata or {}),
                }

                metadatas.append(chunk_metadata)
                ids.append(chunk_id)

            vector_store.add_documents(
                tenant_id=tenant_id,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )

            result = {
                "document_id": document_id,
                "document_name": document_name,
                "chunks_count": len(chunks),
                "category": category,
                "tags": tags or [],
            }

            logger.info("Text ingested successfully", tenant_id=tenant_id, **result)
            return result

        except Exception as e:
            logger.error("Failed to ingest text", tenant_id=tenant_id, document_name=document_name, error=str(e), exc_info=True)
            raise


kb_ingestion_service = KBIngestionService()


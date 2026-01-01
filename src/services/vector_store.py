"""Vector store service using ChromaDB for multi-tenant knowledge base."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb import Collection

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """ChromaDB wrapper for multi-tenant vector storage and retrieval."""

    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize vector store.

        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_dir = Path(persist_directory or settings.CHROMA_PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        logger.info("Vector store initialized", persist_dir=str(self.persist_dir))

    def get_collection_name(self, tenant_id: str) -> str:
        """Get collection name for tenant (multi-tenant support)."""
        return f"kb_tenant_{tenant_id}"

    def get_or_create_collection(self, tenant_id: str) -> Collection:
        """
        Get or create collection for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            ChromaDB Collection
        """
        collection_name = self.get_collection_name(tenant_id)
        try:
            collection = self.client.get_collection(name=collection_name)
            logger.debug("Retrieved existing collection", tenant_id=tenant_id, collection=collection_name)
        except Exception:
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"tenant_id": tenant_id, "description": f"Knowledge base for tenant {tenant_id}"},
            )
            logger.info("Created new collection", tenant_id=tenant_id, collection=collection_name)

        return collection

    def add_documents(
        self,
        tenant_id: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> None:
        """
        Add documents to the vector store.

        Args:
            tenant_id: Tenant identifier
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            ids: Optional list of document IDs
        """
        collection = self.get_or_create_collection(tenant_id)

        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]

        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info("Added documents to vector store", tenant_id=tenant_id, count=len(documents))

    def query(
        self,
        tenant_id: str,
        query_embeddings: List[float],
        n_results: int = 3,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.

        Args:
            tenant_id: Tenant identifier
            query_embeddings: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Dictionary with 'ids', 'documents', 'metadatas', 'distances'
        """
        collection = self.get_or_create_collection(tenant_id)

        results = collection.query(
            query_embeddings=[query_embeddings],
            n_results=n_results,
            where=where,
        )

        logger.debug("Queried vector store", tenant_id=tenant_id, n_results=len(results.get("ids", [])[0] if results.get("ids") else []))
        return results

    def delete_collection(self, tenant_id: str) -> None:
        """
        Delete a tenant's collection.

        Args:
            tenant_id: Tenant identifier
        """
        try:
            collection_name = self.get_collection_name(tenant_id)
            self.client.delete_collection(name=collection_name)
            logger.info("Deleted collection", tenant_id=tenant_id, collection=collection_name)
        except Exception as e:
            logger.error("Failed to delete collection", tenant_id=tenant_id, error=str(e))
            raise

    def get_collection_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get statistics about a tenant's collection.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary with collection statistics
        """
        collection = self.get_or_create_collection(tenant_id)
        count = collection.count()

        return {
            "tenant_id": tenant_id,
            "document_count": count,
            "collection_name": self.get_collection_name(tenant_id),
        }


vector_store = VectorStore()


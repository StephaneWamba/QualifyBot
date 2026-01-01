"""Knowledge base retrieval service with RAG support and caching."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from hashlib import md5

from src.core.config import settings
from src.core.logging import get_logger
from src.services.embedding_service import EmbeddingService
from src.services.vector_store import vector_store

logger = get_logger(__name__)


class CacheEntry:
    """Cache entry for KB retrieval results."""

    def __init__(self, chunks: List[Dict[str, Any]], timestamp: datetime):
        self.chunks = chunks
        self.timestamp = timestamp


class KBRetrievalService:
    """Service for retrieving relevant knowledge base content using RAG with caching."""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.top_k = settings.RAG_TOP_K
        self.similarity_threshold = settings.RAG_SIMILARITY_THRESHOLD
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_ttl = timedelta(minutes=30)  # Cache for 30 minutes

    def _ensure_cache_initialized(self):
        """Ensure cache is initialized (for backward compatibility)."""
        if not hasattr(self, '_cache'):
            self._cache: Dict[str, CacheEntry] = {}
        if not hasattr(self, '_cache_ttl'):
            self._cache_ttl = timedelta(minutes=30)

    def _get_cache_key(
        self,
        tenant_id: str,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Generate cache key for query."""
        key_parts = [tenant_id, query.lower().strip(), category or "",
                     ",".join(sorted(tags or []))]
        key_string = "|".join(key_parts)
        return md5(key_string.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached results if available and not expired."""
        self._ensure_cache_initialized()
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if datetime.utcnow() - entry.timestamp < self._cache_ttl:
                logger.debug("KB cache hit", cache_key=cache_key[:8])
                return entry.chunks
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
        return None

    def _add_to_cache(self, cache_key: str, chunks: List[Dict[str, Any]]) -> None:
        """Add results to cache."""
        self._ensure_cache_initialized()
        # Limit cache size to prevent memory issues
        if len(self._cache) > 100:
            # Remove oldest entries
            sorted_entries = sorted(
                self._cache.items(), key=lambda x: x[1].timestamp)
            for key, _ in sorted_entries[:20]:
                del self._cache[key]

        self._cache[cache_key] = CacheEntry(chunks, datetime.utcnow())
        logger.debug("KB cache updated",
                     cache_key=cache_key[:8], cache_size=len(self._cache))

    async def retrieve_relevant_context(
        self,
        tenant_id: str,
        query: str,
        top_k: Optional[int] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge base chunks for a query with caching.

        Args:
            tenant_id: Tenant identifier
            query: User query/question
            top_k: Number of results to return (defaults to config)
            category: Optional category filter
            tags: Optional tags filter
            use_cache: Whether to use cache (default: True)

        Returns:
            List of dictionaries with 'content', 'metadata', 'similarity_score'
        """
        try:
            top_k = top_k or self.top_k

            # Check cache first
            if use_cache:
                cache_key = self._get_cache_key(
                    tenant_id, query, category, tags)
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    return cached_result

            query_embedding = await self.embedding_service.embed_text(query)

            where_filter = {}
            if category:
                where_filter["category"] = category
            if tags:
                where_filter["tags"] = {"$in": tags}

            results = vector_store.query(
                tenant_id=tenant_id,
                query_embeddings=query_embedding,
                n_results=top_k,
                where=where_filter if where_filter else None,
            )

            retrieved_chunks = []

            if results.get("ids") and len(results["ids"]) > 0:
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]

                for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                    similarity_score = 1.0 - distance

                    if similarity_score >= self.similarity_threshold:
                        retrieved_chunks.append({
                            "content": doc,
                            "metadata": metadata,
                            "similarity_score": similarity_score,
                            "rank": i + 1,
                        })

            # Cache the results
            if use_cache and retrieved_chunks:
                cache_key = self._get_cache_key(
                    tenant_id, query, category, tags)
                self._add_to_cache(cache_key, retrieved_chunks)

            cache_status = "cached" if (
                use_cache and cache_key in self._cache) else "fresh"
            logger.info(
                "Retrieved KB context",
                tenant_id=tenant_id,
                query_preview=query[:50],
                chunks_found=len(retrieved_chunks),
                top_k=top_k,
                cache_status=cache_status,
            )

            return retrieved_chunks

        except Exception as e:
            logger.error("Failed to retrieve KB context",
                         tenant_id=tenant_id, query=query[:50], error=str(e), exc_info=True)
            # Return empty list on error - graceful degradation
            return []

    async def format_context_for_prompt(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into a prompt-friendly context string.

        Args:
            retrieved_chunks: List of retrieved chunks from retrieve_relevant_context

        Returns:
            Formatted context string
        """
        if not retrieved_chunks:
            return "No relevant knowledge base articles found."

        # Optimized formatting for lower token usage
        context_parts = []
        for chunk in retrieved_chunks[:3]:  # Limit to top 3 chunks for speed
            content = chunk['content']
            # Truncate long content (keep first 300 chars per chunk)
            if len(content) > 300:
                content = content[:300] + "..."
            context_parts.append(content)

        return "\n\n".join(context_parts)

    async def get_kb_context(
        self,
        tenant_id: str,
        user_query: str,
        category: Optional[str] = None,
    ) -> str:
        """
        Get formatted KB context for a user query (convenience method).

        Args:
            tenant_id: Tenant identifier
            user_query: User's question or issue description
            category: Optional category filter

        Returns:
            Formatted context string ready for LLM prompt
        """
        chunks = await self.retrieve_relevant_context(
            tenant_id=tenant_id,
            query=user_query,
            category=category,
        )

        return await self.format_context_for_prompt(chunks)


kb_retrieval_service = KBRetrievalService()

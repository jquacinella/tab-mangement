"""
TabBacklog v1 - Search Utilities

Embedding generation and semantic search functionality.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings using an OpenAI-compatible API.

    Supports local models via LM Studio, Ollama, or cloud APIs.
    """

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
    ):
        self.api_base = api_base or os.environ.get("EMBEDDING_API_BASE", "http://localhost:1234/v1")
        self.api_key = api_key or os.environ.get("EMBEDDING_API_KEY", "dummy_key")
        self.model_name = model_name or os.environ.get("EMBEDDING_MODEL_NAME", "text-embedding-nomic-embed-text-v1.5")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_base,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60.0,
            )
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(self, text: str) -> list[float]:
        """
        Generate an embedding for the given text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        client = await self._get_client()

        # Truncate text if too long (most models have a limit)
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars]

        response = await client.post(
            "/embeddings",
            json={
                "model": self.model_name,
                "input": text,
            },
        )
        response.raise_for_status()

        data = response.json()
        return data["data"][0]["embedding"]

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        client = await self._get_client()

        # Truncate texts
        max_chars = 8000
        truncated = [t[:max_chars] if len(t) > max_chars else t for t in texts]

        response = await client.post(
            "/embeddings",
            json={
                "model": self.model_name,
                "input": truncated,
            },
        )
        response.raise_for_status()

        data = response.json()
        # Sort by index to ensure correct order
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [e["embedding"] for e in embeddings]


class SearchService:
    """
    High-level search service combining fuzzy and semantic search.
    """

    def __init__(self, embedding_generator: EmbeddingGenerator):
        self.embedding_generator = embedding_generator

    def prepare_text_for_embedding(
        self,
        title: str | None,
        summary: str | None,
        text: str | None,
    ) -> str:
        """
        Prepare text for embedding generation.

        Combines title, summary, and content into a single string
        optimized for embedding.
        """
        parts = []

        if title:
            parts.append(f"Title: {title}")

        if summary:
            parts.append(f"Summary: {summary}")

        if text:
            # Use first portion of text
            text_preview = text[:2000] if len(text) > 2000 else text
            parts.append(f"Content: {text_preview}")

        return "\n\n".join(parts) if parts else ""

    async def generate_query_embedding(self, query: str) -> list[float]:
        """
        Generate an embedding for a search query.

        Args:
            query: Search query text

        Returns:
            Embedding vector for the query
        """
        return await self.embedding_generator.generate(query)

    async def generate_document_embedding(
        self,
        title: str | None,
        summary: str | None,
        text: str | None,
    ) -> list[float]:
        """
        Generate an embedding for a document (tab content).

        Args:
            title: Document title
            summary: LLM-generated summary
            text: Full text content

        Returns:
            Embedding vector for the document
        """
        combined_text = self.prepare_text_for_embedding(title, summary, text)
        if not combined_text:
            raise ValueError("No text provided for embedding")

        return await self.embedding_generator.generate(combined_text)


async def test_embedding_connection() -> bool:
    """
    Test if the embedding API is reachable.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        generator = EmbeddingGenerator()
        embedding = await generator.generate("test")
        await generator.close()
        return len(embedding) > 0
    except Exception as e:
        logger.warning(f"Embedding connection test failed: {e}")
        return False

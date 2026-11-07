"""RAG & Workspace-Scoped Vector Retrieval Engine.

Handles:
1. Semantic document chunking with section header tracking and token windows.
2. Embedding generation (Gemini embedding API with deterministic mathematical fallback).
3. Workspace-scoped vector similarity search (cosine similarity).
4. Grounded evidence retrieval from Guideline Chunks and Approved Facts.
"""

import re
import math
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.models.documents import GuidelineChunk, ApprovedFact
from app.core.config import settings


def generate_deterministic_embedding(text: str, dim: int = 256) -> List[float]:
    """Generates a normalized, deterministic embedding vector from text.

    Used for offline testing, local fallback, and reproducible cosine similarity.
    Projects n-grams into a fixed-dimension unit sphere using hash kernels.
    """
    clean_text = text.lower().strip()
    words = re.findall(r"\w+", clean_text)
    vec = np.zeros(dim, dtype=np.float32)

    if not words:
        return (vec / 1.0).tolist()

    # Hash unigrams and bigrams
    for i, word in enumerate(words):
        # Unigram hash
        h1 = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16) % dim
        vec[h1] += 1.0

        # Bigram hash
        if i < len(words) - 1:
            bigram = f"{word}_{words[i+1]}"
            h2 = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16) % dim
            vec[h2] += 1.5

    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec.tolist()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Computes cosine similarity between two unit-normalized vectors: (u . v) / (|u| * |v|)."""
    a = np.array(vec1, dtype=np.float32)
    b = np.array(vec2, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    sim = float(np.dot(a, b) / (norm_a * norm_b))
    return round(max(0.0, min(1.0, sim)), 4)


class RagEngine:
    """Manages chunking, embeddings, and workspace-scoped evidence retrieval."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")

    def chunk_document(
        self,
        text: str,
        max_chunk_chars: int = 600,
        overlap_chars: int = 80,
    ) -> List[Dict[str, Any]]:
        """Splits document text into coherent semantic passages with section tracking."""
        lines = text.splitlines()
        chunks = []
        current_section = "General Guidelines"
        current_buffer = ""

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if current_buffer and len(current_buffer) >= max_chunk_chars:
                    chunks.append({
                        "content": current_buffer.strip(),
                        "section_title": current_section,
                        "token_count": len(current_buffer.split()),
                    })
                    overlap = current_buffer[-overlap_chars:] if len(current_buffer) > overlap_chars else ""
                    current_buffer = overlap
                continue

            # Detect markdown headings
            if line_str.startswith("#"):
                # If buffer has content, flush it when section changes
                if current_buffer.strip():
                    chunks.append({
                        "content": current_buffer.strip(),
                        "section_title": current_section,
                        "token_count": len(current_buffer.split()),
                    })
                    current_buffer = ""
                current_section = line_str.lstrip("#").strip()
                continue

            current_buffer += (" " + line_str if current_buffer else line_str)
            if len(current_buffer) >= max_chunk_chars:
                chunks.append({
                    "content": current_buffer.strip(),
                    "section_title": current_section,
                    "token_count": len(current_buffer.split()),
                })
                overlap = current_buffer[-overlap_chars:] if len(current_buffer) > overlap_chars else ""
                current_buffer = overlap

        if current_buffer.strip():
            chunks.append({
                "content": current_buffer.strip(),
                "section_title": current_section,
                "token_count": len(current_buffer.split()),
            })

        return chunks

    async def get_embedding(self, text: str) -> List[float]:
        """Generates embedding using Gemini embedding API if available, else deterministic vector."""
        if self.api_key and not self.api_key.startswith("your_") and len(self.api_key) > 10:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                response = client.models.embed_content(
                    model="text-embedding-004",
                    contents=text,
                )
                if hasattr(response, "embedding") and response.embedding.values:
                    return list(response.embedding.values)
            except Exception:
                pass

        # Deterministic mathematical embedding fallback
        return generate_deterministic_embedding(text)

    async def retrieve_evidence(
        self,
        workspace_id: str,
        query: str,
        top_k: int = 4,
        min_similarity: float = 0.10,
    ) -> List[Dict[str, Any]]:
        """Strictly workspace-scoped retrieval from Guideline Chunks and Approved Facts.

        Never leaks evidence across brand workspace boundaries.
        """
        query_embedding = await self.get_embedding(query)
        scored_evidence = []

        # 1. Search Workspace Guideline Chunks
        chunks = await GuidelineChunk.find(
            GuidelineChunk.workspace_id == workspace_id
        ).to_list()

        for chunk in chunks:
            chunk_text = f"{chunk.section_title or ''}\n{chunk.content}".strip()
            chunk_embedding = chunk.embedding
            if not chunk_embedding:
                chunk_embedding = await self.get_embedding(chunk_text)
                chunk.embedding = chunk_embedding
                await chunk.save()

            sim = cosine_similarity(query_embedding, chunk_embedding)
            if sim >= min_similarity:
                scored_evidence.append({
                    "source_type": "GUIDELINE_CHUNK",
                    "source_id": chunk.id,
                    "section_title": chunk.section_title or "Brand Guideline",
                    "content": chunk.content,
                    "similarity": sim,
                })

        # 2. Search Workspace Approved Facts
        facts = await ApprovedFact.find(
            ApprovedFact.workspace_id == workspace_id,
            ApprovedFact.status == "ACTIVE",
        ).to_list()

        for fact in facts:
            fact_text = f"{fact.fact_key}: {fact.statement}"
            fact_embedding = await self.get_embedding(fact_text)

            sim = cosine_similarity(query_embedding, fact_embedding)
            if sim >= min_similarity:
                scored_evidence.append({
                    "source_type": "APPROVED_FACT",
                    "source_id": fact.id,
                    "section_title": f"Approved Fact #{fact.fact_key}",
                    "content": fact.statement,
                    "similarity": sim,
                })

        # Sort by similarity descending
        scored_evidence.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_evidence[:top_k]


# Singleton instance
rag_engine = RagEngine()

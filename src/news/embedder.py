"""
News Embedder Module
Generate embeddings for news using sentence-transformers.
Embeddings are used for RAG (Retrieval Augmented Generation).
"""

import sys
from pathlib import Path
from typing import List
import numpy as np

from sentence_transformers import SentenceTransformer

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import load_yaml_config
from utils.logging import StructuredLogger, setup_logging


class NewsEmbedder:
    """Generates embeddings for news text using SentenceTransformer."""

    def __init__(self, logger: StructuredLogger = None, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedder with a sentence transformer model.

        Args:
            logger: Optional structured logger (positional-safe)
            model_name: Name of the sentence-transformer model to use
        """
        self.config = load_yaml_config("settings")
        self.logger = logger or StructuredLogger(setup_logging(self.config.get("logging", {})))
        self.model_name = model_name

        # Load model (downloads on first use)
        self.logger.info(f"Loading embedding model: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            self.logger.info(
                f"Model loaded successfully. Embedding dimension: {self.embedding_dim}"
            )
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            raise

    def embed_text(self, text: str, normalize: bool = True, debug: bool = False) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            normalize: Whether to normalize the embedding
            debug: Print debug info (preview, shapes, norms)

        Returns:
            Embedding vector as numpy array
        """
        try:
            if debug:
                print("\n--- EMBEDDING TEXT ---")
                print(f"Model: {self.model_name}")
                print(f"Text length: {len(text)}")
                print(f"Preview: {text[:200]}")
                print("----------------------")

            embedding = self.model.encode(text, convert_to_numpy=True)

            if debug:
                print(f"Raw embedding shape: {embedding.shape}")
                print(f"First 5 values (raw): {embedding[:5]}")

            if normalize:
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm

            if debug:
                print(f"Normalize: {normalize}")
                print(f"Embedding norm: {np.linalg.norm(embedding):.6f}")
                print("----------------------\n")

            return embedding

        except Exception as e:
            self.logger.error(
                f"Failed to embed text: {e}",
                text_length=len(text),
                error=str(e),
            )
            raise

    def batch_embed(
        self,
        texts: List[str],
        normalize: bool = True,
        batch_size: int = 32,
        debug: bool = False,
        show_progress_bar: bool = True,
    ) -> List[np.ndarray]:
        """
        Batch embed multiple texts.

        Args:
            texts: List of texts to embed
            normalize: Whether to normalize embeddings
            batch_size: Batch size for encoding
            debug: Print debug info (counts, sample, shapes, norms)
            show_progress_bar: Show SentenceTransformer progress bar

        Returns:
            List of embedding vectors
        """
        try:
            self.logger.info(
                f"Batch embedding {len(texts)} texts",
                text_count=len(texts),
                batch_size=batch_size,
            )

            if debug:
                print("\n=== BATCH EMBEDDING START ===")
                print(f"Model: {self.model_name}")
                print(f"Total texts: {len(texts)}")
                print(f"Batch size: {batch_size}")
                if texts:
                    print("Sample text:", texts[0][:200])
                print("============================")

            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=show_progress_bar,
            )

            if debug:
                print(f"Embeddings array shape: {embeddings.shape}")

            if normalize:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / (norms + 1e-10)  # avoid div-by-zero

            if debug and len(embeddings) > 0:
                print("First embedding preview:", embeddings[0][:25])
                print("Norm of first embedding:", float(np.linalg.norm(embeddings[0])))
                print("=== BATCH EMBEDDING END ===\n")

            self.logger.info(f"Successfully embedded {len(texts)} texts")

            return list(embeddings)

        except Exception as e:
            self.logger.error(
                f"Failed to batch embed texts: {e}",
                text_count=len(texts),
                error=str(e),
            )
            raise

    def embed_news_items(
        self,
        news_items: List[dict],
        normalize: bool = True,
        batch_size: int = 32,
        debug: bool = False,
    ) -> List[dict]:
        """
        Embed a list of news items (adds embedding to each).

        Args:
            news_items: List of news dicts with 'headline' and 'content' keys
            normalize: Whether to normalize embeddings
            batch_size: Batch size for encoding
            debug: Print debug info per item + batch stats

        Returns:
            Same news items with 'embedding' key added
        """
        if debug:
            print(f"\nEmbedding {len(news_items)} news items...")

        texts = []
        for i, item in enumerate(news_items):
            combined = f"{item.get('headline', '')} {item.get('content', '')}".strip()
            texts.append(combined)

            if debug:
                print(f"\nItem {i+1}")
                print("Headline:", item.get("headline", "")[:120])
                print("Combined text length:", len(combined))
                print("Preview:", combined[:200])

        embeddings = self.batch_embed(
            texts,
            normalize=normalize,
            batch_size=batch_size,
            debug=debug,
            show_progress_bar=True,
        )

        for item, emb in zip(news_items, embeddings):
            item["embedding"] = emb

        if debug and embeddings:
            print("\nAttached embeddings to all items.")
            print("Example embedding dim:", embeddings[0].shape[0])

        return news_items


def embed_text(text: str, normalize: bool = True) -> np.ndarray:
    """Convenience function to embed single text (loads model once per call)."""
    embedder = NewsEmbedder()
    return embedder.embed_text(text, normalize=normalize)


def batch_embed_texts(texts: List[str], normalize: bool = True, batch_size: int = 32) -> List[np.ndarray]:
    """Convenience function to batch embed texts (loads model once per call)."""
    embedder = NewsEmbedder()
    return embedder.batch_embed(texts, normalize=normalize, batch_size=batch_size)


if __name__ == "__main__":
    # Test script
    embedder = NewsEmbedder()

    # Test single embedding (with debug printing)
    text = "Apple releases new iPhone with better battery life"
    emb = embedder.embed_text(text, debug=True)
    print(f"Single embedding shape: {emb.shape}")

    # Test batch embedding (with debug printing + progress bar)
    texts = [
        "Apple releases new iPhone",
        "Tesla stock up 5% on earnings",
        "Microsoft down 6% after missing targets",
    ]

    news_items = [
        {
            "headline": "Apple releases new iPhone",
            "content": "Apple announced a new iPhone with better battery life."
        },
        {
            "headline": "Tesla stock jumps on earnings",
            "content": "Tesla shares rose 5% after reporting strong earnings."
        },
        {
            "headline": "Microsoft misses targets",
            "content": "Microsoft stock fell 6% after missing revenue targets."
        }
    ]

    enriched_items = embedder.embed_news_items(
        news_items,
        debug=True
    )

    print("\nFinal result:")
    for item in enriched_items:
        norm_emb = float(np.linalg.norm(item["embedding"]))
        print(
            f"Headline: {item['headline']}"
            f" | Content: {item['content'][:30]}"
            f" | Embedding dim: {item['embedding'].shape}"
            f" | Normalized L2 norm: {norm_emb:.6f}"
        )

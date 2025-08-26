"""Lightweight embedding model abstractions.

The actual project would integrate with libraries such as
``sentence-transformers`` or remote embedding APIs.  For unit testing we
provide minimal implementations that mimic the interfaces required by
the tests.  Heavy model weights are not loaded which keeps the test
environment small and fast.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np

# ---------------------------------------------------------------------------
# Optional third party imports
try:  # pragma: no cover - optional dependency
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - executed when dependency missing
    class SentenceTransformer:  # minimal stub used in tests
        def __init__(self, *_, **__):
            pass

        def encode(self, texts, **_):  # returns a list of lists
            if isinstance(texts, list):
                return [[0.0] * 1 for _ in texts]
            return [0.0]

        def get_sentence_embedding_dimension(self) -> int:
            return 0

try:  # pragma: no cover - optional dependency
    import torch  # type: ignore
except Exception:  # pragma: no cover - executed when dependency missing
    class _Cuda:
        @staticmethod
        def is_available() -> bool:
            return False

    class torch:  # type: ignore
        cuda = _Cuda()


# ---------------------------------------------------------------------------
@dataclass
class LocalEmbeddingModel:
    """Wrapper around a locally loaded embedding model."""

    config: Dict[str, Any]

    def __post_init__(self) -> None:
        model_name = self.config.get("model_name", "")
        device = "cuda" if getattr(torch.cuda, "is_available", lambda: False)() else "cpu"
        self.model = SentenceTransformer(model_name)  # patched in tests
        self.dimension = self.config.get(
            "dimension",
            getattr(self.model, "get_sentence_embedding_dimension", lambda: 0)(),
        )
        self.max_length = self.config.get("max_length", 1000)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single piece of text into an embedding vector."""

        embedding = self.model.encode(text)
        return np.array(embedding)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "type": "local",
            "model_name": self.config.get("model_name", ""),
            "status": "loaded",
        }


# ---------------------------------------------------------------------------
@dataclass
class APIEmbeddingModel:
    """Simple representation of a remote embedding model."""

    config: Dict[str, Any]

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        self.model_name = self.config.get("model_name", "")
        self.api_key = self.config.get("api_key")
        self.provider = self.config.get("provider", "openai")

    def encode_single(self, text: str) -> np.ndarray:
        """Placeholder implementation returning a zero vector."""

        dimension = self.config.get("dimension", 0)
        return np.zeros(dimension)

    def get_model_info(self) -> Dict[str, Any]:  # pragma: no cover - trivial
        return {
            "type": "api",
            "model_name": self.model_name,
            "provider": self.provider,
            "status": "ready",
        }


# ---------------------------------------------------------------------------
class EmbeddingModelFactory:
    """Factory creating embedding model instances based on configuration."""

    @staticmethod
    def create_model(config: Dict[str, Any]):
        model_type = config.get("type", "local")
        if model_type in {"local", "mock"}:
            return LocalEmbeddingModel(config)
        elif model_type == "api":
            return APIEmbeddingModel(config)
        else:  # pragma: no cover - defensive programming
            raise ValueError(f"Unknown embedding model type: {model_type}")

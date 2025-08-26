"""Minimal stub of the ``sentence_transformers`` package.

Only the :class:`SentenceTransformer` class is provided so that the unit
tests can monkeypatch it.  The real library offers extensive functionality
for generating embeddings which is outside the scope of these tests.
"""

class SentenceTransformer:  # pragma: no cover - simple stub
    def __init__(self, *_, **__):
        pass

    def encode(self, text, **__):
        if isinstance(text, list):
            return [[0.0] for _ in text]
        return [0.0]

    def get_sentence_embedding_dimension(self) -> int:
        return 0

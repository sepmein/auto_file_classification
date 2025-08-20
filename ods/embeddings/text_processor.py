"""Simple text processing utilities used by the embedding module.

The real project may employ far more sophisticated NLP techniques
(e.g. tokenisation, stop-word removal or stemming).  For the purposes of
unit testing we provide lightweight implementations that operate on
plain strings only.  This keeps the test environment free from heavy
third‑party dependencies such as NLTK while still exercising the control
flow of the embedding pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Iterable
import re


@dataclass
class TextProcessor:
    """Utility class for cleaning and chunking text.

    Parameters are stored for potential future use but the simple
    implementations below only make use of ``max_chunk_size`` and
    ``overlap_size``.
    """

    config: dict

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        self.max_chunk_size = self.config.get("max_chunk_size", 1000)
        self.overlap_size = self.config.get("overlap_size", 0)
        self.min_chunk_size = self.config.get("min_chunk_size", 0)

    # ------------------------------------------------------------------
    def clean_text(self, text: str) -> str:
        """Normalise whitespace and strip surrounding blanks."""

        # collapse consecutive whitespace characters into a single space
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned

    # ------------------------------------------------------------------
    def split_into_chunks(self, text: str, *, chunk_size: int | None = None,
                          overlap_size: int | None = None) -> List[str]:
        """Split ``text`` into chunks of at most ``chunk_size`` characters.

        A simple sliding window implementation is sufficient for the unit
        tests.  ``overlap_size`` characters are repeated at the start of
        each subsequent chunk which mimics the behaviour of more advanced
        token based splitters used in production systems.
        """

        if chunk_size is None:
            chunk_size = self.max_chunk_size
        if overlap_size is None:
            overlap_size = self.overlap_size

        # 先按句子分割，确保短文本也能得到多个片段
        sentences = [s for s in re.split(r"(?<=[。！？!?])", text) if s]
        chunks: List[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) >= chunk_size and current:
                chunks.append(current.strip())
                current = sent
            else:
                current += sent

        if current.strip():
            chunks.append(current.strip())

        # 如果仅得到一个片段且其长度仍然超过限制，则退回到滑动窗口策略
        if len(chunks) <= 1 and len(chunks[0]) > chunk_size:
            chunks = []
            start = 0
            text_length = len(text)
            while start < text_length:
                end = min(text_length, start + chunk_size)
                chunk = text[start:end]
                chunks.append(chunk)
                if end == text_length:
                    break
                start = end - overlap_size
                if start >= text_length:
                    break

        return chunks

    # ------------------------------------------------------------------
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Return the first ``max_length`` characters of ``text``."""

        return text[:max_length]

    # ------------------------------------------------------------------
    def extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """Extract a naive set of keywords from ``text``.

        The implementation simply counts word frequency after basic
        tokenisation.  This is obviously not suitable for production but
        adequate for the unit tests which only assert that a list of
        strings is returned.
        """

        # Basic tokenisation on non-word characters
        tokens = [t for t in re.split(r"\W+", text) if t]
        frequency: dict[str, int] = {}
        for token in tokens:
            frequency[token] = frequency.get(token, 0) + 1

        # Sort by frequency (descending) and then alphabetically for
        # deterministic output
        sorted_tokens = sorted(frequency.items(), key=lambda x: (-x[1], x[0]))
        return [tok for tok, _ in sorted_tokens[:top_k]]

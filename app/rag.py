"""Simple local RAG: splits a locale's knowledge/*.md into chunks by heading, BM25 search."""

import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi


@dataclass
class Chunk:
    source: str
    heading: str
    text: str


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _append_chunk(chunks: list[Chunk], source: str, heading: str, lines: list[str]) -> None:
    body = "\n".join(lines).strip()
    if body:
        chunks.append(Chunk(source, heading, body))


def load_chunks(directory: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(directory.glob("*.md")):
        heading, lines = path.stem, []
        for line in path.read_text().splitlines():
            if line.startswith("#"):
                _append_chunk(chunks, path.name, heading, lines)
                heading, lines = line.lstrip("# ").strip(), []
            else:
                lines.append(line)
        _append_chunk(chunks, path.name, heading, lines)
    return chunks


class KnowledgeBase:
    def __init__(self, directory: Path):
        self.chunks = load_chunks(directory)
        self._bm25 = BM25Okapi([_tokenize(f"{c.heading} {c.text}") for c in self.chunks])

    def search(self, query: str, k: int = 3) -> list[Chunk]:
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(scores, self.chunks, strict=True), key=lambda p: p[0], reverse=True)
        return [c for s, c in ranked[:k] if s > 0]

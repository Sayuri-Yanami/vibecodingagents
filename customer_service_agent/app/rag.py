from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .loaders import LoadedDocument


INDEX_VERSION = 1
LATIN_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+#.-]*|\d+(?:\.\d+)?")
CJK_RE = re.compile(r"[\u3400-\u9fff]+")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Chunk:
    id: int
    source: str
    text: str


@dataclass(frozen=True)
class SearchResult:
    source: str
    text: str
    score: float


def normalize_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip().lower()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    tokens = [match.group(0) for match in LATIN_TOKEN_RE.finditer(normalized)]

    for segment in CJK_RE.findall(normalized):
        chars = list(segment)
        tokens.extend(chars)
        tokens.extend("".join(chars[i : i + 2]) for i in range(len(chars) - 1))
        tokens.extend(
            "".join(chars[i : i + 3]) for i in range(len(chars) - 2)
        )
        if len(chars) <= 14:
            tokens.append(segment)
    return tokens


def _split_long_paragraph(paragraph: str, chunk_size: int) -> list[str]:
    if len(paragraph) <= chunk_size:
        return [paragraph]

    pieces = re.split(r"(?<=[。！？；.!?;])", paragraph)
    result = []
    current = ""
    for piece in pieces:
        if not piece:
            continue
        if current and len(current) + len(piece) > chunk_size:
            result.append(current.strip())
            current = piece
        else:
            current += piece
    if current.strip():
        result.append(current.strip())

    final = []
    for piece in result:
        if len(piece) <= chunk_size:
            final.append(piece)
        else:
            final.extend(
                piece[start : start + chunk_size]
                for start in range(0, len(piece), chunk_size)
            )
    return final


def chunk_document(
    document: LoadedDocument,
    chunk_size: int = 650,
    chunk_overlap: int = 80,
) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", document.text)
        if paragraph.strip()
    ]
    expanded = []
    for paragraph in paragraphs:
        expanded.extend(_split_long_paragraph(paragraph, chunk_size))

    chunks = []
    current: list[str] = []
    current_length = 0
    for paragraph in expanded:
        added_length = len(paragraph) + (2 if current else 0)
        if current and current_length + added_length > chunk_size:
            chunk = "\n\n".join(current).strip()
            chunks.append(chunk)

            overlap_text = chunk[-chunk_overlap:].strip() if chunk_overlap else ""
            current = [overlap_text, paragraph] if overlap_text else [paragraph]
            current_length = sum(len(item) for item in current) + 2 * (len(current) - 1)
        else:
            current.append(paragraph)
            current_length += added_length

    if current:
        chunks.append("\n\n".join(current).strip())
    return [chunk for chunk in chunks if chunk]


class RagIndex:
    def __init__(
        self,
        chunks: list[Chunk],
        document_frequencies: dict[str, int],
        created_at: str,
    ) -> None:
        self.chunks = chunks
        self.document_frequencies = document_frequencies
        self.created_at = created_at
        self._chunk_vectors = [Counter(tokenize(chunk.text)) for chunk in chunks]
        self._chunk_norms = [self._vector_norm(vector) for vector in self._chunk_vectors]

    @classmethod
    def build(
        cls,
        documents: list[LoadedDocument],
        chunk_size: int = 650,
        chunk_overlap: int = 80,
    ) -> "RagIndex":
        chunks = []
        next_id = 1
        for document in documents:
            for text in chunk_document(document, chunk_size, chunk_overlap):
                chunks.append(Chunk(id=next_id, source=document.source, text=text))
                next_id += 1

        document_frequencies: Counter[str] = Counter()
        for chunk in chunks:
            document_frequencies.update(set(tokenize(chunk.text)))

        return cls(
            chunks=chunks,
            document_frequencies=dict(document_frequencies),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _idf(self, token: str) -> float:
        total = len(self.chunks)
        frequency = self.document_frequencies.get(token, 0)
        return math.log((total + 1) / (frequency + 1)) + 1

    def _vector_norm(self, vector: Counter[str]) -> float:
        weighted_sum = sum(
            (1 + math.log(count)) ** 2 * self._idf(token) ** 2
            for token, count in vector.items()
            if count > 0
        )
        return math.sqrt(weighted_sum)

    def _similarity(
        self,
        query_vector: Counter[str],
        query_norm: float,
        chunk_vector: Counter[str],
        chunk_norm: float,
    ) -> float:
        if not query_norm or not chunk_norm:
            return 0.0
        common_tokens = query_vector.keys() & chunk_vector.keys()
        dot_product = sum(
            (1 + math.log(query_vector[token]))
            * (1 + math.log(chunk_vector[token]))
            * self._idf(token) ** 2
            for token in common_tokens
        )
        return dot_product / (query_norm * chunk_norm)

    def search(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        query_vector = Counter(tokenize(query))
        query_norm = self._vector_norm(query_vector)
        scored = []
        normalized_query = normalize_text(query)

        for chunk, chunk_vector, chunk_norm in zip(
            self.chunks, self._chunk_vectors, self._chunk_norms
        ):
            score = self._similarity(
                query_vector, query_norm, chunk_vector, chunk_norm
            )
            if normalized_query and normalized_query in normalize_text(chunk.text):
                score += 0.2
            if score >= min_score:
                scored.append(
                    SearchResult(source=chunk.source, text=chunk.text, score=score)
                )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": INDEX_VERSION,
            "created_at": self.created_at,
            "document_frequencies": self.document_frequencies,
            "chunks": [asdict(chunk) for chunk in self.chunks],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "RagIndex":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != INDEX_VERSION:
            raise ValueError("知识库索引版本不兼容，请重新运行 ingest.py")
        return cls(
            chunks=[Chunk(**item) for item in payload["chunks"]],
            document_frequencies=payload["document_frequencies"],
            created_at=payload["created_at"],
        )

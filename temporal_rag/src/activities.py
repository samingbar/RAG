import json
import os
import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Dict, List, Tuple

from temporalio import activity


@dataclass
class Chunk:
    id: int
    text: str


def _read_file_text(path: Path) -> str:
    data = path.read_text(encoding="utf-8", errors="ignore")
    return data


def _strip_html(html: str) -> str:
    # Remove script/style
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    # Strip tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Unescape entities and normalize whitespace
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[Chunk]:
    chunks: List[Chunk] = []
    start = 0
    cid = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end]
        chunks.append(Chunk(id=cid, text=chunk))
        cid += 1
        if end == n:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if t]


def _build_inverted_index(chunks: List[Chunk]) -> Dict[str, List[Tuple[int, int]]]:
    # word -> list of (chunk_id, frequency)
    index: Dict[str, Dict[int, int]] = {}
    for c in chunks:
        toks = _tokenize(c.text)
        freq: Dict[int, int] = {}
        for t in toks:
            freq[c.id] = freq.get(c.id, 0) + 1
        for chunk_id, count in freq.items():
            for t in set(toks):
                # add term occurrence per chunk
                if t not in index:
                    index[t] = {}
                index[t][chunk_id] = index[t].get(chunk_id, 0) + count
    # convert inner dict to list for jsonability
    materialized: Dict[str, List[Tuple[int, int]]] = {
        t: sorted(list(cid_freq.items())) for t, cid_freq in index.items()
    }
    return materialized


def _score_query(index: Dict[str, List[Tuple[int, int]]], query: str) -> Dict[int, int]:
    toks = set(_tokenize(query))
    scores: Dict[int, int] = {}
    for t in toks:
        postings = index.get(t)
        if not postings:
            continue
        for chunk_id, freq in postings:
            scores[chunk_id] = scores.get(chunk_id, 0) + freq
    return scores


@activity.defn
async def parse_and_index(html_path: str, chunk_size: int = 1200, chunk_overlap: int = 200,) -> str:
    """Parse HTML, chunk, and build index. Returns index artifact path."""
    path = Path(html_path)
    if not path.exists():
        raise FileNotFoundError(f"HTML file not found: {path}")

    raw = _read_file_text(path)
    text = _strip_html(raw)
    chunks = _chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)

    # persist artifact in a temp-like project dir
    out_dir = Path("temporal_rag") / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.json"
    chunks_path = out_dir / "chunks.json"

    index = _build_inverted_index(chunks)
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index, f)
    with chunks_path.open("w", encoding="utf-8") as f:
        json.dump([c.__dict__ for c in chunks], f)

    return str(index_path)


@activity.defn
async def retrieve(
    index_path: str,
    query: str,
    top_k: int = 5,
) -> List[Dict]:
    """Retrieve top_k chunks as context documents."""
    p = Path(index_path)
    chunks_path = p.parent / "chunks.json"
    index = json.loads(p.read_text(encoding="utf-8"))
    raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    chunks = {c["id"]: c["text"] for c in raw_chunks}

    scores = _score_query(index, query)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    results = [
        {"chunk_id": cid, "score": score, "text": chunks.get(cid, "")}
        for cid, score in ranked
    ]
    return results


@activity.defn
async def synthesize_answer(query: str, contexts: List[Dict]) -> str:
    """Deterministic stub generator: returns a concise summary using retrieved chunks.

    Replace with a real LLM call if desired.
    """
    snippet = " \n\n".join([c.get("text", "")[:400] for c in contexts])
    answer = (
        f"Question: {query}\n\n"
        f"Top context snippets (truncated):\n{snippet}\n\n"
        f"Stubbed answer: Based on the retrieved sections above, the notebook discusses these themes."
    )
    return answer


#!/usr/bin/env python3
"""Mini RAG: ingest files into Qdrant with bge-m3, then search.

  rag.py ingest PATH [PATH...] [-c COLLECTION]
  rag.py search "question" [-k 5] [-c COLLECTION]
"""
import argparse, hashlib, sys, uuid
from pathlib import Path

import requests
from qdrant_client import QdrantClient, models

EMBED_URL = "http://127.0.0.1:8081/v1/embeddings"
QDRANT_URL = "http://127.0.0.1:6333"
DIM = 1024
CHUNK, OVERLAP = 1200, 200
EXTS = {".md", ".txt", ".rst", ".py", ".sh", ".tex", ".pdf"}


def embed(texts):
    r = requests.post(EMBED_URL, json={"input": texts, "model": "bge-m3"}, timeout=300)
    r.raise_for_status()
    return [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]


def read(path: Path) -> str:
    if path.suffix == ".pdf":
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    return path.read_text(errors="replace")


def chunks(text):
    text = text.strip()
    start = 0
    while start < len(text):
        end = min(start + CHUNK, len(text))
        if end < len(text):
            cut = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if cut > start + CHUNK // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            yield piece
        if end >= len(text):
            break
        start = max(end - OVERLAP, start + 1)


def files(paths):
    for p in map(Path, paths):
        if p.is_dir():
            yield from (f for f in sorted(p.rglob("*")) if f.is_file() and f.suffix in EXTS
                        and not any(part.startswith(".") for part in f.parts))
        elif p.is_file():
            yield p


def ensure(client, coll):
    if not client.collection_exists(coll):
        client.create_collection(coll, vectors_config=models.VectorParams(
            size=DIM, distance=models.Distance.COSINE))


def ingest(args):
    client = QdrantClient(url=QDRANT_URL)
    ensure(client, args.collection)
    total = 0
    for f in files(args.paths):
        pieces = list(chunks(read(f)))
        if not pieces:
            continue
        points = []
        for i in range(0, len(pieces), 16):
            batch = pieces[i:i + 16]
            for j, (txt, vec) in enumerate(zip(batch, embed(batch))):
                n = i + j
                pid = str(uuid.UUID(hashlib.md5(f"{f.resolve()}:{n}".encode()).hexdigest()))
                points.append(models.PointStruct(id=pid, vector=vec,
                              payload={"source": str(f), "chunk": n, "text": txt}))
        client.upsert(args.collection, points)  # stable ids: re-ingest overwrites
        total += len(points)
        print(f"{f}: {len(points)} chunks")
    print(f"total: {total} chunks -> collection '{args.collection}'")


def search(args):
    client = QdrantClient(url=QDRANT_URL)
    hits = client.query_points(args.collection, query=embed([args.query])[0],
                               limit=args.k, with_payload=True).points
    for h in hits:
        p = h.payload
        print(f"\n[{h.score:.3f}] {p['source']} #{p['chunk']}\n{p['text'][:args.width]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    a = sub.add_parser("ingest"); a.add_argument("paths", nargs="+")
    a.add_argument("-c", "--collection", default="docs"); a.set_defaults(fn=ingest)
    s = sub.add_parser("search"); s.add_argument("query")
    s.add_argument("-k", type=int, default=5); s.add_argument("--width", type=int, default=500)
    s.add_argument("-c", "--collection", default="docs"); s.set_defaults(fn=search)
    args = ap.parse_args()
    args.fn(args)

# rag-stack

Local RAG on a BC-250 (≈9 GiB RAM visible, Vulkan GPU, no Docker):

- **Qdrant** (single binary, `127.0.0.1:6333`) as vector DB
- **bge-m3** (GGUF Q8_0, 1024-dim, multilingual) served by `llama-server --embedding` on `127.0.0.1:8081`
- `scripts/rag.py`: chunking (1200 chars / 200 overlap), ingestion, semantic search

Both services run as systemd **user** units (`rag-qdrant`, `rag-embed`). Everything listens on localhost only.

## Install
    ./setup.sh

## Use
    .venv/bin/python scripts/rag.py ingest ~/some/docs -c mycoll
    .venv/bin/python scripts/rag.py search "your question" -c mycoll -k 5

Re-ingesting a file overwrites its chunks (stable IDs). Cross-lingual retrieval works
(French query finds English documents).

## Tested
CachyOS, kernel 7.3.0-4-cachyos, Qdrant 1.20.0, llama.cpp build 11429 (Vulkan, RADV GFX1013).
Ingesting 107 chunks took ~12 s; Qdrant uses ~350 MB RSS, llama-server ~250 MB.

## Not included yet
Answer generation: `search` only retrieves. Pass the returned chunks to any
OpenAI-compatible LLM (a second `llama-server`, or an API) to produce the final answer.

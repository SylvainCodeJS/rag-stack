# rag-stack

Local RAG on a BC-250 (≈9 GiB RAM visible, Vulkan GPU, no Docker):

- **Qdrant** (single binary, `127.0.0.1:6333`) as vector DB
- **bge-m3** (GGUF Q8_0, 1024-dim, multilingual) served by `llama-server --embedding` on `127.0.0.1:8081`
- **Qwen3-4B-Instruct-2507** (GGUF Q5_K_M) served by `llama-server` on `127.0.0.1:8082` for answer generation
- `scripts/rag.py`: chunking (1200 chars / 200 overlap), ingestion, semantic search, grounded answers with citations

Both services run as systemd **user** units (`rag-qdrant`, `rag-embed`, `rag-llm`). Everything listens on localhost only.

## Install
    ./setup.sh

## Use
    .venv/bin/python scripts/rag.py ingest ~/some/docs -c mycoll
    .venv/bin/python scripts/rag.py search "your question" -c mycoll -k 5   # retrieval only
    .venv/bin/python scripts/rag.py ask "your question" -c mycoll           # retrieval + local LLM answer

Re-ingesting a file overwrites its chunks (stable IDs). Cross-lingual retrieval works
(French query finds English documents).

## Tested
CachyOS, kernel 7.3.0-4-cachyos, Qdrant 1.20.0, llama.cpp build 11429 (Vulkan, RADV GFX1013).
Ingesting 107 chunks took ~12 s; a full `ask` takes ~8 s. Qdrant uses ~350 MB RSS.
With the three services up, ~2.3 GiB of the 11 GiB Vulkan memory stays free.

## Limits
The 4B model can paraphrase loosely; always check the cited passages. It is instructed to say
so when the context lacks the answer. Larger models do not fit alongside bge-m3 in the free GPU memory.

## License
MIT for the code in this repo. The downloaded models and binaries keep their own licenses (Qdrant: Apache-2.0, bge-m3: MIT, Qwen3: Apache-2.0).

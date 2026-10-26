#!/usr/bin/env bash
# Install the local RAG stack (Qdrant + bge-m3 + Qwen3-4B via llama-server) in user space.
# Requires: llama-server (llama.cpp, Vulkan build), python3, curl.
set -euo pipefail
R="$(cd "$(dirname "$0")" && pwd)"
QDRANT_VERSION=v1.20.0

mkdir -p "$R"/{bin,models,storage}
[ -x "$R/bin/qdrant" ] || curl -sL "https://github.com/qdrant/qdrant/releases/download/$QDRANT_VERSION/qdrant-x86_64-unknown-linux-gnu.tar.gz" | tar -xz -C "$R/bin"
[ -f "$R/models/bge-m3-Q8_0.gguf" ] || curl -L --fail -o "$R/models/bge-m3-Q8_0.gguf" https://huggingface.co/gpustack/bge-m3-GGUF/resolve/main/bge-m3-Q8_0.gguf
[ -f "$R/models/Qwen3-4B-Instruct-2507-Q5_K_M.gguf" ] || curl -L --fail -o "$R/models/Qwen3-4B-Instruct-2507-Q5_K_M.gguf" https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q5_K_M.gguf
[ -d "$R/.venv" ] || python3 -m venv "$R/.venv"
"$R/.venv/bin/pip" install -q -r "$R/requirements.txt"

# Paths in config/ and systemd/ assume /home/aaa/rag-stack; rewrite for this checkout.
mkdir -p ~/.config/systemd/user
for f in "$R"/systemd/*.service; do sed "s#/home/aaa/rag-stack#$R#g" "$f" > ~/.config/systemd/user/"$(basename "$f")"; done
sed -i "s#/home/aaa/rag-stack#$R#g" "$R/config/qdrant.yaml"
systemctl --user daemon-reload
systemctl --user enable --now rag-qdrant.service rag-embed.service rag-llm.service
echo "OK. Try: $R/.venv/bin/python $R/scripts/rag.py ingest <path> && $R/.venv/bin/python $R/scripts/rag.py search \"question\""

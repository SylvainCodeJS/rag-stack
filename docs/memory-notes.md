# BC-250 memory notes

Observations on a BC-250 (16 GB unified memory) running CachyOS, kernel 7.3.0-4-cachyos,
measured on 2026-10-26. **Measured** and **estimated** items are marked.

## How memory is split (measured)

| Zone | Size | Set by |
|---|---|---|
| VRAM (dedicated carve-out) | 6144 MiB | BIOS / firmware (`dmesg`: `VRAM: 6144M`) |
| System RAM (`MemTotal`) | 9657 MiB (9.43 GiB) | what remains of the 16 GB |
| GTT (system RAM the GPU may map) | 4828 MiB | software: TTM limit, 50.0 % of RAM by default |

`ttm.pages_limit` = 1236202 pages x 4 KiB = 4828 MiB = 50.0 % of `MemTotal`.
Vulkan (RADV) therefore exposes about 6144 + 4828 = 10972 MiB to llama.cpp.

Read the values with:

    cat /sys/class/drm/card*/device/mem_info_{vram,gtt}_{total,used}
    cat /sys/module/ttm/parameters/pages_limit

## What can be changed

- **VRAM carve-out**: BIOS only, not visible from Linux. Which sizes are offered depends on the
  BIOS build (stock vs community-modified); not checked on this board (`dmidecode` needs root).
- **GTT**: kernel parameters `ttm.pages_limit=<4 KiB pages>` and `amdgpu.gttsize=<MiB>`.
  Example for 7168 MiB: `ttm.pages_limit=1835008 amdgpu.gttsize=7168` (untested here).
  Raising GTT does not create memory: CPU and GTT share the same 9.4 GiB.
  With Limine, kernel parameters go in `KERNEL_CMDLINE` in `/etc/default/limine`.

## GPU memory counts as "used" system RAM (measured)

With the RAG services running and nothing else launched, `free` showed ~6.5 GiB used out of 9.4:

| Item | ~MiB |
|---|---|
| GTT in use (GPU buffers living in system RAM) | 3137 |
| 2x llama-server | ~740 |
| qdrant | ~335 |
| desktop (GNOME, browser, ...) | ~2200 |

Before the stack was installed the same machine used ~2.3 GiB. GTT does not show up in per-process RSS,
so the stack costs much more than `ps` suggests. Monitors using decimal GB show 10.13 GB total for 9.43 GiB.

Options: do not enable the services at boot (`systemctl --user disable rag-llm rag-embed rag-qdrant`)
and start them on demand, or start the LLM only for `ask`.

## Maximum model size on a headless server (estimate, not tested)

A headless OS needs ~0.5-0.8 GiB instead of ~2.3 GiB with a desktop. With GTT raised to ~8.8 GiB the
GPU could address about 6144 + 8800 = ~15 GB; realistically **12-13 GB for weights + KV cache**
(KV grows with context, llama.cpp compute buffers, fragmentation, Vulkan allocation size limits).
Whether RADV accepts such large GTT allocations on this board is unknown.

| Model (Q4) | Weights | Expected |
|---|---|---|
| 8B | ~5 GB | comfortable |
| 14B | ~9 GB | comfortable |
| 20-24B | ~12-14 GB | borderline, short context |
| 32B / ~30B MoE | ~17-19 GB | does not fit |

Lowering the BIOS carve-out does not change the 16 GB total; it only moves the VRAM/system-RAM boundary.

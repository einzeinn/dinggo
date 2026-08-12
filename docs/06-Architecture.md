# 06 - Architecture

## Overview

Arsitektur 3-layer orkestrasi model, masing-masing spesialis di tugasnya, load
bergantian (sequential, bukan concurrent) supaya muat di RAM 16GB.

```
┌─────────────────────────────────────────────────────────────┐
│  USER (terminal, Bahasa Indonesia casual)                     │
└───────────────────────────┬─────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — Intent Parsing                                     │
│  Model: Gemma-SEA-LION-V4.5-E2B-IT (Q4_K_M, 4.9GB)             │
│  Tugas: parse prompt casual → structured intent (JSON)        │
└───────────────────────────┬─────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — Planner / Orchestrator                              │
│  Model: Qwen3.5-4B (thinking mode ON)                          │
│  Tugas: reasoning, breakdown task jadi steps, tool-call         │
│         decision, generate plan buat di-confirm user            │
└───────────────────────────┬─────────────────────────────────┘
                             ▼
                  [USER CONFIRM / REVISI]
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — Executor                                             │
│  Tool calls: read_file, write_file, list_dir, run_command       │
│  Codegen delegate → Qwen2.5-Coder-3b (kalau step butuh          │
│         generate kode Python presisi)                            │
└─────────────────────────────────────────────────────────────┘
```

## Kenapa 3 Model Terpisah (bukan 1 model besar)

- Tiap model dioptimalkan buat 1 tugas spesifik → hasil lebih presisi dibanding 1
  model general yang disuruh multitasking
- Total footprint tetap kecil karena load bergantian, bukan sekaligus
- Modular: tiap layer bisa diganti model lain tanpa bongkar layer lain (lihat
  `07-TechnicalDecisions.md` buat kriteria swap)

## Struktur Folder Project

```
nameproject/
│
├── docs/                    # dokumentasi (lihat template referensi)
│
├── core/                    # orkestrasi 3 layer model
│   ├── intent_parser.py     # Layer 1 wrapper (Gemma-SEA-LION)
│   ├── planner.py           # Layer 2 wrapper (Qwen3.5-4B)
│   ├── executor.py          # Layer 3 — jalanin tool calls
│   └── codegen.py           # delegate codegen (Qwen2.5-Coder-3b)
│
├── tools/                   # implementasi tool-calling
│   ├── file_ops.py          # read/write/list/edit file
│   └── shell_ops.py         # run_command dengan safety guard
│
├── cli/                     # entrypoint & UI terminal
│   ├── main.py
│   └── ui.py                # rendering (rich/textual) — lihat 08-design.md
│
├── config/
│   └── models.yaml           # mapping layer → model name di Ollama
│
├── .env                      # config env (base URL Ollama, dll)
├── .env.example
├── README.md
└── LICENSE
```

Catatan soal pemisahan frontend/backend: karena ini murni CLI (bukan web app),
"frontend" digantikan `cli/` (presentation layer di terminal) dan "backend"
digantikan `core/` + `tools/` (logic layer). Pemisahan tetap jelas secara modular,
cuma penamaan disesuaikan konteks CLI, bukan web.

## Data Flow per Request

1. User input ditangkap `cli/main.py`
2. `core/intent_parser.py` panggil Gemma-SEA-LION via Ollama API → hasil JSON intent
3. `core/planner.py` panggil Qwen3.5-4B, kasih intent + context project (root dir,
   isi `docs/` kalau ada) → hasil: list of steps + tool calls yang direncanakan
4. `cli/ui.py` render plan, tunggu confirm user
5. Kalau confirm → `core/executor.py` iterasi tiap step:
   - Kalau step = tool call langsung (read/write/run) → jalankan via `tools/`
   - Kalau step = butuh codegen → delegate ke `core/codegen.py` (Qwen2.5-Coder-3b),
     lalu hasil kode masuk ke `write_file`/`edit_file`
6. Hasil akhir ditampilkan (diff, output, error jika ada)

## Model Loading Strategy

Karena RAM terbatas, model di-load/unload per fase pakai Ollama (model otomatis
unload dari memory setelah idle beberapa saat, atau bisa dipaksa lewat
`ollama stop <model>` di antara fase kalau mau strict).

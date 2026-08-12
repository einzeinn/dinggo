# 07 - Technical Decisions

Setiap keputusan dicatat dengan format: **Keputusan → Alasan → Alternatif yang
dipertimbangkan → Kapan harus di-revisit.**

---

## TD-001: Ollama sebagai Model Runtime

**Keputusan:** Pakai Ollama buat serve semua model lokal.

**Alasan:** Sudah dipakai di project sebelumnya (Bop), API sederhana (REST lokal),
support model management (pull/stop/list) tanpa setup manual llama.cpp.

**Alternatif:** llama.cpp langsung, LM Studio (GUI-based, kurang cocok buat
diintegrasikan ke script Python).

**Revisit kalau:** butuh fitur yang Ollama belum support (misal batching request
paralel yang efisien).

---

## TD-002: Orkestrasi 3 Model Terpisah (bukan 1 model besar)

**Keputusan:** Pisah tugas ke 3 model spesialis — intent parsing, planning/tool-call,
codegen — bukan 1 model serba bisa.

**Alasan:** Model kecil (<4B) yang di-training/dioptimalkan spesifik buat 1 tugas
(misal Qwen2.5-Coder buat kode) secara empiris ngalahin model general size sama di
tugas itu. Tool-calling khususnya sensitif ke training data, bukan cuma parameter
count — model 4B yang bagus di tool-calling bisa ngalahin model 18-25GB yang bukan
spesialis.

**Alternatif:** 1 model besar (misal Llama3.1 8B) buat semua tugas — lebih simpel
tapi kurang presisi per-tugas, dan tetep berat di RAM kalau mau kualitas setara.

**Revisit kalau:** muncul model <4B yang all-rounder-nya udah cukup kuat buat gantiin
2-3 layer sekaligus tanpa turun kualitas.

---

## TD-003: Pemilihan Model per Layer

| Layer | Model | Alasan Singkat |
|---|---|---|
| Intent Parsing | Gemma-SEA-LION-V4.5-E2B-IT | NLU Bahasa Indonesia casual paling natural, sudah tersedia lokal |
| Planner/Tool-call | Qwen3.5-4B | Skor tool-calling tertinggi di kelas <4B, thinking mode, context 262K |
| Codegen | Qwen2.5-Coder-3b | Spesialis kode, ringan, sudah tersedia lokal (tinggal ganti dari Qwen2.5:3b general) |
| Fallback (opsional) | Llama3.1 8B | Reasoning lebih dalam buat task berat non-real-time |

**Revisit kalau:** ada model baru yang lebih kecil/cepat dengan skor tool-calling
setara atau lebih baik dari Qwen3.5-4B.

---

## TD-004: Sequential Model Loading (bukan concurrent)

**Keputusan:** Model dijalankan bergantian sesuai fase aktif, tidak sekaligus 3-3nya
resident di RAM.

**Alasan:** Total RAM 16GB tanpa GPU discrete. 3 model sekaligus (4.9 + ~4 + 1.9 GB)
mepet/berisiko OOM kalau ditambah overhead OS + aplikasi lain.

**Alternatif:** Load semua sekaligus — cuma feasible kalau upgrade RAM atau pindah ke
GPU dengan VRAM cukup.

**Revisit kalau:** upgrade hardware, atau kalau latency switching model jadi bottleneck
signifikan.

---

## TD-005: Python sebagai Bahasa Implementasi

**Keputusan:** Seluruh CLI (`core/`, `tools/`, `cli/`) ditulis Python.

**Alasan:** Konsisten dengan target codegen (Python), ekosistem library CLI/TUI
matang (`rich`, `prompt_toolkit`, `textual`), dan familiar dari project-project
sebelumnya.

---

## TD-006: `rich` + `prompt_toolkit` buat Terminal UI

**Keputusan:** Pakai `rich` buat rendering (panel, syntax highlight, diff view,
spinner) dan `prompt_toolkit` buat input interaktif.

**Alasan:** Kombinasi paling umum & stabil buat bikin CLI IDE kelas Codex/Claude
Code-style, dokumentasi lengkap, tidak perlu reinvent wheel.

**Alternatif:** `textual` (kalau nanti mau full TUI dengan multi-pane) — bisa jadi
upgrade path v2, dicatat di `09-Roadmap.md` kalau relevan.

---

## TD-007: Environment Variables via `.env`

**Keputusan:** Semua config yang bisa berubah (base URL Ollama, nama model per
layer, dll) taruh di `.env`, bukan hardcode.

**Alasan:** Memudahkan swap model/endpoint tanpa ubah kode — selaras prinsip
modular & fleksibel di `01-Vision.md`.

# 02 - Product Requirements Document

## Ringkasan

CLI IDE lokal dengan orkestrasi 3 model (intent parsing, planning/tool-calling,
codegen) yang menjalankan flow: **nalar → plan → confirm user → eksekusi**.

## User Flow (Core Loop)

```
$ cd nameproject/
$ [namaproject]           # masuk ke CLI IDE
> [user kasih prompt bahasa natural/casual]
  → [Layer 1: Intent Parsing] parse maksud user
  → [Layer 2: Planner] reasoning + susun plan bertahap
  → tampilkan plan ke user
> [user confirm / revisi plan]
  → [Layer 3: Executor] jalankan tool calls sesuai plan
  → tampilkan hasil (diff, output command, dll)
```

## Fitur Inti (v1 — MVP)

### F1. Intent Parsing
- Terima prompt bahasa natural (termasuk Bahasa Indonesia casual/slang)
- Convert ke structured request (task type, target file/scope, constraint)

### F2. Reasoning & Planning
- Model reasoning dengan thinking mode buat breakdown task jadi langkah-langkah
- Plan ditampilkan dalam format list yang jelas (numbered steps, target file per step)
- **Wajib berhenti di sini** menunggu confirm dari user — tidak boleh auto-execute

### F3. Confirm / Revisi Plan
- User bisa: `yes` (lanjut eksekusi), `no` (batal), atau kasih revisi teks bebas
  (plan di-generate ulang dengan masukan revisi)

### F4. Tool Calling & Eksekusi
Tools minimal yang harus tersedia di v1:
- `read_file(path)`
- `write_file(path, content)`
- `list_dir(path)`
- `run_command(cmd)` — dengan whitelist/confirmation buat command yang destructive
- `edit_file(path, diff)` — tampilkan diff dulu sebelum apply

### F5. Codegen Delegation
- Step plan yang butuh generate kode Python dilempar ke model codegen khusus
  (bukan model planner) — lihat `06-Architecture.md`

### F6. Session/Context Awareness
- CLI tahu root folder project saat ini (working directory)
- (Opsional v1, wajib v1.1) baca `docs/` project kalau ada, buat konteks tambahan

## Fitur Non-Inti (Nice to Have, bukan v1)

- History/replay session sebelumnya
- Multi-language support (selain Python)
- Auto-dokumentasi (auto-update `docs/12-Changelog.md`) berdasarkan RFC-001

## Out of Scope (v1)

- Remote/cloud model fallback
- Multi-user / auth
- GUI

## Constraint Teknis

- Harus jalan di RAM 16GB, CPU-only (Ryzen 5 6600), tanpa GPU discrete
- Model dijalankan lewat Ollama, load bergantian per fase (bukan concurrent)
- Bahasa implementasi: Python

## Metrik Keberhasilan (kualitatif, v1 personal project)

- Plan yang dihasilkan masuk akal & actionable (subjektif, judged by user)
- Tidak ada eksekusi tanpa confirm (0 toleransi — ini safety requirement, bukan preferensi)
- Total waktu dari prompt → plan tampil masih terasa responsif (bukan hard target angka,
  tapi jangan sampai bikin frustrasi nunggu)

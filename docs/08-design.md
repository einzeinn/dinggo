# 08 - Design (CLI UX/Visual)

## Referensi

Terinspirasi Codex CLI & Claude Code, dengan twist personal: indikator layer model
yang aktif (transparansi proses) dan nuansa Bahasa Indonesia casual di status message.

## Prinsip Desain

1. **Transparent by default** — user selalu tahu fase apa yang sedang berjalan
   (parsing intent / planning / eksekusi) dan model mana yang aktif
2. **Confirm-before-execute selalu terlihat jelas** — plan ditampilkan dalam panel
   yang gak bisa terlewat, bukan nyempil di tengah log
3. **Ringkas tapi informatif** — output tidak flooding terminal, pakai collapsible/
   summary buat detail yang panjang (misal isi file yang di-read)

## Elemen Visual

### Startup
- ASCII art kecil / logo nama project pas start
- Tampilkan working directory aktif & model yang ter-load

### Indikator Layer Aktif (unique twist)
Icon + warna beda per layer, muncul di depan status line:

| Layer | Icon | Label Style |
|---|---|---|
| Intent Parsing (Gemma-SEA-LION) | 🗣️ | "Nyimak..." / "Paham maksudnya..." |
| Planning (Qwen3.5-4B, thinking) | 🧠 | "Mikir dulu..." / "Nyusun plan..." |
| Codegen (Qwen2.5-Coder) | ⚡ | "Nulis kode..." |
| Eksekusi tool | 🔧 | "Ngerjain: <nama tool>" |

Status message pakai Bahasa Indonesia casual (selaras cara komunikasi user), bukan
generic "Thinking..." / "Loading...".

### Plan Display
- Numbered list, tiap step tunjukin: aksi + target file/tool
- Panel dengan border jelas (`rich.Panel`), warna beda dari log biasa
- Prompt confirm di bawah plan: `[Y] Lanjut  [N] Batal  [R] Revisi`

### Diff View (sebelum apply perubahan file)
- Merah (removed) / hijau (added), format unified diff standar
- Tampil per-file, bukan digabung semua sekaligus kalau multi-file

### Eksekusi Progress
- Spinner per step yang sedang jalan
- Checklist step yang udah selesai (✓) vs pending (○) vs gagal (✗)

### Error Handling
- Error ditampilkan dalam panel merah terpisah, dengan opsi: retry step ini,
  skip, atau abort keseluruhan plan

## Tech Stack UI

- `rich` — panel, syntax highlight, diff rendering, spinner, live update
- `prompt_toolkit` — input interaktif, multi-line prompt, history (↑/↓)

## Contoh Alur Visual (kasar)

```
[NamaProject] v0.1 — nameproject/ (root: ~/projects/nameproject)
Model loaded: none (lazy load per fase)

> tambahin fungsi buat validasi email di utils.py

🗣️  Nyimak...
   → Intent: tambah fungsi validasi email, target file: utils.py

🧠  Mikir dulu... nyusun plan...

┌─ Plan ──────────────────────────────────────────┐
│ 1. Baca utils.py buat lihat struktur existing     │
│ 2. Tambah fungsi validate_email(email: str) -> bool│
│ 3. Tambah unit test kecil di test_utils.py         │
└────────────────────────────────────────────────┘
[Y] Lanjut  [N] Batal  [R] Revisi >

> y

⚡  Nulis kode...
🔧  Ngerjain: write_file (utils.py)
   ✓ utils.py updated

┌─ Diff: utils.py ──────────────────────────────────┐
│ + def validate_email(email: str) -> bool:          │
│ +     ...                                          │
└────────────────────────────────────────────────┘

🔧  Ngerjain: write_file (test_utils.py)
   ✓ test_utils.py updated

Selesai. 2 file diubah.
```

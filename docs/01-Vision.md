# 01 - Vision

> Ganti `[NamaProject]` dengan nama final project lo.

## Problem Statement

Tools agentic coding yang ada sekarang (Claude Code, Codex, Cursor CLI, dll) powerful,
tapi semuanya bergantung ke API cloud — butuh koneksi internet, biaya per-token, dan
kode/prompt lo lewat server orang lain. Buat eksperimen personal, project hackathon,
atau kerjaan yang sifatnya privat, ini jadi friksi (biaya, latency, privasi).

Di sisi lain, model open-weight kelas <4B sekarang udah cukup kuat buat tool-calling
dan reasoning terstruktur (lihat `07-TechnicalDecisions.md`), sehingga alur
**"nalar → plan → confirm → eksekusi"** yang biasanya cuma ada di tool cloud, sekarang
bisa dijalanin 100% lokal di hardware consumer.

## Vision

**[NamaProject]** adalah CLI IDE personal yang jalan sepenuhnya lokal (offline-first),
memungkinkan pemilik project masuk ke root folder project apa pun, kasih instruksi
dalam bahasa natural (termasuk Bahasa Indonesia casual), dan dapetin:

1. Pemahaman intent yang akurat
2. Plan kerja yang eksplisit dan bisa di-review sebelum dieksekusi
3. Eksekusi kode (khususnya Python) yang presisi lewat tool-calling

tanpa bergantung ke API berbayar atau koneksi internet, dengan orkestrasi beberapa
model kecil yang masing-masing spesialis di tugasnya.

## Siapa yang Pakai

Personal use — dipakai sendiri buat:
- Project hackathon (forcing function buat selesai cepat)
- Eksperimen AI tooling, game dev, desktop app
- Kerjaan yang butuh privasi/local-first (data tidak boleh keluar mesin)

## Non-Goals (v1)

- **Bukan** produk multi-user / SaaS
- **Bukan** replacement penuh untuk Claude Code/Codex di task yang butuh reasoning
  sangat berat — [NamaProject] optimal di task medium yang bisa di-breakdown jelas
- **Bukan** IDE visual (GUI/editor) — murni CLI/TUI di terminal
- Tidak menargetkan multi-bahasa pemrograman dulu di v1 — fokus Python

## Prinsip Inti

1. **Local-first** — semua model jalan via Ollama di mesin sendiri
2. **Transparent** — plan selalu ditunjukkan dan di-confirm dulu sebelum eksekusi apa pun
3. **Modular & fleksibel** — tiap model/komponen bisa diganti tanpa bongkar arsitektur
4. **Dokumentasi sebelum scope besar** — lihat `RFC-001.md`

## Definition of Success (v1)

- Bisa `cd` ke root folder project apa pun, jalanin `[namaproject]`, kasih prompt,
  dan dapet plan yang masuk akal
- Setelah confirm, eksekusi (read/write file, run command) berjalan tanpa error fatal
- Orkestrasi 3 model (intent parsing → planning/tool-call → codegen) berjalan mulus
  dalam batas RAM 16GB tanpa perlu load semua model sekaligus

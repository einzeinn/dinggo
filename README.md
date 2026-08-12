# Dinggo CLI IDE

Local CLI IDE personal yang berjalan 100% offline dengan orkestrasi 3 model AI via Ollama.

## Fitur Utama
- **Intent Parsing (Layer 1):** Menguraikan instruksi Bahasa Indonesia casual ke JSON terstruktur.
- **Planner (Layer 2):** Breakdown langkah kerja terurut dengan thinking mode.
- **Executor & Codegen (Layer 3):** Menjalankan tool calls (read/write/list/edit) & pemrosesan kode Python presisi.
- **Memory Safe:** `keep_alive: 0` eviction otomatis saat berganti layer (<16GB RAM).
- **Safety Guard:** Konfirmasi eksplisit untuk semua eksekusi shell command.

## Cara Menggunakan
```bash
pip install -e .
dinggo
```

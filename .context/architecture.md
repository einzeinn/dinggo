# Architecture

**Relationships:** - Executor & Codegen (Layer 3): Menjalankan tool calls (read/write/list/edit) & pemrosesan kode Python presisi. - core/planner.py panggil Qwen3.5-4B, kasih intent + context project (root dir, isi docs/ kalau ada) → hasil: list of steps + tool calls yang direncanakan.

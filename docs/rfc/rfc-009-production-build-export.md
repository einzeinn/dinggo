# RFC-009: Production Build, Packaging & Export Gate 3

## Status
**Proposed & Accepted**

## 1. Summary
RFC-009 defines the architecture for Dinggo's **Production Build Engine**, **Packaging Generator**, and **Final Export Gate (Approval Gate 3)**.
It establishes the standard for compiling validated software into production-ready deployment packages, comprehensive documentation, and environment runtime manifests located in `dist/`.

---

## 2. Production Build Engine (`core/builder/builder_engine.py`)

The Build Engine coordinates the compilation and production bundling of the application:

```text
VALIDATED REPOSITORY
        │
        ▼
BUILD ENGINE
        ├── Runtime Artifact Generation
        ├── Frontend Asset Bundling (if applicable)
        ├── Docker & Container Manifest Scaffolding
        └── Production Metadata Generation (dist/metadata.json)
```

### Build Metadata (`dist/metadata.json`)
```json
{
  "project_name": "Inventory App",
  "version": "1.0.0",
  "build_timestamp": "2026-08-17T17:45:00Z",
  "target_architecture": "FastAPI + React",
  "entrypoint": "main.py",
  "artifacts": [
    "dist/bundle.zip",
    "dist/docker-compose.yml",
    "dist/Dockerfile",
    "dist/metadata.json"
  ]
}
```

---

## 3. Packaging & Documentation Packager (`core/builder/packager.py`)

The packager creates release bundles and operational documentation:
- **`dist/bundle.zip`**: Compressed production archive.
- **`dist/Dockerfile`** & **`dist/docker-compose.yml`**: Production containerization.
- **`dist/docs/USER_GUIDE.md`**: Operational guide derived from `ProductSpec`.
- **`dist/docs/API_REFERENCE.md`**: API endpoints and schemas derived from `spec/api.md`.

---

## 4. Approval Gate 3 (Export Review) (`cli/gates/export_review.py`)

Before writing artifacts and marking the session complete:

```text
╭──────────────────────────────────────────╮
│        DINGGO EXPORT REVIEW (GATE 3)     │
├──────────────────────────────────────────┤
│ Build Status:    SUCCESS (dist/ generated)│
│ Target Artifacts: 4 items                │
│  • dist/bundle.zip                       │
│  • dist/docker-compose.yml               │
│  • dist/docs/API_REFERENCE.md            │
│  • dist/metadata.json                    │
│                                          │
│ [1] Export & Finalize                    │
│ [2] Rebuild                              │
│ [3] Cancel                               │
╰──────────────────────────────────────────╯
```

---

## 5. Verification & Test Strategy
- Unit tests for `BuildEngine` creating production `dist/` directory and `metadata.json`.
- Unit tests for `Packager` generating zip bundle, Dockerfile, and user documentation.
- Tests for `ExportReviewGate` interactive and non-interactive approval.

# Dinggo Versioning Rules

Whenever changes, fixes, or upgrades are made to the codebase, automatically bump the version in accordance with Semantic Versioning (`MAJOR.MINOR.PATCH`):

1. **PATCH (angka paling belakang, e.g. `0.2.0` -> `0.2.1`)**:
   - Bug fixes, refactoring, small UX tweaks, minor adjustments, documentation updates.
2. **MINOR (angka di tengah, e.g. `0.2.0` -> `0.3.0`)**:
   - New features, architectural expansions, new modules/workers/adapters, major phase implementations.
3. **MAJOR (angka paling depan, e.g. `1.0.0`)**:
   - Official public production releases or breaking API shifts.

### Files to synchronize on every bump:
- `pyproject.toml` (`version = "x.y.z"`)
- `core/__init__.py` (`__version__ = "x.y.z"`)
- `cli/ui.py` (`PRODUCT FACTORY · vx.y.z`)
- `cli/interface.py` (`· vx.y.z`)

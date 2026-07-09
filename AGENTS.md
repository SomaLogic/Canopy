# AGENTS.md — Canopy (somadata)

## Project Overview

Canopy is a Python library (PyPI package: `somadata`) by SomaLogic/Standard BioTools for reading, writing, and manipulating ADAT files — a proprietary tab-delimited format used in SOMAscan proteomics assays to store relative fluorescent unit (RFU) measurements across biological samples.

The core `Adat` class subclasses `pandas.DataFrame` with metadata preserved via pandas' `_metadata` mechanism.

## Repository Layout

```
somadata/              # Main package
├── adat.py            # Adat class (subclasses pd.DataFrame + mixins)
├── annotations.py     # Annotations wrapper
├── errors.py          # Custom exception hierarchy
├── base/              # Mixin classes (AdatMetaHelpers, AdatMathHelpers)
├── data/              # Bundled reference data (example .adat, lift.zip)
├── io/                # I/O layer (adat reader/writer, annotations reader)
│   ├── adat/
│   └── annotations/
└── tools/             # Utilities (concatenation, math, pandas helpers)
tests/                 # pytest test suite (mirrors package structure)
├── conftest.py        # Shared fixtures (session-scoped control_data)
├── data/              # Test fixtures (control_data.adat)
bin/                   # CLI scripts (somadata_check_adat, somadata_concat_adats)
docs/                  # Sphinx documentation
plans/                 # Feature planning documents (ADAT v2.0 converter)
.github/workflows/     # CI (pytest matrix) + CD (PyPI publish)
```

## Tech Stack

- **Language:** Python 3.9+
- **Build:** Poetry (`pyproject.toml`)
- **Core deps:** pandas, numpy, openpyxl
- **Optional dep:** `cnorm` (AdatNormalization mixin, imported conditionally)
- **Testing:** pytest, pytest-cov
- **Linting/Formatting:** Black (with `-S` for single quotes), isort (Black profile), codespell
- **Pre-commit:** `.pre-commit-config.yaml` enforces formatting on commit

## Development Commands

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Run tests with coverage
pytest --cov=somadata

# Format code
black -S .
isort --profile black --filter-files --skip=__init__.py .

# Spell check
codespell --skip="*.ipynb"
```

## Code Style

- **Formatter:** Black with `-S` (prefer single quotes)
- **Import order:** isort with Black profile; skip `__init__.py`
- **Line length:** 88 characters (Black default)
- **Type hints:** Use `from __future__ import annotations` at the top of modules
- **Docstrings:** NumPy-style (Parameters, Returns, Examples sections)
- **Naming:**
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for module-level constants
  - Leading underscore for private/internal methods
- **Logging:** Use stdlib `logging` (never `print` for diagnostics)
- **Errors:** Raise domain-specific exceptions from `somadata/errors.py` (or submodule `errors.py` files)

## Architecture

### Key Patterns

1. **DataFrame subclassing** — `Adat` extends `pd.DataFrame`. Custom attributes survive pandas operations via `_metadata = ['header_metadata']`.
2. **Mixin composition** — `Adat` inherits from `AdatMetaHelpers`, `AdatMathHelpers`, `pd.DataFrame`, and optionally `AdatNormalization`.
3. **MultiIndex metadata** — Row and column annotations are stored as pandas `MultiIndex` objects for structured access.
4. **Factory constructor** — `Adat.from_features(rfu_matrix, row_metadata, column_metadata, header_metadata)` builds an Adat from parts.
5. **Separated I/O** — Reading/writing logic lives in `somadata/io/`, decoupled from the data model.
6. **Strategy pattern** — Header merging during concatenation uses a configurable `merge_strategy` dict mapping fields to actions.
7. **Lazy-loaded reference data** — `LiftData` loads scale factors from bundled ZIP on demand.

### Error Hierarchy

- `AdatBaseError` — generic base
- `AdatKeyError` — key/column lookup failures
- `AdatMetaError` — metadata operation errors
- `AnnotationsLiftingError` — version lifting issues
- Submodules define additional errors (e.g., `AdatConcatError` in tools)

## Testing

- Tests live in `tests/` and mirror the package directory structure.
- Shared fixtures are in `tests/conftest.py` — notably `control_data` (session-scoped parsed Adat).
- Test data files live in `tests/data/`.
- Mix of `unittest.TestCase` classes and plain pytest functions — both are acceptable.
- CI runs on Windows with Python 3.9 and 3.13.
- Always run `pytest` before submitting changes to verify nothing is broken.

## CI/CD

- **PR checks** (`.github/workflows/python-app.yml`): pytest on Windows, Python 3.9 + 3.13.
- **Release** (`.github/workflows/publish-pypi.yml`): builds wheel/sdist, publishes to PyPI on tag push, creates GitHub Release with Sigstore signatures.

## Working with ADAT Files

An ADAT file has four logical sections:
1. **Header metadata** — key-value pairs (assay version, processing info)
2. **Column metadata** — per-analyte annotations (SeqId, Target, Units, etc.)
3. **Row metadata** — per-sample annotations (SampleId, SampleType, etc.)
4. **RFU matrix** — numeric measurement data (rows × analytes)

When adding features, maintain this separation. I/O concerns belong in `somadata/io/`, data manipulation in `somadata/base/` or `somadata/tools/`.

## Contribution Guidelines

1. Format with Black (`-S`) and isort before committing.
2. Add tests for new functionality in the appropriate `tests/` subdirectory.
3. Use NumPy-style docstrings for public APIs.
4. Raise typed exceptions, never bare `Exception`.
5. Keep I/O decoupled from business logic.
6. Do not commit large binary files or secrets.
7. The `plans/` directory contains design docs for upcoming features — consult them when implementing planned work.

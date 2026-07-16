---
name: summarize-adat
description: >-
  Print a concise structural summary of an ADAT file (header metadata, shape,
  row/column metadata fields, sample type counts) using the somadata library.
  Use when a user asks about the contents of an .adat file, wants to know what
  samples or analytes are in a file, or before any task that requires
  understanding an ADAT's structure. Run the script instead of reading raw
  ADAT text or loading the file manually in Python — this is the fastest,
  lowest-context way to inspect an ADAT.
---

# Summarize ADAT

**Use this skill before any work involving an ADAT file.** Running the script
is far cheaper than reading raw file bytes or doing ad-hoc pandas exploration.

## Run the summary

```bash
poetry run python .cursor/skills/summarize-adat/scripts/summarize_adat.py <path/to/file.adat>
```

The script prints:

| Section | What you get |
|---|---|
| **HEADER** | Version, Title, AssayType, AssayVersion, StudyMatrix, ProcessSteps, etc. |
| **SHAPE** | Number of sample rows × analyte columns |
| **ROW METADATA** | All per-sample annotation field names + unique values (or count if many) |
| **SAMPLE TYPE COUNTS** | Breakdown by SampleType (e.g. Plasma, QC, Calibrator, Blank) |
| **COLUMN METADATA** | All per-analyte annotation field names, Units, HybControl split, Dilution groups |

## Reading the output

### Key header fields

- `!AssayType` — `SomaScan Array` or `SomaScan NGS` (affects which row/col fields exist)
- `!AssayVersion` — panel size (e.g. `SomaScan 11k`, `Illumina Protein Prep 9k`)
- `!ProcessSteps` — comma-separated normalization pipeline; last steps indicate normalization state
- `!StudyMatrix` — sample matrix (Plasma, Serum, CSF, …)

### ADAT structure in somadata

An `Adat` is a `pd.DataFrame` subclass:

```
adat.index        ← pd.MultiIndex: one level per row-metadata field (per-sample annotations)
adat.columns      ← pd.MultiIndex: one level per col-metadata field (per-analyte annotations)
adat.values       ← float64 RFU (or Read Count for NGS) matrix [n_samples × n_analytes]
adat.header_metadata  ← dict of assay-level key/value pairs
```

### Access patterns

```python
import somadata

adat = somadata.read_adat('path/to/file.adat')

# Get a single row-metadata field as a Series
sample_types = adat.index.get_level_values('SampleType')

# Get a single col-metadata field as a Series
targets = adat.columns.get_level_values('Target')

# Filter to biological samples only
bio = adat.pick_on_meta(axis=0, name='SampleType', values=['Plasma'])

# Filter to a subset of analytes
subset = adat.pick_on_meta(axis=1, name='Target', values=['IL-6', 'TNF'])

# RFU matrix as plain numpy array
matrix = adat.to_numpy()   # shape: (n_samples, n_analytes)
```

### Common row-metadata fields

| Field | Meaning |
|---|---|
| `SampleID` | Unique sample identifier |
| `SampleType` | `Plasma`, `Serum`, `QC`, `Calibrator`, `Blank`, etc. |
| `PlateId` | Plate run identifier |
| `RowCheck_PassFlag` | Overall per-sample QC flag (`PASS` / `FLAG`) |

### Common column-metadata fields

| Field | Meaning |
|---|---|
| `SeqId` | Unique SOMAmer reagent ID (e.g. `10000-28`) |
| `Target` | Protein target short name |
| `UniProt ID` | UniProt accession |
| `Units` | `RFU` (Array) or `Read Count` (NGS) |
| `HybControl` | `True` if hybridization control; exclude from biology |
| `Dilution` | Dilution bin (`0.005`, `0.05`, `0.2`) |

## Somadata public API cheat sheet

```python
somadata.read_adat(path)            # read .adat → Adat
adat.to_adat(path)                  # write Adat → .adat

# Row/col filtering
adat.pick_on_meta(axis, name, values)     # keep rows/cols where meta == values
adat.exclude_on_meta(axis, name, values) # drop rows/cols where meta == values
adat.pick_meta(axis, names)              # keep only listed metadata fields
adat.exclude_meta(axis, names)           # drop listed metadata fields

# Concatenation
somadata.smart_adat_concatenation([adat1, adat2])  # inner join on SeqId by default

# Version conversion
somadata.to_v2_adat([adat])         # convert v1 ADAT(s) to v2.0 format
```

## Additional resources

- Format spec: `plans/adat_v2.0_spec.md`
- Conversion plan: `plans/adat_v2.0_converter_implementation_plan.md`
- Tests / usage examples: `tests/`

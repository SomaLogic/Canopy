# CAN-39: Array Field Conversions — Implementation Plan

**Ticket:** [CAN-39](https://illumina.atlassian.net/browse/CAN-39)  
**Parent Epic:** CAN-30 — ADAT v2.0 Combined Format Support (Phase 1)  
**Depends on:** CAN-38 (Phase 0 Foundation) — Done  
**Created:** 2026-07-13  
**Status:** In Progress — Tasks 1.1, 1.2, 1.3 implemented and passing (341/341 tests)

---

## Summary

Implement all array v1.x → v2.0 field mappings across the three ADAT sections:

1. **Task 1.1** — Header metadata conversion
2. **Task 1.2** — SOMAmer annotations (COL_DATA) conversion
3. **Task 1.3** — Sample annotations (ROW_DATA) conversion

These correspond to Section 3.2 of the v2.0 spec (`plans/adat_v2.0_spec.md`).

---

## Foundation Already in Place (CAN-38)

The following modules are complete and available for use:

| Module | Purpose |
|--------|---------|
| `somadata/conversion/detection.py` | `detect_input_type()` → classifies Adat as `native_array`, `bridged_array`, `native_ngs`, `v2_combined` |
| `somadata/conversion/errors.py` | Error hierarchy: `ConversionError`, `UnsupportedCombinationError`, `AssayVersionError`, etc. |
| `somadata/conversion/converter.py` | `to_v2_adat()` router with stub handlers (`NotImplementedError`) |
| `somadata/io/adat/v2_fields.py` | `V2_HEADER_FIELD_TYPES`, `V2_COL_FIELD_TYPES`, `V2_ROW_FIELD_TYPES`, type lookup helpers |
| `tests/conversion/conftest.py` | Factory helpers: `make_adat()`, `make_array_adat()`, `make_bridged_array_adat()`, etc. |

The converter router dispatches to `_convert_native_array()`, `_convert_bridged_array()`, and the pair handlers — all currently raise `NotImplementedError`.

---

## Architecture Decision: Module Layout

### New modules to create

```
somadata/conversion/
├── __init__.py          (existing — add new exports)
├── converter.py         (existing — wire up real handlers)
├── detection.py         (existing)
├── errors.py            (existing)
├── array/               (NEW — array-specific conversion logic)
│   ├── __init__.py
│   ├── header.py        (Task 1.1)
│   ├── col_data.py      (Task 1.2)
│   └── row_data.py      (Task 1.3)
└── _helpers.py          (NEW — shared utilities: GUID generation, JSON consolidation)
```

### Rationale

- Keeps each section's conversion self-contained and testable in isolation.
- The `array/` subpackage mirrors the eventual `ngs/` subpackage (CAN-40+).
- Shared utilities (GUID generation, plate-key JSON consolidation) go in `_helpers.py` so both `array/` and future `ngs/` can reuse them.

---

## Task 1.1: Array Header Field Conversion ✅

**File:** `somadata/conversion/array/header.py`  
**Public function:** `convert_array_header(adat: Adat) -> dict`

### Input

The `adat.header_metadata` dict from a pre-v2.0 array ADAT. Keys may have `!` prefixes (legacy convention).

### Output

A new `dict` conforming to the closed v2.0 header field set (`V2_HEADER_FIELD_TYPES` keys).

### Implementation Steps

#### 1.1.1 — Scaffolding & pass-through fields

```python
def convert_array_header(adat: Adat) -> dict:
    """Convert array v1.x header_metadata to a v2.0-compliant header dict."""
```

- Initialize output dict with all `V2_HEADER_FIELD_TYPES` keys set to `''` (ensures closed set).
- Copy pass-through fields (strip `!` prefix on lookup):
  - `Title`, `StudyOrganism`, `StudyMatrix`, `UseRestriction`, `AssayVersion`

#### 1.1.2 — Static field assignments

- `FileVersion` = `'2.0'`
- `AssayType` = `'Array'` (caller overrides to `'Mixed'` during merge)
- `FileCreatedDate` = current UTC timestamp in ISO 8601 (`YYYY-MM-DDThh:mm:ssZ`)
- `AdatId` = newly generated GUID (`GID-<uuid4>`)

#### 1.1.3 — SourceFile JSON

- Build: `{"1": {"AdatId": "<old_adat_id>"}}` from legacy `AdatId` value.
- If legacy `AdatId` is missing/blank, compute md5sum of source file (or leave a placeholder marker for the caller to fill).

#### 1.1.4 — SOMAmerReferenceSource

- Map from legacy `ProteinEffectiveDate` (with or without `!` prefix).

#### 1.1.5 — ProcessSteps JSON

- Parse legacy comma-separated string into list of step names.
- Wrap in JSON: `{"1": ["step1", "step2", ...]}`.
- The `"1"` key becomes the `ProcessStepsId` for all samples from this source.

#### 1.1.6 — ReportConfig JSON

- If legacy `ReportConfig` is present and non-empty, wrap similarly: `{"1": <value>}`.
- If absent, set to empty string (v2.0 allows blank for this field).

#### 1.1.7 — Plate-keyed field consolidation

This is the most complex sub-step. Legacy headers contain dynamic keys like `PlateScale_Scalar_PLT45241`. These must be consolidated into a single JSON field.

**Helper function** (in `_helpers.py`):

```python
def consolidate_plate_fields(
    header: dict,
    prefix: str,
    stage: str = 'PlatformSpecific',
) -> dict:
    """Extract plate-keyed header values into a JSON dict.

    Scans header for keys matching `<prefix><PlateId>` and returns:
    {"<PlateId>": {"<stage>": <value>}}
    """
```

**Mappings:**

| Legacy prefix pattern | v2.0 field | JSON structure |
|---|---|---|
| `PlateScale_Scalar_` | `PlateScaleScalar` | `{"<PlateId>": {"PlatformSpecific": <float>}}` |
| `CalPlateTailPercent_` | `CalibrateTailPercent` | `{"<PlateId>": {"PlatformSpecific": <float>}}` |
| `CalPlateTailTest_` | `CalibrateTailPercentStatus` | `{"<PlateId>": {"PlatformSpecific": "<PASS/WARNING>"}}` |
| `PlateScale_PassFlag_` | `PlateScaleStatus` | `{"<PlateId>": "<PASS/FLAG>"}` |
| `PlateTailPercent_` | `QCCheckTailPercent` | `{"<PlateId>": {"PlatformSpecific": <float>}}` |
| `PlateTailTest_` | `QCCheckTailPercentStatus` | `{"<PlateId>": {"PlatformSpecific": "<PASS/FAIL>"}}` |

Note: `PlateScaleStatus` uses a flat structure (not nested under `PlatformSpecific`) per spec example.

#### 1.1.8 — GeneratedBy extraction

- Extract `GeneratedBy` value from header (will be used by ROW_DATA as `SoftwareVersion`).
- Do NOT include it in the v2.0 header output (it's removed from header).
- Return it as a secondary output or store on a shared conversion context object.

#### 1.1.9 — NGS-only fields defaulted to blank

- `PlateSOMAmerNormReadsStatus` = `''` (NGS-only; blank for array-only output).

### Design Consideration: Conversion Context Object

Multiple tasks need to share state (e.g., `GeneratedBy` extracted in header conversion is needed in ROW_DATA, `ProcessStepsId` mapping used in both header and ROW_DATA). Introduce a lightweight dataclass:

```python
@dataclasses.dataclass
class ArrayConversionContext:
    """Shared state across header/col/row array conversion steps."""
    source_adat_id: str = ''
    generated_by: str = ''
    process_steps_id: str = '1'
    report_config_id: str = '1'
    source_file_id: str = '1'
    created_date: str = ''  # Legacy CreatedDate for PlateRunDate fallback
```

### Tests (Task 1.1)

**File:** `tests/conversion/array/test_header.py`

| Test case | What it verifies |
|---|---|
| `test_output_has_all_v2_header_keys` | Output dict keys == `V2_HEADER_FIELD_TYPES` keys |
| `test_file_version_is_2_0` | `FileVersion == '2.0'` |
| `test_adat_id_is_new_guid` | AdatId starts with `GID-` and differs from source |
| `test_source_file_contains_old_adat_id` | JSON has `{"1": {"AdatId": "<old>"}}` |
| `test_protein_effective_date_mapped` | `SOMAmerReferenceSource` populated |
| `test_process_steps_json_format` | Valid JSON with list of step strings |
| `test_plate_scale_scalar_consolidated` | Multiple plate keys → single JSON field |
| `test_calibrate_tail_percent_consolidated` | Same for CalibrateTailPercent |
| `test_removed_fields_not_present` | `GeneratedBy`, `LabLocation`, `CreatedBy`, etc. absent |
| `test_assay_type_set_to_array` | Default single-input case |
| `test_pass_through_fields_preserved` | Title, StudyOrganism, etc. |
| `test_bang_prefix_stripped_on_lookup` | `!Title` in source → `Title` in output |

---

## Task 1.2: Array COL_DATA Field Conversion ✅

**File:** `somadata/conversion/array/col_data.py`  
**Public function:** `convert_array_col_data(adat: Adat) -> pd.MultiIndex`

### Input

`adat.columns` — a `pd.MultiIndex` where levels correspond to column annotation fields (SeqId, Target, Type, Dilution, Cal_PLT45241, etc.).

### Output

A new `pd.MultiIndex` with v2.0-compliant level names and values.

### Implementation Steps

#### 1.2.1 — Field renames

Build a rename mapping dict:

```python
_COL_RENAMES = {
    'EntrezGeneID': 'EntrezGeneId',
}
```

For dynamic fields, use pattern matching:
- `Cal_<PlateId>` → `PlatformSpecificCalibrate_<PlateId>_ScaleFactor`
- `CalQcRatio_<PlateId>_<QCSampleId>` → `QCRatio_<PlateId>`
- `PlateScale_Reference` → `Ref.Array.PlateScale_<CalibratorId>`
- `CalReference` → `Ref.Array.Calibrate_<CalibratorId>`
- `QcReference_<QCSampleId>` → `Ref.Array.QCRatio_<QCSampleId>`
- `medNormRef_ReferenceRFU` / `medNormSMP_ReferenceRFU` → `Ref.MedNorm.Id`

#### 1.2.2 — CalQcRatio multi-QC validation

When renaming `CalQcRatio_<PlateId>_<QCSampleId>`:
- Group all `CalQcRatio_*` fields by PlateId.
- If any plate has >1 distinct QCSampleId, raise a `ConversionError` with a message indicating which plate has the conflict and suggesting the optional QC ID argument.
- Otherwise, drop the QCSampleId suffix.

#### 1.2.3 — New field: HybControl

- Add a new level `HybControl` to the MultiIndex.
- Value = `'True'` where `Type == 'Hybridization Control'`, else `'False'`.

#### 1.2.4 — Field removal

Remove these levels from the MultiIndex:
- `SeqIdVersion`, `SomaId`, `ColCheck`, `Units`, `eLOD`

#### 1.2.5 — Reconstruct MultiIndex

- Build a new `pd.MultiIndex.from_arrays()` with the renamed/added/removed levels.
- Preserve the SeqId level as the first level (or per existing convention).

### Tests (Task 1.2)

**File:** `tests/conversion/array/test_col_data.py`

| Test case | What it verifies |
|---|---|
| `test_entrez_gene_id_renamed` | Level name change from `EntrezGeneID` to `EntrezGeneId` |
| `test_cal_plate_id_renamed` | `Cal_PLT123` → `PlatformSpecificCalibrate_PLT123_ScaleFactor` |
| `test_cal_qc_ratio_single_qc_renamed` | `CalQcRatio_PLT1_QC1` → `QCRatio_PLT1` |
| `test_cal_qc_ratio_multi_qc_raises` | Multiple QC IDs on same plate → error |
| `test_plate_scale_reference_renamed` | → `Ref.Array.PlateScale_<CalibratorId>` |
| `test_hyb_control_generated` | `HybControl` level present with correct values |
| `test_removed_fields_absent` | `SeqIdVersion`, `SomaId`, etc. not in output levels |
| `test_seq_id_preserved` | SeqId values unchanged |
| `test_med_norm_ref_renamed` | `medNormRef_ReferenceRFU` → `Ref.MedNorm.Id` |

---

## Task 1.3: Array ROW_DATA Field Conversion ✅

**File:** `somadata/conversion/array/row_data.py`  
**Public function:** `convert_array_row_data(adat: Adat, ctx: ArrayConversionContext) -> pd.MultiIndex`

### Input

- `adat.index` — a `pd.MultiIndex` where levels are row metadata fields (SampleId, SampleType, PlateId, SlideId, etc.).
- `ctx` — the `ArrayConversionContext` carrying header-derived values.

### Output

A new `pd.MultiIndex` with v2.0-compliant level names and values.

### Implementation Steps

#### 1.3.1 — Field renames

```python
_ROW_RENAMES = {
    'PlatePosition': 'WellPosition',
    'HybControlNormScale': 'HybNormScaleFactor',
    'RowCheck': 'RowCheckStatus',
    'StudyId': 'Project',
    'SubjectID': 'SubjectId',
    'Barcode2d': 'MatrixTubeBarcode',
}
```

#### 1.3.2 — New generated fields

For each sample (row), generate:

| Field | Value |
|---|---|
| `SampleReadout` | `'Array'` (constant for all rows) |
| `UniqueSampleKey` | `'GID-<uuid4>'` (new per sample) |
| `SourceFileId` | `ctx.source_file_id` (e.g., `'1'`) |
| `ProcessStepsId` | `ctx.process_steps_id` (e.g., `'1'`) |
| `ReportConfigId` | `ctx.report_config_id` (e.g., `'1'`) |
| `SoftwareVersion` | `ctx.generated_by` |

#### 1.3.3 — HybNormStatus derivation

```python
def _derive_hyb_norm_status(scale_factor: str) -> str:
    """'PASS' if 0.4 <= float(scale_factor) <= 2.5, else 'FLAG'."""
```

- Parse `HybNormScaleFactor` (renamed from `HybControlNormScale`) as float.
- Return `'PASS'` if in [0.4, 2.5], else `'FLAG'`.
- Handle missing/empty values → blank string.

#### 1.3.4 — MedNormIntStatus derivation

Per spec (Appendix A.2):
- Only applies to samples with `SampleType` in `{'Calibrator', 'Buffer'}` that have undergone `medNormInt`.
- Check all `NormScale_<DilutionGroup>` scale factors for the sample.
- `'PASS'` if ALL dilution scale factors are within [0.4, 2.5]; `'FLAG'` otherwise.
- Blank for other SampleTypes.

#### 1.3.5 — PlateRunDate fallback

- If `PlateRunDate` level is blank/missing for a sample, populate from `ctx.created_date`.

#### 1.3.6 — ControlId population

- For rows where `SampleType` is one of `{'QC', 'Buffer', 'Calibrator'}`:
  - Set `ControlId` = `SampleId` value for that row.
- For `'Sample'` type: leave `ControlId` as-is (pass through from source, or blank).

#### 1.3.7 — Field removal

Remove these levels:
- `ExtIdentifier`, `SsfExtId`, `ScannerID`, `Barcode`, `SampleName`
- `SampleDescription`, `TimePoint`, `SampleGroup`, `SiteId`
- `CLI`, `PercentDilution`, `SampleNotes`, `AliquotingNotes`, `AssayNotes`

#### 1.3.8 — NGS-only fields defaulted to blank

**Decision: Add all blank NGS fields now** to produce a fully v2.0-compliant output from a single-array conversion (not deferred to merge step).

Add blank levels for NGS-only fields that must be present in v2.0 but are empty for array samples:
- `SequencingRunId`, `MatrixTubeBarcode` (if not renamed from `Barcode2d`), `InputType`, `KitType`
- `SOMAmerBeadPlate`, `NGSPlateMasterMixLot`, `SOMAmerReads`, `SOMAmerReadsStatus`
- `SOMAmerNormReads`, `SOMAmerNormReadsStatus`, `RefCorr`, `EmpericalHybTemp`
- `EmpiricalHybTempStatus`, `MedNormExtStatus`
- `CrossPlateMedNormIntScaleFactor`, `InstrumentType`, `Flowcell`
- `YieldDemux`, `YieldQ30Demux`, `Q30WeightedMean`

This ensures that `_convert_native_array` and `_convert_bridged_array` produce a standalone v2.0-valid Adat without needing a merge step.

#### 1.3.9 — Reconstruct MultiIndex

- Build new `pd.MultiIndex.from_arrays()` with all renamed/added/removed levels.

### Tests (Task 1.3)

**File:** `tests/conversion/array/test_row_data.py`

| Test case | What it verifies |
|---|---|
| `test_plate_position_renamed_to_well_position` | Level name change |
| `test_hyb_control_norm_scale_renamed` | → `HybNormScaleFactor` |
| `test_row_check_renamed_to_status` | → `RowCheckStatus` |
| `test_study_id_renamed_to_project` | → `Project` |
| `test_sample_readout_set_to_array` | All values = `'Array'` |
| `test_unique_sample_key_is_guid` | Starts with `GID-`, unique per sample |
| `test_source_file_id_from_context` | Matches `ctx.source_file_id` |
| `test_software_version_from_generated_by` | Matches `ctx.generated_by` |
| `test_hyb_norm_status_pass` | Factor 1.0 → `'PASS'` |
| `test_hyb_norm_status_flag_low` | Factor 0.3 → `'FLAG'` |
| `test_hyb_norm_status_flag_high` | Factor 2.6 → `'FLAG'` |
| `test_med_norm_int_status_calibrator` | Derived for Calibrator samples |
| `test_med_norm_int_status_blank_for_sample` | Blank for SampleType=Sample |
| `test_plate_run_date_fallback` | Blank → filled from CreatedDate |
| `test_control_id_for_qc_sample` | QC type → ControlId = SampleId |
| `test_removed_fields_absent` | ExtIdentifier, SsfExtId, etc. not in output |

---

## Wiring: Connecting Handlers to the Router

Once the three conversion functions are implemented, update `converter.py`:

### `_convert_native_array` and `_convert_bridged_array`

Both use the same array conversion pipeline (bridged vs native only differs in detection, not in field mapping):

```python
def _convert_native_array(adat: Adat, *, med_norm_ref: str | None) -> Adat:
    ctx = ArrayConversionContext.from_adat(adat)
    new_header = convert_array_header(adat)
    new_columns = convert_array_col_data(adat)
    new_index = convert_array_row_data(adat, ctx)
    return _assemble_v2_adat(adat, new_header, new_columns, new_index)
```

### `_assemble_v2_adat` helper

```python
def _assemble_v2_adat(
    source: Adat,
    header: dict,
    columns: pd.MultiIndex,
    index: pd.MultiIndex,
) -> Adat:
    """Construct a v2.0 Adat from converted components."""
    result = Adat(
        data=source.values,
        index=index,
        columns=columns,
        header_metadata=header,
    )
    return result
```

---

## Shared Utilities (`somadata/conversion/_helpers.py`)

| Function | Purpose |
|---|---|
| `generate_guid() -> str` | Returns `'GID-<uuid4>'` |
| `consolidate_plate_fields(header, prefix, stage) -> dict` | Extracts plate-keyed values into JSON structure |
| `strip_bang_prefix(key: str) -> str` | `'!Title'` → `'Title'` |
| `lookup_header(header: dict, *keys) -> str` | Try multiple key variants (with/without `!`) |
| `parse_process_steps(raw: str) -> list[str]` | Split comma-separated steps into clean list |

---

## Execution Order & Dependencies

```
┌─────────────────────────────────────┐
│  _helpers.py (shared utilities)     │  ← Start here
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  ArrayConversionContext dataclass    │  ← Define context structure
└─────────────┬───────────────────────┘
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼
┌──────┐  ┌──────┐  ┌──────┐
│ 1.1  │  │ 1.2  │  │ 1.3  │         ← Can be developed in parallel
│Header│  │COL   │  │ROW   │           (1.3 depends on context from 1.1)
└──┬───┘  └──┬───┘  └──┬───┘
   │         │         │
   └─────────┼─────────┘
             ▼
┌─────────────────────────────────────┐
│  Wire into converter.py handlers    │  ← Final integration step
└─────────────────────────────────────┘
```

**Recommended implementation order:**
1. `_helpers.py` — shared utilities
2. `ArrayConversionContext` dataclass
3. Task 1.1 (header) — produces context needed by 1.3
4. Task 1.2 (COL_DATA) — independent of 1.1/1.3
5. Task 1.3 (ROW_DATA) — uses context from 1.1
6. Wire handlers in `converter.py`
7. Integration tests

---

## Test Data Strategy

### Extend `tests/conversion/conftest.py`

Add richer factory helpers that include the legacy fields being converted:

```python
def make_full_legacy_array_adat() -> Adat:
    """Array Adat with ALL legacy header/col/row fields for conversion testing."""
```

This fixture should include:
- Header with plate-keyed fields (`PlateScale_Scalar_PLT1`, `CalPlateTailPercent_PLT1`, etc.)
- `GeneratedBy`, `ProteinEffectiveDate`, `CreatedDate`, `AdatId`
- COL_DATA with `Cal_PLT1`, `CalQcRatio_PLT1_QC1`, `PlateScale_Reference`, `EntrezGeneID`
- ROW_DATA with `PlatePosition`, `HybControlNormScale`, `RowCheck`, `StudyId`, etc.

### Test file layout

```
tests/conversion/
├── conftest.py              (existing — extend with richer helpers)
├── array/
│   ├── __init__.py
│   ├── conftest.py          (array-specific fixtures if needed)
│   ├── test_header.py       (Task 1.1)
│   ├── test_col_data.py     (Task 1.2)
│   └── test_row_data.py     (Task 1.3)
├── test_converter.py        (existing — add integration tests)
└── test_detection.py        (existing)
```

---

## Edge Cases & Decisions Needed

### 1. Multiple plates in header

A single ADAT can have data from multiple plates. The consolidation logic must handle:
- `PlateScale_Scalar_PLT1` AND `PlateScale_Scalar_PLT2` → `{"PLT1": {...}, "PLT2": {...}}`

### 2. `!` prefix inconsistency

Legacy fields may or may not have the `!` prefix. The `lookup_header` helper must try both variants.

### 3. Missing optional fields

Many legacy fields are optional. Conversion must not fail if they're absent — just produce blank values in the v2.0 output.

### 4. PlateRunDate fallback from CreatedDate

Only use `CreatedDate` as fallback if `PlateRunDate` is actually blank. Do not overwrite existing values.

### 5. ControlId population scope

Spec says: "Populate with SampleId for QC/Buffer/Calibrator SampleType." This means:
- If source already has a `ControlId` value for these types, overwrite with `SampleId`.
- If `SampleType` is `'Sample'`, keep existing `ControlId` (pass through, typically blank).

### 6. RMA → Project merge

Spec says: "Move RMA value into Project field." Implementation:
- If only `StudyId` is present, use it as `Project`.
- If only `RMA` is present, use `RMA` as `Project`.
- If both are present, concatenate them pipe-delimited: `"<StudyId>|<RMA>"`.

---

## Risks

| Risk | Mitigation |
|---|---|
| Dynamic field pattern matching is fragile | Comprehensive regex tests; document exact expected patterns |
| MultiIndex manipulation is verbose/error-prone | Build helper to convert to/from dict-of-lists for easier manipulation |
| Real ADAT files may have unexpected field variants | Add defensive handling; log warnings for unrecognized fields |
| Large ADATs (11k+ analytes) may have many dynamic columns | Ensure COL_DATA conversion scales with vectorized operations where possible |

---

## Definition of Done

- [x] All three conversion functions implemented and unit-tested
- [x] `_convert_native_array` and `_convert_bridged_array` in `converter.py` no longer raise `NotImplementedError`
- [x] `pytest` passes with no regressions (341/341)
- [ ] Code formatted with `black -S` and `isort`
- [x] Validated against `V2_HEADER_FIELD_TYPES` (output header keys match closed set)
- [x] Edge cases documented and tested (missing fields, multiple plates, `!` prefix)

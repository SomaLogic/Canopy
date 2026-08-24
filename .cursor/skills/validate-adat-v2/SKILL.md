---
name: validate-adat-v2
description: >-
  Validate that an ADAT file conforms to the v2.0 specification (plans/adat_v2.0_spec.md).
  Checks header field set (closed, no removed fields, required non-empty), JSON field schemas,
  COL_DATA/ROW_DATA required fields and removed fields, SampleReadout consistency with AssayType,
  UniqueSampleKey uniqueness/GUIDs, ProcessStepsId linkage, and RFU matrix sanity.
  Use when performing end-to-end testing of the v2.0 converter, verifying a converted output
  file, or whenever the user asks whether an ADAT is v2.0-compliant or conforms to the spec.
---

# Validate ADAT v2.0 Compliance

Run this skill after any v2.0 conversion to verify the output is spec-compliant before
treating test results as authoritative.

## Run the validator

```bash
poetry run python .cursor/skills/validate-adat-v2/scripts/validate_adat_v2.py <path/to/file.adat>
```

Exit codes: **0** = all checks pass · **1** = one or more FAILs · **2** = file could not be loaded.

## What is checked

| Section | Checks |
|---|---|
| **FileVersion** | Must equal `"2.0"` (gates all other checks) |
| **Header.ClosedFieldSet** | No extra fields beyond the 19-field v2.0 closed set |
| **Header.NoRemovedFields** | Pre-v2 / moved fields (`!Version`, `CreatedDate`, `GeneratedBy`, `AssayVersion`, `InstrumentType`, `Flowcell`, `YieldDemux`, legacy NGS scalars, etc.) absent |
| **Header.RequiredFields** | All `Value Required = True` fields present and non-empty |
| **Header.AssayType** | Value is one of `"Array"`, `"NGS"`, `"Mixed"` |
| **Header.AdatId** | Matches `GID-<uuid>` pattern |
| **Header.FileCreatedDate** | ISO 8601 date format |
| **Header.JSON.\*** | All JSON-typed fields parse as valid JSON |
| **Header.ProcessSteps.Schema** | `{"<int>": ["step1", ...], ...}` schema |
| **Header.NoBangPrefix** | No `!` prefix on any header field names |
| **ColData.RequiredFields** | `SeqId`, `Target`, `TargetFullName`, `Type`, `Organism`, `HybControl`, `Dilution` present |
| **ColData.NoRemovedFields** | `SeqIdVersion`, `SomaId`, `ColCheck`, `Units`, `eLOD` absent |
| **ColData.HybControl.Values** | Only `"True"` / `"False"` values |
| **ColData.NoLegacyCal** | No `Cal_<PlateId>` legacy naming |
| **RowData.RequiredFields** | `SampleId`, `SampleReadout`, `UniqueSampleKey`, `SampleType`, `AssayVersion`, `ProcessStepsId`, `SoftwareVersion`, `PlateId`, `WellPosition`, `HybNormStatus`, `RowCheckStatus` present |
| **RowData.NoRemovedFields** | `PlatePosition`, `HybControlNormScale`, `HybNorm_1_ScaleFactor`, `RowCheck`, `StudyId`, `Barcode2d`, legacy `_PassFlag` fields, etc. absent |
| **RowData.SampleReadout** | Values are `"Array"` / `"NGS"`; consistent with `AssayType` header |
| **RowData.UniqueSampleKey** | GUIDs (FAIL on bad format), all unique |
| **RowData.ProcessStepsId** | All values resolve to keys in `ProcessSteps` header JSON |
| **RowData.RowCheckStatus** | Values are `"PASS"`, `"FLAG"`, or `"LEAK"` |
| **DataMatrix** | No negative RFU values (FAIL); NaN% reported (expected for SeqId union) |

WARN (not FAIL) is used for checks that indicate likely issues but may have valid exceptions
(e.g., `AdatId` GUID pattern, missing reference columns, NGS-specific fields not present).

## Interpreting the output

```
--- Header ---
  [PASS] ✓ Header.ClosedFieldSet
  [FAIL] ✗ Header.NoRemovedFields: Removed pre-v2 fields found: ['!Version', 'CreatedDate']
  [WARN] ⚠ Header.AdatId: AdatId 'abc-123' does not match GID-<uuid> pattern
  [INFO] ℹ DataMatrix.Shape: 176 samples × 11372 analytes

SUMMARY  37 passed · 1 failed · 1 warnings
```

- Any **FAIL** means the file does not conform to spec — investigate the listed field.
- **WARN** is informational — review but not necessarily blocking.
- **INFO** provides structural context (shape, NaN %).

## Integration with end-to-end testing

Use alongside the integration test suite for the v2.0 converter:

```bash
# Run the validator on a freshly converted file
poetry run python .cursor/skills/validate-adat-v2/scripts/validate_adat_v2.py data/output-mixed-v2.0.adat

# Run the pytest integration tests
poetry run pytest tests/conversion/test_integration.py -v
```

## Additional resources

- v2.0 format specification: `plans/adat_v2.0_spec.md`
- Converter implementation plan: `plans/adat_v2.0_converter_implementation_plan.md`
- Integration tests: `tests/conversion/test_integration.py`
- ADAT structure reference: see `summarize-adat` skill

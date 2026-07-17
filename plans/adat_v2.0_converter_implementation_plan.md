# ADAT v2.0 Converter — Implementation Plan

**Created:** 2026-07-07  
**Status:** Draft  
**Applies to:** Canopy/somadata (Python)  
**References:** `plans/adat_v2.0_spec.md`, `plans/ADAT-v2.0-converter-functional-requirements.pdf`

---

## Strategy

This plan is structured for **incremental delivery**. Phase 1 delivers the primary ICM use case (Path 1: `bridged_array` + `native_ngs` → Mixed v2.0) end-to-end as a shippable increment. Subsequent phases layer in remaining conversion paths, the v2.0 reader, and edge-case hardening.

Tickets are sized at ~1–2 days of work each with clear acceptance criteria.

---

## Phase 0: Foundation & Infrastructure

Prerequisite work that unblocks all subsequent phases.

### Ticket 0.1: Input Type Detection Module

**Description:** Implement the platform detection logic (Section 6 of functional requirements) as a standalone module that classifies an Adat into one of: `native_array`, `bridged_array`, `native_ngs`, `v2_combined`.

**Acceptance Criteria:**
- New module: `somadata/conversion/detection.py`
- Function `detect_input_type(adat: Adat) -> InputType` implementing the decision tree:
  1. `FileVersion == "2.0"` → `v2_combined`
  2. SlideId + Subarray non-empty → array branch:
     - AssayVersion < v4 → raise error (Section 5.3)
     - ProcessSteps ends with `[CrossPlatformPlateScale, CrossPlatformCalibrate, MedNormExt]` → `bridged_array`
     - Otherwise → `native_array`
  3. SOMAmerReads column present and non-empty → `native_ngs`
  4. Otherwise → raise error (unrecognized format)
- `InputType` enum defined
- Unit tests covering all branches and edge cases (empty fields, missing columns)

---

### Ticket 0.2: Conversion Error Classes & Validation Framework

**Description:** Extend the existing error hierarchy with conversion-specific errors matching Section 5 of the functional requirements.

**Acceptance Criteria:**
- New module: `somadata/conversion/errors.py`
- Error classes: `ConversionError(AdatBaseError)`, `UnsupportedCombinationError`, `SampleMatrixMismatchError`, `AssayVersionError`, `MedNormMismatchError`, `ProcessStepsMismatchError`
- Error messages match the exact strings specified in Section 5 (parameterized with filenames, types, etc.)
- SampleMatrix equivalence logic (Appendix C: Plasma ↔ EDTA Plasma, CSF ↔ Cerebrospinal Fluid, case-insensitive)
- Unit tests for each error condition

---

### Ticket 0.3: Conversion Path Router

**Description:** Implement the path lookup table (Section 4) and the `to_v2_adat()` function signature/skeleton that dispatches to the correct conversion path.

**Acceptance Criteria:**
- New module: `somadata/conversion/converter.py` with public function:
  ```python
  def to_v2_adat(adats: list[str | Adat], med_norm_ref: str | None = None) -> Adat
  ```
- Path validation: looks up `(typeA, typeB)` in approved combinations table; rejects unlisted combinations
- Handles: empty list error, >2 inputs error, single `v2_combined` warning (return as-is)
- Dispatches to path-specific handler (stub/NotImplementedError initially)
- Exposed via `somadata.__init__.py` as `somadata.to_v2_adat()`
- Unit tests for routing logic and error conditions (5.1)

---

### Ticket 0.4: v2.0 Writer Path

**Description:** Update `write_adat()` to support v2.0 output format when `FileVersion == "2.0"` in header metadata.

**Acceptance Criteria:**
- Version dispatch in `write_adat()`: if `header_metadata.get("FileVersion") == "2.0"`, use v2.0 writer logic
- v2.0 writer rules:
  - Closed header field set (all Section 2.3 fields present; no additional)
  - No `!` prefix on field names in `^COL_DATA` / `^ROW_DATA` Name/Type rows
  - No `!Checksum` line
  - JSON fields serialized as single-line minified JSON
  - Sections in order: `^HEADER`, `^COL_DATA`, `^ROW_DATA`, `^TABLE_BEGIN`
  - COL_DATA and ROW_DATA each have `Name` and `Type` rows (no `!` prefix)
  - Correct type annotations (String, Integer, Decimal, Date, JSON) based on field definitions in spec
- Pre-v2.0 writer path unchanged (regression tests pass)
- Unit test: write a manually constructed v2.0 Adat, verify output format compliance

---

## Phase 1: Primary Use Case (Path 1 — bridged_array + native_ngs)

This is the ICM-critical path. Delivers a working end-to-end converter for the most important combination.

### Ticket 1.1: Array Header Field Conversion

**Description:** Implement header field mapping for array v1.x → v2.0 (Section 3.2.1 of spec).

**Acceptance Criteria:**
- New GUID generated for `AdatId`; old value stored in `SourceFile` JSON
- `FileVersion` set to `"2.0"`
- `FileCreatedDate` set to write timestamp
- `ProteinEffectiveDate` → `SOMAmerReferenceSource`
- `ProcessSteps` reformatted to JSON: `{"<id>": ["step1", ...]}`
- `ReportConfig` reformatted to JSON with ID key
- Plate-keyed fields consolidated into JSON:
  - `PlateScale_Scalar_<PlateId>` → `PlateScaleScalar`
  - `CalPlateTailPercent_<PlateId>` → `CalibrateTailPercent`
  - `CalPlateTailTest_<PlateId>` → `CalibrateTailPercentStatus`
  - `PlateScale_PassFlag_<PlateId>` → `PlateScaleStatus`
  - `PlateTailPercent_<PlateId>` → `QCCheckTailPercent`
  - `PlateTailTest_<PlateId>` → `QCCheckTailPercentStatus`
- Removed fields stripped; `GeneratedBy` moved to sample table
- `AssayType` set correctly (`"Array"` for single, `"Mixed"` for merge)
- Unit tests comparing transformed header against expected v2.0 structure

---

### Ticket 1.2: Array COL_DATA Field Conversion

**Description:** Implement SOMAmer annotation field mapping for array → v2.0 (Section 3.2.2).

**Acceptance Criteria:**
- Field renames:
  - `EntrezGeneID` → `EntrezGeneId`
  - `Cal_<PlateId>` → `PlatformSpecificCalibrate_<PlateId>_ScaleFactor`
  - `CalQcRatio_<PlateId>_<QCSampleId>` → `QCRatio_<PlateId>` (error if multiple QC IDs per plate)
  - `PlateScale_Reference` → `Ref.Array.PlateScale_<CalibratorId>`
  - `CalReference` → `Ref.Array.Calibrate_<CalibratorId>`
  - `QcReference_<QCSampleId>` → `Ref.Array.QCRatio_<QCSampleId>`
  - `medNormRef_ReferenceRFU` / `medNormSMP_ReferenceRFU` → `Ref.MedNorm.Id`
- New field generated: `HybControl` (`"True"` if Type == "Hybridization Control", else `"False"`)
- Removed fields: `SeqIdVersion`, `SomaId`, `ColCheck`, `Units`, `eLOD`
- Unit tests with sample COL_DATA transformation

---

### Ticket 1.3: Array ROW_DATA Field Conversion

**Description:** Implement sample annotation field mapping for array → v2.0 (Section 3.2.3).

**Acceptance Criteria:**
- Field renames:
  - `PlatePosition` → `WellPosition`
  - `HybControlNormScale` → `HybNormScaleFactor`
  - `RowCheck` → `RowCheckStatus`
  - `StudyId` → `Project`
  - `SubjectID` → `SubjectId`
  - `Barcode2d` → `MatrixTubeBarcode`
- New fields generated:
  - `SampleReadout` = `"Array"` for all rows
  - `UniqueSampleKey` = new GUID per sample
  - `SourceFileId` = integer key to SourceFile header JSON
  - `ProcessStepsId` = integer key to ProcessSteps header JSON
  - `ReportConfigId` = integer key to ReportConfig header JSON
  - `SoftwareVersion` = from `GeneratedBy` header value
  - `HybNormStatus` = `"PASS"` if HybNormScaleFactor in [0.4, 2.5], else `"FLAG"`
  - `MedNormIntStatus` = derived per spec (Calibrator/Buffer only)
- `PlateRunDate` populated from `CreatedDate` header if blank
- `ControlId` populated with `SampleId` for QC/Buffer/Calibrator `SampleType`
- Removed fields stripped (ExtIdentifier, SsfExtId, ScannerID, Barcode, SampleName, etc.)
- Unit tests

---

### Ticket 1.4: NGS Header Field Conversion

**Description:** Implement header field mapping for NGS → v2.0 (Section 3.3.1).

**Acceptance Criteria:**
- New GUID for `AdatId`; old in `SourceFile`
- `FileVersion` = `"2.0"`
- `Version` (DPQ version) moved to `SoftwareVersion` in sample table
- Header-to-sample-table fields: `InstrumentType`, `Flowcell`, `YieldDemux`, `YieldQ30Demux`, `Q30WeightedMean`
- `RunId` → removed from header; `SequencingRunId` in sample table
- Plate-keyed fields consolidated to JSON:
  - `PlatformSpecificPlateScale_ScaleFactor` + `CrossPlatformPlateScale_ScaleFactor` → `PlateScaleScalar`
  - `PlatformSpecificCalibrateTailPercent` + `CrossPlatformCalibrateTailPercent` → `CalibrateTailPercent`
  - Tail percent pass flags → `CalibrateTailPercentStatus`
  - `QCCheckTailPercent` → `QCCheckTailPercent` JSON
  - `PlateSOMAmerNormReads_PassFlag` → `PlateSOMAmerNormReadsStatus` JSON
- `AssayType` = `"NGS"` or `"Mixed"`
- `ReportConfig` left blank for NGS
- Unit tests

---

### Ticket 1.5: NGS COL_DATA Field Conversion

**Description:** Implement SOMAmer annotation field mapping for NGS → v2.0 (Section 3.3.2).

**Acceptance Criteria:**
- Field renames:
  - `Target Full Name` → `TargetFullName`
  - `UniProt ID` → `UniProt`
  - `Entrez Gene ID` → `EntrezGeneId`
  - `Entrez Gene Symbol` → `EntrezGeneSymbol`
  - `DRC_Level` → `DRCLevelNGS`
  - `QCCheck_<PlateId>_ScaleFactor` → `QCRatio_<PlateId>`
  - `BlockList` → `BlockListNGS`
- Reference field prefixing: existing `Ref.*` → ensure `Ref.NGS.*` prefix
- Removed: `SomaId`, `QCCheck_<PlateId>_PassFlag`, `Units`, `LoD.*`
- Unit tests

---

### Ticket 1.6: NGS ROW_DATA Field Conversion

**Description:** Implement sample annotation field mapping for NGS → v2.0 (Section 3.3.3).

**Acceptance Criteria:**
- Field renames:
  - `SampleID` → `SampleId`
  - `SequencingRunID` → `SequencingRunId`
  - `ControlD` → `ControlId` (PascalCase)
  - `BatchID` → `BatchId`
  - `MatrixType` → `KitType`
  - `ProbePlate` → `NGSPlateMasterMixLot`
  - `HybNorm_1_ScaleFactor` → `HybNormScaleFactor`
  - `CrossPlateMedNormInt_ScaleFactor` → `CrossPlateMedNormIntScaleFactor`
  - All `*_PassFlag` → `*Status` (HybNorm, MedNormInt, MedNormExt, RowCheck)
- New fields: `SampleReadout` = `"NGS"`, `UniqueSampleKey`, `SourceFileId`, `ProcessStepsId`
- Header fields moved to sample rows: `InstrumentType`, `Flowcell`, `YieldDemux`, `YieldQ30Demux`, `Q30WeightedMean` (replicated to all NGS rows)
- `MedNormInt_Dilution_ScaleFactor`: replace `-` with `_` in dilution suffix
- `PlateRunDate` left blank for NGS
- Unit tests

---

### Ticket 1.7: SeqId Union & Missing Value Fill

**Description:** Implement the SeqId union logic for merging two ADATs with different SOMAmer content (Section 9).

**Acceptance Criteria:**
- Output contains the union of all SeqIds from both sources
- SeqIds absent in a source get `NA` (NaN) in that source's sample rows
- COL_DATA populated for all SeqIds; platform-specific annotation fields for the "other" platform are blank/NA
- Column order: SeqId ascending (consistent between COL_DATA and data matrix)
- Unit tests with overlapping and non-overlapping SeqId sets

---

### Ticket 1.8: MedNorm Reference Validation

**Description:** Implement MedNorm compatibility checks required before merge (Section 5.4, Section 8, Section 3.4).

**Acceptance Criteria:**
- For bridged_array + native_ngs merge (Path 1):
  1. Array ProcessSteps must end with the bridged terminal triple
  2. NGS ProcessSteps must match the required sequence (Appendix A/B)
  3. `Ref.MedNormExt.<Matrix>` RFU vectors must be element-wise identical across sources for shared SeqIds
- If MedNorm mismatch: raise error unless `med_norm_ref` specified
- If `med_norm_ref` specified: use values from source whose `Ref.MedNorm.Id` matches; raise error if value not found
- Unit tests for: matching refs, mismatched refs, med_norm_ref resolution, missing med_norm_ref

---

### Ticket 1.9: Mixed Merge — Header & Metadata Combination

**Description:** Implement the header merge rules for producing a Mixed output (Section 10, Section 3.4).

**Acceptance Criteria:**
- `AssayType` = `"Mixed"`
- New GUID for `AdatId`
- `SourceFile` JSON with both source identifiers: `{"1": {"AdatId": "..."}, "2": {"AdatId": "..."}}`
- `ProcessSteps`: each distinct set gets unique ID; samples mapped via `ProcessStepsId`
- `ReportConfig`: same approach (array only contributes)
- Pipe-delimited merge: `Title`, `StudyOrganism`, `StudyMatrix`, `SOMAmerReferenceSource`
- Plate-keyed JSON fields: combine all PlateId keys; error if duplicate PlateId across sources
- `AssayVersion`: pass through (array version for Array content context)
- Unit tests

---

### Ticket 1.10: Path 1 End-to-End Integration & Testing

**Description:** Wire together all Phase 1 components into the complete Path 1 flow. Integration test with real example files.

**Acceptance Criteria:**
- `to_v2_adat(["bridged_array.adat", "ngs_sample.adat"])` produces a valid v2.0 Mixed Adat
- Output passes v2.0 writer without error
- Round-trip: write → re-read with existing parser → verify structure
- All field mappings correct in output
- `SampleReadout` correctly set per source (`"Array"` / `"NGS"`)
- Integration test using example ADAT files
- Verify against expected output structure (if `example_v2.0_Mixed.adat` available)

---

## Phase 2: Single-Input Conversions (Paths 6, 7, 8)

Lower complexity paths — format conversion without merge.

### Ticket 2.1: Path 6 — bridged_array → Array v2.0

**Description:** Single-input conversion of a bridged array ADAT to v2.0 format.

**Acceptance Criteria:**
- `to_v2_adat(["bridged_array.adat"])` produces v2.0 with `AssayType = "Array"`
- Reuses array field conversion from Phase 1 (Tickets 1.1–1.3)
- No MedNorm checks required (single input)
- `CrossPlateMedNormIntScaleFactor` is pass-through
- Integration test

---

### Ticket 2.2: Path 7 — native_array → Array v2.0

**Description:** Single-input conversion of a native array ADAT.

**Acceptance Criteria:**
- `to_v2_adat(["native_array.adat"])` produces v2.0 with `AssayType = "Array"`
- Same array field conversion; no bridged terminal requirement
- Integration test

---

### Ticket 2.3: Path 8 — native_ngs → NGS v2.0

**Description:** Single-input conversion of a native NGS ADAT.

**Acceptance Criteria:**
- `to_v2_adat(["ngs_sample.adat"])` produces v2.0 with `AssayType = "NGS"`
- Reuses NGS field conversion from Phase 1 (Tickets 1.4–1.6)
- No MedNorm checks (single input)
- Integration test

---

## Phase 3: Two-Input Merge Paths (Paths 2, 3, 4, 5)

### Ticket 3.1: Path 2 — bridged_array + v2_combined

**Description:** Merge a bridged array with an existing v2.0 combined ADAT.

**Acceptance Criteria:**
- `v2_combined` may be Array/NGS/Mixed — MedNorm validated accordingly
- Array undergoes full conversion; v2_combined is already in target format
- SeqId union applied
- Integration test

---

### Ticket 3.2: Path 3 — native_ngs + v2_combined

**Description:** Merge a native NGS ADAT with an existing v2.0 ADAT.

**Acceptance Criteria:**
- Output AssayType: NGS if v2_combined is NGS-only; Mixed otherwise
- NGS undergoes full conversion; v2_combined already in format
- Integration test

---

### Ticket 3.3: Path 4 — native_array + native_array

**Description:** Merge two native array ADATs.

**Acceptance Criteria:**
- Both must be same SomaScan AssayVersion (error if not)
- Output `AssayType = "Array"`
- No ProcessSteps restriction beyond classification rules
- Existing array-only merge logic applied
- Integration test

---

### Ticket 3.4: Path 5 — v2_combined + v2_combined

**Description:** Merge two existing v2.0 ADATs.

**Acceptance Criteria:**
- Output `AssayType` derived from union of `SampleReadout` values
- Both already in v2.0 format — merge involves SeqId union, header combination, metadata merge
- ProcessSteps must be identical if both are NGS-only
- Integration test

---

## Phase 4: v2.0 Reader (Follow-up)

### Ticket 4.1: v2.0-Aware Reader Dispatch

**Description:** Update `read_adat()` to detect and handle v2.0 format.

**Acceptance Criteria:**
- Detect `FileVersion: 2.0` in header and apply v2.0 parsing rules
- No `!` prefix expected on field names
- JSON header values parsed correctly (already partially handled)
- Type row (`Name`/`Type` without `!` prefix) handled
- Round-trip test: write v2.0 → read → verify equivalence

---

### Ticket 4.2: v2.0 Field Type Validation on Read

**Description:** Validate field values match declared types on read.

**Acceptance Criteria:**
- Integer fields contain only integers or `NA`
- Decimal fields contain valid floats or `NA`
- Date fields match ISO 8601 format
- JSON fields parse as valid JSON
- String fields within 1024 char limit
- Warnings (not errors) on type mismatches to be lenient for early adoption

---


## Dependency Graph

```
Phase 0 (Foundation)
  ├── 0.1 Detection
  ├── 0.2 Errors
  ├── 0.3 Router (depends on 0.1, 0.2)
  └── 0.4 v2.0 Writer

Phase 1 (Path 1) — depends on Phase 0
  ├── 1.1 Array Header
  ├── 1.2 Array COL_DATA
  ├── 1.3 Array ROW_DATA
  ├── 1.4 NGS Header
  ├── 1.5 NGS COL_DATA
  ├── 1.6 NGS ROW_DATA
  ├── 1.7 SeqId Union (depends on 1.2, 1.5)
  ├── 1.8 MedNorm Validation
  ├── 1.9 Mixed Merge (depends on 1.1–1.8)
  └── 1.10 Integration (depends on all above + 0.4)

Phase 2 (Single-input) — depends on Phase 1 field converters
  ├── 2.1 Path 6
  ├── 2.2 Path 7
  └── 2.3 Path 8

Phase 3 (Two-input) — depends on Phase 1, Phase 2
  ├── 3.1 Path 2
  ├── 3.2 Path 3
  ├── 3.3 Path 4
  └── 3.4 Path 5

Phase 4 (Reader) — depends on Phase 0.4 writer
  ├── 4.1 Reader dispatch
  └── 4.2 Type validation

```

---

## Effort Estimates (Approximate)

| Phase | Tickets | Est. Days | Notes |
|-------|---------|-----------|-------|
| Phase 0 | 4 | 1-2 | Foundation; enables all other work |
| Phase 1 | 10 | 5-8 | Primary ICM use case; highest value |
| Phase 2 | 3 | 2-3 | Low complexity; reuses Phase 1 code |
| Phase 3 | 4 | 3-5 | Moderate complexity; merge edge cases |
| Phase 4 | 2 | 1-2 | Reader follow-up |
| **Total** | **26** | **12-20** | |

**MVP (Phases 0 + 1):** ~6-10 days → shippable Path 1 for ICM  
**Full scope (all phases):** ~12-20 days

---

## Risks & Open Questions

1. **NGS ADAT parsing:** The existing generic reader should handle NGS ADATs since the section structure is identical. Needs verification with actual NGS test files early in Phase 0.

2. **`AssayVersion` mapping for NGS:** Spec says `6k→v1, 9k TMS→v2, 9k xTMS→v3, Calypso→v4`. Need to confirm these input strings are consistently formatted or if detection logic needs to be fuzzy.

3. **Multiple QC IDs per plate:** Array COL_DATA conversion drops the QCSampleId suffix from `CalQcRatio`. If multiple QC IDs exist on a plate, the spec says to throw an exception. Confirm this is the desired behavior vs. providing an optional argument.

4. **`Ref.MedNormExt.<Matrix>` identity check:** "Element-wise identical for shared SeqIds" — need to define tolerance for floating-point comparison (exact match? epsilon?).

5. **`cnorm` dependency:** The Adat class inherits from `AdatNormalization` (optional `cnorm` package). Confirm the converter does not need to invoke any normalization — it only operates on already-normalized data.

6. **Backwards-compatible writer:** The v2.0 writer shares the `write_adat()` entry point but dispatches on FileVersion. Need to ensure no regressions in the pre-v2.0 path.

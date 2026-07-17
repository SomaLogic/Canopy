# ADAT v2.0 Combined Format File Specification

---

## Section 1: Introduction and Rationale

### 1.1 Purpose

The ADAT v2.0 format is a unified file specification that accommodates both SomaSeq (NGS readout) and SomaScan (array readout) outputs in a single file structure. Prior to v2.0, each platform produced its own ADAT variant with diverging field names, conventions, and structural assumptions, creating a growing maintenance burden for downstream software and analysis pipelines.

### 1.2 High-Level Design Decisions and Rationale

**Combining array and NGS in one file**  
Several new fields were added to manage combined NGS vs array source data. For example, a per-sample `SampleReadout` field (`"Array"` or `"NGS"`) makes the platform identity of each row explicit. Other fields have moved from the header to the sample table in cases where information was study-centric and is now sample-specific in a combined context. Detailed field information is found in Section 2 of the file specification. 

**Fieldname changes**  
Significant effort was made to preserve field name consistency from pre-2.0 ADAT versions. However, where fields in pre-2.0 ADAT formats represented equivalent data but had different names, those fields were combined into a single field and renamed. In cases where platform-specific fields shared a common name but represented fundamentally different information, those fields were assigned to differently named unique fields. Other fields were renamed to more accurately reflect the field data or to comply with a file-wide naming standard.

**Union of SeqIds and missing values**  
The NGS and array standard deliverables can contain differing sets of SeqIds. In order to preserve standard product content of both platforms, the v2.0 format will take the union of SeqId measurements from input ADATs with differing SOMAmer Reagent content. One repercussion of this decision is an expectation of missing values in the SOMAmer Reagent measurement table in the combined format.

**Defined field types**  
Pre-v2.0 ADATs had no formal type system — field types were implicit, requiring each consumer to infer or handle type conversion independently. The v2.0 format defines five explicit types (String, Integer, Decimal, Date, JSON) that specify allowed values, missing value representations, and encoding constraints for every field. Explicit types enable parser validation, reduce ambiguous edge cases, and provide a shared vocabulary that aligns array and NGS parsers under a single standard.

**Unique Sample Identifiers**  
Pre-v2.0 ADATs had no stable cross-file sample identity — `SampleId` was locally unique within a plate but not guaranteed unique across files or platforms. The `UniqueSampleKey` field (a GUID assigned at merge time) provides a persistent, cross-file identifier that survives subsequent read/write cycles. Once assigned, this value is preserved in all future ADAT files derived from the same data, enabling reliable sample tracking across combined array and NGS datasets.

**Removal of '!' tokens**  
In pre-v2.0 ADATs a subset of field names were preceded by "!" character to indicate a "required" field. However, that convention was applied inconsistently over time and ultimately caused more confusion than benefit to end users. In the v2.0 format, those tokens have been removed and requirements for each field are defined in the file specification.

**JSON for structured and multi-value data**
Fields that contain plate-keyed values (e.g., `PlateScaleScalar`, `CalibrateTailPercent`) or configuration objects (e.g., `ProcessSteps`, `ReportConfig`) use JSON. This replaces both dynamic key patterns (`FieldName_<PlateId>`) and comma-separated lists, providing structure that can be parsed unambiguously. All JSON values are single-line and minified (no embedded newlines or formatting whitespace).

**PlatformSpecific / CrossPlatform processing stage taxonomy**  
NGS sample processing involves two calibration stages: one within-platform and one cross-platform. In the combined format, array calibration maps to the `PlatformSpecific` stage. JSON-valued fields that carry platform-stage data use the keys `"PlatformSpecific"` and `"CrossPlatform"`, with array files only populating `"PlatformSpecific"`.

**Sunset service-lab-specific fields**  
Fields used exclusively for internal service lab operations (e.g., `LabLocation`, `CreatedBy`, `CLI`, `RMA`, `ScannerID`) are removed. The transition to a more distributed assay model makes the utility of these fields more niche than generally useful. Users requiring this metadata can append it as external sample annotation information.

**Closed header field set**  
The header in v2.0 is static — all defined fields must be present, and no additional fields are permitted. This is a deliberate departure from v1.x array ADATs, where the header was open-ended. The closed set simplifies parser validation and prevents field proliferation. Plate-level data that previously created dynamic per-plate keys is consolidated into JSON fields keyed by PlateId.

**Platform detection for auto-parsing pre-v2.0 files**
Parsers that auto-detect legacy format versions can use: non-empty `SlideId` and `Subarray` fields to identify array v1.x ADATs; non-empty `SOMAmerReads` columns in the sample table to identify NGS ADATs.

**Intentional data loss on conversion**  
Conversion of pre-v2.0 ADATs to v2.0 involves field removal, renaming, and restructuring. This is intentional and documented. Back-conversion from v2.0 to a prior platform-specific format is not supported (lossless round-trip is not a design goal). See Scope below for more details.

**File versioning**  
The `FileVersion` field is intended to be the authoritative indicator of format version in v2.0 ADATs and beyond. Parsers must read this field to determine which parsing logic to apply. Users should consult the corresponding specification version for formatting details.

### 1.3 Scope

**Supported source formats for conversion to v2.0:**

- Array: SomaScan ADATS from AssayVersion v4 and above, generated by PharmaServices (PX), DataDelve Normalization (DDN), SomaDataIO, or Canopy/SomaData
- NGS: All Illumina Protein Prep (IPP) and SomaSeq data generated by DRAGEN Protein Quantification (DPQ) software
- Normalization: To combine median normalized study data (including ANML), source ADATs data must first undergo median normalization to a common reference

**Production scope:**
SomaScan (array) and DPQ (NGS) software will continue to generate platform-specific ADATs in pre-v2.0 format as their standard output. The v2.0 combined format is produced exclusively by converter functions in OSS packages (Canopy for Python, SomaDataIO for R). The primary near-term use case is an internal Canopy-based pipeline that merges bridged array and NGS ADATs into a v2.0 output.

---

## Section 2: Format Specification

### 2.1 General File Layout and Conventions

The ADAT v2.0 file is a tab-delimited plain-text file with four mandatory sections that must appear in the following order:

```
^HEADER        key-value metadata about the file and assay
^COL_DATA      SOMAmer/analyte annotations (one row per annotation field)
^ROW_DATA      Sample annotation column names
^TABLE_BEGIN   RFU/count data matrix (samples × analytes)
```

The diagram below illustrates the spatial relationship between sections, including the padding regions within `^TABLE_BEGIN` and the alignment of column and row metadata with the data matrix:

ADAT format layout

**Encoding and delimiters**

- On-disk encoding: ASCII character set. All field names, values, and JSON content must be ASCII-encoded text.
- Field delimiter: TAB (`\t`). The tab (`\t`), newline (`\n`), and carriage return (`\r`)  characters must not appear within a value; no escape mechanism is defined.
- Line endings: platform-dependent at time of file writing; no specific newline representation is required.

**Field naming rules**

- All field names use **PascalCase**
  - **Exception — dynamic fields:** Fields tied to a specific entity (e.g., plate, calibrator) use underscore-delimited embedded variables: `FieldName_<Variable>`. Leading or trailing underscores that result from an empty variable are trimmed
  - **Exception — reference fields:** SOMAmer annotation reference fields use dotted prefixes `Ref.Array.`* or `Ref.NGS.`* to indicate platform applicability
- Field names are case-sensitive
- Field names must be comprised of only letters (A-Z, a-z), numbers (0-9), periods (.), or underscores (_)
- Field names must begin with a letter character, not a number, period, or underscore
- Field names are unique across the entire ADAT file. A name used in one section cannot appear in any other section
- Maximum field name length: 64 characters

**Checksum line**
The `!Checksum` line is not supported in v2.0. File integrity verification should be performed externally using standard cryptographic hashing of the complete file.

**File extension**  
The `.adat` extension is retained for v2.0.

### 2.2 Field Value Types

All fields in the v2.0 ADAT file conform to one of the following types:

#### String

- Maximum length: 1024 characters
- Limited to the ASCII character set
- Tab (`\t`), newline (`\n`), and carriage return (`\r`)  characters must not appear within a value
- The pipe character (`|`) - no padding spaces - is interpreted a delimiter to represent multiple string values within a field
- Missing values are represented using a blank string (`""`) 
- Examples: `"Research Use Only"`, `"SS-2343677_v5.0_Plasma"`

#### Integer

- Whole number (positive, negative, or zero)
- Limits: up to ±9.22×10^18 (fits 64-bit range)
- Missing values are represented using `NA`
- Examples: `-1`, `0`, `9999999`

#### Decimal

- Floating-point number with optional scientific notation
- Use period (`.`) for decimal; no other separators such as commas for thousands allowed
- Limits: Max of 16 significant digits
- Scientific notation allowed using `e` for moving decimal right or `e-` for  moving decimal left
- Missing values are represented using `NA`
- Examples: `0.72`, `-12.345`, `5e-05`, `6.02214e23`, `123456789012345`, `1.23456789012345e7`

#### Date

- Format: `YYYY-MM-DD[<T>hh:mm:ss<Z>]` 
  - ISO 8601 compliant 
  - `YYYY-MM-DD` - required 
  - `YYYY-MM-DDThh:mm:ssZ` - optional hour:minute:seconds in ISO 8601 compliant format
- Examples:
  - `2026-02-04`
  - `2026-01-31T16:25:23Z`

#### JSON

- Structured data encoded as valid JSON (RFC 8259)
- Serialized single-line minified format (no embedded newlines, tabs or formatting whitespace)
- Field limit of 4096 characters
- Missing value represented as blank string (`""`) . 
- Examples:

```
{"1":{"PlatformSpecific":0.72,"CrossPlatform":1.001},"2":{"PlatformSpecific":0.85}}
{"1":["Raw RFU","Hyb Normalization","medNormInt"],"2":["Raw RFU","Hyb Normalization"]}
```

### 2.3 ^HEADER Section — Field Definitions

Fields are tab-separated key-value pairs: `FieldName\tValue`. The section begins with the `^HEADER` token line.

**The set of header fields in v2.0 is static and closed.** All fields in the table below must be present in every v2.0 ADAT file. No additional fields are permitted. Field ordering has no hard requirement; parsers must not assume positional mapping.

Field values are not ordered and may be empty (blank string) where a field is not applicable. The `Value Required` column uses the following values:

- **True** — value must be non-empty in all v2.0 ADATs
- **False** — value may be empty (optional)
- **Array-only** — must be non-empty when array data is present; blank for NGS-only ADATs
- **NGS-only** — must be non-empty when NGS data is present; blank for array-only ADATs

> For `Mixed` ADATs (`AssayType = "Mixed"`), both Array-only and NGS-only fields will be populated simultaneously.


| Field                       | Type   | Value Required | Example Value                                                                                                                                                              | Description                                                                                                                                                                                                                                                                                                    |
| --------------------------- | ------ | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FileVersion                 | String | True           | `2.0`                                                                                                                                                                      | `2.0` — ADAT file version defined in this specification document                                                                                                                                                                                                                                               |
| AdatId                      | String | True           | `GID-b3a1f9e2-4c7d-4e8f-a012-8e3bc5d6f1a9`                                                                                                                                 | Unique file identifier (GUID); new value generated on merge of multiple ADATs or version convert; preserved on read/write without modification                                                                                                                                                                 |
| AssayType                   | String | True           | `Mixed`                                                                                                                                                                    | Indicator of assay readout for samples in file. Options are `"Array"`, `"NGS"`, or `"Mixed"`                                                                                                                                                                                                                   |
| AssayVersion                | String | True           | `v5.0`                                                                                                                                                                     | SomaScan or SomaSeq assay version. Use in conjunction with AssayType field. Example: "v5.0" (Array), "1.9.0" (NGS)                                                                                                                                                                                             |
| UseRestriction              | String | True           | `Research Use Only`                                                                                                                                                        | Assay usage designation: `"Research Use Only"`                                                                                                                                                                                                                                                                 |
| SourceFile                  | JSON   | False          | `{"1":{"AdatId":"GID-6591e474-9f28-4e1c-8c7f-0f5a84dcbe5d"},"2":{"md5sum":"d5d5c48070766aeb078b50b111897e25"}}`                                                            | Maps SourceFileId integers to parent ADAT identifiers; blank if no source ADAT was used. In the case of source ADATs with no AdatId field, md5sum of input file is used. Schema: `{"<id>": {"AdatId": "<value>"}, ...}`                                                                                        |
| SOMAmerReferenceSource      | String | True           | `2025-04-10`                                                                                                                                                               | SOMAmer Reagent annotation reference identifier                                                                                                                                                                                                                                                                |
| FileCreatedDate             | Date   | True           | `2026-01-31T16:25:23Z`                                                                                                                                                     | Timestamp of ADAT file creation                                                                                                                                                                                                                                                                                |
| Title                       | String | False          | SS-26158660_v5.0_EDTAPlasma                                                                                                                                                | HRC_Plasma_Sample_Handling_v2`                                                                                                                                                                                                                                                                                 |
| StudyOrganism               | String | False          | `Human`                                                                                                                                                                    | Organism of study samples (e.g., `"Human"`, `"Mouse"`); pipe-separated unique values if mixed. Refer to SampleOrganism field for sample-specific info                                                                                                                                                          |
| StudyMatrix                 | String | False          | `Plasma`                                                                                                                                                                   | Biological fluid or tissue type of study samples (e.g., `"EDTA Plasma"`); pipe-separated unique values if mixed. Refer to SampleMatrix field for individual matrix data if mixed-matrix data.                                                                                                                  |
| ProcessSteps                | JSON   | True           | `{"ProcessStepsId":{"1":["Raw RFU","Hyb Normalization","medNormInt (SampleId)","Calibrate"],"2":["Raw RFU","Hyb Normalization","medNormInt (SampleId)","plateScale"]}}`    | The set of data processing steps applied to samples in this ADAT file. Because exact processing steps can differ between readouts, multiple processing routines are supported in the JSON object by linking sample ProcessStepsId field to key in JSON: `{"<id>": ["step1", "step2", ...], ...}`               |
| ReportConfig                | JSON   | Array-only     | `{"1":{"analysisSteps":[{"stepType":"hybNorm","referenceSource":"intraplate"},{"stepType":"plateScale","referenceSource":"Reference_Cal_230420_Plasma_V5.0.24UP_Lot2"}]}}` | Full data processing configuration for a given run. Samples in ADAT may have only undergone partially processing. Refer to ProcessSteps for specific stage of samples in this file. Use ReportConfigId sample field to map to analysis configuration: `{"<id>": {"analysisSteps": [...]}, ...}`; blank for NGS |
| PlateScaleScalar            | JSON   | False          | `{"PLT45241":{"PlatformSpecific":0.9117},"TS00000001":{"PlatformSpecific":0.72,"CrossPlatform":1.001}}`                                                                    | Scalar applied to all samples on a plate. Generated by the PlateScale processing step. Plate scale factors keyed by PlateId. Array: `{"<PlateId>": {"PlatformSpecific": <value>}}`. NGS: `{"<PlateId>": {"PlatformSpecific": <value>, "CrossPlatform": <value>}}`                                              |
| CalibrateTailPercent        | JSON   | False          | `{"PLT45241":{"PlatformSpecific":2.4},"TS00000001":{"PlatformSpecific":0.325,"CrossPlatform":0.0}}`                                                                        | Percent of calibration scale factors in tails of distribution. Tails are defined as scale factors +/- 0.4 or greater outside the median scale factor within each dilution group and for each plate.                                                                                                            |
| CalibrateTailPercentStatus  | JSON   | False          | `{"PLT45241":{"PlatformSpecific":"PASS"},"TS00000001":{"PlatformSpecific":"PASS","CrossPlatform":"PASS"}}`                                                                 | Per-plate QC check of CalibrateTailPercent values. `"PASS"` if within or `"WARNING"` per plate per calibration stage                                                                                                                                                                                           |
| QCCheckTailPercent          | JSON   | False          | `{"PLT45241":{"PlatformSpecific":4.8},"TS00000001":{"PlatformSpecific":1.855}}`                                                                                            | Percent of QC scale factors in tails per plate                                                                                                                                                                                                                                                                 |
| QCCheckTailPercentStatus    | JSON   | False          | `{"PLT45241":{"PlatformSpecific":"PASS"},"TS00000001":{"PlatformSpecific":"PASS"}}`                                                                                        | `"PASS"` or `"FAIL"` per plate. Value is `"FAIL"` if the QCCheckTailPercent threshold (> 0.15) is exceeded for a given plate.                                                                                                                                                                                  |
| PlateScaleStatus            | JSON   | False          | `{"PLT45241":"PASS"}`                                                                                                                                                      | `"PASS"` or `"FLAG"` per plate based on PlateScale scalar acceptance criteria.                                                                                                                                                                                                                                 |
| PlateSOMAmerNormReadsStatus | JSON   | NGS-only       | `{"TS00000001":"PASS"}`                                                                                                                                                    | `"PASS"` or `"WARNING"` per plate; WARNING if > 70% of blank samples have `SOMAmerNormReadsStatus = FLAG`                                                                                                                                                                                                      |


### 2.4 ^COL_DATA Section (SOMAmer Annotation)

The `COL_DATA` section lists the fields for SeqId-specific annotations in the data table. The section begins with the `^COL_DATA` token line. Directly below that line, two rows enumerate the field structure:

- Row 1 (`Name`): field names
- Row 2 (`Type`): field types (must comply with the types defined in Section 2.2)

All fields defined in `^COL_DATA` must be present. Note the absence of the "!" token before these field names. The order in which fields appear in `^COL_DATA` defines the column order used in the `^TABLE_BEGIN` data table. Fields may appear in any order, but the order must be consistent between the two sections. Full field definitions are in Section 2.6.1.

### 2.5 ^ROW_DATA Section (Sample Annotation)

The `ROW_DATA` section lists the fields for sample-specific annotations in the data table. The section begins with the `^ROW_DATA` token line. Directly below that line, two rows enumerate the field structure:

- Row 1 (`Name`): field names
- Row 2 (`Type`): field types (must comply with the types defined in Section 2.2)

All fields defined in `^ROW_DATA` must be present. Note the absence of the "!" token before these field names. The order in which fields appear in `^ROW_DATA` defines the column order used in the `^TABLE_BEGIN` data table. Fields may appear in any order, but the order must be consistent between the two sections. Full field definitions are in Section 2.6.2.

### 2.6 ^TABLE_BEGIN Section — Data Table

The data matrix begins with the `^TABLE_BEGIN` token line. The table has a combined structure: the left-hand columns contain per-sample metadata (matching the fields declared in `^ROW_DATA`), and the right-hand columns contain the RFU/count values for each SOMAmer (matching the analytes declared in `^COL_DATA`). See the layout diagram in Section 2.1.

#### 2.6.1 SOMAmer (Column) Fields

These fields are declared in `^COL_DATA` and define the analyte-level annotation. One column per SOMAmer Reagent appears in the data matrix.


| Field                                         | Type    | Value Required | Example Value                                    | Description                                                                                  |
| --------------------------------------------- | ------- | -------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| SeqId                                         | String  | True           | `10015-119`                                      | SOMAmer unique identifier (e.g., `"1234-56"`)                                                |
| Target                                        | String  | True           | `KCAB2`                                          | Short protein target name                                                                    |
| TargetFullName                                | String  | True           | `Voltage-gated potassium channel subunit beta-2` | Full protein construct description                                                           |
| Type                                          | String  | True           | `Protein`                                        | e.g., `"Protein"`, `"Hybridization Control"`, `"Spuriomer"`, `"Non-human Protein"`           |
| Organism                                      | String  | True           | `Human`                                          | Target organism (e.g., `"Human"`, `"non-Human"`)                                             |
| UniProt                                       | String  | False          | `Q13303`                                         | UniProt accession                                                                            |
| EntrezGeneId                                  | Integer | False          | `8514`                                           | Entrez Gene numeric ID                                                                       |
| EntrezGeneSymbol                              | String  | False          | `KCNAB2`                                         | Entrez Gene symbol                                                                           |
| HybControl                                    | String  | True           | `False`                                          | `"True"` if Type = Hybridization Control, otherwise `"False"`                                |
| Dilution                                      | String  | True           | `0.2`                                            | Sample dilution associated with SOMAmer mix group (fraction)                                 |
| PlatformSpecificCalibrate_PlateId_ScaleFactor | Decimal | True           | `1.0403`                                         | Platform-specific calibration scale factor per plate (NGS naming adopted for both platforms) |
| CrossPlatformCalibrate_PlateId_ScaleFactor    | Decimal | NGS-only       | `0.9433`                                         | Cross-platform calibration scale factor per plate                                            |
| QCRatio_PlateId                               | Decimal | True           | `0.9576`                                         | QC ratio per plate; simplified from `CalQcRatio` (array) and `QCCheck` (NGS)                 |
| DRCLevelNGS                                   | String  | NGS-only       | `1.0`                                            | Dynamic Range Compression level during assay                                                 |
| BlockListNGS                                  | String  | NGS-only       | `False`                                          | `"True"` if SOMAmer excluded from normalization; present in raw count ADATs only             |
| Ref.Array.PlateScale_CalibratorId             | Decimal | Array-only     | `3117.03`                                        | External RFU reference for array plate scale calculation                                     |
| Ref.Array.Calibrate_CalibratorId              | Decimal | Array-only     | `3117.03`                                        | External RFU reference for array calibration                                                 |
| Ref.Array.QCRatio_QCSampleId                  | Decimal | Array-only     | `1.02`                                           | External RFU reference for array QC sample                                                   |
| Ref.NGS.Bridging.params                       | Decimal | NGS-only       | `3117.03`                                        | NGS bridging reference RFU values (one field per bridging parameter set)                     |
| Ref.NGS.MedNormExt.Matrix                     | Decimal | NGS-only       | `3000.87`                                        | NGS external median normalization reference                                                  |
| Ref.NGS.QCCheck.Matrix                        | Decimal | NGS-only       | `1.02`                                           | NGS QC check reference                                                                       |
| Ref.MedNorm.Id                                | String  | False          | `REF001`                                         | Median normalization reference identifier; links to MedNormRefId in sample table             |


#### 2.6.2 Sample (Row) Fields

These fields are declared in `^ROW_DATA` and define per-sample metadata. One row per sample appears in the data matrix.


| Field                           | Type    | Value Required | Example Value                              | Description                                                                                                                                                                        |
| ------------------------------- | ------- | -------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SampleId                        | String  | True           | `B10_S804-5522`                            | Primary sample identifier; uniqueness not enforced by spec                                                                                                                         |
| SampleReadout                   | String  | True           | `Array`                                    | `"Array"` or `"NGS"`; determines assay platform readout for a given sample                                                                                                         |
| UniqueSampleKey                 | String  | False          | `GID-d1249d15-78e9-451a-b6b2-1ca28e27cde5` | GUID assigned post-merge for guaranteed cross-platform uniqueness. This value is assigned once and maintained in future ADAT files                                                 |
| SampleType                      | String  | True           | `Sample`                                   | e.g., `"Sample"`, `"Calibrator"`, `"QC"`, `"Buffer"`; values not altered during conversion                                                                                         |
| SourceFileId                    | String  | False          | `1`                                        | Maps to `SourceFile` JSON object in header; blank if no source merge                                                                                                               |
| ProcessStepsId                  | String  | True           | `1`                                        | Maps to `ProcessSteps` JSON object in header                                                                                                                                       |
| ReportConfigId                  | String  | Array-only     | `1`                                        | Maps to `ReportConfig` in header; blank for NGS-derived samples                                                                                                                    |
| SoftwareVersion                 | String  | True           | `Px (Build: 1120)`                         | Data generation software version, e.g., `"DPQ v2.1"`, `"Px 1030"`                                                                                                                  |
| SequencingRunId                 | String  | NGS-only       | `250916_A00255R_0644_AHFFKNDSXF`           | Sequencing run identifier                                                                                                                                                          |
| PlateId                         | String  | True           | `PLT45241`                                 | Plate identifier                                                                                                                                                                   |
| PlateRunDate                    | Date    | Array-only     | `2026-02-04`                               | Date plate was assayed; blank for NGS samples                                                                                                                                      |
| WellPosition                    | String  | True           | `B2`                                       | 96-well position; values not altered during conversion (array: `"B2"`, NGS: `"A-B02"`)                                                                                             |
| SlideId                         | String  | Array-only     | `258740110837`                             | Microarray slide identifier                                                                                                                                                        |
| Subarray                        | Integer | Array-only     | `3`                                        | Microarray subarray identifier                                                                                                                                                     |
| MatrixTubeBarcode               | String  | NGS-only       | `409256120`                                | Matrix tube barcode scanned during library prep                                                                                                                                    |
| ControlId                       | String  | False          | `SS-26158660`                              | Control lot ID; for array: populated with SampleId for QC/Buffer/Calibrator samples                                                                                                |
| BatchId                         | String  | False          | `FCR1_DVT1_01_PL`                          | User-provided batch identifier                                                                                                                                                     |
| InputType                       | String  | NGS-only       | `Plasma_Sample`                            | Sample type from manifest (e.g., `"Plasma_Calibrator"`, `"Plasma_QC"`)                                                                                                             |
| KitType                         | String  | NGS-only       | `Plasma`                                   | Biological matrix type from DPQ (converted from legacy `MatrixType`)                                                                                                               |
| SampleMatrix                    | String  | Array-only     | `EDTA Plasma`                              | Biological matrix descriptor (e.g., `"Plasma"`, `"Serum"`)                                                                                                                         |
| Project                         | String  | False          | `StudyA`                                   | Study/project identifier; array `StudyId` maps here; RMA values migrated here                                                                                                      |
| SubjectId                       | String  | False          | `SUBJ-001`                                 | Subject-level identifier (PascalCase from `SubjectID`)                                                                                                                             |
| SOMAmerBeadPlate                | String  | NGS-only       | `Lot2B`                                    | SOMAmer bead plate lot number                                                                                                                                                      |
| NGSPlateMasterMixLot            | String  | NGS-only       | `Lot7C`                                    | Probe plate lot number (renamed from `ProbePlate`)                                                                                                                                 |
| SOMAmerReads                    | Integer | NGS-only       | `14250000`                                 | Raw human SOMAmer read count (excluding controls)                                                                                                                                  |
| SOMAmerReadsStatus              | String  | NGS-only       | `PASS`                                     | `"PASS"` if >= 10M reads; `"FLAG"` otherwise (non-blank samples only)                                                                                                              |
| SOMAmerNormReads                | Decimal | NGS-only       | `13800000`                                 | Normalized SOMAmer read count at plate scale step                                                                                                                                  |
| SOMAmerNormReadsStatus          | String  | NGS-only       | `PASS`                                     | `"PASS"` if normalized reads <= 20M; `"FLAG"` otherwise (blank samples only)                                                                                                       |
| RefCorr                         | Decimal | NGS-only       | `0.984`                                    | Spearman correlation to plasma/serum reference                                                                                                                                     |
| EmpericalHybTemp                | Decimal | NGS-only       | `53.5`                                     | Empirical hybridization temperature from temperature controls                                                                                                                      |
| EmpiricalHybTempStatus          | String  | NGS-only       | `PASS`                                     | `"PASS"` if < 54.2; `"FLAG"` otherwise                                                                                                                                             |
| HybNormScaleFactor              | Decimal | True           | `1.024`                                    | Hybridization normalization scale factor; array: from `HybControlNormScale`, NGS: from `HybNorm_1_ScaleFactor`; see Appendix A.1                                                   |
| NormScale_DilutionGroup         | Decimal | Array-only     | `0.989`                                    | Array median normalization scale factor per dilution group, e.g., `NormScale_20`, `NormScale_0_005`, `NormScale_0_5`; see Appendix A.1                                             |
| MedNormInt_Dilution_ScaleFactor | Decimal | NGS-only       | `1.024`                                    | NGS internal median normalization scale factor per dilution group, e.g., `MedNormInt_0_2_ScaleFactor`, `MedNormInt_0_005_ScaleFactor`; see Appendix A.1                            |
| MedNormExt_Dilution_ScaleFactor | Decimal | NGS-only       | `0.990`                                    | NGS external normalization scale factor per dilution group                                                                                                                         |
| ANMLFractionUsed_DilutionGroup  | Decimal | Array-only     | `0.72`                                     | ANML fraction used per dilution group                                                                                                                                              |
| HybNormStatus                   | String  | True           | `PASS`                                     | `"PASS"` if hyb normalization scale factor within 0.4–2.5; see Appendix A.2                                                                                                        |
| MedNormIntStatus                | String  | NGS-only       | `PASS`                                     | `"PASS"` if all MedNormInt dilution scale factors within 0.4–2.5; see Appendix A.2                                                                                                 |
| MedNormExtStatus                | String  | NGS-only       | `PASS`                                     | `"PASS"` if all MedNormExt scale factors within 0.4–2.5                                                                                                                            |
| RowCheckStatus                  | String  | True           | `PASS`                                     | Composite QC result: `"PASS"`, `"FLAG"`, or `"LEAK"` (array only); for bridged array `LEAK` is preserved, for NGS a `FLAG` is set if any norm step fails; see Appendix A.2 and A.3 |
| CrossPlateMedNormIntScaleFactor | Decimal | NGS-only       | `0.993`                                    | Cross-platform internal median normalization scale factor; pass-through for NGS-only data; blank for array-only data                                                               |
| InstrumentType                  | String  | NGS-only       | `NovaSeq`                                  | Sequencing instrument type (e.g., `"NovaSeq"`); moved from NGS header; see Appendix A.4                                                                                            |
| Flowcell                        | String  | NGS-only       | `HFFKNDSXF`                                | Flowcell identifier; moved from NGS header; see Appendix A.4                                                                                                                       |
| YieldDemux                      | Integer | NGS-only       | `222843111190`                             | Total demultiplexed yield (base pairs); moved from NGS header; see Appendix A.4                                                                                                    |
| YieldQ30Demux                   | Integer | NGS-only       | `209705605492`                             | Q30 demultiplexed yield; moved from NGS header; see Appendix A.4                                                                                                                   |
| Q30WeightedMean                 | Decimal | NGS-only       | `0.9410`                                   | Q30 weighted mean quality score; moved from NGS header; see Appendix A.4                                                                                                           |


#### 2.6.3 RFU Data Matrix


| Aspect            | Specification                                                                         |
| ----------------- | ------------------------------------------------------------------------------------- |
| Row order         | Matches the order of samples in `^ROW_DATA`                                           |
| Column order      | Matches the order of analytes in `^COL_DATA`, keyed by SeqId                          |
| Value type        | Decimal                                                                               |
| Value content     | RFU (array) or normalized count (NGS); determined by per-sample `SampleReadout` field |
| Numeric precision | One decimal place precision for RFU                                                   |


---

## Section 3: Conversion from Legacy Formats to v2.0

This section is the definitive source for converter function requirements in OSS packages (Canopy/Python and SomaDataIO/R). It covers both field-by-field mapping and behavioral rules. "Removed" fields documented here had their rationale captured in the source mapping CSVs; that rationale is preserved in the Notes column.

### 3.1 General Conversion Rules

**Platform detection (for auto-detecting pre-v2.0 input files)**

- Array v1.x: `SlideId` and `Subarray` header fields are non-empty
- NGS: `SOMAmerReads` column is present and non-empty in the sample table

**AdatId lifecycle**

- A new GUID is generated when: (a) merging two or more ADATs, (b) converting between FileVersions, or (c) the user explicitly requests a new ID.
- AdatId is preserved on a simple read/write cycle with no structural modification.

**Multi-valued String field merging**
When merging two source ADATs, the following header fields are merged as pipe-delimited lists of unique values: `Title`, `StudyOrganism`, `StudyMatrix`, `SOMAmerReferenceSource`.

**SourceFile population**
When writing a converted or merged v2.0 ADAT, the `SourceFile` header field must be populated with a JSON object mapping integer IDs to the parent ADAT identifier(s). The schema is:

```json
{"1": {"AdatId": "<source_adat_id>"}, "2": {"AdatId": "<source_adat_id_2>"}}
```

Each sample row must have its `SourceFileId` set to the corresponding integer key.

**ProcessStepsId and ReportConfigId assignment**
During merge, if source ADATs have differing `ProcessSteps` or `ReportConfig` values, each distinct value is assigned a new integer ID. Samples are mapped to their original configuration via `ProcessStepsId` and `ReportConfigId`.

**FileCreatedDate**
`FileCreatedDate` is always set to the file write timestamp. During array v1.x conversion, if `PlateRunDate` is blank for array samples, populate it from the legacy `CreatedDate` header field value.

**AssayType determination**

- If all samples have `SampleReadout = "Array"`: `AssayType = "Array"`
- If all samples have `SampleReadout = "NGS"`: `AssayType = "NGS"`
- If both are present: `AssayType = "Mixed"`

### 3.2 Array (v1.x) to v2.0 Field Mapping

#### 3.2.1 Header Fields


| Legacy Array Field               | v2.0 Field                 | Transformation                                                                                                                 | Notes                                                   |
| -------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| Version                          | *(removed)*                | —                                                                                                                              | Value not mapped; `FileVersion` is set to `2.0` by spec |
| FileVersion                      | FileVersion                | Set to `"2.0"`                                                                                                                 | —                                                       |
| AdatId                           | AdatId                     | Generate new GUID; preserve old in `SourceFile`                                                                                | —                                                       |
| Title                            | Title                      | Pass through; pipe-separate on merge                                                                                           | Optional                                                |
| SourceFile                       | SourceFile                 | Populate from legacy AdatId; if no AdatId, use md5sum of source file                                                           | New field; generated during conversion                  |
| ProteinEffectiveDate             | SOMAmerReferenceSource     | Map date value to this field                                                                                                   | Parser uses most recent reference available             |
| AssayType                        | AssayType                  | Set to `"Array"` (or `"Mixed"` if merging with NGS)                                                                            | Proposal was `AssayReadout`; `AssayType` retained       |
| AssayVersion                     | AssayVersion               | Pass through (`v4`, `v5`, etc.)                                                                                                | —                                                       |
| MasterMixLot                     | *(removed from header)*    | —                                                                                                                              | Moved to sample table; no array equivalent defined      |
| CreatedDate                      | FileCreatedDate            | Set `FileCreatedDate` to write timestamp; map `CreatedDate` value to `PlateRunDate` in sample table if `PlateRunDate` is blank | —                                                       |
| StudyOrganism                    | StudyOrganism              | Pass through                                                                                                                   | —                                                       |
| StudyMatrix                      | StudyMatrix                | Pass through                                                                                                                   | —                                                       |
| CalibratorId                     | *(removed)*                | —                                                                                                                              | Point logic to `ControlId` in sample table              |
| CalibratorReference              | *(removed)*                | —                                                                                                                              | Refer users to `ReportConfig`                           |
| DerivedFrom                      | *(removed)*                | —                                                                                                                              | —                                                       |
| ExpDate                          | *(removed)*                | —                                                                                                                              | Value superseded by `PlateRunDate` in sample table      |
| ProcessSteps                     | ProcessSteps               | Reformat to JSON: `{"<id>": ["step1", ...]}`                                                                                   | Assign `ProcessStepsId` in sample table                 |
| ReportConfig                     | ReportConfig               | Reformat to JSON with `ReportConfigId` key                                                                                     | Assign `ReportConfigId` in sample table                 |
| NormalizationAlgorithm           | *(removed)*                | —                                                                                                                              | Deprecated; info in `ProcessSteps`                      |
| HybNormReference                 | *(removed)*                | —                                                                                                                              | Refer users to `ReportConfig`                           |
| MedNormReference                 | *(removed)*                | —                                                                                                                              | Refer users to `ReportConfig`                           |
| PlateScale_ReferenceSource       | *(removed)*                | —                                                                                                                              | Refer users to `ReportConfig`                           |
| PlateMedianCal_PlateId           | *(removed)*                | —                                                                                                                              | Not meaningful metric for v4+ array data                |
| PlateMedianTest_PlateId          | *(removed)*                | —                                                                                                                              | Dependent on `PlateMedianCal`; removed with it          |
| QcReferenceSource_SampleId       | *(removed)*                | —                                                                                                                              | Use `ReportConfig`                                      |
| CalPlateTailPercent_PlateId      | CalibrateTailPercent       | Consolidate per-plate values into JSON keyed by PlateId, using `"PlatformSpecific"` key                                        | —                                                       |
| CalPlateTailTest_PlateId         | CalibrateTailPercentStatus | Same consolidation into JSON                                                                                                   | —                                                       |
| PlateScale_Scalar_PlateId        | PlateScaleScalar           | Consolidate into JSON: `{"<PlateId>": {"PlatformSpecific": <value>}}`                                                          | —                                                       |
| PlateScale_PassFlag_PlateId      | PlateScaleStatus           | Consolidate into JSON keyed by PlateId                                                                                         | —                                                       |
| PlateTailPercent_PlateId         | QCCheckTailPercent         | Consolidate into JSON keyed by PlateId                                                                                         | —                                                       |
| PlateTailTest_PlateId            | QCCheckTailPercentStatus   | Consolidate into JSON keyed by PlateId                                                                                         | —                                                       |
| UseRestriction                   | UseRestriction             | Pass through                                                                                                                   | —                                                       |
| GeneratedBy                      | *(removed from header)*    | —                                                                                                                              | Value migrated to `SoftwareVersion` in sample table     |
| CreatedBy                        | *(removed)*                | —                                                                                                                              | —                                                       |
| LabLocation                      | *(removed)*                | —                                                                                                                              | —                                                       |
| Legal                            | *(removed)*                | —                                                                                                                              | —                                                       |
| PlateType                        | *(removed)*                | —                                                                                                                              | Not needed outside of SLGC services lab                 |
| IntraPlate/InterPlate CV metrics | *(removed)*                | —                                                                                                                              | Move to downstream ICM                                  |
| MedianS2B                        | *(removed)*                | —                                                                                                                              | Move to downstream ICM                                  |
| `!Checksum` line                 | *(not supported)*          | —                                                                                                                              | Use external file integrity hashing                     |


#### 3.2.2 SOMAmer Annotation (COL_DATA) Fields


| Legacy Array Field            | v2.0 Field                                    | Transformation                                                                                                                               | Notes                                                      |
| ----------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| SeqId                         | SeqId                                         | Pass through                                                                                                                                 | —                                                          |
| SeqIdVersion                  | *(removed)*                                   | —                                                                                                                                            | Deprecated                                                 |
| SomaId                        | *(removed)*                                   | —                                                                                                                                            | Deprecated                                                 |
| Target                        | Target                                        | Pass through                                                                                                                                 | Get from static annotation data                            |
| TargetFullName                | TargetFullName                                | Pass through                                                                                                                                 | Ensure PascalCase (no spaces)                              |
| Type                          | Type                                          | Pass through                                                                                                                                 | —                                                          |
| UniProt                       | UniProt                                       | Pass through                                                                                                                                 | —                                                          |
| EntrezGeneID                  | EntrezGeneId                                  | Pass through (rename to PascalCase)                                                                                                          | —                                                          |
| EntrezGeneSymbol              | EntrezGeneSymbol                              | Pass through                                                                                                                                 | —                                                          |
| *(not present)*               | HybControl                                    | Set `"True"` for `Type = "Hybridization Control"`, else `"False"`                                                                            | New field; generated during conversion                     |
| Organism                      | Organism                                      | Pass through                                                                                                                                 | —                                                          |
| Cal_PlateId                   | PlatformSpecificCalibrate_PlateId_ScaleFactor | Rename                                                                                                                                       | —                                                          |
| CalQcRatio_PlateId_QCSampleId | QCRatio_PlateId                               | Rename; drop QCSampleId suffix. If multiple QC IDs exist on a plate, throw exception (provide optional argument to specify preferred QC ID). | —                                                          |
| ColCheck                      | *(removed)*                                   | —                                                                                                                                            | FLAG values misunderstood by users                         |
| Dilution                      | Dilution                                      | Pass through                                                                                                                                 | —                                                          |
| PlateScale_Reference          | Ref.Array.PlateScale_CalibratorId             | Rename with `Ref.Array.` prefix                                                                                                              | —                                                          |
| CalReference                  | Ref.Array.Calibrate_CalibratorId              | Rename with `Ref.Array.` prefix                                                                                                              | —                                                          |
| QcReference_QCSampleId        | Ref.Array.QCRatio_QCSampleId                  | Rename with `Ref.Array.` prefix                                                                                                              | —                                                          |
| medNormRef_ReferenceRFU       | Ref.MedNorm.Id                                | Convert: append `.Id` suffix; associate ID to `MedNormRefId` in sample table                                                                 | —                                                          |
| medNormSMP_ReferenceRFU       | Ref.MedNorm.Id                                | Same as above                                                                                                                                | —                                                          |
| Units                         | *(removed)*                                   | —                                                                                                                                            | Use per-sample `SampleReadout` to determine platform/units |
| eLOD                          | *(removed)*                                   | —                                                                                                                                            | Downstream addition; not included in ADAT                  |


#### 3.2.3 Sample Annotation (ROW_DATA) Fields


| Legacy Array Field             | v2.0 Field                     | Transformation                                                                                                             | Notes                                                   |
| ------------------------------ | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| SampleId                       | SampleId                       | Pass through                                                                                                               | —                                                       |
| *(not present)*                | SampleReadout                  | Set to `"Array"` for all rows from an array source ADAT                                                                    | New field; generated during conversion                  |
| *(not present)*                | UniqueSampleKey                | Assign new GUID to each sample at merge time; preserve on subsequent read/write                                            | New field; once assigned, value is immutable            |
| SampleType                     | SampleType                     | Pass through; do not alter values                                                                                          | —                                                       |
| *(not present)*                | SourceFileId                   | Assign integer key matching sample to `SourceFile` header JSON entry                                                       | New field; generated during conversion                  |
| *(not present)*                | ProcessStepsId                 | Assign integer key matching sample to `ProcessSteps` header JSON entry                                                     | New field; generated during conversion                  |
| *(not present)*                | ReportConfigId                 | Assign integer key matching sample to `ReportConfig` header JSON entry                                                     | New field; generated during conversion                  |
| GeneratedBy (from header)      | SoftwareVersion                | Move from header; parse software and version                                                                               | —                                                       |
| PlateId                        | PlateId                        | Pass through                                                                                                               | —                                                       |
| PlateRunDate                   | PlateRunDate                   | Pass through; populate from `CreatedDate` if blank                                                                         | —                                                       |
| PlatePosition                  | WellPosition                   | Rename                                                                                                                     | Keep standard 96-well plate format; do not alter values |
| SlideId                        | SlideId                        | Pass through                                                                                                               | —                                                       |
| Subarray                       | Subarray                       | Pass through                                                                                                               | —                                                       |
| ExtIdentifier                  | *(removed)*                    | —                                                                                                                          | Replaced by `UniqueSampleKey`                           |
| SsfExtId                       | *(removed)*                    | —                                                                                                                          | Replaced by `UniqueSampleKey`                           |
| ScannerID                      | *(removed)*                    | —                                                                                                                          | Available from internal services; not needed in ADAT    |
| Barcode                        | *(removed)*                    | —                                                                                                                          | —                                                       |
| Barcode2d                      | MatrixTubeBarcode              | Rename                                                                                                                     | Use more explicit name                                  |
| SampleName                     | *(removed)*                    | —                                                                                                                          | —                                                       |
| SampleType                     | SampleType                     | Pass through                                                                                                               | —                                                       |
| SampleMatrix                   | SampleMatrix                   | Pass through                                                                                                               | —                                                       |
| ControlId                      | ControlId                      | Populate with `SampleId` for QC/Buffer/Calibrator `SampleType`                                                             | —                                                       |
| BatchId                        | BatchId                        | Pass through                                                                                                               | —                                                       |
| StudyId                        | Project                        | Rename                                                                                                                     | Adopt `Project` as unified field name                   |
| RMA                            | *(removed; value moved)*       | Move RMA value into `Project` field                                                                                        | —                                                       |
| SubjectID                      | SubjectId                      | Rename to PascalCase                                                                                                       | —                                                       |
| CLI                            | *(removed)*                    | —                                                                                                                          | Treat as external sample metadata                       |
| PercentDilution                | *(removed)*                    | —                                                                                                                          | Check with Platform on ProteinQuant field               |
| SampleNotes                    | *(removed)*                    | —                                                                                                                          | Not used; questionable utility                          |
| AliquotingNotes                | *(removed)*                    | —                                                                                                                          | Not used; questionable utility                          |
| AssayNotes                     | *(removed)*                    | —                                                                                                                          | Not used; questionable utility                          |
| SampleDescription              | *(removed)*                    | —                                                                                                                          | —                                                       |
| TimePoint                      | *(removed)*                    | —                                                                                                                          | —                                                       |
| SampleGroup                    | *(removed)*                    | —                                                                                                                          | —                                                       |
| SiteId                         | *(removed)*                    | —                                                                                                                          | —                                                       |
| HybControlNormScale            | HybNormScaleFactor             | Rename to unified field                                                                                                    | See Appendix A.1                                        |
| NormScale_DilutionGroup        | NormScale_DilutionGroup        | Pass through                                                                                                               | Platform-specific name retained; see Appendix A.1       |
| ANMLFractionUsed_DilutionGroup | ANMLFractionUsed_DilutionGroup | Pass through                                                                                                               | —                                                       |
| *(not present)*                | HybNormStatus                  | Derive from `HybControlNormScale`: `"PASS"` if 0.4–2.5; `"FLAG"` otherwise                                                 | New field; generated during conversion                  |
| *(not present)*                | MedNormIntStatus               | For Calibrator/Buffer with medNormInt: `"PASS"` if all dilution SFs in 0.4–2.5; else `"FLAG"`; blank for other SampleTypes | New field; generated during conversion                  |
| RowCheck                       | RowCheckStatus                 | Rename; preserve `"LEAK"` value if present                                                                                 | See Appendix A.2 and A.3                                |


### 3.3 NGS to v2.0 Field Mapping

#### 3.3.1 Header Fields


| Legacy NGS Field                              | v2.0 Field                  | Transformation                                                                          | Notes                                                         |
| --------------------------------------------- | --------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Version                                       | SoftwareVersion             | Move to sample table                                                                    | DPQ version                                                   |
| FileVersion                                   | FileVersion                 | Set to `"2.0"`                                                                          | —                                                             |
| AdatId                                        | AdatId                      | Generate new GUID; preserve old in `SourceFile`                                         | —                                                             |
| Title                                         | Title                       | Pass through; pipe-separate on merge                                                    | —                                                             |
| SourceFile                                    | SourceFile                  | Populate from legacy AdatId                                                             | New field                                                     |
| SOMAmerReferenceSource                        | SOMAmerReferenceSource      | Pass through (file path)                                                                | —                                                             |
| AssayType                                     | AssayType                   | Set to `"NGS"` (or `"Mixed"` if merging with array)                                     | —                                                             |
| AssayVersion                                  | AssayVersion                | Map: 6k→`v1`, 9k TMS→`v2`, 9k xTMS→`v3`, Calypso→`v4`                                   | —                                                             |
| RunId                                         | *(removed from header)*     | —                                                                                       | Moved to `SequencingRunId` in sample table                    |
| CreatedDate                                   | FileCreatedDate             | Set `FileCreatedDate` to write timestamp                                                | —                                                             |
| StudyOrganism                                 | StudyOrganism               | Pass through; stop hardcoding `"Human"`                                                 | —                                                             |
| StudyMatrix                                   | StudyMatrix                 | Pass through                                                                            | —                                                             |
| CalibratorId                                  | *(removed)*                 | —                                                                                       | Point logic to `ControlId` in sample table                    |
| ProcessSteps                                  | ProcessSteps                | Reformat to JSON with `ProcessStepsId` key                                              | —                                                             |
| ReportConfig                                  | *(not applicable)*          | Leave blank                                                                             | NGS ReportConfig resides in a separate YAML file, not in ADAT |
| InstrumentType                                | InstrumentType              | Move to sample table (NGS-only); replicate header value to all NGS sample rows          | See Appendix A.4                                              |
| Flowcell                                      | Flowcell                    | Move to sample table (NGS-only); replicate header value to all NGS sample rows          | See Appendix A.4                                              |
| YieldDemux                                    | YieldDemux                  | Move to sample table (NGS-only); replicate header value to all NGS sample rows          | See Appendix A.4                                              |
| YieldQ30Demux                                 | YieldQ30Demux               | Move to sample table (NGS-only); replicate header value to all NGS sample rows          | See Appendix A.4                                              |
| Q30WeightedMean                               | Q30WeightedMean             | Move to sample table (NGS-only); replicate header value to all NGS sample rows          | See Appendix A.4                                              |
| PlatformSpecificPlateScale_ScaleFactor        | PlateScaleScalar            | Consolidate into JSON: `{"<PlateId>": {"PlatformSpecific": <v>, "CrossPlatform": <v>}}` | —                                                             |
| CrossPlatformPlateScale_ScaleFactor           | PlateScaleScalar            | Merge into same JSON as above                                                           | —                                                             |
| PlatformSpecificCalibrateTailPercent          | CalibrateTailPercent        | Consolidate into JSON keyed by PlateId and stage                                        | —                                                             |
| CrossPlatformCalibrateTailPercent             | CalibrateTailPercent        | Merge into same JSON as above                                                           | —                                                             |
| PlatformSpecificCalibrateTailPercent_PassFlag | CalibrateTailPercentStatus  | Consolidate into JSON                                                                   | —                                                             |
| QCCheckTailPercent                            | QCCheckTailPercent          | Consolidate into JSON keyed by PlateId                                                  | —                                                             |
| QCCheckTailPercent_PassFlag                   | QCCheckTailPercentStatus    | Consolidate into JSON keyed by PlateId                                                  | —                                                             |
| PlateSOMAmerNormReads_PassFlag                | PlateSOMAmerNormReadsStatus | Rename (PassFlag → Status); consolidate into JSON                                       | —                                                             |
| IntraPlate/InterPlate CV metrics              | *(removed)*                 | —                                                                                       | Move to downstream ICM                                        |
| MedianS2B                                     | *(removed)*                 | —                                                                                       | Move to downstream ICM                                        |
| UseRestriction                                | UseRestriction              | Pass through                                                                            | —                                                             |


#### 3.3.2 SOMAmer Annotation (COL_DATA) Fields


| Legacy NGS Field                              | v2.0 Field                                    | Transformation                               | Notes                                                                   |
| --------------------------------------------- | --------------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------- |
| SeqId                                         | SeqId                                         | Pass through                                 | —                                                                       |
| SomaId                                        | *(removed)*                                   | —                                            | Deprecated                                                              |
| Target                                        | Target                                        | Pass through                                 | —                                                                       |
| Target Full Name                              | TargetFullName                                | Rename (remove space)                        | PascalCase                                                              |
| Type                                          | Type                                          | Pass through                                 | —                                                                       |
| UniProt ID                                    | UniProt                                       | Rename (remove `" ID"`)                      | —                                                                       |
| Entrez Gene ID                                | EntrezGeneId                                  | Rename to PascalCase                         | —                                                                       |
| Entrez Gene Symbol                            | EntrezGeneSymbol                              | Rename to PascalCase                         | —                                                                       |
| HybControl                                    | HybControl                                    | Pass through                                 | —                                                                       |
| Organism                                      | Organism                                      | Pass through                                 | —                                                                       |
| DRC_Level                                     | DRCLevelNGS                                   | Rename; add `_NGS` suffix                    | NGS-specific field                                                      |
| PlatformSpecificCalibrate_PlateId_ScaleFactor | PlatformSpecificCalibrate_PlateId_ScaleFactor | Pass through                                 | —                                                                       |
| CrossPlatformCalibrate_PlateId_ScaleFactor    | CrossPlatformCalibrate_PlateId_ScaleFactor    | Pass through                                 | —                                                                       |
| QCCheck_PlateId_ScaleFactor                   | QCRatio_PlateId                               | Rename                                       | —                                                                       |
| QCCheck_PlateId_PassFlag                      | *(removed)*                                   | —                                            | FLAG values misunderstood by users                                      |
| Dilution                                      | Dilution                                      | Pass through                                 | —                                                                       |
| BlockList                                     | BlockListNGS                                  | Rename; add `_NGS` suffix                    | NGS-specific; present only in raw count ADATs                           |
| Ref.* references                              | Ref.NGS.                                      | Add `Ref.NGS.` prefix if not already present | e.g., `Ref.NGS.Bridging.`*, `Ref.NGS.MedNormExt.`*, `Ref.NGS.QCCheck.*` |
| Units                                         | *(removed)*                                   | —                                            | Use per-sample `SampleReadout`                                          |
| LoD.Plasma                                    | *(removed)*                                   | —                                            | Downstream addition; not in ADAT                                        |
| LoD.Serum                                     | *(removed)*                                   | —                                            | Downstream addition; not in ADAT                                        |


#### 3.3.3 Sample Annotation (ROW_DATA) Fields


| Legacy NGS Field                 | v2.0 Field                      | Transformation                                                                  | Notes                                        |
| -------------------------------- | ------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------- |
| SampleID                         | SampleId                        | Rename to PascalCase                                                            | —                                            |
| *(not present)*                  | SampleReadout                   | Set to `"NGS"` for all rows from an NGS source ADAT                             | New field; generated during conversion       |
| *(not present)*                  | UniqueSampleKey                 | Assign new GUID to each sample at merge time; preserve on subsequent read/write | New field; once assigned, value is immutable |
| SampleType                       | SampleType                      | Pass through; do not alter values                                               | —                                            |
| *(not present)*                  | SourceFileId                    | Assign integer key matching sample to `SourceFile` header JSON entry            | New field; generated during conversion       |
| *(not present)*                  | ProcessStepsId                  | Assign integer key matching sample to `ProcessSteps` header JSON entry          | New field; generated during conversion       |
| ReportConfigId                   | ReportConfigId                  | Leave blank (NGS has no ReportConfig)                                           | —                                            |
| Version (from header)            | SoftwareVersion                 | Move from header                                                                | e.g., `"DPQ v2.1"`                           |
| SequencingRunID                  | SequencingRunId                 | Rename to PascalCase                                                            | Moved from header                            |
| PlateId                          | PlateId                         | Pass through                                                                    | —                                            |
| PlateRunDate                     | PlateRunDate                    | Leave blank for NGS                                                             | —                                            |
| WellPosition                     | WellPosition                    | Pass through; do not alter values                                               | —                                            |
| MatrixTubeBarcode                | MatrixTubeBarcode               | Pass through                                                                    | —                                            |
| ControlD                         | ControlId                       | Rename to PascalCase                                                            | —                                            |
| BatchID                          | BatchId                         | Rename to PascalCase                                                            | —                                            |
| InputType                        | InputType                       | Pass through                                                                    | —                                            |
| MatrixType / KitType             | KitType                         | Rename `MatrixType` to `KitType` if legacy field present; keep `KitType` as-is  | —                                            |
| ProbePlate                       | NGSPlateMasterMixLot            | Rename                                                                          | —                                            |
| SOMAmerBeadPlate                 | SOMAmerBeadPlate                | Pass through                                                                    | —                                            |
| Project (Optional)               | Project                         | Pass through                                                                    | —                                            |
| SOMAmerReads                     | SOMAmerReads                    | Pass through                                                                    | —                                            |
| SOMAmerReads_PassFlag            | SOMAmerReadsStatus              | Rename (`_PassFlag` → `Status`)                                                 | —                                            |
| SOMAmerNormReads                 | SOMAmerNormReads                | Pass through                                                                    | —                                            |
| SOMAmerNormReads_PassFlag        | SOMAmerNormReadsStatus          | Rename (`_PassFlag` → `Status`)                                                 | —                                            |
| RefCorr                          | RefCorr                         | Pass through                                                                    | —                                            |
| EmpericalHybTemp                 | EmpericalHybTemp                | Pass through (retain legacy spelling)                                           | —                                            |
| EmpiricalHybTemp_PassFlag        | EmpiricalHybTempStatus          | Rename (`_PassFlag` → `Status`)                                                 | —                                            |
| HybNorm_1_ScaleFactor            | HybNormScaleFactor              | Rename to unified field                                                         | See Appendix A.1                             |
| MedNormInt_Dilution_ScaleFactor  | MedNormInt_Dilution_ScaleFactor | Pass through; replace `-` in dilution suffix with `_` for R compatibility       | See Appendix A.1                             |
| MedNormExt_Dilution_ScaleFactor  | MedNormExt_Dilution_ScaleFactor | Pass through                                                                    | TBD alignment                                |
| CrossPlateMedNormInt_ScaleFactor | CrossPlateMedNormIntScaleFactor | Rename to PascalCase; pass through                                              | NGS-only; blank for array; see Section 3.4   |
| HybNorm_PassFlag                 | HybNormStatus                   | Rename (`_PassFlag` → `Status`)                                                 | See Appendix A.2                             |
| MedNormInt_PassFlag              | MedNormIntStatus                | Rename (`_PassFlag` → `Status`)                                                 | See Appendix A.2                             |
| MedNormExt_PassFlag              | MedNormExtStatus                | Rename (`_PassFlag` → `Status`)                                                 | —                                            |
| RowCheck_PassFlag                | RowCheckStatus                  | Rename (`_PassFlag` → `Status`)                                                 | See Appendix A.3                             |
| InstrumentType (from header)     | InstrumentType                  | Move from header; replicate to all NGS sample rows                              | See Appendix A.4                             |
| Flowcell (from header)           | Flowcell                        | Move from header; replicate to all NGS sample rows                              | See Appendix A.4                             |
| YieldDemux (from header)         | YieldDemux                      | Move from header; replicate to all NGS sample rows                              | See Appendix A.4                             |
| YieldQ30Demux (from header)      | YieldQ30Demux                   | Move from header; replicate to all NGS sample rows                              | See Appendix A.4                             |
| Q30WeightedMean (from header)    | Q30WeightedMean                 | Move from header; replicate to all NGS sample rows                              | See Appendix A.4                             |


### 3.4 Mixed (Merge) Conversion Rules

These rules apply when producing a `Mixed` AssayType ADAT by combining an array source and an NGS source.

- **AdatId:** Generate a new GUID.
- **SourceFile:** Populate with both source file identifiers (assigned integer keys `"1"` and `"2"`).
- **ProcessSteps / ReportConfig:** Each distinct set retains its own ID; samples map to their original configuration via `ProcessStepsId` / `ReportConfigId`.
- **StudyOrganism / StudyMatrix / Title:** Merge as pipe-delimited lists of unique values.
- **Header QC fields:** Plate-keyed JSON fields (`PlateScaleScalar`, `CalibrateTailPercent`, etc.) are merged by combining all PlateId keys from both sources into a single JSON object.
- **MedNorm compatibility checks (pre-conditions for merge):** Before merging source ADATs into a `Mixed` output, the converter must validate normalization compatibility. The specific checks depend on the combination type:
  - *Combining NGS + Array data:* All three of the following must be satisfied; raise an exception if any check fails:
    1. Array `ProcessSteps` must end with `"CrossPlatformPlateScale"`, `"CrossPlatformCalibrate"`, `"MedNormExt"` as the last three steps.
    2. NGS `ProcessSteps` must be: `"Raw"`, `"HybNorm"`, `"MedNormInt"`, `"PlatformSpecificPlateScale"`, `"PlatformSpecificCalibrate"`, `"CrossPlatformPlateScale"`, `"CrossPlatformCalibrate"`, `"MedNormExt"`.
    3. `Ref.MedNormExt.<Matrix>` RFU reference values must be identical across the array and NGS source files.
  - *Combining NGS-only data:* `ProcessSteps` must be identical across all source ADATs. If external MedNorm has been performed, `Ref.MedNormExt.<Matrix>` RFU reference values must match across all source files. Raise an exception if `CrossPlateMedNormInt`-only normalization is detected without a corresponding `MedNormExt` step.
  - *Combining Array-only data:* Apply existing array-only parser merge logic.
  - *Format conversion only (no merge):* `CrossPlateMedNormIntScaleFactor` is a pass-through; no MedNorm compatibility check is required.

---


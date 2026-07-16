"""Validate that an ADAT file conforms to the v2.0 specification.

Prints a categorised report of PASS / FAIL / WARN checks and exits with
code 0 if all checks pass, 1 if any check FAILs, 2 if the file cannot
be loaded at all.

Usage:
    poetry run python .cursor/skills/validate-adat-v2/scripts/validate_adat_v2.py <path.adat>
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any

warnings.filterwarnings('ignore')

import somadata
from somadata.adat import Adat

# ---------------------------------------------------------------------------
# v2.0 spec constants
# ---------------------------------------------------------------------------

V2_FILE_VERSION = '2.0'

# All header fields defined in spec Section 2.3, mapped to their type.
V2_HEADER_FIELDS: dict[str, str] = {
    'FileVersion': 'String',
    'AdatId': 'String',
    'AssayType': 'String',
    'AssayVersion': 'String',
    'UseRestriction': 'String',
    'SourceFile': 'JSON',
    'SOMAmerReferenceSource': 'String',
    'FileCreatedDate': 'Date',
    'Title': 'String',
    'StudyOrganism': 'String',
    'StudyMatrix': 'String',
    'ProcessSteps': 'JSON',
    'ReportConfig': 'JSON',
    'PlateScaleScalar': 'JSON',
    'CalibrateTailPercent': 'JSON',
    'CalibrateTailPercentStatus': 'JSON',
    'QCCheckTailPercent': 'JSON',
    'QCCheckTailPercentStatus': 'JSON',
    'PlateScaleStatus': 'JSON',
    'PlateSOMAmerNormReadsStatus': 'JSON',
}

# Required (must be non-empty) for all v2.0 ADATs.
V2_HEADER_REQUIRED: set[str] = {
    'FileVersion',
    'AdatId',
    'AssayType',
    'AssayVersion',
    'UseRestriction',
    'SOMAmerReferenceSource',
    'FileCreatedDate',
    'ProcessSteps',
}

# Required col metadata fields (Section 2.6.1, Value Required = True or not NGS/Array-only).
V2_COL_REQUIRED: set[str] = {
    'SeqId',
    'Target',
    'TargetFullName',
    'Type',
    'Organism',
    'HybControl',
    'Dilution',
}

# Col fields that must NOT appear (removed in v2.0).
V2_COL_REMOVED: set[str] = {
    'SeqIdVersion',
    'SomaId',
    'ColCheck',
    'Units',
    'eLOD',
}

# Required row metadata fields (Value Required = True for all ADATs).
V2_ROW_REQUIRED: set[str] = {
    'SampleId',
    'SampleReadout',
    'SampleType',
    'ProcessStepsId',
    'SoftwareVersion',
    'PlateId',
    'WellPosition',
    'HybNormScaleFactor',
    'HybNormStatus',
    'RowCheckStatus',
}

# Row fields that must NOT appear (removed or renamed in v2.0).
V2_ROW_REMOVED: set[str] = {
    'PlatePosition',
    'HybControlNormScale',
    'RowCheck',
    'StudyId',
    'SubjectID',
    'ExtIdentifier',
    'SsfExtId',
    'ScannerID',
    'Barcode',
    'SampleName',
    'SampleNotes',
    'AliquotingNotes',
    'AssayNotes',
    'SampleDescription',
    'TimePoint',
    'SampleGroup',
    'SiteId',
    'PercentDilution',
    'CLI',
    'RMA',
}

# Header fields that must NOT appear (removed in v2.0 or pre-v2.0 only).
V2_HEADER_REMOVED: set[str] = {
    '!Version',
    'Version',
    'CreatedDate',
    'CalibratorId',
    'CalibratorReference',
    'DerivedFrom',
    'ExpDate',
    'NormalizationAlgorithm',
    'HybNormReference',
    'MedNormReference',
    'PlateScale_ReferenceSource',
    'MasterMixLot',
    'GeneratedBy',
    'CreatedBy',
    'LabLocation',
    'Legal',
    'PlateType',
    'RunId',
    '!Checksum',
}

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$')
_GUID_RE = re.compile(r'^GID-[0-9a-f\-]{32,}$', re.IGNORECASE)

# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

PASS = 'PASS'
FAIL = 'FAIL'
WARN = 'WARN'
INFO = 'INFO'


@dataclass
class CheckResult:
    status: str  # PASS | FAIL | WARN | INFO
    name: str
    detail: str = ''


@dataclass
class Report:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, status: str, name: str, detail: str = '') -> None:
        self.checks.append(CheckResult(status, name, detail))

    def pass_(self, name: str, detail: str = '') -> None:
        self.add(PASS, name, detail)

    def fail(self, name: str, detail: str) -> None:
        self.add(FAIL, name, detail)

    def warn(self, name: str, detail: str) -> None:
        self.add(WARN, name, detail)

    def info(self, name: str, detail: str) -> None:
        self.add(INFO, name, detail)

    @property
    def failed(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == FAIL]

    @property
    def warned(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == WARN]


# ---------------------------------------------------------------------------
# Individual check groups
# ---------------------------------------------------------------------------


def check_file_version(adat: Adat, r: Report) -> bool:
    """Return True if FileVersion == '2.0' (gates all other checks)."""
    hm = adat.header_metadata
    fv = hm.get('FileVersion') or hm.get('!FileVersion', '')
    if fv == V2_FILE_VERSION:
        r.pass_('FileVersion', f'FileVersion = {fv!r}')
        return True
    r.fail(
        'FileVersion',
        f'FileVersion = {fv!r}; expected {V2_FILE_VERSION!r}. '
        'This file does not appear to be a v2.0 ADAT.',
    )
    return False


def check_header_fields(adat: Adat, r: Report, assay_type: str) -> None:
    hm = adat.header_metadata

    # 1. No removed / pre-v2 fields present
    present_removed = [k for k in V2_HEADER_REMOVED if k in hm]
    if present_removed:
        r.fail('Header.NoRemovedFields', f'Removed pre-v2 fields found: {present_removed}')
    else:
        r.pass_('Header.NoRemovedFields')

    # 2. No extra fields beyond the closed v2 set
    extra = [k for k in hm if k not in V2_HEADER_FIELDS]
    if extra:
        r.fail('Header.ClosedFieldSet', f'Extra fields not in v2 spec: {extra}')
    else:
        r.pass_('Header.ClosedFieldSet')

    # 3. All required fields present and non-empty
    missing_required: list[str] = []
    empty_required: list[str] = []
    for fname in V2_HEADER_REQUIRED:
        if fname not in hm:
            missing_required.append(fname)
        elif not str(hm[fname]).strip():
            empty_required.append(fname)
    if missing_required:
        r.fail('Header.RequiredFieldsPresent', f'Missing: {missing_required}')
    elif empty_required:
        r.fail('Header.RequiredFieldsNonEmpty', f'Empty: {empty_required}')
    else:
        r.pass_('Header.RequiredFields')

    # 4. AssayType value
    at = hm.get('AssayType', '')
    if at in ('Array', 'NGS', 'Mixed'):
        r.pass_('Header.AssayType', f'AssayType = {at!r}')
    else:
        r.fail('Header.AssayType', f'AssayType = {at!r}; must be "Array", "NGS", or "Mixed"')

    # 5. AdatId is a GUID
    adat_id = str(hm.get('AdatId', ''))
    if _GUID_RE.match(adat_id):
        r.pass_('Header.AdatId', f'AdatId = {adat_id!r}')
    else:
        r.warn('Header.AdatId', f'AdatId {adat_id!r} does not match GID-<uuid> pattern')

    # 6. FileCreatedDate format
    fcd = str(hm.get('FileCreatedDate', ''))
    if _DATE_RE.match(fcd):
        r.pass_('Header.FileCreatedDate', f'FileCreatedDate = {fcd!r}')
    else:
        r.fail('Header.FileCreatedDate', f'FileCreatedDate {fcd!r} not ISO 8601 (YYYY-MM-DD[Thh:mm:ssZ])')

    # 7. JSON fields are valid JSON (when non-empty)
    json_fields = [k for k, t in V2_HEADER_FIELDS.items() if t == 'JSON']
    for jf in json_fields:
        val = hm.get(jf, '')
        if not val:
            continue
        if isinstance(val, (dict, list)):
            r.pass_(f'Header.JSON.{jf}', 'already parsed as dict/list')
            continue
        try:
            json.loads(str(val))
            r.pass_(f'Header.JSON.{jf}')
        except json.JSONDecodeError as exc:
            r.fail(f'Header.JSON.{jf}', f'Invalid JSON: {exc}')

    # 8. ProcessSteps is a dict with integer-string keys
    ps = hm.get('ProcessSteps')
    if isinstance(ps, dict):
        keys_ok = all(str(k).isdigit() for k in ps.keys())
        vals_ok = all(isinstance(v, list) for v in ps.values())
        if keys_ok and vals_ok:
            r.pass_('Header.ProcessSteps.Schema')
        else:
            r.fail(
                'Header.ProcessSteps.Schema',
                'ProcessSteps must be {"<int>": ["step1", ...], ...}',
            )
    elif ps:
        r.fail('Header.ProcessSteps.Schema', f'ProcessSteps is not a dict (got {type(ps).__name__})')

    # 9. ReportConfig is blank for NGS-only files
    rc = hm.get('ReportConfig', '')
    if assay_type == 'NGS' and rc:
        r.fail('Header.ReportConfig.NGSBlank', 'ReportConfig must be blank for NGS-only ADATs')
    elif assay_type == 'NGS':
        r.pass_('Header.ReportConfig.NGSBlank')

    # 10. No '!' prefix on any field names
    bang_fields = [k for k in hm if k.startswith('!')]
    if bang_fields:
        r.fail('Header.NoBangPrefix', f'Fields with "!" prefix (pre-v2 convention): {bang_fields}')
    else:
        r.pass_('Header.NoBangPrefix')


def check_col_fields(adat: Adat, r: Report) -> None:
    col_names: list[str] = list(adat.columns.names)

    # 1. Required COL fields present
    missing = [f for f in V2_COL_REQUIRED if f not in col_names]
    if missing:
        r.fail('ColData.RequiredFields', f'Missing required COL_DATA fields: {missing}')
    else:
        r.pass_('ColData.RequiredFields')

    # 2. Removed fields absent
    present_removed = [f for f in V2_COL_REMOVED if f in col_names]
    if present_removed:
        r.fail('ColData.NoRemovedFields', f'Removed fields still present: {present_removed}')
    else:
        r.pass_('ColData.NoRemovedFields')

    # 3. No '!' prefix on any col field names
    bang = [f for f in col_names if f.startswith('!')]
    if bang:
        r.fail('ColData.NoBangPrefix', f'COL_DATA fields with "!" prefix: {bang}')
    else:
        r.pass_('ColData.NoBangPrefix')

    # 4. HybControl values are "True"/"False" strings
    if 'HybControl' in col_names:
        vals = adat.columns.get_level_values('HybControl').unique().tolist()
        invalid = [v for v in vals if str(v) not in ('True', 'False', '')]
        if invalid:
            r.fail('ColData.HybControl.Values', f'HybControl has unexpected values: {invalid}')
        else:
            r.pass_('ColData.HybControl.Values')

    # 5. PlatformSpecificCalibrate fields use correct naming convention
    ps_cal_cols = [c for c in col_names if c.startswith('PlatformSpecificCalibrate_')]
    if ps_cal_cols:
        r.pass_('ColData.PlatformSpecificCalibrate', f'{len(ps_cal_cols)} field(s) found')
    else:
        r.warn('ColData.PlatformSpecificCalibrate', 'No PlatformSpecificCalibrate_* columns found')

    # 6. Ref.Array.* or Ref.NGS.* reference columns (at least one expected)
    ref_cols = [c for c in col_names if c.startswith('Ref.')]
    if ref_cols:
        r.pass_('ColData.RefColumns', f'{len(ref_cols)} Ref.* column(s): {ref_cols[:5]}{"..." if len(ref_cols) > 5 else ""}')
    else:
        r.warn('ColData.RefColumns', 'No Ref.* reference columns found')

    # 7. No legacy 'Cal_<PlateId>' fields (should have been renamed)
    legacy_cal = [c for c in col_names if re.match(r'^Cal_', c)]
    if legacy_cal:
        r.fail('ColData.NoLegacyCal', f'Legacy Cal_<PlateId> fields (should be renamed): {legacy_cal}')
    else:
        r.pass_('ColData.NoLegacyCal')


def check_row_fields(adat: Adat, r: Report, assay_type: str) -> None:
    row_names: list[str] = list(adat.index.names)

    # 1. Required ROW fields present
    missing = [f for f in V2_ROW_REQUIRED if f not in row_names]
    if missing:
        r.fail('RowData.RequiredFields', f'Missing required ROW_DATA fields: {missing}')
    else:
        r.pass_('RowData.RequiredFields')

    # 2. Removed fields absent
    present_removed = [f for f in V2_ROW_REMOVED if f in row_names]
    if present_removed:
        r.fail('RowData.NoRemovedFields', f'Removed fields still present: {present_removed}')
    else:
        r.pass_('RowData.NoRemovedFields')

    # 3. No '!' prefix
    bang = [f for f in row_names if f.startswith('!')]
    if bang:
        r.fail('RowData.NoBangPrefix', f'ROW_DATA fields with "!" prefix: {bang}')
    else:
        r.pass_('RowData.NoBangPrefix')

    # 4. SampleReadout values
    if 'SampleReadout' in row_names:
        vals = adat.index.get_level_values('SampleReadout').unique().tolist()
        invalid = [v for v in vals if v not in ('Array', 'NGS', '')]
        if invalid:
            r.fail('RowData.SampleReadout.Values', f'Invalid SampleReadout values: {invalid}')
        else:
            r.pass_('RowData.SampleReadout.Values', f'Values: {vals}')
        # AssayType consistency
        has_array = 'Array' in vals
        has_ngs = 'NGS' in vals
        expected_at = 'Mixed' if (has_array and has_ngs) else ('Array' if has_array else 'NGS')
        if assay_type != expected_at:
            r.fail(
                'RowData.SampleReadout.AssayTypeConsistency',
                f'AssayType={assay_type!r} but SampleReadout values imply {expected_at!r}',
            )
        else:
            r.pass_('RowData.SampleReadout.AssayTypeConsistency')

    # 5. UniqueSampleKey — if present, values should be GUIDs and unique
    if 'UniqueSampleKey' in row_names:
        keys = list(adat.index.get_level_values('UniqueSampleKey'))
        non_blank = [k for k in keys if k and str(k) != 'nan']
        if non_blank:
            bad_guids = [k for k in non_blank if not _GUID_RE.match(str(k))]
            if bad_guids:
                r.warn(
                    'RowData.UniqueSampleKey.GuidFormat',
                    f'{len(bad_guids)} key(s) not in GID-<uuid> format: {bad_guids[:3]}',
                )
            else:
                r.pass_('RowData.UniqueSampleKey.GuidFormat')
            if len(set(non_blank)) != len(non_blank):
                r.fail('RowData.UniqueSampleKey.Unique', 'UniqueSampleKey values are not all unique')
            else:
                r.pass_('RowData.UniqueSampleKey.Unique')
    else:
        r.warn('RowData.UniqueSampleKey', 'UniqueSampleKey field not present')

    # 6. ProcessStepsId links to header ProcessSteps keys
    hm = adat.header_metadata
    ps = hm.get('ProcessSteps')
    if isinstance(ps, dict) and 'ProcessStepsId' in row_names:
        sample_ids = set(str(v) for v in adat.index.get_level_values('ProcessStepsId'))
        missing_keys = sample_ids - set(ps.keys())
        if missing_keys:
            r.fail(
                'RowData.ProcessStepsId.KeysMatch',
                f'ProcessStepsId values {missing_keys} not found in header ProcessSteps keys',
            )
        else:
            r.pass_('RowData.ProcessStepsId.KeysMatch')

    # 7. RowCheckStatus values
    if 'RowCheckStatus' in row_names:
        vals = adat.index.get_level_values('RowCheckStatus').unique().tolist()
        invalid = [v for v in vals if str(v) not in ('PASS', 'FLAG', 'LEAK', '')]
        if invalid:
            r.fail('RowData.RowCheckStatus.Values', f'Invalid RowCheckStatus values: {invalid}')
        else:
            r.pass_('RowData.RowCheckStatus.Values', f'Values: {vals}')

    # 8. HybNormStatus values
    if 'HybNormStatus' in row_names:
        vals = adat.index.get_level_values('HybNormStatus').unique().tolist()
        invalid = [v for v in vals if str(v) not in ('PASS', 'FLAG', '')]
        if invalid:
            r.fail('RowData.HybNormStatus.Values', f'Invalid HybNormStatus values: {invalid}')
        else:
            r.pass_('RowData.HybNormStatus.Values')

    # 9. PlateRunDate blank for NGS rows
    if assay_type in ('NGS', 'Mixed') and 'PlateRunDate' in row_names and 'SampleReadout' in row_names:
        readouts = list(adat.index.get_level_values('SampleReadout'))
        plate_run_dates = list(adat.index.get_level_values('PlateRunDate'))
        ngs_with_date = [
            d for r_, d in zip(readouts, plate_run_dates)
            if r_ == 'NGS' and str(d).strip() not in ('', 'nan', 'NaN')
        ]
        if ngs_with_date:
            r.warn(
                'RowData.PlateRunDate.NGSBlank',
                f'{len(ngs_with_date)} NGS row(s) have non-blank PlateRunDate (should be blank)',
            )
        else:
            r.pass_('RowData.PlateRunDate.NGSBlank')

    # 10. NGS-specific fields: check presence for Mixed/NGS
    if assay_type in ('NGS', 'Mixed'):
        ngs_expected = ['SequencingRunId', 'SOMAmerReads', 'SOMAmerReadsStatus']
        missing_ngs = [f for f in ngs_expected if f not in row_names]
        if missing_ngs:
            r.fail('RowData.NGSSpecificFields', f'Expected NGS row fields missing: {missing_ngs}')
        else:
            r.pass_('RowData.NGSSpecificFields', f'NGS fields present: {ngs_expected}')


def check_data_matrix(adat: Adat, r: Report) -> None:
    import numpy as np

    n_samples, n_analytes = adat.shape
    r.info('DataMatrix.Shape', f'{n_samples} samples × {n_analytes} analytes')

    vals = adat.to_numpy().astype(float)

    # Non-NaN values should be non-negative (RFU / read counts are positive)
    non_nan = vals[~np.isnan(vals)]
    if len(non_nan) == 0:
        r.warn('DataMatrix.Values', 'All RFU values are NaN — check conversion')
        return

    n_neg = int((non_nan < 0).sum())
    if n_neg:
        r.warn('DataMatrix.NonNegative', f'{n_neg} negative RFU/count values found')
    else:
        r.pass_('DataMatrix.NonNegative')

    nan_pct = 100.0 * np.isnan(vals).sum() / vals.size
    r.info('DataMatrix.NaNPercent', f'{nan_pct:.1f}% of cells are NaN (expected for SeqId union)')


# ---------------------------------------------------------------------------
# Main validation entry point
# ---------------------------------------------------------------------------


def validate(path: str) -> int:
    """Run all v2.0 checks; return exit code (0=all pass, 1=failures, 2=load error)."""
    print(f'=== ADAT v2.0 VALIDATION: {path} ===\n')

    try:
        adat = somadata.read_adat(path)
    except Exception as exc:
        print(f'[FAIL] Could not load ADAT: {exc}')
        return 2

    hm = adat.header_metadata
    r = Report()

    # Gate: must be v2.0
    is_v2 = check_file_version(adat, r)

    assay_type = str(hm.get('AssayType', ''))

    if is_v2:
        check_header_fields(adat, r, assay_type)
        check_col_fields(adat, r)
        check_row_fields(adat, r, assay_type)
        check_data_matrix(adat, r)
    else:
        r.info(
            'SkippedChecks',
            'All v2.0-specific checks skipped because FileVersion != "2.0".',
        )

    # ------- Print report -------
    section = ''
    for c in r.checks:
        prefix = c.name.split('.')[0]
        if prefix != section:
            section = prefix
            print(f'--- {section} ---')
        icon = {'PASS': '✓', 'FAIL': '✗', 'WARN': '⚠', 'INFO': 'ℹ'}.get(c.status, '?')
        msg = f'  [{c.status}] {icon} {c.name}'
        if c.detail:
            msg += f': {c.detail}'
        print(msg)

    # ------- Summary -------
    n_pass = sum(1 for c in r.checks if c.status == PASS)
    n_fail = len(r.failed)
    n_warn = len(r.warned)
    print(f'\n{"─" * 50}')
    print(f'SUMMARY  {n_pass} passed · {n_fail} failed · {n_warn} warnings')

    if n_fail:
        print('\nFAILED CHECKS:')
        for c in r.failed:
            print(f'  ✗ {c.name}: {c.detail}')
        return 1

    if n_warn:
        print('\nWARNINGS:')
        for c in r.warned:
            print(f'  ⚠ {c.name}: {c.detail}')

    print('\nResult: PASS — file conforms to ADAT v2.0 specification.')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python validate_adat_v2.py <path_to.adat>')
        sys.exit(1)
    sys.exit(validate(sys.argv[1]))

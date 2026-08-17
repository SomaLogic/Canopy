"""Tests for somadata.conversion.array.header.convert_array_header."""

from __future__ import annotations

import pytest

from somadata.conversion.array import ArrayConversionContext
from somadata.conversion.array.header import convert_array_header
from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES
from tests.conversion.conftest import make_full_legacy_array_adat


@pytest.fixture
def legacy_adat():
    return make_full_legacy_array_adat()


@pytest.fixture
def ctx(legacy_adat):
    return ArrayConversionContext.from_adat(legacy_adat)


@pytest.fixture
def result(legacy_adat, ctx):
    return convert_array_header(legacy_adat, ctx)


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------


def test_output_has_all_v2_header_keys(result):
    assert set(result.keys()) == set(V2_HEADER_FIELD_TYPES.keys())


def test_file_version_is_2_0(result):
    assert result['FileVersion'] == '2.0'


def test_assay_type_set_to_array(result):
    assert result['AssayType'] == 'Array'


def test_assay_type_overridable_to_mixed(legacy_adat, ctx):
    r = convert_array_header(legacy_adat, ctx, assay_type='Mixed')
    assert r['AssayType'] == 'Mixed'


# ---------------------------------------------------------------------------
# GUID generation
# ---------------------------------------------------------------------------


def test_adat_id_is_new_guid(result, legacy_adat):
    """AdatId must be a new GID-* value distinct from source."""
    assert result['AdatId'].startswith('GID-')
    assert result['AdatId'] != legacy_adat.header_metadata.get('!AdatId', '')


def test_adat_id_differs_across_calls(legacy_adat, ctx):
    r1 = convert_array_header(legacy_adat, ctx)
    r2 = convert_array_header(legacy_adat, ctx)
    assert r1['AdatId'] != r2['AdatId']


# ---------------------------------------------------------------------------
# FileCreatedDate
# ---------------------------------------------------------------------------


def test_file_created_date_is_iso_format(result):
    import re

    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
    assert re.match(pattern, result['FileCreatedDate'])


# ---------------------------------------------------------------------------
# SourceFile JSON
# ---------------------------------------------------------------------------


def test_source_file_contains_old_adat_id(result):
    sf = result['SourceFile']
    assert isinstance(sf, dict)
    assert '1' in sf
    assert sf['1']['AdatId'] == 'SL-99999'


def test_source_file_uses_file_md5sum_when_no_adat_id(legacy_adat):
    """File checksum is used as-is (no mem. prefix) when AdatId absent."""
    del legacy_adat.header_metadata['!AdatId']
    file_md5 = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
    ctx = ArrayConversionContext.from_adat(legacy_adat, source_file_md5sum=file_md5)
    result = convert_array_header(legacy_adat, ctx)
    sf = result['SourceFile']
    assert '1' in sf
    assert sf['1']['md5sum'] == file_md5
    assert not sf['1']['md5sum'].startswith('mem.')


def test_source_file_uses_mem_prefix_for_object_md5sum(legacy_adat):
    """In-memory checksum gets a mem. prefix when no AdatId and no file checksum."""
    del legacy_adat.header_metadata['!AdatId']
    ctx = ArrayConversionContext.from_adat(legacy_adat, source_file_md5sum=None)
    result = convert_array_header(legacy_adat, ctx)
    sf = result['SourceFile']
    assert '1' in sf
    md5val = sf['1']['md5sum']
    assert md5val.startswith('mem.')
    digest = md5val[len('mem.') :]
    assert len(digest) == 32
    assert all(c in '0123456789abcdef' for c in digest)


def test_source_file_file_md5sum_preferred_over_object(legacy_adat):
    """File md5sum takes precedence over in-memory computation."""
    del legacy_adat.header_metadata['!AdatId']
    file_md5 = 'cccccccccccccccccccccccccccccccc'
    ctx = ArrayConversionContext.from_adat(legacy_adat, source_file_md5sum=file_md5)
    r1 = convert_array_header(legacy_adat, ctx)
    # Confirm the file md5 is used, not a mem. prefixed value
    assert r1['SourceFile']['1']['md5sum'] == file_md5


# ---------------------------------------------------------------------------
# Pass-through fields
# ---------------------------------------------------------------------------


def test_pass_through_title(result):
    assert result['Title'] == 'Test Study'


def test_pass_through_study_organism(result):
    assert result['StudyOrganism'] == 'Human'


def test_pass_through_study_matrix(result):
    assert result['StudyMatrix'] == 'EDTA Plasma'


def test_pass_through_use_restriction(result):
    assert result['UseRestriction'] == 'Research Use Only'


def test_pass_through_assay_version(result):
    # AssayVersion is no longer in the header (spec §3.2.1 moves it to ROW_DATA).
    assert 'AssayVersion' not in result


def test_bang_prefix_stripped_on_lookup(result):
    """Fields stored with ! prefix in source must still be mapped."""
    assert result['Title'] == 'Test Study'  # stored as !Title


# ---------------------------------------------------------------------------
# SOMAmerReferenceSource
# ---------------------------------------------------------------------------


def test_protein_effective_date_mapped(result):
    assert result['SOMAmerReferenceSource'] == '2020-08-07'


# ---------------------------------------------------------------------------
# ProcessSteps JSON
# ---------------------------------------------------------------------------


def test_process_steps_json_format(result):
    ps = result['ProcessSteps']
    assert isinstance(ps, dict)
    assert '1' in ps
    steps = ps['1']
    assert isinstance(steps, list)
    assert 'Raw RFU' in steps
    assert 'Calibration' in steps


def test_process_steps_all_trimmed(result):
    steps = result['ProcessSteps']['1']
    for step in steps:
        assert step == step.strip()


# ---------------------------------------------------------------------------
# ReportConfig JSON
# ---------------------------------------------------------------------------


def test_report_config_wrapped(result):
    rc = result['ReportConfig']
    assert isinstance(rc, dict)
    assert '1' in rc
    assert rc['1'] == 'DefaultReport'


# ---------------------------------------------------------------------------
# Plate-keyed field consolidation
# ---------------------------------------------------------------------------


def test_plate_scale_scalar_consolidated(result):
    pss = result['PlateScaleScalar']
    assert isinstance(pss, dict)
    assert 'PLT1' in pss and 'PLT2' in pss
    assert pss['PLT1'] == {'PlatformSpecific': 1.02}
    assert pss['PLT2'] == {'PlatformSpecific': 0.98}


def test_calibrate_tail_percent_consolidated(result):
    ctp = result['CalibrateTailPercent']
    assert isinstance(ctp, dict)
    assert 'PLT1' in ctp and 'PLT2' in ctp
    assert ctp['PLT1']['PlatformSpecific'] == 5.2


def test_calibrate_tail_percent_status_consolidated(result):
    ctps = result['CalibrateTailPercentStatus']
    assert ctps['PLT1']['PlatformSpecific'] == 'PASS'
    assert ctps['PLT2']['PlatformSpecific'] == 'WARNING'


def test_plate_scale_status_flat_structure(result):
    """PlateScaleStatus uses flat {"PlateId": value}, not nested."""
    pss = result['PlateScaleStatus']
    assert pss['PLT1'] == 'PASS'
    assert pss['PLT2'] == 'FLAG'


def test_qc_check_tail_percent_consolidated(result):
    qctp = result['QCCheckTailPercent']
    assert 'PLT1' in qctp
    # QCCheckTailPercent is flat (no PlatformSpecific nesting)
    assert qctp['PLT1'] == 3.1


def test_qc_check_tail_percent_status_consolidated(result):
    qctps = result['QCCheckTailPercentStatus']
    # QCCheckTailPercentStatus is flat (no PlatformSpecific nesting)
    assert qctps['PLT1'] == 'PASS'


# ---------------------------------------------------------------------------
# Removed / NGS-only fields
# ---------------------------------------------------------------------------


def test_generated_by_not_in_output(result):
    assert 'GeneratedBy' not in result


def test_ngs_only_field_blank(result):
    assert result['PlateSOMAmerNormReadsStatus'] == ''

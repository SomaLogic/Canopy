"""Tests for somadata.conversion.array.row_data.convert_array_row_data."""

from __future__ import annotations

import pytest

from somadata.conversion.array import ArrayConversionContext
from somadata.conversion.array.row_data import convert_array_row_data

from tests.conversion.conftest import make_full_legacy_array_adat


@pytest.fixture
def legacy_adat():
    return make_full_legacy_array_adat()


@pytest.fixture
def ctx(legacy_adat):
    return ArrayConversionContext.from_adat(legacy_adat)


@pytest.fixture
def result(legacy_adat, ctx):
    return convert_array_row_data(legacy_adat, ctx)


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


def test_returns_multiindex(result):
    import pandas as pd

    assert isinstance(result, pd.MultiIndex)


def test_row_count_preserved(result, legacy_adat):
    assert len(result) == len(legacy_adat.index)


# ---------------------------------------------------------------------------
# Static field renames
# ---------------------------------------------------------------------------


def test_plate_position_renamed_to_well_position(result):
    assert 'WellPosition' in result.names
    assert 'PlatePosition' not in result.names


def test_hyb_control_norm_scale_renamed(result):
    assert 'HybNormScaleFactor' in result.names
    assert 'HybControlNormScale' not in result.names


def test_row_check_renamed_to_status(result):
    assert 'RowCheckStatus' in result.names
    assert 'RowCheck' not in result.names


def test_study_id_renamed_to_project(result):
    assert 'Project' in result.names
    assert 'StudyId' not in result.names


def test_subject_id_renamed(result):
    assert 'SubjectId' in result.names
    assert 'SubjectID' not in result.names


def test_barcode_2d_renamed(result):
    assert 'MatrixTubeBarcode' in result.names
    assert 'Barcode2d' not in result.names


# ---------------------------------------------------------------------------
# New generated fields
# ---------------------------------------------------------------------------


def test_sample_readout_set_to_array(result):
    values = list(result.get_level_values('SampleReadout'))
    assert all(v == 'Array' for v in values)


def test_unique_sample_key_is_guid(result):
    values = list(result.get_level_values('UniqueSampleKey'))
    for v in values:
        assert v.startswith('GID-'), f'Expected GID- prefix, got {v!r}'


def test_unique_sample_key_unique_per_row(result):
    values = list(result.get_level_values('UniqueSampleKey'))
    assert len(set(values)) == len(values)


def test_source_file_id_from_context(result, ctx):
    values = list(result.get_level_values('SourceFileId'))
    assert all(v == ctx.source_file_id for v in values)


def test_process_steps_id_from_context(result, ctx):
    values = list(result.get_level_values('ProcessStepsId'))
    assert all(v == ctx.process_steps_id for v in values)


def test_report_config_id_from_context(result, ctx):
    values = list(result.get_level_values('ReportConfigId'))
    assert all(v == ctx.report_config_id for v in values)


def test_software_version_from_generated_by(result, ctx):
    values = list(result.get_level_values('SoftwareVersion'))
    assert all(v == ctx.generated_by for v in values)
    assert ctx.generated_by == 'SomaSuite 4.0.0'


# ---------------------------------------------------------------------------
# HybNormStatus derivation
# ---------------------------------------------------------------------------
# Fixture data: HybControlNormScale = ['1.05', '0.35', '2.60']
# Expected:     PASS, FLAG (0.35 < 0.4), FLAG (2.60 > 2.5)


def test_hyb_norm_status_pass(result):
    values = list(result.get_level_values('HybNormStatus'))
    assert values[0] == 'PASS'


def test_hyb_norm_status_flag_low(result):
    values = list(result.get_level_values('HybNormStatus'))
    assert values[1] == 'FLAG'


def test_hyb_norm_status_flag_high(result):
    values = list(result.get_level_values('HybNormStatus'))
    assert values[2] == 'FLAG'


# ---------------------------------------------------------------------------
# MedNormIntStatus derivation
# ---------------------------------------------------------------------------
# SampleTypes: ['Sample', 'Calibrator', 'QC']
# NormScale_0.5: ['1.1', '1.0', '0.9']  — all in [0.4, 2.5]
# S1 (Sample) → blank; S2 (Calibrator) → PASS; S3 (QC) → blank


def test_med_norm_int_status_blank_for_sample(result):
    values = list(result.get_level_values('MedNormIntStatus'))
    assert values[0] == ''


def test_med_norm_int_status_calibrator_pass(result):
    values = list(result.get_level_values('MedNormIntStatus'))
    assert values[1] == 'PASS'


def test_med_norm_int_status_blank_for_qc(result):
    """QC is not in the eligible MedNormInt SampleTypes (only Calibrator/Buffer)."""
    values = list(result.get_level_values('MedNormIntStatus'))
    assert values[2] == ''


# ---------------------------------------------------------------------------
# PlateRunDate fallback
# ---------------------------------------------------------------------------


def test_plate_run_date_fallback_from_created_date(result, ctx):
    """S1 had a blank PlateRunDate → should be filled from ctx.created_date."""
    values = list(result.get_level_values('PlateRunDate'))
    assert values[0] == ctx.created_date  # '2021-01-15'


def test_plate_run_date_not_overwritten_when_present(result):
    """S2 had '2021-01-10' → must not be overwritten."""
    values = list(result.get_level_values('PlateRunDate'))
    assert values[1] == '2021-01-10'


# ---------------------------------------------------------------------------
# ControlId population
# ---------------------------------------------------------------------------
# SampleTypes: ['Sample', 'Calibrator', 'QC']
# SampleIds:   ['S1',     'S2',          'S3']


def test_control_id_blank_for_sample_type(result):
    values = list(result.get_level_values('ControlId'))
    assert values[0] == ''


def test_control_id_for_calibrator(result):
    values = list(result.get_level_values('ControlId'))
    assert values[1] == 'S2'


def test_control_id_for_qc_sample(result):
    values = list(result.get_level_values('ControlId'))
    assert values[2] == 'S3'


# ---------------------------------------------------------------------------
# Removed fields
# ---------------------------------------------------------------------------


def test_ext_identifier_removed(result):
    assert 'ExtIdentifier' not in result.names


def test_sample_name_removed(result):
    assert 'SampleName' not in result.names


# ---------------------------------------------------------------------------
# NGS-only blank fields present
# ---------------------------------------------------------------------------


def test_ngs_only_fields_present(result):
    ngs_fields = [
        'SequencingRunId',
        'InputType',
        'KitType',
        'SOMAmerReads',
        'SOMAmerReadsStatus',
        'Flowcell',
    ]
    for field in ngs_fields:
        assert field in result.names, f'{field!r} missing from output'


def test_ngs_only_fields_blank(result):
    for field in ['SequencingRunId', 'InputType', 'KitType']:
        values = list(result.get_level_values(field))
        assert all(v == '' for v in values), f'{field!r} has non-blank values'

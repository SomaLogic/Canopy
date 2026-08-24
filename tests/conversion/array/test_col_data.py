"""Tests for somadata.conversion.array.col_data.convert_array_col_data."""

from __future__ import annotations

import pandas as pd
import pytest

from somadata.conversion.array.col_data import convert_array_col_data
from somadata.conversion.errors import ConversionError

from tests.conversion.conftest import make_full_legacy_array_adat


@pytest.fixture
def legacy_adat():
    return make_full_legacy_array_adat()


@pytest.fixture
def result(legacy_adat):
    return convert_array_col_data(legacy_adat)


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


def test_returns_multiindex(result):
    assert isinstance(result, pd.MultiIndex)


def test_seq_id_preserved(result, legacy_adat):
    src_seqids = list(legacy_adat.columns.get_level_values('SeqId'))
    out_seqids = list(result.get_level_values('SeqId'))
    assert src_seqids == out_seqids


# ---------------------------------------------------------------------------
# Static field renames
# ---------------------------------------------------------------------------


def test_entrez_gene_id_renamed(result):
    assert 'EntrezGeneId' in result.names
    assert 'EntrezGeneID' not in result.names


# ---------------------------------------------------------------------------
# Dynamic field renames
# ---------------------------------------------------------------------------


def test_cal_plate_id_renamed(result):
    assert 'PlatformSpecificCalibrate_PLT1_ScaleFactor' in result.names
    assert 'Cal_PLT1' not in result.names


def test_cal_qc_ratio_single_qc_renamed(result):
    assert 'QCRatio_PLT1' in result.names
    assert 'CalQcRatio_PLT1_QC1' not in result.names


def test_plate_scale_reference_renamed(result):
    # With no calibrator_id, the suffix is omitted but Ref.Array.PlateScale is present
    assert 'Ref.Array.PlateScale' in result.names
    assert 'PlateScale_Reference' not in result.names


def test_cal_reference_renamed(result):
    assert 'Ref.Array.Calibrate' in result.names
    assert 'CalReference' not in result.names


def test_qc_reference_renamed(result):
    assert 'Ref.Array.QCRatio_QC1' in result.names
    assert 'QcReference_QC1' not in result.names


def test_med_norm_ref_renamed(result):
    assert 'Ref.MedNorm.Id' in result.names
    assert 'medNormRef_ReferenceRFU' not in result.names


def test_plate_scale_reference_with_calibrator_id(legacy_adat):
    r = convert_array_col_data(legacy_adat, calibrator_id='SL-CAL-42')
    assert 'Ref.Array.PlateScale_SL-CAL-42' in r.names


# ---------------------------------------------------------------------------
# HybControl derived field
# ---------------------------------------------------------------------------


def test_hyb_control_level_present(result):
    assert 'HybControl' in result.names


def test_hyb_control_true_for_hybridization_control(result, legacy_adat):
    """Third analyte has Type='Hybridization Control' → HybControl='True'."""
    hc_values = list(result.get_level_values('HybControl'))
    type_values = list(legacy_adat.columns.get_level_values('Type'))
    for hc, typ in zip(hc_values, type_values):
        expected = 'True' if typ == 'Hybridization Control' else 'False'
        assert (
            hc == expected
        ), f'Type={typ!r}: expected HybControl={expected!r}, got {hc!r}'


# ---------------------------------------------------------------------------
# Removed fields
# ---------------------------------------------------------------------------


def test_seq_id_version_removed(result):
    assert 'SeqIdVersion' not in result.names


def test_soma_id_removed(result):
    assert 'SomaId' not in result.names


def test_col_check_removed(result):
    assert 'ColCheck' not in result.names


# ---------------------------------------------------------------------------
# CalQcRatio multi-QC raises
# ---------------------------------------------------------------------------


def test_cal_qc_ratio_multi_qc_raises():
    """Multiple QC IDs on the same plate must raise ConversionError."""
    from somadata.adat import Adat

    col_values = [
        ['10000-28', '10001-7'],
        ['1.0', '1.0'],
        ['1.0', '1.0'],
    ]
    col_names = ['SeqId', 'CalQcRatio_PLT1_QC1', 'CalQcRatio_PLT1_QC2']
    index = pd.MultiIndex.from_arrays(
        [['S1'], ['Sample']], names=['SampleId', 'SampleType']
    )
    columns = pd.MultiIndex.from_arrays(col_values, names=col_names)
    adat = Adat(data=[[1.0, 1.0]], index=index, columns=columns, header_metadata={})

    with pytest.raises(ConversionError, match='Multiple QCSampleIds'):
        convert_array_col_data(adat)

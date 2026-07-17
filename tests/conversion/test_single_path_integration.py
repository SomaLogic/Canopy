"""Integration tests for single-input ADAT v2.0 conversions (CAN-43, CAN-44, CAN-45).

Each test class covers one source type converting to a v2.0 Adat without any
merge logic, MedNorm validation, or SeqId union:

  TestBridgedArrayToV2   — bridged array source → AssayType "Array"
  TestNativeArrayToV2    — native array source  → AssayType "Array"
  TestNativeNGSToV2      — native NGS source    → AssayType "NGS"
"""

from __future__ import annotations

import os
import tempfile

import pytest

from somadata.adat import Adat
from somadata.conversion.converter import to_v2_adat
from somadata.io.adat.file import read_adat, write_adat
from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES, validate_v2_header_fields

pytestmark = pytest.mark.integration

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
BRIDGED_ARRAY_PATH = os.path.join(_DATA_DIR, 'sample-bridged-array.adat')
NATIVE_ARRAY_PATH = os.path.join(_DATA_DIR, 'sample-plasma-native-array.adat')
NATIVE_NGS_PATH = os.path.join(_DATA_DIR, 'sample-native-ngs.adat')


# ===========================================================================
# Bridged array → Array v2.0 (CAN-43)
# ===========================================================================


@pytest.fixture(scope='session')
def source_bridged_array():
    return read_adat(BRIDGED_ARRAY_PATH)


@pytest.fixture(scope='session')
def bridged_array_v2(source_bridged_array):
    return to_v2_adat([source_bridged_array])


@pytest.fixture(scope='session')
def bridged_array_v2_written(bridged_array_v2):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adat', delete=False) as f:
        tmppath = f.name
        write_adat(bridged_array_v2, f)
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture(scope='session')
def bridged_array_v2_round_trip(bridged_array_v2_written):
    return read_adat(bridged_array_v2_written)


class TestBridgedArrayToV2:
    """Bridged array → Array v2.0 single-input conversion (CAN-43)."""

    def test_returns_adat(self, bridged_array_v2):
        assert isinstance(bridged_array_v2, Adat)

    def test_file_version_is_2_0(self, bridged_array_v2):
        assert bridged_array_v2.header_metadata['FileVersion'] == '2.0'

    def test_assay_type_is_array(self, bridged_array_v2):
        assert bridged_array_v2.header_metadata['AssayType'] == 'Array'

    def test_row_count_preserved(self, bridged_array_v2, source_bridged_array):
        assert len(bridged_array_v2) == len(source_bridged_array)

    def test_seqid_set_preserved(self, bridged_array_v2, source_bridged_array):
        orig = set(source_bridged_array.columns.get_level_values('SeqId'))
        assert set(bridged_array_v2.columns.get_level_values('SeqId')) == orig

    def test_new_adat_id_generated(self, bridged_array_v2, source_bridged_array):
        new_id = bridged_array_v2.header_metadata['AdatId']
        assert new_id.startswith('GID-')
        assert new_id != source_bridged_array.header_metadata.get('!AdatId', '')

    def test_closed_header_field_set(self, bridged_array_v2):
        assert set(bridged_array_v2.header_metadata.keys()) == set(V2_HEADER_FIELD_TYPES.keys())

    def test_header_passes_validation(self, bridged_array_v2):
        assert validate_v2_header_fields(bridged_array_v2.header_metadata)

    def test_source_file_has_one_entry(self, bridged_array_v2):
        sf = bridged_array_v2.header_metadata['SourceFile']
        assert isinstance(sf, dict) and len(sf) == 1 and '1' in sf

    def test_process_steps_converted_to_json(self, bridged_array_v2):
        ps = bridged_array_v2.header_metadata['ProcessSteps']
        assert isinstance(ps, dict) and '1' in ps
        assert isinstance(ps['1'], list)

    def test_no_mednorm_validation_for_single_input(self, source_bridged_array):
        from unittest.mock import patch

        with patch(
            'somadata.conversion.converter.validate_mednorm_compatibility'
        ) as mock_mednorm:
            to_v2_adat([source_bridged_array])
        mock_mednorm.assert_not_called()

    def test_col_metadata_renames_applied(self, bridged_array_v2):
        assert 'EntrezGeneId' in bridged_array_v2.columns.names
        assert 'EntrezGeneID' not in bridged_array_v2.columns.names
        assert 'HybControl' in bridged_array_v2.columns.names
        assert 'SomaId' not in bridged_array_v2.columns.names
        assert 'ColCheck' not in bridged_array_v2.columns.names

    def test_row_metadata_renames_applied(self, bridged_array_v2):
        assert 'WellPosition' in bridged_array_v2.index.names
        assert 'PlatePosition' not in bridged_array_v2.index.names
        assert 'HybNormScaleFactor' in bridged_array_v2.index.names
        assert 'HybControlNormScale' not in bridged_array_v2.index.names
        assert 'RowCheckStatus' in bridged_array_v2.index.names

    def test_sample_readout_is_array(self, bridged_array_v2):
        vals = list(bridged_array_v2.index.get_level_values('SampleReadout'))
        assert all(v == 'Array' for v in vals)

    def test_unique_sample_keys_generated(self, bridged_array_v2):
        keys = list(bridged_array_v2.index.get_level_values('UniqueSampleKey'))
        assert len(set(keys)) == len(keys)
        assert all(k.startswith('GID-') for k in keys)

    def test_writer_does_not_raise(self, bridged_array_v2_written):
        assert os.path.exists(bridged_array_v2_written)
        assert os.path.getsize(bridged_array_v2_written) > 0

    def test_round_trip_shape_preserved(self, bridged_array_v2, bridged_array_v2_round_trip):
        assert bridged_array_v2_round_trip.shape == bridged_array_v2.shape

    def test_round_trip_seqids_preserved(self, bridged_array_v2, bridged_array_v2_round_trip):
        orig = set(bridged_array_v2.columns.get_level_values('SeqId'))
        assert set(bridged_array_v2_round_trip.columns.get_level_values('SeqId')) == orig

    def test_round_trip_assay_type_preserved(self, bridged_array_v2_round_trip):
        assert bridged_array_v2_round_trip.header_metadata.get('AssayType') == 'Array'

    def test_round_trip_row_metadata_preserved(self, bridged_array_v2, bridged_array_v2_round_trip):
        assert list(bridged_array_v2_round_trip.index.names) == list(bridged_array_v2.index.names)


# ===========================================================================
# Native array → Array v2.0 (CAN-44)
# ===========================================================================


@pytest.fixture(scope='session')
def source_native_array():
    return read_adat(NATIVE_ARRAY_PATH)


@pytest.fixture(scope='session')
def native_array_v2(source_native_array):
    return to_v2_adat([source_native_array])


@pytest.fixture(scope='session')
def native_array_v2_written(tmp_path_factory, native_array_v2):
    tmppath = str(tmp_path_factory.mktemp('native_array') / 'native_array_v2.adat')
    with open(tmppath, 'w') as f:
        write_adat(native_array_v2, f)
    return tmppath


@pytest.fixture(scope='session')
def native_array_v2_round_trip(native_array_v2_written):
    return read_adat(native_array_v2_written)


class TestNativeArrayToV2:
    """Native array → Array v2.0 single-input conversion (CAN-44).

    Uses the same array conversion pipeline as bridged array, but with no
    requirement on the terminal ProcessSteps sequence.
    """

    def test_source_has_non_bridged_process_steps(self, source_native_array):
        """Confirms the sample file is correctly classified as native (not bridged)."""
        steps = source_native_array.header_metadata.get(
            '!ProcessSteps', source_native_array.header_metadata.get('ProcessSteps', '')
        )
        assert 'CrossPlatformPlateScale' not in steps
        assert 'CrossPlatformCalibrate' not in steps
        assert 'MedNormExt' not in steps

    def test_returns_adat(self, native_array_v2):
        assert isinstance(native_array_v2, Adat)

    def test_file_version_is_2_0(self, native_array_v2):
        assert native_array_v2.header_metadata['FileVersion'] == '2.0'

    def test_assay_type_is_array(self, native_array_v2):
        assert native_array_v2.header_metadata['AssayType'] == 'Array'

    def test_row_count_preserved(self, native_array_v2, source_native_array):
        assert len(native_array_v2) == len(source_native_array)

    def test_seqid_set_preserved(self, native_array_v2, source_native_array):
        orig = set(source_native_array.columns.get_level_values('SeqId'))
        assert set(native_array_v2.columns.get_level_values('SeqId')) == orig

    def test_new_adat_id_generated(self, native_array_v2, source_native_array):
        new_id = native_array_v2.header_metadata['AdatId']
        assert new_id.startswith('GID-')
        assert new_id != source_native_array.header_metadata.get('!AdatId', '')

    def test_closed_header_field_set(self, native_array_v2):
        assert set(native_array_v2.header_metadata.keys()) == set(V2_HEADER_FIELD_TYPES.keys())

    def test_header_passes_validation(self, native_array_v2):
        assert validate_v2_header_fields(native_array_v2.header_metadata)

    def test_no_mednorm_validation_for_single_input(self, source_native_array):
        from unittest.mock import patch

        with patch(
            'somadata.conversion.converter.validate_mednorm_compatibility'
        ) as mock_mednorm:
            to_v2_adat([source_native_array])
        mock_mednorm.assert_not_called()

    def test_col_metadata_renames_applied(self, native_array_v2):
        assert 'EntrezGeneId' in native_array_v2.columns.names
        assert 'EntrezGeneID' not in native_array_v2.columns.names
        assert 'HybControl' in native_array_v2.columns.names
        assert 'SomaId' not in native_array_v2.columns.names
        assert 'ColCheck' not in native_array_v2.columns.names

    def test_row_metadata_renames_applied(self, native_array_v2):
        assert 'WellPosition' in native_array_v2.index.names
        assert 'PlatePosition' not in native_array_v2.index.names
        assert 'HybNormScaleFactor' in native_array_v2.index.names
        assert 'HybControlNormScale' not in native_array_v2.index.names
        assert 'RowCheckStatus' in native_array_v2.index.names

    def test_sample_readout_is_array(self, native_array_v2):
        vals = list(native_array_v2.index.get_level_values('SampleReadout'))
        assert all(v == 'Array' for v in vals)

    def test_unique_sample_keys_generated(self, native_array_v2):
        keys = list(native_array_v2.index.get_level_values('UniqueSampleKey'))
        assert len(set(keys)) == len(keys)
        assert all(k.startswith('GID-') for k in keys)

    def test_writer_does_not_raise(self, native_array_v2_written):
        assert os.path.exists(native_array_v2_written)
        assert os.path.getsize(native_array_v2_written) > 0

    def test_round_trip_shape_preserved(self, native_array_v2, native_array_v2_round_trip):
        assert native_array_v2_round_trip.shape == native_array_v2.shape

    def test_round_trip_seqids_preserved(self, native_array_v2, native_array_v2_round_trip):
        orig = set(native_array_v2.columns.get_level_values('SeqId'))
        assert set(native_array_v2_round_trip.columns.get_level_values('SeqId')) == orig

    def test_round_trip_assay_type_preserved(self, native_array_v2, native_array_v2_round_trip):
        assert native_array_v2_round_trip.header_metadata.get('AssayType') == 'Array'

    def test_round_trip_row_metadata_preserved(self, native_array_v2, native_array_v2_round_trip):
        assert list(native_array_v2_round_trip.index.names) == list(native_array_v2.index.names)


# ===========================================================================
# Native NGS → NGS v2.0 (CAN-45)
# ===========================================================================


@pytest.fixture(scope='session')
def source_native_ngs():
    return read_adat(NATIVE_NGS_PATH)


@pytest.fixture(scope='session')
def native_ngs_v2(source_native_ngs):
    return to_v2_adat([source_native_ngs])


@pytest.fixture(scope='session')
def native_ngs_v2_written(native_ngs_v2):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adat', delete=False) as f:
        tmppath = f.name
        write_adat(native_ngs_v2, f)
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture(scope='session')
def native_ngs_v2_round_trip(native_ngs_v2_written):
    return read_adat(native_ngs_v2_written)


class TestNativeNGSToV2:
    """Native NGS → NGS v2.0 single-input conversion (CAN-45)."""

    def test_returns_adat(self, native_ngs_v2):
        assert isinstance(native_ngs_v2, Adat)

    def test_file_version_is_2_0(self, native_ngs_v2):
        assert native_ngs_v2.header_metadata['FileVersion'] == '2.0'

    def test_assay_type_is_ngs(self, native_ngs_v2):
        assert native_ngs_v2.header_metadata['AssayType'] == 'NGS'

    def test_row_count_preserved(self, native_ngs_v2, source_native_ngs):
        assert len(native_ngs_v2) == len(source_native_ngs)

    def test_seqid_set_preserved(self, native_ngs_v2, source_native_ngs):
        orig = set(source_native_ngs.columns.get_level_values('SeqId'))
        assert set(native_ngs_v2.columns.get_level_values('SeqId')) == orig

    def test_new_adat_id_generated(self, native_ngs_v2, source_native_ngs):
        new_id = native_ngs_v2.header_metadata['AdatId']
        assert new_id.startswith('GID-')
        assert new_id != source_native_ngs.header_metadata.get('!AdatId', '')

    def test_closed_header_field_set(self, native_ngs_v2):
        assert set(native_ngs_v2.header_metadata.keys()) == set(V2_HEADER_FIELD_TYPES.keys())

    def test_header_passes_validation(self, native_ngs_v2):
        assert validate_v2_header_fields(native_ngs_v2.header_metadata)

    def test_no_mednorm_validation_for_single_input(self, source_native_ngs):
        from unittest.mock import patch

        with patch(
            'somadata.conversion.converter.validate_mednorm_compatibility'
        ) as mock_mednorm:
            to_v2_adat([source_native_ngs])
        mock_mednorm.assert_not_called()

    def test_source_file_has_one_entry(self, native_ngs_v2):
        sf = native_ngs_v2.header_metadata['SourceFile']
        assert isinstance(sf, dict) and len(sf) == 1 and '1' in sf

    def test_report_config_blank(self, native_ngs_v2):
        assert native_ngs_v2.header_metadata['ReportConfig'] == ''

    def test_col_metadata_renames_applied(self, native_ngs_v2):
        assert 'TargetFullName' in native_ngs_v2.columns.names
        assert 'Target Full Name' not in native_ngs_v2.columns.names
        assert 'UniProt' in native_ngs_v2.columns.names
        assert 'UniProt ID' not in native_ngs_v2.columns.names
        assert 'EntrezGeneId' in native_ngs_v2.columns.names
        assert 'Entrez Gene ID' not in native_ngs_v2.columns.names

    def test_row_metadata_renames_applied(self, native_ngs_v2):
        assert 'KitType' in native_ngs_v2.index.names
        assert 'MatrixType' not in native_ngs_v2.index.names
        assert 'NGSPlateMasterMixLot' in native_ngs_v2.index.names
        assert 'ProbePlate' not in native_ngs_v2.index.names
        assert 'HybNormScaleFactor' in native_ngs_v2.index.names

    def test_sample_readout_is_ngs(self, native_ngs_v2):
        vals = list(native_ngs_v2.index.get_level_values('SampleReadout'))
        assert all(v == 'NGS' for v in vals)

    def test_unique_sample_keys_generated(self, native_ngs_v2):
        keys = list(native_ngs_v2.index.get_level_values('UniqueSampleKey'))
        assert len(set(keys)) == len(keys)
        assert all(k.startswith('GID-') for k in keys)

    def test_sequencing_run_fields_replicated_to_rows(self, native_ngs_v2):
        for field in ('InstrumentType', 'Flowcell', 'YieldDemux', 'YieldQ30Demux', 'Q30WeightedMean'):
            assert field in native_ngs_v2.index.names, f'{field} missing from row metadata'
            vals = list(native_ngs_v2.index.get_level_values(field))
            assert all(v != '' for v in vals), f'{field} has blank values in rows'

    def test_software_version_replicated_to_rows(self, native_ngs_v2):
        assert 'SoftwareVersion' in native_ngs_v2.index.names
        vals = list(native_ngs_v2.index.get_level_values('SoftwareVersion'))
        assert all(v != '' for v in vals)

    def test_writer_does_not_raise(self, native_ngs_v2_written):
        assert os.path.exists(native_ngs_v2_written)
        assert os.path.getsize(native_ngs_v2_written) > 0

    def test_round_trip_shape_preserved(self, native_ngs_v2, native_ngs_v2_round_trip):
        assert native_ngs_v2_round_trip.shape == native_ngs_v2.shape

    def test_round_trip_seqids_preserved(self, native_ngs_v2, native_ngs_v2_round_trip):
        orig = set(native_ngs_v2.columns.get_level_values('SeqId'))
        assert set(native_ngs_v2_round_trip.columns.get_level_values('SeqId')) == orig

    def test_round_trip_assay_type_preserved(self, native_ngs_v2_round_trip):
        assert native_ngs_v2_round_trip.header_metadata.get('AssayType') == 'NGS'

    def test_round_trip_row_metadata_preserved(self, native_ngs_v2, native_ngs_v2_round_trip):
        assert list(native_ngs_v2_round_trip.index.names) == list(native_ngs_v2.index.names)

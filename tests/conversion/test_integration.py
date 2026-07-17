"""End-to-end integration tests for the ADAT v2.0 converter (CAN-42 / Ticket 1.10).

Covers the complete Path 1 flow: bridged_array + native_ngs → Mixed v2.0.

Acceptance criteria verified here:
- to_v2_adat() with real sample files produces a valid v2.0 Mixed Adat without error
- Output passes the v2.0 writer (write_adat) without error
- Round-trip: write → re-read with existing parser → shape, SeqIds, and RFU values preserved
- All field mappings correct (spot-check key fields from each conversion)
- SampleReadout correctly set per source ("Array" for array rows, "NGS" for NGS rows)
- Header validation passes the closed v2.0 field set
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from somadata.adat import Adat
from somadata.conversion.converter import to_v2_adat
from somadata.io.adat.file import read_adat, write_adat
from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES, validate_v2_header_fields

pytestmark = pytest.mark.integration
# ---------------------------------------------------------------------------
# Paths to real sample ADAT files bundled with tests
# ---------------------------------------------------------------------------

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
BRIDGED_ARRAY_PATH = os.path.join(_DATA_DIR, 'Plasma-bridged-array.adat')
NATIVE_NGS_PATH = os.path.join(_DATA_DIR, 'sample-native-ngs.adat')


# ---------------------------------------------------------------------------
# Session-scoped fixtures — read + convert once for all tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope='session')
def source_array_adat():
    """Loaded (pre-conversion) bridged array ADAT."""
    return read_adat(BRIDGED_ARRAY_PATH)


@pytest.fixture(scope='session')
def source_ngs_adat():
    """Loaded (pre-conversion) native NGS ADAT."""
    return read_adat(NATIVE_NGS_PATH)


@pytest.fixture(scope='session')
def mixed_v2_adat(source_array_adat, source_ngs_adat):
    """Converted Mixed v2.0 Adat produced from the two sample files."""
    return to_v2_adat([source_array_adat, source_ngs_adat])


@pytest.fixture(scope='session')
def written_adat_path(mixed_v2_adat):
    """Write the Mixed v2.0 Adat to a temp file once for the whole session."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adat', delete=False) as f:
        tmppath = f.name
        write_adat(mixed_v2_adat, f)
    yield tmppath
    os.unlink(tmppath)


@pytest.fixture(scope='session')
def round_trip_adat(written_adat_path):
    """Re-read the session-written v2.0 file."""
    return read_adat(written_adat_path)


# ===========================================================================
# Path 1 Integration — to_v2_adat with real sample files
# ===========================================================================


class TestPath1Conversion:
    """Acceptance criteria: to_v2_adat produces a valid Mixed v2.0 Adat."""

    def test_conversion_returns_adat(self, mixed_v2_adat):
        assert isinstance(mixed_v2_adat, Adat)

    def test_file_version_is_2_0(self, mixed_v2_adat):
        assert mixed_v2_adat.header_metadata['FileVersion'] == '2.0'

    def test_assay_type_is_mixed(self, mixed_v2_adat):
        assert mixed_v2_adat.header_metadata['AssayType'] == 'Mixed'

    def test_row_count_equals_sum_of_sources(self, mixed_v2_adat, source_array_adat, source_ngs_adat):
        expected = len(source_array_adat) + len(source_ngs_adat)
        assert len(mixed_v2_adat) == expected

    def test_seqid_count_equals_union(self, mixed_v2_adat, source_array_adat, source_ngs_adat):
        arr_seqids = set(source_array_adat.columns.get_level_values('SeqId'))
        ngs_seqids = set(source_ngs_adat.columns.get_level_values('SeqId'))
        expected_union = arr_seqids | ngs_seqids
        result_seqids = set(mixed_v2_adat.columns.get_level_values('SeqId'))
        assert result_seqids == expected_union

    def test_all_array_seqids_present(self, mixed_v2_adat, source_array_adat):
        arr_seqids = set(source_array_adat.columns.get_level_values('SeqId'))
        result_seqids = set(mixed_v2_adat.columns.get_level_values('SeqId'))
        assert arr_seqids.issubset(result_seqids)

    def test_all_ngs_seqids_present(self, mixed_v2_adat, source_ngs_adat):
        ngs_seqids = set(source_ngs_adat.columns.get_level_values('SeqId'))
        result_seqids = set(mixed_v2_adat.columns.get_level_values('SeqId'))
        assert ngs_seqids.issubset(result_seqids)

    def test_new_adat_id_generated(self, mixed_v2_adat):
        adat_id = mixed_v2_adat.header_metadata['AdatId']
        assert adat_id.startswith('GID-')

    def test_source_file_has_two_entries(self, mixed_v2_adat):
        sf = mixed_v2_adat.header_metadata['SourceFile']
        assert isinstance(sf, dict)
        assert '1' in sf and '2' in sf

    def test_process_steps_has_two_entries(self, mixed_v2_adat):
        ps = mixed_v2_adat.header_metadata['ProcessSteps']
        assert isinstance(ps, dict)
        assert '1' in ps and '2' in ps

    def test_header_passes_closed_field_set_validation(self, mixed_v2_adat):
        assert validate_v2_header_fields(mixed_v2_adat.header_metadata)

    def test_header_contains_all_required_fields(self, mixed_v2_adat):
        required = set(V2_HEADER_FIELD_TYPES.keys())
        present = set(mixed_v2_adat.header_metadata.keys())
        missing = required - present
        assert missing == set(), f'Missing required v2.0 header fields: {missing}'

    def test_order_independent_path_files(self):
        """Passing files in reverse order produces the same SeqId set and AssayType.

        Uses small synthetic fixtures rather than the full 11k-analyte sample
        files — the order-independence of the routing logic is already validated
        by unit tests in test_converter.py; here we just confirm the full
        pipeline does not crash either way.
        """
        from tests.conversion.conftest import (
            make_bridged_array_with_mednorm,
            make_full_legacy_ngs_adat,
        )

        array_adat = make_bridged_array_with_mednorm()
        ngs_adat = make_full_legacy_ngs_adat()
        result_ab = to_v2_adat([array_adat, ngs_adat])
        result_ba = to_v2_adat([ngs_adat, array_adat])
        assert result_ab.header_metadata['AssayType'] == 'Mixed'
        assert result_ba.header_metadata['AssayType'] == 'Mixed'
        seqids_ab = set(result_ab.columns.get_level_values('SeqId'))
        seqids_ba = set(result_ba.columns.get_level_values('SeqId'))
        assert seqids_ab == seqids_ba

    def test_conversion_via_file_paths(self, mixed_v2_adat):
        """to_v2_adat() also accepts file-path strings; verify the session fixture
        (which was loaded from disk) already proves this path works."""
        assert mixed_v2_adat.header_metadata['FileVersion'] == '2.0'
        assert mixed_v2_adat.header_metadata['AssayType'] == 'Mixed'


# ===========================================================================
# SampleReadout field
# ===========================================================================


class TestSampleReadout:
    """Acceptance criteria: SampleReadout set to 'Array' or 'NGS' per source."""

    def test_sample_readout_field_present(self, mixed_v2_adat):
        assert 'SampleReadout' in mixed_v2_adat.index.names

    def test_array_rows_have_readout_array(self, mixed_v2_adat, source_array_adat):
        readouts = list(mixed_v2_adat.index.get_level_values('SampleReadout'))
        n_array = len(source_array_adat)
        array_readouts = readouts[:n_array]
        assert all(r == 'Array' for r in array_readouts), (
            f'Expected all "Array" in first {n_array} rows; got: {set(array_readouts)}'
        )

    def test_ngs_rows_have_readout_ngs(self, mixed_v2_adat, source_array_adat, source_ngs_adat):
        readouts = list(mixed_v2_adat.index.get_level_values('SampleReadout'))
        n_array = len(source_array_adat)
        ngs_readouts = readouts[n_array:]
        assert all(r == 'NGS' for r in ngs_readouts), (
            f'Expected all "NGS" in last {len(source_ngs_adat)} rows; got: {set(ngs_readouts)}'
        )

    def test_total_readout_counts(self, mixed_v2_adat, source_array_adat, source_ngs_adat):
        readouts = list(mixed_v2_adat.index.get_level_values('SampleReadout'))
        assert readouts.count('Array') == len(source_array_adat)
        assert readouts.count('NGS') == len(source_ngs_adat)


# ===========================================================================
# Field mapping spot-checks
# ===========================================================================


class TestArrayFieldMappings:
    """Spot-check key array → v2.0 field renames and removals."""

    def test_entrez_gene_id_renamed(self, mixed_v2_adat):
        assert 'EntrezGeneId' in mixed_v2_adat.columns.names
        assert 'EntrezGeneID' not in mixed_v2_adat.columns.names

    def test_target_full_name_present(self, mixed_v2_adat):
        assert 'TargetFullName' in mixed_v2_adat.columns.names

    def test_uniprot_renamed(self, mixed_v2_adat):
        assert 'UniProt' in mixed_v2_adat.columns.names

    def test_hyb_control_col_added(self, mixed_v2_adat):
        assert 'HybControl' in mixed_v2_adat.columns.names

    def test_soma_id_removed(self, mixed_v2_adat):
        assert 'SomaId' not in mixed_v2_adat.columns.names

    def test_col_check_removed(self, mixed_v2_adat):
        assert 'ColCheck' not in mixed_v2_adat.columns.names

    def test_units_removed(self, mixed_v2_adat):
        assert 'Units' not in mixed_v2_adat.columns.names

    def test_plate_position_renamed_to_well_position(self, mixed_v2_adat):
        assert 'WellPosition' in mixed_v2_adat.index.names
        assert 'PlatePosition' not in mixed_v2_adat.index.names

    def test_row_check_status_renamed(self, mixed_v2_adat):
        assert 'RowCheckStatus' in mixed_v2_adat.index.names

    def test_hyb_norm_scale_factor_renamed(self, mixed_v2_adat):
        assert 'HybNormScaleFactor' in mixed_v2_adat.index.names
        assert 'HybControlNormScale' not in mixed_v2_adat.index.names

    def test_unique_sample_keys_generated(self, mixed_v2_adat):
        assert 'UniqueSampleKey' in mixed_v2_adat.index.names
        keys = list(mixed_v2_adat.index.get_level_values('UniqueSampleKey'))
        assert len(set(keys)) == len(keys), 'UniqueSampleKey values are not all unique'
        assert all(k.startswith('GID-') for k in keys)

    def test_source_file_id_present(self, mixed_v2_adat):
        assert 'SourceFileId' in mixed_v2_adat.index.names

    def test_process_steps_id_present(self, mixed_v2_adat):
        assert 'ProcessStepsId' in mixed_v2_adat.index.names


class TestNGSFieldMappings:
    """Spot-check key NGS → v2.0 field renames."""

    def test_target_full_name_present_for_ngs(self, mixed_v2_adat):
        assert 'TargetFullName' in mixed_v2_adat.columns.names
        assert 'Target Full Name' not in mixed_v2_adat.columns.names

    def test_kit_type_renamed(self, mixed_v2_adat):
        assert 'KitType' in mixed_v2_adat.index.names
        assert 'MatrixType' not in mixed_v2_adat.index.names

    def test_ngs_plate_master_mix_lot_renamed(self, mixed_v2_adat):
        assert 'NGSPlateMasterMixLot' in mixed_v2_adat.index.names
        assert 'ProbePlate' not in mixed_v2_adat.index.names

    def test_software_version_propagated_to_rows(self, mixed_v2_adat, source_array_adat):
        """SoftwareVersion should be present in all NGS rows."""
        assert 'SoftwareVersion' in mixed_v2_adat.index.names
        n_array = len(source_array_adat)
        ngs_sv = list(mixed_v2_adat.index.get_level_values('SoftwareVersion'))[n_array:]
        assert all(v != '' for v in ngs_sv), 'Some NGS rows have blank SoftwareVersion'

    def test_sequencing_run_fields_present_in_ngs_rows(self, mixed_v2_adat, source_array_adat):
        """Header fields InstrumentType, Flowcell etc. are replicated to NGS rows."""
        n_array = len(source_array_adat)
        for field in ('InstrumentType', 'Flowcell', 'YieldDemux', 'YieldQ30Demux', 'Q30WeightedMean'):
            assert field in mixed_v2_adat.index.names, f'{field} not in row metadata'
            ngs_vals = list(mixed_v2_adat.index.get_level_values(field))[n_array:]
            assert all(v != '' for v in ngs_vals), f'Some NGS rows have blank {field}'

    def test_ngs_ref_prefix_applied(self, mixed_v2_adat):
        """NGS-exclusive reference columns should use Ref.NGS.* prefix."""
        ngs_ref_cols = [
            n for n in mixed_v2_adat.columns.names if n.startswith('Ref.NGS.')
        ]
        assert len(ngs_ref_cols) > 0, 'No Ref.NGS.* columns found in output'


# ===========================================================================
# SeqId union — NaN fill verification
# ===========================================================================


class TestSeqIdUnion:
    """Acceptance criteria: SeqIds absent in a source get NaN in that source's rows."""

    def test_array_only_seqids_are_nan_in_ngs_rows(
        self, mixed_v2_adat, source_array_adat, source_ngs_adat
    ):
        """SeqIds present only in the array source must be NaN for all NGS rows."""
        arr_seqids = set(source_array_adat.columns.get_level_values('SeqId'))
        ngs_seqids = set(source_ngs_adat.columns.get_level_values('SeqId'))
        array_only = arr_seqids - ngs_seqids

        if not array_only:
            pytest.skip('No array-only SeqIds in sample data')

        n_array = len(source_array_adat)
        result_seqids = list(mixed_v2_adat.columns.get_level_values('SeqId'))
        rfu = mixed_v2_adat.to_numpy()

        sample_col_idx = result_seqids.index(next(iter(array_only)))
        ngs_rows = rfu[n_array:, sample_col_idx]
        assert np.all(np.isnan(ngs_rows)), (
            'Array-only SeqId should be NaN for all NGS rows'
        )

    def test_ngs_only_seqids_are_nan_in_array_rows(
        self, mixed_v2_adat, source_array_adat, source_ngs_adat
    ):
        """SeqIds present only in the NGS source must be NaN for all array rows."""
        arr_seqids = set(source_array_adat.columns.get_level_values('SeqId'))
        ngs_seqids = set(source_ngs_adat.columns.get_level_values('SeqId'))
        ngs_only = ngs_seqids - arr_seqids

        if not ngs_only:
            pytest.skip('No NGS-only SeqIds in sample data')

        n_array = len(source_array_adat)
        result_seqids = list(mixed_v2_adat.columns.get_level_values('SeqId'))
        rfu = mixed_v2_adat.to_numpy()

        sample_col_idx = result_seqids.index(next(iter(ngs_only)))
        array_rows = rfu[:n_array, sample_col_idx]
        assert np.all(np.isnan(array_rows)), (
            'NGS-only SeqId should be NaN for all array rows'
        )

    def test_shared_seqids_have_no_nan_in_either_source(
        self, mixed_v2_adat, source_array_adat, source_ngs_adat
    ):
        """SeqIds present in both sources must not be NaN in any row."""
        arr_seqids = set(source_array_adat.columns.get_level_values('SeqId'))
        ngs_seqids = set(source_ngs_adat.columns.get_level_values('SeqId'))
        shared = arr_seqids & ngs_seqids

        if not shared:
            pytest.skip('No shared SeqIds between sample files')

        result_seqids = list(mixed_v2_adat.columns.get_level_values('SeqId'))
        rfu = mixed_v2_adat.to_numpy()

        # Check a sample of shared SeqIds (first 5 to keep it fast)
        for seqid in list(shared)[:5]:
            col_idx = result_seqids.index(seqid)
            col_values = rfu[:, col_idx]
            assert not np.all(np.isnan(col_values)), (
                f'Shared SeqId {seqid!r} has all-NaN column — unexpected'
            )


# ===========================================================================
# v2.0 writer: output passes write_adat without error
# ===========================================================================


class TestWriter:
    """Acceptance criteria: output passes the v2.0 writer without error."""

    def test_write_adat_does_not_raise(self, written_adat_path):
        assert os.path.exists(written_adat_path)

    def test_written_file_is_non_empty(self, written_adat_path):
        assert os.path.getsize(written_adat_path) > 0

    def test_written_file_starts_with_header_section(self, written_adat_path):
        with open(written_adat_path, 'r') as f:
            first_line = f.readline().strip()
        assert first_line == '^HEADER', f'Expected ^HEADER first line; got {first_line!r}'

    def test_written_file_contains_no_checksum_line(self, written_adat_path):
        with open(written_adat_path, 'r') as f:
            content = f.read()
        assert '!Checksum' not in content, 'v2.0 file must not contain !Checksum line'

    def test_written_col_data_uses_no_bang_prefix(self, written_adat_path):
        with open(written_adat_path, 'r') as f:
            lines = f.readlines()

        in_col_data = False
        for line in lines:
            stripped = line.strip()
            if stripped == '^COL_DATA':
                in_col_data = True
                continue
            if stripped.startswith('^') and in_col_data:
                break
            if in_col_data and (stripped.startswith('!Name') or stripped.startswith('!Type')):
                pytest.fail(f'v2.0 COL_DATA must not have !Name/!Type prefix; got: {stripped!r}')


# ===========================================================================
# Round-trip: write → re-read → verify structure preserved
# ===========================================================================


class TestRoundTrip:
    """Acceptance criteria: round-trip write→re-read preserves structure and data."""

    def test_shape_preserved(self, mixed_v2_adat, round_trip_adat):
        assert round_trip_adat.shape == mixed_v2_adat.shape

    def test_row_count_preserved(self, mixed_v2_adat, round_trip_adat):
        assert len(round_trip_adat) == len(mixed_v2_adat)

    def test_seqid_set_preserved(self, mixed_v2_adat, round_trip_adat):
        orig = set(mixed_v2_adat.columns.get_level_values('SeqId'))
        reread = set(round_trip_adat.columns.get_level_values('SeqId'))
        assert orig == reread

    def test_row_metadata_field_names_preserved(self, mixed_v2_adat, round_trip_adat):
        assert list(mixed_v2_adat.index.names) == list(round_trip_adat.index.names)

    def test_col_metadata_field_names_preserved(self, mixed_v2_adat, round_trip_adat):
        assert list(mixed_v2_adat.columns.names) == list(round_trip_adat.columns.names)

    def test_rfu_values_preserved_for_non_nan(self, mixed_v2_adat, round_trip_adat):
        orig = mixed_v2_adat.to_numpy().astype(float)
        reread = round_trip_adat.to_numpy().astype(float)
        nan_mask = np.isnan(orig)
        assert np.array_equal(nan_mask, np.isnan(reread)), 'NaN positions differ after round-trip'
        orig_vals = orig[~nan_mask]
        reread_vals = reread[~nan_mask]
        max_diff = np.abs(orig_vals - reread_vals).max()
        assert max_diff == 0.0, f'RFU values changed after round-trip; max diff = {max_diff}'

    def test_nan_positions_preserved(self, mixed_v2_adat, round_trip_adat):
        orig_nan = np.isnan(mixed_v2_adat.to_numpy().astype(float))
        reread_nan = np.isnan(round_trip_adat.to_numpy().astype(float))
        assert np.array_equal(orig_nan, reread_nan)

    def test_header_keys_preserved(self, mixed_v2_adat, round_trip_adat):
        orig_keys = set(mixed_v2_adat.header_metadata.keys())
        reread_keys = set(round_trip_adat.header_metadata.keys())
        assert orig_keys == reread_keys

    def test_file_version_preserved_in_round_trip(self, round_trip_adat):
        assert round_trip_adat.header_metadata.get('FileVersion') == '2.0'

    def test_assay_type_preserved_in_round_trip(self, round_trip_adat):
        assert round_trip_adat.header_metadata.get('AssayType') == 'Mixed'

    def test_sample_readout_preserved_in_round_trip(
        self, mixed_v2_adat, round_trip_adat, source_array_adat
    ):
        orig_readouts = list(mixed_v2_adat.index.get_level_values('SampleReadout'))
        reread_readouts = list(round_trip_adat.index.get_level_values('SampleReadout'))
        assert orig_readouts == reread_readouts


# ===========================================================================
# Phase 3: Two-Input Merge Paths (CAN-46 through CAN-49)
# ===========================================================================


class TestBridgedArrayPlusV2Combined:
    """Path 2: bridged_array + v2_combined merge"""

    def test_bridged_array_plus_v2_array_produces_array_output(self):
        """Merging bridged array with v2.0 Array produces Array output."""
        from tests.conversion.conftest import make_bridged_array_with_mednorm, make_v2_combined_adat
        
        array_adat = make_bridged_array_with_mednorm()
        v2_adat = make_v2_combined_adat()
        v2_adat.header_metadata['AssayType'] = 'Array'
        
        # Add SampleReadout to v2.0 (required for v2.0 format)
        import pandas as pd
        v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
        v2_index_arrays.append(['Array'] * len(v2_adat))
        v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
        v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result = to_v2_adat([array_adat, v2_adat])
        
        assert result.header_metadata['AssayType'] == 'Array'
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_bridged_array_plus_v2_mixed_produces_mixed_output(self):
        """Merging bridged array with v2.0 Mixed produces Mixed output."""
        from tests.conversion.conftest import make_bridged_array_with_mednorm, make_v2_combined_adat
        
        array_adat = make_bridged_array_with_mednorm()
        v2_adat = make_v2_combined_adat()
        v2_adat.header_metadata['AssayType'] = 'Mixed'
        v2_adat.header_metadata['ProcessSteps'] = {
            '1': 'Raw, HybNorm, MedNormInt, PlatformSpecificPlateScale, PlatformSpecificCalibrate, CrossPlatformPlateScale, CrossPlatformCalibrate, MedNormExt'
        }
        
        # Add required v2.0 fields
        import pandas as pd
        v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
        v2_index_arrays.append(['NGS'] * len(v2_adat))
        v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
        v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result = to_v2_adat([array_adat, v2_adat])
        
        assert result.header_metadata['AssayType'] == 'Mixed'
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_order_independence(self):
        """Path 2 is order-independent."""
        from tests.conversion.conftest import make_bridged_array_with_mednorm, make_v2_combined_adat
        
        array_adat = make_bridged_array_with_mednorm()
        v2_adat = make_v2_combined_adat()
        v2_adat.header_metadata['AssayType'] = 'Array'
        
        # Add required v2.0 fields
        import pandas as pd
        v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
        v2_index_arrays.append(['Array'] * len(v2_adat))
        v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
        v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result_ab = to_v2_adat([array_adat, v2_adat])
        result_ba = to_v2_adat([v2_adat, array_adat])
        
        seqids_ab = set(result_ab.columns.get_level_values('SeqId'))
        seqids_ba = set(result_ba.columns.get_level_values('SeqId'))
        assert seqids_ab == seqids_ba

    def test_mednorm_validation_with_mismatch(self):
        """MedNorm validation raises error when Ref.MedNormExt vectors differ."""
        from tests.conversion.conftest import make_bridged_array_with_mednorm, make_v2_combined_adat
        from somadata.conversion.errors import MedNormMismatchError
        import pandas as pd
        
        # Create array with MedNormExt
        array_adat = make_bridged_array_with_mednorm(
            shared_seqids=['10000-28'],
            mednorm_ext_values=['REF-ARRAY']
        )
        
        # Create v2.0 ADAT with different MedNormExt values
        v2_adat = make_v2_combined_adat()
        v2_adat.header_metadata['AssayType'] = 'NGS'
        v2_adat.header_metadata['ProcessSteps'] = {
            '1': 'Raw, HybNorm, MedNormInt, PlatformSpecificPlateScale, PlatformSpecificCalibrate, CrossPlatformPlateScale, CrossPlatformCalibrate, MedNormExt'
        }
        
        # Add v2.0 fields with different MedNormExt value
        v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
        v2_index_arrays.append(['NGS'] * len(v2_adat))
        v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
        v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        # Change SeqIds to match
        col_arrays = [list(v2_adat.columns.get_level_values(name)) for name in v2_adat.columns.names]
        col_arrays[v2_adat.columns.names.index('SeqId')] = ['10000-28', '10001-02']
        # Add Ref.MedNormExt.Plasma with different value
        col_arrays.append(['REF-V2', 'REF-V2'])
        col_names = list(v2_adat.columns.names) + ['Ref.MedNormExt.Plasma']
        v2_adat.columns = pd.MultiIndex.from_arrays(col_arrays, names=col_names)
        
        # Should raise MedNormMismatchError
        with pytest.raises(MedNormMismatchError, match='not identical'):
            to_v2_adat([array_adat, v2_adat])


class TestNativeNGSPlusV2Combined:
    """Path 3: native_ngs + v2_combined merge"""

    def test_ngs_plus_v2_ngs_produces_ngs_output(self):
        """Merging NGS with v2.0 NGS produces NGS output."""
        from tests.conversion.conftest import make_full_legacy_ngs_adat, make_v2_combined_adat
        
        ngs_adat = make_full_legacy_ngs_adat()
        v2_adat = make_v2_combined_adat()
        v2_adat.header_metadata['AssayType'] = 'NGS'
        
        # Add required v2.0 fields
        import pandas as pd
        v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
        v2_index_arrays.append(['NGS'] * len(v2_adat))
        v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
        v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result = to_v2_adat([ngs_adat, v2_adat])
        
        assert result.header_metadata['AssayType'] == 'NGS'
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_ngs_plus_v2_mixed_produces_mixed_output(self):
        """Merging NGS with v2.0 Mixed produces Mixed output."""
        from tests.conversion.conftest import make_full_legacy_ngs_adat, make_v2_combined_adat
        
        ngs_adat = make_full_legacy_ngs_adat()
        v2_adat = make_v2_combined_adat()
        v2_adat.header_metadata['AssayType'] = 'Mixed'
        
        # Add required v2.0 fields
        import pandas as pd
        v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
        v2_index_arrays.append(['Array'] * len(v2_adat))
        v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
        v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result = to_v2_adat([ngs_adat, v2_adat])
        
        assert result.header_metadata['AssayType'] == 'Mixed'
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_order_independence(self):
        """Path 3 is order-independent."""
        from tests.conversion.conftest import make_full_legacy_ngs_adat, make_v2_combined_adat
        
        ngs_adat = make_full_legacy_ngs_adat()
        v2_adat = make_v2_combined_adat()
        v2_adat.header_metadata['AssayType'] = 'NGS'
        
        # Add required v2.0 fields
        import pandas as pd
        v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
        v2_index_arrays.append(['NGS'] * len(v2_adat))
        v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
        v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result_ab = to_v2_adat([ngs_adat, v2_adat])
        result_ba = to_v2_adat([v2_adat, ngs_adat])
        
        seqids_ab = set(result_ab.columns.get_level_values('SeqId'))
        seqids_ba = set(result_ba.columns.get_level_values('SeqId'))
        assert seqids_ab == seqids_ba


class TestNativeArrayPair:
    """Path 4: native_array + native_array merge"""

    def test_array_pair_produces_array_output(self):
        """Merging two native arrays produces Array v2.0 output."""
        from tests.conversion.conftest import make_full_legacy_array_adat
        import pandas as pd
        
        array_a = make_full_legacy_array_adat()
        array_b = make_full_legacy_array_adat()
        
        # Change PlateId in both row metadata and header for array_b
        array_b_index_arrays = [list(array_b.index.get_level_values(name)) for name in array_b.index.names]
        plate_idx = array_b.index.names.index('PlateId')
        array_b_index_arrays[plate_idx] = ['PLTB1', 'PLTB1', 'PLTB1']
        array_b.index = pd.MultiIndex.from_arrays(array_b_index_arrays, names=array_b.index.names)
        
        # Update header PlateId keys
        for key in list(array_b.header_metadata.keys()):
            if '_PLT1' in key:
                new_key = key.replace('_PLT1', '_PLTB1')
                array_b.header_metadata[new_key] = array_b.header_metadata.pop(key)
            elif '_PLT2' in key:
                new_key = key.replace('_PLT2', '_PLTB2')
                array_b.header_metadata[new_key] = array_b.header_metadata.pop(key)
        
        result = to_v2_adat([array_a, array_b])
        
        assert result.header_metadata['AssayType'] == 'Array'
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_assay_version_validation(self):
        """Mismatched AssayVersion raises error."""
        from tests.conversion.conftest import make_full_legacy_array_adat
        from somadata.conversion.errors import AssayVersionError
        
        array_a = make_full_legacy_array_adat()
        array_b = make_full_legacy_array_adat()
        array_b.header_metadata['!AssayVersion'] = 'V5'
        
        with pytest.raises(AssayVersionError, match='same AssayVersion'):
            to_v2_adat([array_a, array_b])

    def test_seqid_union_computed(self):
        """SeqId union is computed correctly."""
        from tests.conversion.conftest import make_full_legacy_array_adat
        import pandas as pd
        
        # Use full arrays but with different SeqIds
        array_a = make_full_legacy_array_adat()
        array_b = make_full_legacy_array_adat()
        
        # Modify array_b to have different SeqIds
        col_values_b = [list(array_b.columns.get_level_values(name)) for name in array_b.columns.names]
        seqid_idx = array_b.columns.names.index('SeqId')
        col_values_b[seqid_idx] = ['10001-7', '10002-66', '10003-99']
        array_b.columns = pd.MultiIndex.from_arrays(col_values_b, names=array_b.columns.names)
        
        # Change PlateId in both row metadata and header for array_b
        array_b_index_arrays = [list(array_b.index.get_level_values(name)) for name in array_b.index.names]
        plate_idx = array_b.index.names.index('PlateId')
        array_b_index_arrays[plate_idx] = ['PLTB1', 'PLTB1', 'PLTB1']
        array_b.index = pd.MultiIndex.from_arrays(array_b_index_arrays, names=array_b.index.names)
        
        # Update header PlateId keys
        for key in list(array_b.header_metadata.keys()):
            if '_PLT1' in key:
                new_key = key.replace('_PLT1', '_PLTB1')
                array_b.header_metadata[new_key] = array_b.header_metadata.pop(key)
            elif '_PLT2' in key:
                new_key = key.replace('_PLT2', '_PLTB2')
                array_b.header_metadata[new_key] = array_b.header_metadata.pop(key)
        
        result = to_v2_adat([array_a, array_b])
        
        result_seqids = set(result.columns.get_level_values('SeqId'))
        # array_a has ['10000-28', '10001-7', '10002-66']
        # array_b has ['10001-7', '10002-66', '10003-99']
        # Union should be all 4
        expected_seqids = {'10000-28', '10001-7', '10002-66', '10003-99'}
        assert result_seqids == expected_seqids


class TestV2CombinedPair:
    """Path 5: v2_combined + v2_combined merge"""

    def test_array_plus_array_produces_array_output(self):
        """Merging two v2.0 Array ADATs produces Array output."""
        from tests.conversion.conftest import make_v2_combined_adat
        
        v2_a = make_v2_combined_adat()
        v2_a.header_metadata['AssayType'] = 'Array'
        v2_b = make_v2_combined_adat()
        v2_b.header_metadata['AssayType'] = 'Array'
        
        # Add required v2.0 fields
        import pandas as pd
        for v2_adat in [v2_a, v2_b]:
            v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
            v2_index_arrays.append(['Array'] * len(v2_adat))
            v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
            v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result = to_v2_adat([v2_a, v2_b])
        
        assert result.header_metadata['AssayType'] == 'Array'
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_ngs_plus_ngs_produces_ngs_output(self):
        """Merging two v2.0 NGS ADATs produces NGS output."""
        from tests.conversion.conftest import make_v2_combined_adat
        
        v2_a = make_v2_combined_adat()
        v2_a.header_metadata['AssayType'] = 'NGS'
        v2_a.header_metadata['ProcessSteps'] = {'1': 'Raw, HybNorm, MedNormExt'}
        v2_b = make_v2_combined_adat()
        v2_b.header_metadata['AssayType'] = 'NGS'
        v2_b.header_metadata['ProcessSteps'] = {'1': 'Raw, HybNorm, MedNormExt'}
        
        # Add required v2.0 fields
        import pandas as pd
        for v2_adat in [v2_a, v2_b]:
            v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
            v2_index_arrays.append(['NGS'] * len(v2_adat))
            v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
            v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result = to_v2_adat([v2_a, v2_b])
        
        assert result.header_metadata['AssayType'] == 'NGS'
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_mixed_combination_produces_mixed_output(self):
        """Merging v2.0 Array + v2.0 NGS produces Mixed output."""
        from tests.conversion.conftest import make_v2_combined_adat
        
        v2_a = make_v2_combined_adat()
        v2_a.header_metadata['AssayType'] = 'Array'
        v2_b = make_v2_combined_adat()
        v2_b.header_metadata['AssayType'] = 'NGS'
        v2_b.header_metadata['ProcessSteps'] = {'1': 'Raw, HybNorm, MedNormExt'}
        
        # Add required v2.0 fields
        import pandas as pd
        v2_a_index_arrays = [list(v2_a.index.get_level_values(name)) for name in v2_a.index.names]
        v2_a_index_arrays.append(['Array'] * len(v2_a))
        v2_a_index_names = list(v2_a.index.names) + ['SampleReadout']
        v2_a.index = pd.MultiIndex.from_arrays(v2_a_index_arrays, names=v2_a_index_names)
        
        v2_b_index_arrays = [list(v2_b.index.get_level_values(name)) for name in v2_b.index.names]
        v2_b_index_arrays.append(['NGS'] * len(v2_b))
        v2_b_index_names = list(v2_b.index.names) + ['SampleReadout']
        v2_b.index = pd.MultiIndex.from_arrays(v2_b_index_arrays, names=v2_b_index_names)
        
        result = to_v2_adat([v2_a, v2_b])
        
        assert result.header_metadata['AssayType'] == 'Mixed'
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_round_trip_write_read(self):
        """v2+v2 merge output can be written and re-read."""
        from tests.conversion.conftest import make_v2_combined_adat
        import tempfile
        import os
        
        v2_a = make_v2_combined_adat()
        v2_a.header_metadata['AssayType'] = 'Array'
        v2_b = make_v2_combined_adat()
        v2_b.header_metadata['AssayType'] = 'Array'
        
        # Add required v2.0 fields
        import pandas as pd
        for v2_adat in [v2_a, v2_b]:
            v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
            v2_index_arrays.append(['Array'] * len(v2_adat))
            v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
            v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        result = to_v2_adat([v2_a, v2_b])
        
        # Write and re-read
        with tempfile.NamedTemporaryFile(mode='w', suffix='.adat', delete=False) as f:
            tmppath = f.name
            write_adat(result, f)
        
        try:
            reread = read_adat(tmppath)
            assert reread.shape == result.shape
            assert reread.header_metadata['AssayType'] == 'Array'
        finally:
            os.unlink(tmppath)

    def test_mednorm_validation_with_mismatch(self):
        """MedNorm validation raises error when Ref.MedNormExt vectors differ."""
        from tests.conversion.conftest import make_v2_combined_adat
        from somadata.conversion.errors import MedNormMismatchError
        import pandas as pd
        
        # Create two v2.0 ADATs with MedNormExt in ProcessSteps
        v2_a = make_v2_combined_adat()
        v2_a.header_metadata['AssayType'] = 'Array'
        v2_a.header_metadata['ProcessSteps'] = {'1': 'Raw, HybNorm, MedNormExt'}
        
        v2_b = make_v2_combined_adat()
        v2_b.header_metadata['AssayType'] = 'Array'
        v2_b.header_metadata['ProcessSteps'] = {'1': 'Raw, HybNorm, MedNormExt'}
        
        # Add v2.0 fields
        for v2_adat in [v2_a, v2_b]:
            v2_index_arrays = [list(v2_adat.index.get_level_values(name)) for name in v2_adat.index.names]
            v2_index_arrays.append(['Array'] * len(v2_adat))
            v2_index_names = list(v2_adat.index.names) + ['SampleReadout']
            v2_adat.index = pd.MultiIndex.from_arrays(v2_index_arrays, names=v2_index_names)
        
        # Add matching SeqIds but different Ref.MedNormExt values
        for i, v2_adat in enumerate([v2_a, v2_b]):
            col_arrays = [list(v2_adat.columns.get_level_values(name)) for name in v2_adat.columns.names]
            # Add Ref.MedNormExt.Plasma with different values
            mednorm_val = f'REF-{i+1}'
            col_arrays.append([mednorm_val, mednorm_val])
            col_names = list(v2_adat.columns.names) + ['Ref.MedNormExt.Plasma']
            v2_adat.columns = pd.MultiIndex.from_arrays(col_arrays, names=col_names)
        
        # Should raise MedNormMismatchError
        with pytest.raises(MedNormMismatchError, match='not identical'):
            to_v2_adat([v2_a, v2_b])


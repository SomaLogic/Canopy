"""Tests for somadata.conversion.merge."""

from __future__ import annotations

import numpy as np
import pytest
import pandas as pd

from somadata.adat import Adat
from somadata.conversion.merge import (
    compute_seqid_union,
    merge_mixed_headers,
    validate_mednorm_compatibility,
)
from somadata.conversion._helpers import merge_pipe_delimited, merge_plate_json
from somadata.conversion.errors import MedNormMismatchError, ProcessStepsMismatchError
from tests.conversion.conftest import (
    make_bridged_array_with_mednorm,
    make_full_legacy_ngs_adat,
)


# ---------------------------------------------------------------------------
# Helpers — build minimal v2.0 converted Adats for SeqId union tests
# ---------------------------------------------------------------------------


def _make_converted_adat(
    seqids: list[str],
    extra_levels: dict | None = None,
    n_rows: int = 2,
) -> Adat:
    """Build a minimal converted v2.0 Adat with given SeqIds in COL_DATA."""
    extra_levels = extra_levels or {}
    col_arrays = [seqids]
    col_names = ['SeqId']
    for level_name, values in extra_levels.items():
        col_names.append(level_name)
        col_arrays.append(values)

    columns = pd.MultiIndex.from_arrays(col_arrays, names=col_names)
    index = pd.MultiIndex.from_arrays(
        [[f'S{i}' for i in range(n_rows)], ['Sample'] * n_rows],
        names=['SampleId', 'SampleType'],
    )
    data = [[1.0] * len(seqids)] * n_rows
    return Adat(data=data, index=index, columns=columns, header_metadata={})


# ===========================================================================
# SeqId Union & Missing Value Fill
# ===========================================================================


class TestComputeSeqidUnion:
    def test_identical_seqid_sets(self):
        seqids = ['A', 'B', 'C']
        array_adat = _make_converted_adat(seqids)
        ngs_adat = _make_converted_adat(seqids)
        rfu_df, merged_cols = compute_seqid_union(array_adat, ngs_adat)

        assert list(merged_cols.get_level_values('SeqId')) == seqids
        assert rfu_df.shape == (4, 3)  # 2+2 rows, 3 cols

    def test_overlapping_seqid_sets(self):
        array_adat = _make_converted_adat(['A', 'B'])
        ngs_adat = _make_converted_adat(['B', 'C'])
        rfu_df, merged_cols = compute_seqid_union(array_adat, ngs_adat)

        union_seqids = list(merged_cols.get_level_values('SeqId'))
        assert union_seqids == ['A', 'B', 'C']
        assert rfu_df.shape == (4, 3)  # 2+2 rows, 3 SeqIds

    def test_disjoint_seqid_sets(self):
        array_adat = _make_converted_adat(['A', 'B'])
        ngs_adat = _make_converted_adat(['C', 'D'])
        rfu_df, merged_cols = compute_seqid_union(array_adat, ngs_adat)

        union_seqids = list(merged_cols.get_level_values('SeqId'))
        assert union_seqids == ['A', 'B', 'C', 'D']
        assert rfu_df.shape == (4, 4)

    def test_nan_fill_for_missing_seqids(self):
        """Array-only SeqIds should be NaN in NGS rows and vice versa."""
        array_adat = _make_converted_adat(['A', 'B'], n_rows=1)
        ngs_adat = _make_converted_adat(['B', 'C'], n_rows=1)
        rfu_df, _ = compute_seqid_union(array_adat, ngs_adat)

        # Row 0 = array, row 1 = ngs (after concat)
        assert rfu_df.shape == (2, 3)
        # Array row: A=1.0, B=1.0, C=NaN
        assert rfu_df.iloc[0, 0] == 1.0
        assert rfu_df.iloc[0, 1] == 1.0
        assert np.isnan(rfu_df.iloc[0, 2])
        # NGS row: A=NaN, B=1.0, C=1.0
        assert np.isnan(rfu_df.iloc[1, 0])
        assert rfu_df.iloc[1, 1] == 1.0
        assert rfu_df.iloc[1, 2] == 1.0

    def test_column_ordering_sorted_ascending(self):
        """Union SeqIds must be sorted ascending."""
        array_adat = _make_converted_adat(['Z', 'A'])
        ngs_adat = _make_converted_adat(['M', 'A'])
        _, merged_cols = compute_seqid_union(array_adat, ngs_adat)

        union_seqids = list(merged_cols.get_level_values('SeqId'))
        assert union_seqids == sorted(union_seqids)

    def test_array_rows_first(self):
        """Array sample IDs should appear before NGS sample IDs."""
        array_adat = _make_converted_adat(['A', 'B'], n_rows=2)
        ngs_adat = _make_converted_adat(['A', 'B'], n_rows=3)
        rfu_df, _ = compute_seqid_union(array_adat, ngs_adat)

        sample_ids = list(rfu_df.index.get_level_values('SampleId'))
        assert sample_ids[:2] == ['S0', 'S1']   # array
        assert sample_ids[2:] == ['S0', 'S1', 'S2']  # ngs

    def test_merged_col_data_annotation_levels(self):
        """Merged COL_DATA includes levels from both sources."""
        array_adat = _make_converted_adat(
            ['A', 'B'],
            extra_levels={'Target': ['ProteinA', 'ProteinB'], 'HybControl': ['False', 'False']},
        )
        ngs_adat = _make_converted_adat(
            ['B', 'C'],
            extra_levels={'Target': ['ProteinB', 'ProteinC'], 'DRCLevel_Plasma_NGS': ['0', '1']},
        )
        _, merged_cols = compute_seqid_union(array_adat, ngs_adat)

        assert 'SeqId' in merged_cols.names
        assert 'Target' in merged_cols.names
        assert 'HybControl' in merged_cols.names
        assert 'DRCLevel_Plasma_NGS' in merged_cols.names

    def test_shared_seqid_prefers_array_annotation(self):
        """For shared SeqIds, array annotation values take precedence."""
        array_adat = _make_converted_adat(
            ['A'], extra_levels={'Target': ['ArrayTarget']}
        )
        ngs_adat = _make_converted_adat(
            ['A'], extra_levels={'Target': ['NGSTarget']}
        )
        _, merged_cols = compute_seqid_union(array_adat, ngs_adat)

        target_vals = list(merged_cols.get_level_values('Target'))
        assert target_vals == ['ArrayTarget']  # array value preferred

    def test_ngs_only_seqid_blank_array_fields(self):
        """NGS-only SeqIds get blank values for array-exclusive annotation fields."""
        array_adat = _make_converted_adat(
            ['A'], extra_levels={'HybControl': ['False']}
        )
        ngs_adat = _make_converted_adat(
            ['B'], extra_levels={'DRCLevel_Plasma_NGS': ['0']}
        )
        _, merged_cols = compute_seqid_union(array_adat, ngs_adat)

        union_seqids = list(merged_cols.get_level_values('SeqId'))
        hyb_vals = dict(zip(union_seqids, merged_cols.get_level_values('HybControl')))
        # NGS-only SeqId 'B' has no HybControl from array → blank
        assert hyb_vals['B'] == ''
        assert hyb_vals['A'] == 'False'

    def test_raises_without_seqid_level(self):
        """Raises ValueError if either Adat lacks a SeqId level."""
        bad = _make_converted_adat(['A'])
        # Replace columns with one lacking SeqId
        bad_cols = pd.MultiIndex.from_arrays([['A']], names=['Other'])
        bad = Adat(data=bad.values, index=bad.index, columns=bad_cols, header_metadata={})
        good = _make_converted_adat(['A'])
        with pytest.raises(ValueError, match='SeqId'):
            compute_seqid_union(bad, good)



# ===========================================================================
# MedNorm Reference Validation
# ===========================================================================


class TestValidateMednormCompatibility:
    def test_matching_refs_pass(self):
        """Matching Ref.MedNormExt vectors and correct ProcessSteps should pass."""
        array_adat = make_bridged_array_with_mednorm()
        ngs_adat = make_full_legacy_ngs_adat()
        # Should not raise
        validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_wrong_array_process_steps_raises(self):
        """Non-bridged array ProcessSteps should raise ProcessStepsMismatchError."""
        from tests.conversion.conftest import make_array_adat, NATIVE_STEPS

        array_adat = make_array_adat(process_steps=NATIVE_STEPS)
        ngs_adat = make_full_legacy_ngs_adat()
        with pytest.raises(ProcessStepsMismatchError, match='terminal triple'):
            validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_wrong_ngs_process_steps_raises(self):
        """NGS with non-standard ProcessSteps should raise ProcessStepsMismatchError."""
        from tests.conversion.conftest import make_ngs_adat

        array_adat = make_bridged_array_with_mednorm()
        # make_ngs_adat has no ProcessSteps → will fail validation
        ngs_adat = make_ngs_adat()
        with pytest.raises(ProcessStepsMismatchError, match='NGS ADAT ProcessSteps'):
            validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_mismatched_refs_raise_mednorm_error(self):
        """Mismatched Ref.MedNormExt values should raise MedNormMismatchError."""
        array_adat = make_bridged_array_with_mednorm(
            mednorm_ext_values=[1200.0, 950.0]
        )
        ngs_adat = make_full_legacy_ngs_adat(
            mednorm_ext_values=[1200.0, 999.9]
        )
        with pytest.raises(MedNormMismatchError, match='Ref.MedNormExt'):
            validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_med_norm_ref_override_resolves_mismatch(self):
        """With no override mechanism, a mismatch always raises MedNormMismatchError."""
        array_adat = make_bridged_array_with_mednorm(
            mednorm_ext_values=[1200.0, 950.0]
        )
        ngs_adat = make_full_legacy_ngs_adat(
            mednorm_ext_values=[1200.0, 999.9]
        )
        # spec §3.4: mismatched Ref.MedNormExt must raise — no override allowed
        with pytest.raises(MedNormMismatchError, match='Ref.MedNormExt'):
            validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_med_norm_ref_returns_none_when_vectors_identical(self):
        """validate_mednorm_compatibility returns None when no mismatch exists."""
        array_adat = make_bridged_array_with_mednorm()
        ngs_adat = make_full_legacy_ngs_adat()
        # Should not raise when vectors are identical
        validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_med_norm_ref_returns_array_when_override_matches_array(self):
        """Mismatch always raises; override behavior is no longer supported."""
        from somadata.adat import Adat
        from tests.conversion.conftest import BRIDGED_STEPS, NGS_BRIDGED_STEPS

        # Array source with Ref.MedNorm.Id = 'ARRAY-REF'
        array_cols = pd.MultiIndex.from_arrays(
            [['10000-28', '10001-7'], ['1.0', '2.0'], ['ARRAY-REF', 'ARRAY-REF']],
            names=['SeqId', 'Ref.MedNormExt.Plasma', 'Ref.MedNorm.Id'],
        )
        array_adat = Adat(
            data=[[1.0, 1.0]],
            index=pd.MultiIndex.from_arrays([['S1'], ['Sample']], names=['SampleId', 'SampleType']),
            columns=array_cols,
            header_metadata={'!ProcessSteps': BRIDGED_STEPS},
        )
        # NGS source with different values — mismatch → must raise
        ngs_cols = pd.MultiIndex.from_arrays(
            [['10000-28', '10001-7'], ['1.0', '99.0'], ['NGS-REF', 'NGS-REF']],
            names=['SeqId', 'Ref.MedNormExt.Plasma', 'Ref.MedNorm.Id'],
        )
        ngs_adat = Adat(
            data=[[1.0, 1.0]],
            index=pd.MultiIndex.from_arrays([['N1'], ['Sample']], names=['SampleId', 'SampleType']),
            columns=ngs_cols,
            header_metadata={'!ProcessSteps': NGS_BRIDGED_STEPS},
        )
        with pytest.raises(MedNormMismatchError):
            validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_med_norm_ref_returns_ngs_when_override_matches_ngs(self):
        """Mismatch always raises; override behavior is no longer supported."""
        from somadata.adat import Adat
        from tests.conversion.conftest import BRIDGED_STEPS, NGS_BRIDGED_STEPS

        array_cols = pd.MultiIndex.from_arrays(
            [['10000-28', '10001-7'], ['1.0', '2.0'], ['ARRAY-REF', 'ARRAY-REF']],
            names=['SeqId', 'Ref.MedNormExt.Plasma', 'Ref.MedNorm.Id'],
        )
        array_adat = Adat(
            data=[[1.0, 1.0]],
            index=pd.MultiIndex.from_arrays([['S1'], ['Sample']], names=['SampleId', 'SampleType']),
            columns=array_cols,
            header_metadata={'!ProcessSteps': BRIDGED_STEPS},
        )
        ngs_cols = pd.MultiIndex.from_arrays(
            [['10000-28', '10001-7'], ['1.0', '99.0'], ['NGS-REF', 'NGS-REF']],
            names=['SeqId', 'Ref.MedNormExt.Plasma', 'Ref.MedNorm.Id'],
        )
        ngs_adat = Adat(
            data=[[1.0, 1.0]],
            index=pd.MultiIndex.from_arrays([['N1'], ['Sample']], names=['SampleId', 'SampleType']),
            columns=ngs_cols,
            header_metadata={'!ProcessSteps': NGS_BRIDGED_STEPS},
        )
        with pytest.raises(MedNormMismatchError):
            validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_bad_med_norm_ref_raises(self):
        """Mismatch always raises MedNormMismatchError regardless of source IDs."""
        array_adat = make_bridged_array_with_mednorm(
            mednorm_ext_values=[1200.0, 950.0]
        )
        ngs_adat = make_full_legacy_ngs_adat(
            mednorm_ext_values=[1200.0, 999.9]
        )
        with pytest.raises(MedNormMismatchError, match='Ref.MedNormExt'):
            validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_no_shared_seqids_skips_vector_check(self):
        """Completely disjoint SeqId sets should skip MedNorm vector comparison."""
        array_adat = make_bridged_array_with_mednorm(
            shared_seqids=['10000-28'],
            array_only_seqids=['30000-01'],
            mednorm_ext_values=[1200.0],
        )
        ngs_adat = make_full_legacy_ngs_adat(
            shared_seqids=['99999-01'],  # no overlap with array source
            ngs_only_seqids=['88888-01'],
            mednorm_ext_values=[800.0],  # 1 value for 1 shared SeqId
        )
        # Should not raise — no shared SeqIds means no vector comparison
        validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_numeric_mednorm_values_with_rounding_tolerance(self):
        """Numeric MedNormExt values should use tolerance-based comparison.
        
        Real-world RFU reference values may differ slightly due to floating-point
        precision from different computation paths (e.g., reading from different
        file formats, intermediate rounding in pipelines). These should be
        considered equal within a reasonable tolerance.
        """
        # Create ADATs with numeric MedNormExt values that differ by tiny amounts
        # due to floating-point precision (not actual biological differences)
        array_adat = make_bridged_array_with_mednorm(
            shared_seqids=['10000-28', '10001-7'],
            array_only_seqids=['30000-01'],
            mednorm_ext_values=[1234.56789, 9876.54321],
        )
        
        # Simulate slightly different values from NGS source due to rounding
        # (difference of ~1e-12, within floating-point tolerance)
        ngs_adat = make_full_legacy_ngs_adat(
            shared_seqids=['10000-28', '10001-7'],
            ngs_only_seqids=['20000-01'],
            mednorm_ext_values=[1234.567890000001, 9876.543210000001],
        )
        
        # Should not raise — values are identical within tolerance
        validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_numeric_mednorm_values_outside_tolerance_raises(self):
        """Numeric MedNormExt values that differ significantly should raise."""
        array_adat = make_bridged_array_with_mednorm(
            mednorm_ext_values=[1234.5, 9876.5],
        )
        
        # Significant difference (0.1 units) should raise
        ngs_adat = make_full_legacy_ngs_adat(
            mednorm_ext_values=[1234.5, 9876.6],  # Different by 0.1
        )
        
        with pytest.raises(MedNormMismatchError, match='Ref.MedNormExt'):
            validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_missing_ngs_mednorm_values_skipped(self):
        """SeqIds with missing/NA MedNormExt values in NGS should be skipped.
        
        Internal-use-only (IUO) SOMAmers or array-exclusive calibrators may
        appear in both datasets but have no MedNormExt reference value in the
        NGS source (e.g., NaN, blank, or 'NA'). These should not cause
        validation failures.
        """
        # Create array ADAT with MedNormExt values for all SeqIds (including IUO)
        array_adat = make_bridged_array_with_mednorm(
            shared_seqids=['10000-28', '10001-7'],
            array_only_seqids=['10002-9'],  # IUO analyte
            mednorm_ext_values=[1234.5, 5678.9],  # Only for shared SeqIds
        )
        
        # Create NGS ADAT with one extra SeqId that has a missing MedNormExt value
        # The third SeqId (10002-9) appears in both, but NGS has blank/missing value
        ngs_adat = make_full_legacy_ngs_adat(
            shared_seqids=['10000-28', '10001-7'],
            ngs_only_seqids=['10002-9'],  # Same IUO analyte
            mednorm_ext_values=[1234.5, 5678.9],  # Only for first two
        )
        
        # Manually add the third SeqId to NGS with blank MedNormExt
        # (simulating an IUO analyte that exists in both but has no NGS MedNormExt ref)
        # For now, this scenario is handled by SeqId filtering — the IUO analyte
        # won't be in shared_seqids if it's in different lists. Let me revise...
        
        # Actually, create a simpler test: both have the same SeqIds, but NGS
        # has a blank value for one
        array_adat = make_bridged_array_with_mednorm(
            shared_seqids=['10000-28', '10001-7'],
            array_only_seqids=[],
            mednorm_ext_values=[1234.5, 5678.9],
        )
        
        # Manually modify NGS ADAT to have a blank MedNormExt for second SeqId
        ngs_adat = make_full_legacy_ngs_adat(
            shared_seqids=['10000-28', '10001-7'],
            ngs_only_seqids=[],
            mednorm_ext_values=[1234.5, ''],  # Second is blank (IUO)
        )
        
        # Should not raise — missing NGS values are skipped
        validate_mednorm_compatibility(array_adat, ngs_adat)

    def test_na_string_mednorm_values_skipped(self):
        """SeqIds with 'NA' string MedNormExt values should be skipped."""
        array_adat = make_bridged_array_with_mednorm(
            shared_seqids=['10000-28', '10001-7'],
            array_only_seqids=[],
            mednorm_ext_values=[1234.5, 'NA'],  # Second value is 'NA'
        )

        ngs_adat = make_full_legacy_ngs_adat(
            shared_seqids=['10000-28', '10001-7'],
            ngs_only_seqids=[],
            mednorm_ext_values=[1234.5, 'NA'],  # Also 'NA'
        )

        # Should not raise — 'NA' values are treated as missing
        validate_mednorm_compatibility(array_adat, ngs_adat)


# ===========================================================================
# Mixed Header & Metadata Combination
# ===========================================================================


def _make_minimal_array_ctx():
    from somadata.conversion.array import ArrayConversionContext

    ctx = ArrayConversionContext()
    ctx.source_file_id = '1'
    ctx.process_steps_id = '1'
    ctx.report_config_id = '1'
    return ctx


def _make_minimal_ngs_ctx():
    from somadata.conversion.ngs import NGSConversionContext

    ctx = NGSConversionContext()
    ctx.source_file_id = '2'
    ctx.process_steps_id = '2'
    return ctx


def _base_array_header():
    from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES

    h = {k: '' for k in V2_HEADER_FIELD_TYPES}
    h['FileVersion'] = '2.0'
    h['AssayType'] = 'Mixed'
    h['AdatId'] = 'GUID-ARRAY'
    h['AssayVersion'] = 'v4'
    h['SourceFile'] = {'1': {'AdatId': 'SL-OLD-ARRAY'}}
    h['ProcessSteps'] = {'1': ['Raw', 'Hyb', 'MedNormExt']}
    h['ReportConfig'] = {'1': 'DefaultReport'}
    h['Title'] = 'Study A'
    h['StudyOrganism'] = 'Human'
    h['StudyMatrix'] = 'EDTA Plasma'
    h['SOMAmerReferenceSource'] = '2020-08-07'
    h['UseRestriction'] = 'Research Use Only'
    h['PlateScaleScalar'] = {'PLT1': {'PlatformSpecific': '1.02'}}
    h['PlateScaleStatus'] = {'PLT1': 'PASS'}
    return h


def _base_ngs_header():
    from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES

    h = {k: '' for k in V2_HEADER_FIELD_TYPES}
    h['FileVersion'] = '2.0'
    h['AssayType'] = 'Mixed'
    h['AdatId'] = 'GUID-NGS'
    h['SourceFile'] = {'1': {'AdatId': 'SL-OLD-NGS'}}
    h['ProcessSteps'] = {'1': ['Raw', 'HybNorm', 'MedNormExt']}
    h['ReportConfig'] = ''
    h['Title'] = 'Study B'
    h['StudyOrganism'] = 'Mouse'
    h['StudyMatrix'] = 'Serum'
    h['SOMAmerReferenceSource'] = '2020-08-07'
    h['UseRestriction'] = 'Research Use Only'
    h['PlateScaleScalar'] = {'NGSPLT1': {'PlatformSpecific': '1.01', 'CrossPlatform': '0.99'}}
    h['PlateSOMAmerNormReadsStatus'] = {'NGSPLT1': 'PASS'}
    return h


class TestMergeMixedHeaders:
    def test_assay_type_is_mixed(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert h['AssayType'] == 'Mixed'

    def test_file_version_is_2_0(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert h['FileVersion'] == '2.0'

    def test_adat_id_is_new_guid(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert h['AdatId'].startswith('GID-')
        assert h['AdatId'] not in ('GUID-ARRAY', 'GUID-NGS')

    def test_assay_version_from_array(self):
        # AssayVersion is no longer in the header (spec §3.2.1 moves it to ROW_DATA).
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert h.get('AssayVersion', '') == ''

    def test_source_file_has_both_entries(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert '1' in h['SourceFile']
        assert '2' in h['SourceFile']
        assert h['SourceFile']['1'] == {'AdatId': 'SL-OLD-ARRAY'}
        assert h['SourceFile']['2'] == {'AdatId': 'SL-OLD-NGS'}

    def test_process_steps_has_both_ids(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert '1' in h['ProcessSteps']
        assert '2' in h['ProcessSteps']

    def test_report_config_from_array_only(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert h['ReportConfig'] == {'1': 'DefaultReport'}

    def test_pipe_delimited_title_merged(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert h['Title'] == 'Study A|Study B'

    def test_pipe_delimited_identical_values_deduplicated(self):
        """Identical values in both sources produce a single value, no pipe."""
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        # UseRestriction is 'Research Use Only' in both
        assert h['UseRestriction'] == 'Research Use Only'

    def test_plate_scale_scalar_combined(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert 'PLT1' in h['PlateScaleScalar']
        assert 'NGSPLT1' in h['PlateScaleScalar']

    def test_plate_scale_status_from_array(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert h['PlateScaleStatus'] == {'PLT1': 'PASS'}

    def test_plate_someter_norm_reads_from_ngs(self):
        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert h['PlateSOMAmerNormReadsStatus'] == {'NGSPLT1': 'PASS'}

    def test_duplicate_plate_id_raises(self):
        array_h = _base_array_header()
        ngs_h = _base_ngs_header()
        # Both have PLT1 in PlateScaleScalar
        ngs_h['PlateScaleScalar'] = {'PLT1': {'CrossPlatform': '0.99'}}
        with pytest.raises(ValueError, match="Duplicate PlateId"):
            merge_mixed_headers(
                array_h, ngs_h,
                _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
            )

    def test_file_created_date_is_new(self):
        import re

        h = merge_mixed_headers(
            _base_array_header(), _base_ngs_header(),
            _make_minimal_array_ctx(), _make_minimal_ngs_ctx(),
        )
        assert re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', h['FileCreatedDate'])


# ===========================================================================
# merge_pipe_delimited and merge_plate_json utility helpers
# ===========================================================================


class TestMergePipeDelimited:
    def test_same_value_deduplicates(self):
        assert merge_pipe_delimited('Human', 'Human') == 'Human'

    def test_different_values_joined_with_pipe(self):
        assert merge_pipe_delimited('Human', 'Mouse') == 'Human|Mouse'

    def test_empty_first_arg(self):
        assert merge_pipe_delimited('', 'EDTA Plasma') == 'EDTA Plasma'

    def test_empty_second_arg(self):
        assert merge_pipe_delimited('Human', '') == 'Human'

    def test_both_empty(self):
        assert merge_pipe_delimited('', '') == ''

    def test_already_pipe_delimited_inputs(self):
        assert merge_pipe_delimited('A|B', 'B|C') == 'A|B|C'

    def test_order_preserved(self):
        result = merge_pipe_delimited('First', 'Second')
        assert result.startswith('First')


class TestMergePlateJson:
    def test_disjoint_keys_merged(self):
        result = merge_plate_json({'PLT1': '1.02'}, {'PLT2': '0.98'})
        assert result == {'PLT1': '1.02', 'PLT2': '0.98'}

    def test_empty_dicts(self):
        assert merge_plate_json({}, {}) == {}
        assert merge_plate_json({'PLT1': 'x'}, {}) == {'PLT1': 'x'}
        assert merge_plate_json({}, {'PLT2': 'y'}) == {'PLT2': 'y'}

    def test_duplicate_plate_id_raises(self):
        with pytest.raises(ValueError, match="Duplicate PlateId"):
            merge_plate_json({'PLT1': '1.02'}, {'PLT1': '0.98'})

    def test_duplicate_error_includes_field_name(self):
        with pytest.raises(ValueError, match="MyField"):
            merge_plate_json({'PLT1': 'a'}, {'PLT1': 'b'}, field_name='MyField')

    def test_nested_dict_values_preserved(self):
        a = {'PLT1': {'PlatformSpecific': '1.02'}}
        b = {'PLT2': {'CrossPlatform': '0.98'}}
        result = merge_plate_json(a, b)
        assert result['PLT1'] == {'PlatformSpecific': '1.02'}
        assert result['PLT2'] == {'CrossPlatform': '0.98'}


# ===========================================================================
# End-to-end: _merge_bridged_array_and_ngs via to_v2_adat
# ===========================================================================


class TestEndToEndMerge:
    def _run_merge(self):
        from somadata.conversion.converter import to_v2_adat

        array_adat = make_bridged_array_with_mednorm()
        ngs_adat = make_full_legacy_ngs_adat()
        inputs = [array_adat, ngs_adat]
        return to_v2_adat(inputs)

    def test_returns_adat(self):
        result = self._run_merge()
        assert isinstance(result, Adat)

    def test_assay_type_is_mixed(self):
        result = self._run_merge()
        assert result.header_metadata['AssayType'] == 'Mixed'

    def test_file_version_is_2_0(self):
        result = self._run_merge()
        assert result.header_metadata['FileVersion'] == '2.0'

    def test_row_count_equals_sum_of_sources(self):
        """All sample rows from both sources appear in the output."""
        result = self._run_merge()
        # 2 array samples + 2 ngs samples = 4 total
        assert len(result) == 4

    def test_seqid_union_covers_all_sources(self):
        """Output SeqIds are the union of both source SeqId sets."""
        array_adat = make_bridged_array_with_mednorm(
            shared_seqids=['10000-28', '10001-7'],
            array_only_seqids=['30000-01'],
        )
        ngs_adat = make_full_legacy_ngs_adat(
            shared_seqids=['10000-28', '10001-7'],
            ngs_only_seqids=['20000-01'],
        )
        from somadata.conversion.converter import to_v2_adat

        result = to_v2_adat([array_adat, ngs_adat])
        result_seqids = set(result.columns.get_level_values('SeqId'))
        assert '10000-28' in result_seqids
        assert '10001-7' in result_seqids
        assert '30000-01' in result_seqids  # array-only
        assert '20000-01' in result_seqids  # ngs-only

    def test_source_file_has_two_entries(self):
        result = self._run_merge()
        sf = result.header_metadata['SourceFile']
        assert '1' in sf and '2' in sf

    def test_process_steps_has_two_entries(self):
        result = self._run_merge()
        ps = result.header_metadata['ProcessSteps']
        assert '1' in ps and '2' in ps

    def test_order_independent_input(self):
        """Result is equivalent whether array or NGS is listed first."""
        from somadata.conversion.converter import to_v2_adat

        array_adat = make_bridged_array_with_mednorm()
        ngs_adat = make_full_legacy_ngs_adat()
        result_ab = to_v2_adat([array_adat, ngs_adat])
        result_ba = to_v2_adat([ngs_adat, array_adat])
        # Both should return a valid Mixed Adat with same SeqId set
        assert result_ab.header_metadata['AssayType'] == 'Mixed'
        assert result_ba.header_metadata['AssayType'] == 'Mixed'
        seqids_ab = set(result_ab.columns.get_level_values('SeqId'))
        seqids_ba = set(result_ba.columns.get_level_values('SeqId'))
        assert seqids_ab == seqids_ba


# ===========================================================================
# Phase 3: Helper Functions Unit Tests
# ===========================================================================


class TestMergeV2Headers:
    """Unit tests for _merge_v2_headers helper (Path 5)."""

    def test_derives_assay_type_from_parameter(self):
        """Output AssayType matches the assay_type parameter."""
        from somadata.conversion.utils import HeaderMerger
        
        header_a = {'FileVersion': '2.0', 'AssayType': 'Array', 'SourceFile': {'1': {}}}
        header_b = {'FileVersion': '2.0', 'AssayType': 'Array', 'SourceFile': {'1': {}}}
        
        result = HeaderMerger.merge_v2_headers(header_a, header_b, 'Mixed')
        assert result['AssayType'] == 'Mixed'
        
        result = HeaderMerger.merge_v2_headers(header_a, header_b, 'Array')
        assert result['AssayType'] == 'Array'

    def test_generates_new_adat_id(self):
        """Output has a new GUID-format AdatId."""
        from somadata.conversion.utils import HeaderMerger
        
        header_a = {'AdatId': 'GID-old-1', 'SourceFile': {}, 'ProcessSteps': {}}
        header_b = {'AdatId': 'GID-old-2', 'SourceFile': {}, 'ProcessSteps': {}}
        
        result = HeaderMerger.merge_v2_headers(header_a, header_b, 'Array')
        assert result['AdatId'].startswith('GID-')
        assert result['AdatId'] != 'GID-old-1'
        assert result['AdatId'] != 'GID-old-2'

    def test_merges_source_file_dicts(self):
        """SourceFile entries are renumbered sequentially."""
        from somadata.conversion.utils import HeaderMerger
        
        header_a = {'SourceFile': {'1': {'AdatId': 'A'}, '2': {'AdatId': 'B'}}}
        header_b = {'SourceFile': {'1': {'AdatId': 'C'}}}
        
        result = HeaderMerger.merge_v2_headers(header_a, header_b, 'Array')
        assert '1' in result['SourceFile']
        assert '2' in result['SourceFile']
        assert '3' in result['SourceFile']
        assert result['SourceFile']['1']['AdatId'] == 'A'
        assert result['SourceFile']['2']['AdatId'] == 'B'
        assert result['SourceFile']['3']['AdatId'] == 'C'

    def test_merges_process_steps_dicts(self):
        """ProcessSteps entries are renumbered sequentially."""
        from somadata.conversion.utils import HeaderMerger
        
        header_a = {'ProcessSteps': {'1': 'Raw, HybNorm'}}
        header_b = {'ProcessSteps': {'1': 'Raw, MedNorm'}}
        
        result = HeaderMerger.merge_v2_headers(header_a, header_b, 'NGS')
        assert '1' in result['ProcessSteps']
        assert '2' in result['ProcessSteps']
        assert result['ProcessSteps']['1'] == 'Raw, HybNorm'
        assert result['ProcessSteps']['2'] == 'Raw, MedNorm'

    def test_pipe_delimited_fields_merged(self):
        """Study-level fields are pipe-merged."""
        from somadata.conversion.utils import HeaderMerger
        
        header_a = {'Title': 'Study A', 'StudyOrganism': 'Human'}
        header_b = {'Title': 'Study B', 'StudyOrganism': 'Human'}
        
        result = HeaderMerger.merge_v2_headers(header_a, header_b, 'Array')
        assert result['Title'] == 'Study A|Study B'
        assert result['StudyOrganism'] == 'Human'


class TestMergeArrayHeaders:
    """Unit tests for _merge_array_headers helper (Path 4)."""

    def test_assay_type_is_array(self):
        """Output AssayType is always 'Array'."""
        from somadata.conversion.utils import HeaderMerger
        from somadata.conversion.array import ArrayConversionContext
        
        header_a = {'AssayType': 'Array', 'SourceFile': {}, 'ProcessSteps': {}, 'ReportConfig': {}}
        header_b = {'AssayType': 'Array', 'SourceFile': {}, 'ProcessSteps': {}, 'ReportConfig': {}}
        
        ctx_a = ArrayConversionContext.from_adat(None, source_file_md5sum=None)
        ctx_a.source_file_id = '1'
        ctx_a.process_steps_id = '1'
        ctx_a.report_config_id = '1'
        
        ctx_b = ArrayConversionContext.from_adat(None, source_file_md5sum=None)
        ctx_b.source_file_id = '2'
        ctx_b.process_steps_id = '2'
        ctx_b.report_config_id = '2'
        
        result = HeaderMerger.merge_array_headers(header_a, header_b, ctx_a, ctx_b)
        assert result['AssayType'] == 'Array'

    def test_merges_report_config(self):
        """ReportConfig entries from both sources are merged."""
        from somadata.conversion.utils import HeaderMerger
        from somadata.conversion.array import ArrayConversionContext
        
        header_a = {'ReportConfig': {'1': 'ConfigA'}, 'SourceFile': {}, 'ProcessSteps': {}}
        header_b = {'ReportConfig': {'1': 'ConfigB'}, 'SourceFile': {}, 'ProcessSteps': {}}
        
        ctx_a = ArrayConversionContext.from_adat(None, source_file_md5sum=None)
        ctx_a.source_file_id = '1'
        ctx_a.process_steps_id = '1'
        ctx_a.report_config_id = '1'
        
        ctx_b = ArrayConversionContext.from_adat(None, source_file_md5sum=None)
        ctx_b.source_file_id = '2'
        ctx_b.process_steps_id = '2'
        ctx_b.report_config_id = '2'
        
        result = HeaderMerger.merge_array_headers(header_a, header_b, ctx_a, ctx_b)
        assert '1' in result['ReportConfig']
        assert '2' in result['ReportConfig']
        assert result['ReportConfig']['1'] == 'ConfigA'
        assert result['ReportConfig']['2'] == 'ConfigB'


class TestValidateV2NGSProcessSteps:
    """Unit tests for _validate_v2_ngs_process_steps (Path 5)."""

    def test_identical_process_steps_pass(self):
        """NGS-only pair with identical ProcessSteps passes."""
        from somadata.conversion.utils import validate_v2_ngs_process_steps
        
        adat_a = Adat(
            data=[[1.0]], index=pd.MultiIndex.from_arrays([['S1']], names=['SampleId']),
            columns=pd.MultiIndex.from_arrays([['10000-01']], names=['SeqId']),
            header_metadata={'ProcessSteps': {'1': 'Raw, HybNorm, MedNorm'}}
        )
        adat_b = Adat(
            data=[[1.0]], index=pd.MultiIndex.from_arrays([['S2']], names=['SampleId']),
            columns=pd.MultiIndex.from_arrays([['10000-01']], names=['SeqId']),
            header_metadata={'ProcessSteps': {'1': 'Raw, HybNorm, MedNorm'}}
        )
        
        validate_v2_ngs_process_steps(adat_a, adat_b)

    def test_mismatched_process_steps_raise(self):
        """NGS-only pair with different ProcessSteps raises error."""
        from somadata.conversion.utils import validate_v2_ngs_process_steps
        
        adat_a = Adat(
            data=[[1.0]], index=pd.MultiIndex.from_arrays([['S1']], names=['SampleId']),
            columns=pd.MultiIndex.from_arrays([['10000-01']], names=['SeqId']),
            header_metadata={'ProcessSteps': {'1': 'Raw, HybNorm'}}
        )
        adat_b = Adat(
            data=[[1.0]], index=pd.MultiIndex.from_arrays([['S2']], names=['SampleId']),
            columns=pd.MultiIndex.from_arrays([['10000-01']], names=['SeqId']),
            header_metadata={'ProcessSteps': {'1': 'Raw, MedNorm'}}
        )
        
        with pytest.raises(ProcessStepsMismatchError, match='identical ProcessSteps'):
            validate_v2_ngs_process_steps(adat_a, adat_b)


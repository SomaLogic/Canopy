"""Unit tests for somadata.conversion.detection.

Covers every branch of detect_input_type() and its helper functions,
including edge cases for empty fields and missing columns.
"""

from __future__ import annotations

import pytest

from somadata.adat import Adat
from somadata.conversion.detection import (
    InputType,
    _has_array_row_metadata,
    _has_ngs_row_metadata,
    _is_bridged_array,
    _parse_assay_version_major,
    detect_input_type,
)
from somadata.conversion.errors import AssayVersionError, UnrecognizedFormatError

# ---------------------------------------------------------------------------
# Helpers: minimal Adat factories
# ---------------------------------------------------------------------------


def _make_adat(
    header: dict | None = None,
    row_names: list[str] | None = None,
    row_values: list[list] | None = None,
    col_names: list[str] | None = None,
) -> Adat:
    """Build a minimal Adat for testing without needing real file fixtures."""
    import pandas as pd

    header = header or {}
    row_names = row_names or ['SampleId', 'SampleType']
    row_values = row_values or [['S1', 'S2'], ['Sample', 'Sample']]
    col_names = col_names or ['10000-01', '10001-02']

    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    columns = pd.MultiIndex.from_arrays([col_names], names=['SeqId'])
    data = [[1.0] * len(col_names)] * len(row_values[0])
    return Adat(data=data, index=index, columns=columns, header_metadata=header)


def _array_adat(
    assay_version: str = 'V4',
    process_steps: str = 'Raw RFU, Hyb Normalization, medNormInt, plateScale, Calibration',
    n_samples: int = 2,
) -> Adat:
    """Minimal array Adat with SlideId and Subarray row metadata."""
    return _make_adat(
        header={
            '!AssayVersion': assay_version,
            '!ProcessSteps': process_steps,
        },
        row_names=['SampleId', 'SampleType', 'SlideId', 'Subarray'],
        row_values=[
            [f'S{i}' for i in range(n_samples)],
            ['Sample'] * n_samples,
            ['258740110837'] * n_samples,
            ['3'] * n_samples,
        ],
    )


def _ngs_adat() -> Adat:
    """Minimal NGS Adat with SOMAmerReads row metadata."""
    return _make_adat(
        header={'!AssayVersion': 'v1'},
        row_names=['SampleId', 'SampleType', 'SOMAmerReads'],
        row_values=[['S1', 'S2'], ['Sample', 'Sample'], ['14250000', '13800000']],
    )


def _v2_combined_adat() -> Adat:
    """Minimal Adat already in v2.0 combined format."""
    return _make_adat(header={'FileVersion': '2.0'})


# ---------------------------------------------------------------------------
# detect_input_type: v2_combined
# ---------------------------------------------------------------------------


class TestDetectV2Combined:
    def test_fileversion_2_returns_v2_combined(self):
        adat = _v2_combined_adat()
        assert detect_input_type(adat) == InputType.V2_COMBINED

    def test_fileversion_other_value_not_v2(self):
        """FileVersion present but not '2.0' should NOT match v2_combined."""
        adat = _make_adat(header={'FileVersion': '1.2'})
        with pytest.raises(UnrecognizedFormatError):
            detect_input_type(adat)

    def test_missing_fileversion_not_v2(self):
        adat = _array_adat()
        result = detect_input_type(adat)
        assert result != InputType.V2_COMBINED


# ---------------------------------------------------------------------------
# detect_input_type: bridged_array
# ---------------------------------------------------------------------------

_BRIDGED_STEPS = (
    'Raw RFU, Hyb Normalization, medNormInt, plateScale, Calibration, '
    'CrossPlatformPlateScaling, CrossPlatformCalibrate, MedNormExt'
)


class TestDetectBridgedArray:
    def test_bridged_terminal_steps_returns_bridged_array(self):
        adat = _array_adat(process_steps=_BRIDGED_STEPS)
        assert detect_input_type(adat) == InputType.BRIDGED_ARRAY

    def test_bridged_exact_three_step_sequence(self):
        """Only the three terminal steps — still bridged."""
        adat = _array_adat(
            process_steps='CrossPlatformPlateScaling, CrossPlatformCalibrate, MedNormExt'
        )
        assert detect_input_type(adat) == InputType.BRIDGED_ARRAY

    def test_wrong_terminal_step_not_bridged(self):
        adat = _array_adat(
            process_steps='Raw RFU, CrossPlatformPlateScaling, CrossPlatformCalibrate, plateScale'
        )
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY

    def test_missing_last_medNormExt_not_bridged(self):
        adat = _array_adat(
            process_steps='CrossPlatformPlateScaling, CrossPlatformCalibrate'
        )
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY


# ---------------------------------------------------------------------------
# detect_input_type: native_array
# ---------------------------------------------------------------------------


class TestDetectNativeArray:
    def test_standard_array_returns_native_array(self):
        adat = _array_adat()
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY

    def test_v5_array_returns_native_array(self):
        adat = _array_adat(assay_version='V5')
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY

    def test_assay_version_exactly_4_passes(self):
        adat = _array_adat(assay_version='v4')
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY


# ---------------------------------------------------------------------------
# detect_input_type: AssayVersionError for old array
# ---------------------------------------------------------------------------


class TestDetectAssayVersionError:
    def test_v3_raises_assay_version_error(self):
        adat = _array_adat(assay_version='V3')
        with pytest.raises(AssayVersionError):
            detect_input_type(adat)

    def test_v1_raises_assay_version_error(self):
        adat = _array_adat(assay_version='v1')
        with pytest.raises(AssayVersionError):
            detect_input_type(adat)

    def test_unparseable_version_raises_assay_version_error(self):
        adat = _array_adat(assay_version='unknown')
        with pytest.raises(AssayVersionError):
            detect_input_type(adat)

    def test_empty_version_raises_assay_version_error(self):
        adat = _array_adat(assay_version='')
        with pytest.raises(AssayVersionError):
            detect_input_type(adat)


# ---------------------------------------------------------------------------
# detect_input_type: native_ngs
# ---------------------------------------------------------------------------


class TestDetectNativeNGS:
    def test_somamer_reads_column_returns_native_ngs(self):
        adat = _ngs_adat()
        assert detect_input_type(adat) == InputType.NATIVE_NGS

    def test_empty_somamer_reads_not_ngs(self):
        """SOMAmerReads column present but all empty — should NOT classify as NGS."""
        adat = _make_adat(
            header={'!AssayVersion': 'v1'},
            row_names=['SampleId', 'SampleType', 'SOMAmerReads'],
            row_values=[['S1', 'S2'], ['Sample', 'Sample'], ['', '']],
        )
        with pytest.raises(UnrecognizedFormatError):
            detect_input_type(adat)


# ---------------------------------------------------------------------------
# detect_input_type: UnrecognizedFormatError
# ---------------------------------------------------------------------------


class TestDetectUnrecognizedFormat:
    def test_no_slide_no_ngs_raises(self):
        adat = _make_adat(header={})
        with pytest.raises(UnrecognizedFormatError):
            detect_input_type(adat)

    def test_slide_id_only_no_subarray_raises_unrecognized(self):
        """SlideId present but no Subarray — should NOT classify as array."""
        adat = _make_adat(
            header={'!AssayVersion': 'V4'},
            row_names=['SampleId', 'SampleType', 'SlideId'],
            row_values=[['S1'], ['Sample'], ['258740110837']],
        )
        with pytest.raises(UnrecognizedFormatError):
            detect_input_type(adat)

    def test_empty_slide_id_raises_unrecognized(self):
        """SlideId and Subarray present but all empty — NOT array."""
        adat = _make_adat(
            header={'!AssayVersion': 'V4'},
            row_names=['SampleId', 'SampleType', 'SlideId', 'Subarray'],
            row_values=[['S1'], ['Sample'], [''], ['']],
        )
        with pytest.raises(UnrecognizedFormatError):
            detect_input_type(adat)


# ---------------------------------------------------------------------------
# Helper unit tests: _parse_assay_version_major
# ---------------------------------------------------------------------------


class TestParseAssayVersionMajor:
    @pytest.mark.parametrize(
        'version_str, expected',
        [
            ('V4', 4),
            ('v4', 4),
            ('V5', 5),
            ('v5.0', 5),
            ('V4.1', 4),
            ('4', 4),
            ('v10', 10),
            ('', None),
            ('unknown', None),
        ],
    )
    def test_parses_correctly(self, version_str: str, expected: int | None):
        assert _parse_assay_version_major(version_str) == expected


# ---------------------------------------------------------------------------
# Helper unit tests: _has_array_row_metadata
# ---------------------------------------------------------------------------


class TestHasArrayRowMetadata:
    def test_returns_true_when_both_present_and_nonempty(self):
        adat = _array_adat()
        assert _has_array_row_metadata(adat) is True

    def test_returns_false_when_slide_id_missing(self):
        adat = _make_adat(
            row_names=['SampleId', 'Subarray'],
            row_values=[['S1'], ['3']],
        )
        assert _has_array_row_metadata(adat) is False

    def test_returns_false_when_subarray_missing(self):
        adat = _make_adat(
            row_names=['SampleId', 'SlideId'],
            row_values=[['S1'], ['258740110837']],
        )
        assert _has_array_row_metadata(adat) is False

    def test_returns_false_when_values_empty(self):
        adat = _make_adat(
            row_names=['SampleId', 'SlideId', 'Subarray'],
            row_values=[['S1'], [''], ['']],
        )
        assert _has_array_row_metadata(adat) is False


# ---------------------------------------------------------------------------
# Helper unit tests: _has_ngs_row_metadata
# ---------------------------------------------------------------------------


class TestHasNgsRowMetadata:
    def test_returns_true_when_somamer_reads_nonempty(self):
        adat = _ngs_adat()
        assert _has_ngs_row_metadata(adat) is True

    def test_returns_false_when_column_absent(self):
        adat = _make_adat()
        assert _has_ngs_row_metadata(adat) is False

    def test_returns_false_when_all_empty(self):
        adat = _make_adat(
            row_names=['SampleId', 'SOMAmerReads'],
            row_values=[['S1'], ['']],
        )
        assert _has_ngs_row_metadata(adat) is False


# ---------------------------------------------------------------------------
# Helper unit tests: _is_bridged_array
# ---------------------------------------------------------------------------


class TestIsBridgedArray:
    def test_returns_true_for_bridged_terminal(self):
        adat = _array_adat(process_steps=_BRIDGED_STEPS)
        assert _is_bridged_array(adat) is True

    def test_returns_false_for_native_steps(self):
        adat = _array_adat()
        assert _is_bridged_array(adat) is False

    def test_returns_false_when_process_steps_absent(self):
        adat = _make_adat(header={})
        assert _is_bridged_array(adat) is False

    def test_returns_false_when_process_steps_is_dict(self):
        """v2.0-style JSON ProcessSteps dict — bridged check should return False."""
        adat = _make_adat(
            header={
                'ProcessSteps': {
                    '1': [
                        'CrossPlatformPlateScaling',
                        'CrossPlatformCalibrate',
                        'MedNormExt',
                    ]
                }
            }
        )
        assert _is_bridged_array(adat) is False

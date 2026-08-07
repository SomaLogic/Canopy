"""Unit tests for somadata.conversion.detection.

Covers every branch of detect_input_type() and its helper functions,
including edge cases for empty fields and missing columns.
"""

from __future__ import annotations

import pytest

from somadata.adat import Adat
from somadata.conversion.detection import (
    InputType,
    _BRIDGED_TERMINAL_STEPS,
    _has_array_row_metadata,
    _has_ngs_row_metadata,
    _is_bridged_array,
    _parse_assay_version_major,
    detect_input_type,
    diagnose_bridging,
)
from somadata.conversion.errors import AssayVersionError, UnrecognizedFormatError
from tests.conversion.conftest import (
    BRIDGED_STEPS,
    NATIVE_STEPS,
    make_adat,
    make_array_adat,
    make_bridged_array_adat,
    make_ngs_adat,
    make_v2_combined_adat,
)

# ---------------------------------------------------------------------------
# detect_input_type: v2_combined
# ---------------------------------------------------------------------------


class TestDetectV2Combined:
    def test_fileversion_2_returns_v2_combined(self):
        adat = make_v2_combined_adat()
        assert detect_input_type(adat) == InputType.V2_COMBINED

    def test_fileversion_other_value_not_v2(self):
        """FileVersion present but not '2.0' should NOT match v2_combined."""
        adat = make_adat(header={'FileVersion': '1.2'})
        with pytest.raises(UnrecognizedFormatError):
            detect_input_type(adat)

    def test_missing_fileversion_not_v2(self):
        adat = make_array_adat()
        result = detect_input_type(adat)
        assert result != InputType.V2_COMBINED


# ---------------------------------------------------------------------------
# detect_input_type: bridged_array
# ---------------------------------------------------------------------------


class TestDetectBridgedArray:
    def test_bridged_terminal_steps_returns_bridged_array(self):
        adat = make_array_adat(process_steps=BRIDGED_STEPS)
        assert detect_input_type(adat) == InputType.BRIDGED_ARRAY

    def test_bridged_exact_three_step_sequence(self):
        """Only the three terminal steps — still bridged."""
        adat = make_array_adat(
            process_steps='CrossPlatformPlateScale, CrossPlatformCalibrate, MedNormExt'
        )
        assert detect_input_type(adat) == InputType.BRIDGED_ARRAY

    def test_wrong_terminal_step_not_bridged(self):
        adat = make_array_adat(
            process_steps='Raw RFU, CrossPlatformPlateScale, CrossPlatformCalibrate, plateScale'
        )
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY

    def test_missing_last_medNormExt_not_bridged(self):
        adat = make_array_adat(
            process_steps='CrossPlatformPlateScale, CrossPlatformCalibrate'
        )
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY


# ---------------------------------------------------------------------------
# detect_input_type: native_array
# ---------------------------------------------------------------------------


class TestDetectNativeArray:
    def test_standard_array_returns_native_array(self):
        adat = make_array_adat()
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY

    def test_v5_array_returns_native_array(self):
        adat = make_array_adat(assay_version='V5')
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY

    def test_assay_version_exactly_4_passes(self):
        adat = make_array_adat(assay_version='v4')
        assert detect_input_type(adat) == InputType.NATIVE_ARRAY


# ---------------------------------------------------------------------------
# detect_input_type: AssayVersionError for old array
# ---------------------------------------------------------------------------


class TestDetectAssayVersionError:
    def test_v3_raises_assay_version_error(self):
        adat = make_array_adat(assay_version='V3')
        with pytest.raises(AssayVersionError):
            detect_input_type(adat)

    def test_v1_raises_assay_version_error(self):
        adat = make_array_adat(assay_version='v1')
        with pytest.raises(AssayVersionError):
            detect_input_type(adat)

    def test_unparseable_version_raises_assay_version_error(self):
        adat = make_array_adat(assay_version='unknown')
        with pytest.raises(AssayVersionError):
            detect_input_type(adat)

    def test_empty_version_raises_assay_version_error(self):
        adat = make_array_adat(assay_version='')
        with pytest.raises(AssayVersionError):
            detect_input_type(adat)


# ---------------------------------------------------------------------------
# detect_input_type: native_ngs
# ---------------------------------------------------------------------------


class TestDetectNativeNGS:
    def test_somamer_reads_column_returns_native_ngs(self):
        adat = make_ngs_adat()
        assert detect_input_type(adat) == InputType.NATIVE_NGS

    def test_empty_somamer_reads_not_ngs(self):
        """SOMAmerReads column present but all empty — should NOT classify as NGS."""
        adat = make_adat(
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
        adat = make_adat(header={})
        with pytest.raises(UnrecognizedFormatError):
            detect_input_type(adat)

    def test_slide_id_only_no_subarray_raises_unrecognized(self):
        """SlideId present but no Subarray — should NOT classify as array."""
        adat = make_adat(
            header={'!AssayVersion': 'V4'},
            row_names=['SampleId', 'SampleType', 'SlideId'],
            row_values=[['S1'], ['Sample'], ['258740110837']],
        )
        with pytest.raises(UnrecognizedFormatError):
            detect_input_type(adat)

    def test_empty_slide_id_raises_unrecognized(self):
        """SlideId and Subarray present but all empty — NOT array."""
        adat = make_adat(
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
        adat = make_array_adat()
        assert _has_array_row_metadata(adat) is True

    def test_returns_false_when_slide_id_missing(self):
        adat = make_adat(
            row_names=['SampleId', 'Subarray'],
            row_values=[['S1'], ['3']],
        )
        assert _has_array_row_metadata(adat) is False

    def test_returns_false_when_subarray_missing(self):
        adat = make_adat(
            row_names=['SampleId', 'SlideId'],
            row_values=[['S1'], ['258740110837']],
        )
        assert _has_array_row_metadata(adat) is False

    def test_returns_false_when_values_empty(self):
        adat = make_adat(
            row_names=['SampleId', 'SlideId', 'Subarray'],
            row_values=[['S1'], [''], ['']],
        )
        assert _has_array_row_metadata(adat) is False


# ---------------------------------------------------------------------------
# Helper unit tests: _has_ngs_row_metadata
# ---------------------------------------------------------------------------


class TestHasNgsRowMetadata:
    def test_returns_true_when_somamer_reads_nonempty(self):
        adat = make_ngs_adat()
        assert _has_ngs_row_metadata(adat) is True

    def test_returns_false_when_column_absent(self):
        adat = make_adat()
        assert _has_ngs_row_metadata(adat) is False

    def test_returns_false_when_all_empty(self):
        adat = make_adat(
            row_names=['SampleId', 'SOMAmerReads'],
            row_values=[['S1'], ['']],
        )
        assert _has_ngs_row_metadata(adat) is False


# ---------------------------------------------------------------------------
# Helper unit tests: _is_bridged_array
# ---------------------------------------------------------------------------


class TestIsBridgedArray:
    def test_returns_true_for_bridged_terminal(self):
        adat = make_array_adat(process_steps=BRIDGED_STEPS)
        assert _is_bridged_array(adat) is True

    def test_returns_false_for_native_steps(self):
        adat = make_array_adat()
        assert _is_bridged_array(adat) is False

    def test_returns_false_when_process_steps_absent(self):
        adat = make_adat(header={})
        assert _is_bridged_array(adat) is False

    def test_returns_false_when_process_steps_is_dict(self):
        """v2.0-style JSON ProcessSteps dict — bridged check should return False."""
        adat = make_adat(
            header={
                'ProcessSteps': {
                    '1': [
                        'CrossPlatformPlateScale',
                        'CrossPlatformCalibrate',
                        'MedNormExt',
                    ]
                }
            }
        )
        assert _is_bridged_array(adat) is False


# ---------------------------------------------------------------------------
# Unit tests: diagnose_bridging
# ---------------------------------------------------------------------------


class TestDiagnoseBridging:
    def test_returns_none_when_already_bridged(self):
        """Properly bridged ADAT returns None (no diagnostic needed)."""
        adat = make_bridged_array_adat()
        assert diagnose_bridging(adat) is None

    def test_returns_message_when_process_steps_missing(self):
        """Missing ProcessSteps header yields an explanatory message."""
        adat = make_adat(
            header={'!AssayVersion': 'V4'},
            row_names=['SampleId', 'SampleType', 'SlideId', 'Subarray'],
            row_values=[['S1'], ['Sample'], ['258740110837'], ['3']],
        )
        msg = diagnose_bridging(adat)
        assert msg is not None
        expected_terminal = ', '.join(_BRIDGED_TERMINAL_STEPS[0])
        assert 'ProcessSteps' in msg
        assert expected_terminal in msg

    def test_returns_message_when_process_steps_empty_string(self):
        """Empty ProcessSteps string (key present but blank) yields a message."""
        adat = make_adat(
            header={'!AssayVersion': 'V4', '!ProcessSteps': ''},
            row_names=['SampleId', 'SampleType', 'SlideId', 'Subarray'],
            row_values=[['S1'], ['Sample'], ['258740110837'], ['3']],
        )
        msg = diagnose_bridging(adat)
        assert msg is not None
        assert 'ProcessSteps' in msg

    def test_mismatch_message_includes_expected_and_actual_steps(self):
        """Wrong terminal steps produce a diff with expected vs actual values."""
        adat = make_array_adat(process_steps=NATIVE_STEPS)
        msg = diagnose_bridging(adat)
        assert msg is not None
        # Should mention both what was expected and what was found
        assert 'expected' in msg
        assert 'got' in msg

    def test_mismatch_message_includes_actual_tail(self):
        """The actual last-N steps appear in the diagnostic output."""
        wrong_steps = 'Raw RFU, Hyb Normalization, medNormInt, plateScale, WrongStep'
        adat = make_array_adat(process_steps=wrong_steps)
        msg = diagnose_bridging(adat)
        assert msg is not None
        assert 'WrongStep' in msg

    def test_too_few_steps_returns_count_message(self):
        """Fewer steps than the required terminal triple yields a count message."""
        adat = make_array_adat(process_steps='CrossPlatformPlateScale')
        msg = diagnose_bridging(adat)
        assert msg is not None
        # Either a count message or a mismatch message — either way informative
        assert 'step' in msg.lower() or 'position' in msg.lower()

    def test_single_wrong_terminal_step_is_identified(self):
        """Only the last step differs — the mismatch detail pinpoints that position."""
        steps = 'CrossPlatformPlateScale, CrossPlatformCalibrate, WrongLastStep'
        adat = make_array_adat(process_steps=steps)
        msg = diagnose_bridging(adat)
        assert msg is not None
        assert 'MedNormExt' in msg  # expected value should appear
        assert 'WrongLastStep' in msg  # actual value should appear

"""Tests for somadata.conversion.array.validation.validate_source_array_adat."""
from __future__ import annotations

import pytest

from somadata.conversion.array.validation import validate_source_array_adat
from somadata.conversion.errors import ConversionError

from tests.conversion.conftest import make_adat, make_full_legacy_array_adat


# ---------------------------------------------------------------------------
# Valid input — should not raise
# ---------------------------------------------------------------------------


def test_valid_adat_passes():
    adat = make_full_legacy_array_adat()
    validate_source_array_adat(adat)  # must not raise


# ---------------------------------------------------------------------------
# Missing ProcessSteps
# ---------------------------------------------------------------------------


def test_missing_process_steps_raises():
    adat = make_adat(header={'!AssayVersion': 'V4', '!ProteinEffectiveDate': '2020-08-07'})
    with pytest.raises(ConversionError, match="'ProcessSteps'"):
        validate_source_array_adat(adat)


def test_blank_process_steps_raises():
    adat = make_adat(
        header={
            '!AssayVersion': 'V4',
            '!ProcessSteps': '',
            '!ProteinEffectiveDate': '2020-08-07',
        }
    )
    with pytest.raises(ConversionError, match="'ProcessSteps'"):
        validate_source_array_adat(adat)


# ---------------------------------------------------------------------------
# Missing ProteinEffectiveDate (→ SOMAmerReferenceSource)
# ---------------------------------------------------------------------------


def test_missing_protein_effective_date_raises():
    adat = make_adat(
        header={
            '!AssayVersion': 'V4',
            '!ProcessSteps': 'Raw RFU, Calibration',
        }
    )
    with pytest.raises(ConversionError, match="'ProteinEffectiveDate'"):
        validate_source_array_adat(adat)


def test_blank_protein_effective_date_raises():
    adat = make_adat(
        header={
            '!AssayVersion': 'V4',
            '!ProcessSteps': 'Raw RFU, Calibration',
            '!ProteinEffectiveDate': '',
        }
    )
    with pytest.raises(ConversionError, match="'ProteinEffectiveDate'"):
        validate_source_array_adat(adat)


# ---------------------------------------------------------------------------
# Multiple missing fields reported together
# ---------------------------------------------------------------------------


def test_multiple_missing_fields_all_reported():
    adat = make_adat(header={'!AssayVersion': 'V4'})
    with pytest.raises(ConversionError) as exc_info:
        validate_source_array_adat(adat)
    msg = str(exc_info.value)
    assert "'ProcessSteps'" in msg
    assert "'ProteinEffectiveDate'" in msg


# ---------------------------------------------------------------------------
# bang-prefixed fields are accepted
# ---------------------------------------------------------------------------


def test_bang_prefixed_fields_accepted():
    adat = make_adat(
        header={
            '!AssayVersion': 'V4',
            '!ProcessSteps': 'Raw RFU, Calibration',
            '!ProteinEffectiveDate': '2020-08-07',
        }
    )
    validate_source_array_adat(adat)  # must not raise


# ---------------------------------------------------------------------------
# Optional fields absent does NOT raise
# ---------------------------------------------------------------------------


def test_missing_title_does_not_raise():
    """Title is optional — its absence must not trigger validation errors."""
    adat = make_adat(
        header={
            '!AssayVersion': 'V4',
            '!ProcessSteps': 'Raw RFU, Calibration',
            '!ProteinEffectiveDate': '2020-08-07',
        }
    )
    validate_source_array_adat(adat)  # must not raise


def test_missing_report_config_does_not_raise():
    adat = make_adat(
        header={
            '!AssayVersion': 'V4',
            '!ProcessSteps': 'Raw RFU, Calibration',
            '!ProteinEffectiveDate': '2020-08-07',
        }
    )
    validate_source_array_adat(adat)  # must not raise

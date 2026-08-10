from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING

from somadata.conversion.errors import AssayVersionError, UnrecognizedFormatError

if TYPE_CHECKING:
    from somadata.adat import Adat

# Valid terminal triples that identify a bridged array ADAT.
# Each inner tuple is a sequence of the last 3 ProcessSteps that qualifies.
_BRIDGED_TERMINAL_STEPS = (
    ('CrossPlatformPlateScale', 'CrossPlatformCalibrate', 'MedNormExt'),
    # Legacy variant: older ADATs used 'CrossPlatformPlateScaling' (with trailing 'ing')
    ('CrossPlatformPlateScaling', 'CrossPlatformCalibrate', 'MedNormExt'),
)


# Header keys for AssayVersion — stored with or without the '!' prefix in legacy files.
_ASSAY_VERSION_KEYS = ('!AssayVersion', 'AssayVersion')

# Minimum required assay version for array ADATs (v4 and above are supported).
_MIN_ARRAY_ASSAY_VERSION = 4


class InputType(Enum):
    """Classification of an Adat input for v2.0 conversion routing."""

    NATIVE_ARRAY = 'native_array'
    BRIDGED_ARRAY = 'bridged_array'
    NATIVE_NGS = 'native_ngs'
    V2_COMBINED = 'v2_combined'


def detect_input_type(adat: Adat) -> InputType:
    """

    Classify an Adat into one of the four recognised input types.


    Parameters
    ----------
    adat : Adat
        The Adat object to classify.

    Returns
    -------
    InputType
        One of ``native_array``, ``bridged_array``, ``native_ngs``, or
        ``v2_combined``.

    Raises
    ------
    AssayVersionError
        If the Adat is identified as array but its AssayVersion is below v4.
    UnrecognizedFormatError
        If the Adat does not match any known input pattern.

    Examples
    --------
    >>> input_type = detect_input_type(adat)
    >>> input_type == InputType.native_array
    True
    """
    # Step 1 — v2.0 combined: FileVersion field is present and equals "2.0".
    if adat.header_metadata.get('FileVersion') == '2.0':
        return InputType.V2_COMBINED

    # Step 2 — Array branch: SlideId and Subarray are row metadata fields with
    # at least one non-empty value across all samples.
    if _has_array_row_metadata(adat):
        _validate_array_assay_version(adat)
        if _is_bridged_array(adat):
            return InputType.BRIDGED_ARRAY
        return InputType.NATIVE_ARRAY

    # Step 3 — NGS branch: SOMAmerReads column present and non-empty.
    if _has_ngs_row_metadata(adat):
        return InputType.NATIVE_NGS

    # Step 4 — Unrecognised.
    raise UnrecognizedFormatError(
        'Unable to determine input type: the Adat does not match any known '
        'format. Expected non-empty SlideId/Subarray row metadata (array), '
        'a non-empty SOMAmerReads column (NGS), or FileVersion == "2.0" '
        '(v2_combined).'
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _has_array_row_metadata(adat: Adat) -> bool:
    """Return True when SlideId AND Subarray are both present as row metadata
    fields and at least one sample has a non-empty SlideId value."""
    names = adat.index.names
    if 'SlideId' not in names or 'Subarray' not in names:
        return False
    slide_values = adat.index.get_level_values('SlideId')
    subarray_values = adat.index.get_level_values('Subarray')
    has_slide = any(v for v in slide_values if str(v).strip())
    has_subarray = any(v for v in subarray_values if str(v).strip())
    return has_slide and has_subarray


def _validate_array_assay_version(adat: Adat) -> None:
    """Raise AssayVersionError when AssayVersion is below v4.

    Accepts version strings of the form ``V4``, ``v4``, ``v4.0``, ``V5``,
    ``v5.0``, etc. Anything that cannot be parsed as a major version >= 4
    raises the error.
    """
    raw_version = ''
    for key in _ASSAY_VERSION_KEYS:
        raw_version = adat.header_metadata.get(key, '')
        if raw_version:
            break

    major = _parse_assay_version_major(raw_version)
    if major is None or major < _MIN_ARRAY_ASSAY_VERSION:
        raise AssayVersionError(
            f'AssayVersion "{raw_version}" is not supported for v2.0 conversion. '
            f'Only array ADATs from AssayVersion v4 and above are supported.'
        )


def _parse_assay_version_major(version_str: str) -> int | None:
    """Extract the major version integer from a version string like 'V4', 'v5.0'.

    Returns None if the string cannot be parsed.
    """
    match = re.search(r'[vV]?(\d+)', str(version_str))
    if match:
        return int(match.group(1))
    return None


def _is_bridged_array(adat: Adat) -> bool:
    """Return True when the ProcessSteps header ends with the bridged terminal triple.

    The ProcessSteps field may be a comma-separated string (pre-v2.0 array) or a
    JSON dict (v2.0). Only string form is expected here since v2.0 files are
    handled earlier in the decision tree.
    """
    steps = _get_process_steps_list(adat)
    if not steps:
        return False

    for terminal in _BRIDGED_TERMINAL_STEPS:
        if len(steps) >= len(terminal) and tuple(steps[-len(terminal) :]) == terminal:
            return True
    return False


def diagnose_bridging(adat: Adat) -> str | None:
    """Return a diagnostic message explaining why the ADAT was not detected as bridged.

    If the ADAT *is* properly bridged (terminal steps match), returns None.
    Otherwise returns a human-readable explanation of what was expected vs. found.

    Parameters
    ----------
    adat : Adat
        An Adat already identified as having array row metadata.

    Returns
    -------
    str or None
        Diagnostic message, or None if the ADAT matches a valid bridged triple.
    """
    steps = _get_process_steps_list(adat)
    if not steps:
        return (
            'ProcessSteps header field is missing or empty. A bridged array '
            'ADAT must contain a ProcessSteps field ending with: '
            f'{", ".join(_BRIDGED_TERMINAL_STEPS[0])}.'
        )

    # Check if it actually matches (should not reach here if called correctly).
    for terminal in _BRIDGED_TERMINAL_STEPS:
        if len(steps) >= len(terminal) and tuple(steps[-len(terminal) :]) == terminal:
            return None

    # Build a helpful diff showing expected vs actual terminal steps.
    expected = _BRIDGED_TERMINAL_STEPS[0]
    n = len(expected)
    actual_tail = tuple(steps[-n:]) if len(steps) >= n else tuple(steps)

    mismatches = []
    for i, (exp, act) in enumerate(
        zip(expected[-len(actual_tail) :], actual_tail)
    ):
        if exp != act:
            mismatches.append(f'  position -{n - i}: expected {exp!r}, got {act!r}')

    if mismatches:
        detail = '\n'.join(mismatches)
        return (
            f'ProcessSteps do not end with the required bridged terminal triple '
            f'({", ".join(expected)}). '
            f'Last {n} steps found: {", ".join(actual_tail)}.\n'
            f'Mismatched steps:\n{detail}'
        )

    # Fewer steps than expected.
    return (
        f'ProcessSteps has only {len(steps)} step(s), but the bridged '
        f'terminal triple requires at least {n}: {", ".join(expected)}.'
    )


def _get_process_steps_list(adat: Adat) -> list[str]:
    """Extract ProcessSteps as a list of trimmed step names from the header."""
    process_steps_raw = ''
    for key in ('!ProcessSteps', 'ProcessSteps'):
        process_steps_raw = adat.header_metadata.get(key, '')
        if process_steps_raw:
            break

    if not process_steps_raw or not isinstance(process_steps_raw, str):
        return []

    return [s.strip() for s in process_steps_raw.split(',') if s.strip()]


def _has_ngs_row_metadata(adat: Adat) -> bool:
    """Return True when SOMAmerReads is a row metadata column with at least one
    non-empty value."""
    if 'SOMAmerReads' not in adat.index.names:
        return False
    values = adat.index.get_level_values('SOMAmerReads')
    return any(str(v).strip() for v in values)

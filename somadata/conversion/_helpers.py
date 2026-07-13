"""Shared utility functions for ADAT v2.0 conversion.

These helpers are used by both the ``array/`` and (future) ``ngs/``
conversion sub-packages.
"""

from __future__ import annotations

import re
import uuid
from typing import Any


def generate_guid() -> str:
    """Return a new GUID in ``GID-<uuid4>`` format."""
    return f'GID-{uuid.uuid4()}'


def strip_bang_prefix(key: str) -> str:
    """Strip a leading ``!`` from a header key.

    Parameters
    ----------
    key : str
        A header key, possibly prefixed with ``!``.

    Returns
    -------
    str
        The key with any leading ``!`` removed.

    Examples
    --------
    >>> strip_bang_prefix('!Title')
    'Title'
    >>> strip_bang_prefix('Title')
    'Title'
    """
    return key.lstrip('!')


def lookup_header(header: dict, *keys: str) -> str:
    """Try multiple key variants (with and without ``!`` prefix) in *header*.

    Parameters
    ----------
    header : dict
        The ADAT header_metadata dictionary.
    *keys : str
        One or more canonical (no-bang) key names to try.

    Returns
    -------
    str
        The first non-empty value found, or ``''`` if none match.

    Examples
    --------
    >>> lookup_header({'!Title': 'Study 1'}, 'Title')
    'Study 1'
    """
    for key in keys:
        for candidate in (key, f'!{key}'):
            val = header.get(candidate, '')
            val_str = '' if val is None else str(val).strip()
            if val_str:
                return val_str
    return ''


def parse_process_steps(raw: str) -> list[str]:
    """Split a comma-separated ProcessSteps string into a clean list.

    Parameters
    ----------
    raw : str
        Legacy ProcessSteps value, e.g.
        ``'Raw RFU, Hyb Normalization, plateScale, Calibration'``.

    Returns
    -------
    list[str]
        Ordered list of stripped step names.

    Examples
    --------
    >>> parse_process_steps('Raw RFU, Hyb Normalization, plateScale')
    ['Raw RFU', 'Hyb Normalization', 'plateScale']
    """
    if not raw or not raw.strip():
        return []
    return [step.strip() for step in raw.split(',') if step.strip()]


def consolidate_plate_fields(
    header: dict,
    prefix: str,
    stage: str | None = 'PlatformSpecific',
) -> dict[str, Any]:
    """Extract plate-keyed header values into a JSON-ready dict.

    Scans *header* for keys matching ``<prefix><PlateId>`` (after stripping
    any leading ``!``) and returns a nested dict.

    Parameters
    ----------
    header : dict
        The ADAT header_metadata dictionary.
    prefix : str
        The key prefix to match (e.g. ``'PlateScale_Scalar_'``).
    stage : str or None, optional
        If provided, the value is wrapped under this sub-key:
        ``{"<PlateId>": {"<stage>": <value>}}``.
        If ``None``, the value is stored flat:
        ``{"<PlateId>": <value>}``.

    Returns
    -------
    dict
        A dict mapping PlateId to the (possibly nested) value, or an empty
        dict if no matching keys are found.

    Examples
    --------
    >>> consolidate_plate_fields(
    ...     {'PlateScale_Scalar_PLT1': '1.23', '!PlateScale_Scalar_PLT2': '0.99'},
    ...     prefix='PlateScale_Scalar_',
    ... )
    {'PLT1': {'PlatformSpecific': '1.23'}, 'PLT2': {'PlatformSpecific': '0.99'}}
    """
    result: dict[str, Any] = {}
    for raw_key, value in header.items():
        clean_key = strip_bang_prefix(raw_key)
        if clean_key.startswith(prefix):
            plate_id = clean_key[len(prefix) :]
            if plate_id:
                result[plate_id] = {stage: value} if stage is not None else value
    return result


# ---------------------------------------------------------------------------
# Pattern helpers used by col_data conversion
# ---------------------------------------------------------------------------

_CAL_PLATE_RE = re.compile(r'^Cal_(.+)$')
_CAL_QC_RATIO_RE = re.compile(r'^CalQcRatio_(.+?)_(.+)$')
_QC_REFERENCE_RE = re.compile(r'^QcReference_(.+)$')


def match_cal_plate(name: str) -> str | None:
    """Return the PlateId if *name* matches ``Cal_<PlateId>``, else ``None``."""
    m = _CAL_PLATE_RE.match(name)
    return m.group(1) if m else None


def match_cal_qc_ratio(name: str) -> tuple[str, str] | None:
    """Return ``(plate_id, qc_sample_id)`` if *name* matches ``CalQcRatio_*``, else ``None``."""
    m = _CAL_QC_RATIO_RE.match(name)
    return (m.group(1), m.group(2)) if m else None


def match_qc_reference(name: str) -> str | None:
    """Return the QCSampleId if *name* matches ``QcReference_<QCSampleId>``, else ``None``."""
    m = _QC_REFERENCE_RE.match(name)
    return m.group(1) if m else None

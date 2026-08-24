"""Utility classes and helpers for ADAT v2.0 conversion.

This module provides reusable utility classes for conversion operations
including source context management, MedNorm validation, and header merging.
It also contains shared helper functions used by both the ``array/`` and
``ngs/`` conversion sub-packages.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import math
import re
import uuid
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from somadata.adat import Adat

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helper functions (formerly in _helpers.py)
# ---------------------------------------------------------------------------


def generate_guid() -> str:
    """Return a new GUID in ``GID-<uuid4>`` format."""
    return f'GID-{uuid.uuid4()}'


def compute_file_md5sum(file_path: str) -> str:
    """Compute MD5 checksum of a file.

    Parameters
    ----------
    file_path : str
        Path to the file.

    Returns
    -------
    str
        Hexadecimal MD5 digest (32 characters).
    """
    md5 = hashlib.md5(usedforsecurity=False)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def compute_adat_md5sum(adat: Adat) -> str:
    """Compute MD5 checksum of an Adat's structure and data.

    Computes a deterministic hash of the Adat's header metadata, column
    structure, row structure, and RFU values. Used as a fallback identifier
    when the source ADAT lacks an AdatId and was not loaded from a file.

    Parameters
    ----------
    adat : Adat
        The source ADAT object.

    Returns
    -------
    str
        Hexadecimal MD5 digest string (32 characters).

    Examples
    --------
    >>> md5 = compute_adat_md5sum(adat)
    >>> len(md5)
    32
    """
    md5 = hashlib.md5(usedforsecurity=False)

    hdr = getattr(adat, 'header_metadata', {})
    for key in sorted(hdr.keys()):
        val = str(hdr[key])
        md5.update(key.encode('utf-8'))
        md5.update(val.encode('utf-8'))

    if hasattr(adat, 'columns'):
        for name in adat.columns.names:
            md5.update(str(name).encode('utf-8'))
        for i in range(min(10, adat.columns.nlevels)):
            vals = adat.columns.get_level_values(i)
            for val in list(vals)[:10]:
                md5.update(str(val).encode('utf-8'))

    if hasattr(adat, 'index'):
        for name in adat.index.names:
            md5.update(str(name).encode('utf-8'))
        for i in range(min(10, adat.index.nlevels)):
            vals = adat.index.get_level_values(i)
            for val in list(vals)[:10]:
                md5.update(str(val).encode('utf-8'))

    if hasattr(adat, 'values'):
        values = adat.values
        if values.size > 10000:
            md5.update(values[:5, :5].tobytes())
            md5.update(values[-5:, -5:].tobytes())
            mid_r, mid_c = values.shape[0] // 2, values.shape[1] // 2
            md5.update(values[mid_r : mid_r + 5, mid_c : mid_c + 5].tobytes())
        else:
            md5.update(values.tobytes())

    return md5.hexdigest()


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
    {'PLT1': {'PlatformSpecific': 1.23}, 'PLT2': {'PlatformSpecific': 0.99}}
    """
    result: dict[str, Any] = {}
    for raw_key, value in header.items():
        clean_key = strip_bang_prefix(raw_key)
        if clean_key.startswith(prefix):
            plate_id = clean_key[len(prefix) :]
            if plate_id:
                coerced = coerce_numeric(value)
                result[plate_id] = {stage: coerced} if stage is not None else coerced
    return result


def coerce_numeric(value: Any) -> Any:
    """Return *value* as a float if it represents a number, else unchanged.

    Converts string representations of numbers to ``float``.  Non-numeric
    strings and non-string types are returned unchanged.

    Always returns ``float`` (never ``int``) so that decimal-valued header JSON
    fields (e.g. PlateScaleScalar, CalibrateTailPercent) are serialised as
    bare JSON numbers with a decimal point when appropriate.

    Parameters
    ----------
    value : any
        The value to coerce.

    Returns
    -------
    float, or the original value
        The float representation if conversion is possible, otherwise the
        original value.

    Examples
    --------
    >>> coerce_numeric('1.23')
    1.23
    >>> coerce_numeric('PASS')
    'PASS'
    >>> coerce_numeric(0.72)
    0.72
    >>> coerce_numeric('1.0')
    1.0
    """
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            pass
    return value


# ---------------------------------------------------------------------------
# Merge utilities (used by merge.py for Mixed conversions)
# ---------------------------------------------------------------------------


def merge_pipe_delimited(val_a: str, val_b: str) -> str:
    """Merge two strings by combining unique, non-empty pipe-delimited values.

    Values already pipe-delimited inside each argument are split and
    deduplicated before rejoining.  Insertion order is preserved (``val_a``
    tokens first).

    Parameters
    ----------
    val_a : str
        First string value (may itself be pipe-delimited).
    val_b : str
        Second string value (may itself be pipe-delimited).

    Returns
    -------
    str
        A single pipe-delimited string of unique non-empty tokens, or ``''``
        if both inputs are blank.

    Examples
    --------
    >>> merge_pipe_delimited('Human', 'Human')
    'Human'
    >>> merge_pipe_delimited('Human', 'Mouse')
    'Human|Mouse'
    >>> merge_pipe_delimited('A|B', 'B|C')
    'A|B|C'
    >>> merge_pipe_delimited('', 'EDTA Plasma')
    'EDTA Plasma'
    """
    seen: set[str] = set()
    tokens: list[str] = []
    for raw in (val_a, val_b):
        if not raw:
            continue
        for part in raw.split('|'):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                tokens.append(part)
    return '|'.join(tokens)


def merge_plate_json(
    dict_a: dict,
    dict_b: dict,
    field_name: str = '',
) -> dict:
    """Combine two plate-keyed JSON dicts, raising on duplicate PlateId.

    Parameters
    ----------
    dict_a : dict
        First plate-keyed dict (e.g. ``{"PLT1": {"PlatformSpecific": "1.02"}}``).
    dict_b : dict
        Second plate-keyed dict.
    field_name : str, optional
        Field name used in the error message when a duplicate is found.

    Returns
    -------
    dict
        Merged dict containing all PlateId keys from both inputs.

    Raises
    ------
    ValueError
        If the same PlateId key appears in both ``dict_a`` and ``dict_b``.

    Examples
    --------
    >>> merge_plate_json({'PLT1': '1.02'}, {'PLT2': '0.98'})
    {'PLT1': '1.02', 'PLT2': '0.98'}
    >>> merge_plate_json({'PLT1': '1.02'}, {'PLT1': '0.98'})
    Traceback (most recent call last):
        ...
    ValueError: Duplicate PlateId 'PLT1' in field ...
    """
    duplicates = set(dict_a) & set(dict_b)
    if duplicates:
        dup_list = ', '.join(repr(k) for k in sorted(duplicates))
        field_info = f' for field {field_name!r}' if field_name else ''
        raise ValueError(
            f'Duplicate PlateId {dup_list} found when merging plate-keyed JSON'
            f'{field_info}. Each PlateId must appear in only one source ADAT.'
        )
    return {**dict_a, **dict_b}


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


# ---------------------------------------------------------------------------
# Row data conversion helpers (shared by array/row_data and ngs/row_data)
# ---------------------------------------------------------------------------


def try_float(value: str) -> float | None:
    """Return *value* as float, or ``None`` on failure.

    Parameters
    ----------
    value : str
        String value to convert to float.

    Returns
    -------
    float or None
        Float value if conversion succeeds, None otherwise.

    Examples
    --------
    >>> try_float('1.23')
    1.23
    >>> try_float('invalid') is None
    True
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def derive_hyb_norm_status(scale_factor: str) -> str:
    """Return ``'PASS'`` if 0.4 <= float(scale_factor) <= 2.5, else ``'FLAG'``.

    Returns ``''`` for missing / non-numeric values.

    Parameters
    ----------
    scale_factor : str
        HybNormScaleFactor value to check.

    Returns
    -------
    str
        'PASS', 'FLAG', or '' (empty for non-numeric).

    Examples
    --------
    >>> derive_hyb_norm_status('1.0')
    'PASS'
    >>> derive_hyb_norm_status('3.0')
    'FLAG'
    >>> derive_hyb_norm_status('')
    ''
    """
    f = try_float(scale_factor)
    if f is None:
        return ''
    return 'PASS' if 0.4 <= f <= 2.5 else 'FLAG'


def derive_hyb_norm_status_vectorized(scale_factors: list[str]) -> list[str]:
    """Vectorized version of HybNormStatus derivation.

    Returns 'PASS' if 0.4 <= float(value) <= 2.5, else 'FLAG', or '' for non-numeric.

    Parameters
    ----------
    scale_factors : list[str]
        HybNormScaleFactor values for all rows.

    Returns
    -------
    list[str]
        Status values ('PASS', 'FLAG', or '') for each row.

    Examples
    --------
    >>> derive_hyb_norm_status_vectorized(['1.0', '3.0', 'invalid'])
    ['PASS', 'FLAG', '']
    """
    arr = np.array(scale_factors, dtype=object)
    result = np.full(len(arr), '', dtype=object)

    try:
        numeric = pd.to_numeric(arr, errors='coerce')
        valid_mask = ~np.isnan(numeric)

        pass_mask = valid_mask & (numeric >= 0.4) & (numeric <= 2.5)
        flag_mask = valid_mask & ~pass_mask

        result[pass_mask] = 'PASS'
        result[flag_mask] = 'FLAG'
    except Exception:
        logger.debug('Vectorized HybNormStatus derivation failed; falling back to scalar.')
        return [derive_hyb_norm_status(v) for v in scale_factors]

    return result.tolist()


# ---------------------------------------------------------------------------
# Source Context Classes
# ---------------------------------------------------------------------------


class V2SourceContext:
    """Lightweight context for v2.0 ADAT sources in merge operations.

    Used when merging a pre-conversion ADAT with an existing v2.0 ADAT to
    provide consistent source identifiers for header merging.

    Attributes
    ----------
    source_file_id : str
        Source file identifier (e.g. '1', '2').
    process_steps_id : str
        ProcessSteps identifier.
    report_config_id : str
        ReportConfig identifier.
    """

    def __init__(
        self,
        source_file_id: str = '1',
        process_steps_id: str = '1',
        report_config_id: str = '1',
    ):
        self.source_file_id = source_file_id
        self.process_steps_id = process_steps_id
        self.report_config_id = report_config_id


# ---------------------------------------------------------------------------
# MedNorm Validation Utilities
# ---------------------------------------------------------------------------


class MedNormValidator:
    """Utilities for validating MedNorm compatibility between ADATs."""

    @staticmethod
    def get_mednorm_ext_vectors(adat: Adat) -> dict[str, dict[str, str]]:
        """Extract Ref.MedNormExt.* column values keyed by (field, SeqId).

        Parameters
        ----------
        adat : Adat
            Source ADAT.

        Returns
        -------
        dict
            ``{field_name: {seq_id: value}}`` for all ``Ref.MedNormExt.*`` levels.
        """
        columns = getattr(adat, 'columns', None)
        if columns is None or not hasattr(columns, 'names'):
            return {}

        result: dict[str, dict[str, str]] = {}
        seq_id_level = None
        if 'SeqId' in columns.names:
            seq_id_level = columns.get_level_values('SeqId')

        for name in columns.names:
            if name.startswith('Ref.MedNormExt.'):
                values = columns.get_level_values(name)
                if seq_id_level is not None:
                    result[name] = {
                        str(sid): str(val) for sid, val in zip(seq_id_level, values)
                    }
                else:
                    result[name] = {}

        return result

    @staticmethod
    def get_mednorm_id_set(adat: Adat) -> set[str]:
        """Return the set of Ref.MedNorm.Id values present in COL_DATA.

        Parameters
        ----------
        adat : Adat
            Source ADAT.

        Returns
        -------
        set[str]
            Set of Ref.MedNorm.Id values.
        """
        columns = getattr(adat, 'columns', None)
        if columns is None or 'Ref.MedNorm.Id' not in columns.names:
            return set()
        return set(str(v) for v in columns.get_level_values('Ref.MedNorm.Id') if v)

    @staticmethod
    def has_mednorm_ext(header: dict) -> bool:
        """Check if ProcessSteps contains MedNormExt (pre-conversion format).

        Parameters
        ----------
        header : dict
            Pre-conversion header metadata (ProcessSteps is a string).

        Returns
        -------
        bool
            True if ProcessSteps contains 'MedNormExt'.
        """
        raw = lookup_header(header, 'ProcessSteps')
        if not raw:
            return False
        steps = parse_process_steps(raw)
        return 'MedNormExt' in steps

    @staticmethod
    def has_mednorm_ext_v2(header: dict) -> bool:
        """Check if ProcessSteps contains MedNormExt (v2.0 format).

        Parameters
        ----------
        header : dict
            v2.0 header metadata (ProcessSteps is a dict).

        Returns
        -------
        bool
            True if any ProcessSteps entry contains 'MedNormExt'.
        """
        ps = header.get('ProcessSteps')
        if not ps or not isinstance(ps, dict):
            return False
        for steps_str in ps.values():
            if 'MedNormExt' in steps_str:
                return True
        return False

    @staticmethod
    def validate_with_v2(
        raw_adat: Adat,
        v2_adat: Adat,
        med_norm_ref: str | None,
    ) -> Literal['array', 'ngs'] | None:
        """Validate MedNorm compatibility between a pre-conversion and v2.0 ADAT.

        Parameters
        ----------
        raw_adat : Adat
            Pre-conversion ADAT (array or NGS).
        v2_adat : Adat
            v2.0 ADAT.
        med_norm_ref : str or None
            MedNorm reference override identifier.

        Returns
        -------
        Literal['array', 'ngs'] or None
            Which source's Ref.MedNormExt values to use, or None if identical.

        Raises
        ------
        MedNormMismatchError
            If Ref.MedNormExt vectors are incompatible.
        """
        from somadata.conversion.detection import InputType, detect_input_type
        from somadata.conversion.errors import MedNormMismatchError

        raw_vecs = MedNormValidator.get_mednorm_ext_vectors(raw_adat)
        v2_vecs = MedNormValidator.get_mednorm_ext_vectors(v2_adat)

        shared_fields = set(raw_vecs) & set(v2_vecs)
        if not shared_fields:
            return None

        raw_cols = getattr(raw_adat, 'columns', None)
        v2_cols = getattr(v2_adat, 'columns', None)
        if raw_cols is None or v2_cols is None:
            return None

        if 'SeqId' in raw_cols.names and 'SeqId' in v2_cols.names:
            raw_seqids = set(raw_cols.get_level_values('SeqId'))
            v2_seqids = set(v2_cols.get_level_values('SeqId'))
            shared_seqids = raw_seqids & v2_seqids
        else:
            return None

        if not shared_seqids:
            return None

        mismatches: list[str] = []
        for field in sorted(shared_fields):
            for seq_id in sorted(shared_seqids):
                raw_val_str = raw_vecs[field].get(seq_id, '')
                v2_val_str = v2_vecs[field].get(seq_id, '')

                # Skip if either value is missing/NA sentinel
                def _is_missing(v: str) -> bool:
                    return not v or v.upper() in ('NA', 'NAN', 'NONE', '')

                if _is_missing(raw_val_str) or _is_missing(v2_val_str):
                    continue

                try:
                    raw_float = float(raw_val_str)
                    v2_float = float(v2_val_str)
                    if abs(raw_float - v2_float) > 0.1:
                        mismatches.append(
                            f'{field}[{seq_id}]: raw={raw_val_str!r} vs v2={v2_val_str!r} '
                            f'(diff={abs(raw_float - v2_float):.2e})'
                        )
                except (ValueError, TypeError):
                    if raw_val_str != v2_val_str:
                        mismatches.append(
                            f'{field}[{seq_id}]: raw={raw_val_str!r} vs v2={v2_val_str!r}'
                        )

        if not mismatches:
            return None

        if med_norm_ref is not None:
            raw_ids = MedNormValidator.get_mednorm_id_set(raw_adat)
            v2_ids = MedNormValidator.get_mednorm_id_set(v2_adat)

            raw_type = detect_input_type(raw_adat)

            if med_norm_ref in raw_ids:
                source_name = (
                    'array'
                    if raw_type in (InputType.BRIDGED_ARRAY, InputType.NATIVE_ARRAY)
                    else 'ngs'
                )
                logger.info(
                    'Ref.MedNormExt mismatch resolved by med_norm_ref=%r (%s source)',
                    med_norm_ref,
                    source_name,
                )
                return source_name
            if med_norm_ref in v2_ids:
                source_name = (
                    'ngs'
                    if raw_type in (InputType.BRIDGED_ARRAY, InputType.NATIVE_ARRAY)
                    else 'array'
                )
                logger.info(
                    'Ref.MedNormExt mismatch resolved by med_norm_ref=%r (v2 source as %s)',
                    med_norm_ref,
                    source_name,
                )
                return source_name

            raise MedNormMismatchError(
                f'med_norm_ref={med_norm_ref!r} does not match any Ref.MedNorm.Id '
                f'value in either source. '
                f'Raw IDs: {sorted(raw_ids)!r}. v2.0 IDs: {sorted(v2_ids)!r}.'
            )

        detail = '\n  '.join(mismatches[:10])
        if len(mismatches) > 10:
            detail += f'\n  ... and {len(mismatches) - 10} more'
        raise MedNormMismatchError(
            f'Ref.MedNormExt reference vectors are not equivalent for shared SeqIds '
            f'(spec §3.4 requires |a − b| ≤ 0.1 RFU for common non-missing SeqIds). '
            f'Mismatches ({len(mismatches)} total):\n  {detail}\n'
            f'Provide med_norm_ref to override.'
        )

    @staticmethod
    def validate_v2_pair(
        adat_a: Adat,
        adat_b: Adat,
        med_norm_ref: str | None,
    ) -> Literal['array', 'ngs'] | None:
        """Validate MedNorm compatibility between two v2.0 ADATs.

        Parameters
        ----------
        adat_a : Adat
            First v2.0 ADAT.
        adat_b : Adat
            Second v2.0 ADAT.
        med_norm_ref : str or None
            MedNorm reference override identifier.

        Returns
        -------
        Literal['array', 'ngs'] or None
            Which source's Ref.MedNormExt values to use, or None if identical.

        Raises
        ------
        MedNormMismatchError
            If Ref.MedNormExt vectors are incompatible.
        """
        from somadata.conversion.errors import MedNormMismatchError

        vecs_a = MedNormValidator.get_mednorm_ext_vectors(adat_a)
        vecs_b = MedNormValidator.get_mednorm_ext_vectors(adat_b)

        shared_fields = set(vecs_a) & set(vecs_b)
        if not shared_fields:
            return None

        cols_a = getattr(adat_a, 'columns', None)
        cols_b = getattr(adat_b, 'columns', None)
        if cols_a is None or cols_b is None:
            return None

        if 'SeqId' in cols_a.names and 'SeqId' in cols_b.names:
            seqids_a = set(cols_a.get_level_values('SeqId'))
            seqids_b = set(cols_b.get_level_values('SeqId'))
            shared_seqids = seqids_a & seqids_b
        else:
            return None

        if not shared_seqids:
            return None

        mismatches: list[str] = []
        for field in sorted(shared_fields):
            for seq_id in sorted(shared_seqids):
                val_a_str = vecs_a[field].get(seq_id, '')
                val_b_str = vecs_b[field].get(seq_id, '')

                # Skip if either value is missing/NA sentinel
                def _is_missing_v(v: str) -> bool:
                    return not v or v.upper() in ('NA', 'NAN', 'NONE', '')

                if _is_missing_v(val_a_str) or _is_missing_v(val_b_str):
                    continue

                # NGS-only pairs require exact match — use tight float tolerance
                # to absorb float-representation noise while treating any
                # meaningful difference as a true mismatch.
                try:
                    float_a = float(val_a_str)
                    float_b = float(val_b_str)
                    if not math.isclose(float_a, float_b, rel_tol=1e-9, abs_tol=1e-12):
                        mismatches.append(
                            f'{field}[{seq_id}]: source_a={val_a_str!r} vs source_b={val_b_str!r} '
                            f'(diff={abs(float_a - float_b):.2e})'
                        )
                except (ValueError, TypeError):
                    if val_a_str != val_b_str:
                        mismatches.append(
                            f'{field}[{seq_id}]: source_a={val_a_str!r} vs source_b={val_b_str!r}'
                        )

        if not mismatches:
            return None

        if med_norm_ref is not None:
            ids_a = MedNormValidator.get_mednorm_id_set(adat_a)
            ids_b = MedNormValidator.get_mednorm_id_set(adat_b)

            if med_norm_ref in ids_a:
                logger.info(
                    'Ref.MedNormExt mismatch resolved by med_norm_ref=%r (first source)',
                    med_norm_ref,
                )
                return 'array'
            if med_norm_ref in ids_b:
                logger.info(
                    'Ref.MedNormExt mismatch resolved by med_norm_ref=%r (second source)',
                    med_norm_ref,
                )
                return 'ngs'

            raise MedNormMismatchError(
                f'med_norm_ref={med_norm_ref!r} does not match any Ref.MedNorm.Id '
                f'value in either source. '
                f'Source A IDs: {sorted(ids_a)!r}. Source B IDs: {sorted(ids_b)!r}.'
            )

        detail = '\n  '.join(mismatches[:10])
        if len(mismatches) > 10:
            detail += f'\n  ... and {len(mismatches) - 10} more'
        raise MedNormMismatchError(
            f'Ref.MedNormExt reference vectors are not equivalent for shared SeqIds '
            f'(NGS-only merges require near-exact Ref.MedNormExt match across sources; '
            f'float representation noise is tolerated but meaningful differences are not). '
            f'Mismatches ({len(mismatches)} total):\n  {detail}\n'
            f'Provide med_norm_ref to override.'
        )


# ---------------------------------------------------------------------------
# ProcessSteps Validation
# ---------------------------------------------------------------------------


def validate_v2_ngs_process_steps(adat_a: Adat, adat_b: Adat) -> None:
    """Validate that two v2.0 NGS-only ADATs have identical ProcessSteps.

    For NGS-only pairs, both sources must have the same ProcessSteps entries.

    Parameters
    ----------
    adat_a : Adat
        First v2.0 NGS ADAT.
    adat_b : Adat
        Second v2.0 NGS ADAT.

    Raises
    ------
    ProcessStepsMismatchError
        If ProcessSteps are not identical.
    """
    from somadata.conversion.errors import ProcessStepsMismatchError

    ps_a = adat_a.header_metadata.get('ProcessSteps', {})
    ps_b = adat_b.header_metadata.get('ProcessSteps', {})

    if not isinstance(ps_a, dict) or not isinstance(ps_b, dict):
        return

    steps_a = sorted(ps_a.values())
    steps_b = sorted(ps_b.values())

    if steps_a != steps_b:
        raise ProcessStepsMismatchError(
            f'NGS-only v2.0 pair requires identical ProcessSteps. '
            f'Source A has {len(ps_a)} ProcessSteps entries; '
            f'Source B has {len(ps_b)} ProcessSteps entries. '
            f'ProcessSteps values do not match.'
        )


# ---------------------------------------------------------------------------
# Header Merging Utilities
# ---------------------------------------------------------------------------


class HeaderMerger:
    """Utilities for merging v2.0 headers from multiple sources."""

    @staticmethod
    def merge_array_headers(
        header_a: dict,
        header_b: dict,
        ctx_a,
        ctx_b,
    ) -> dict:
        """Merge two converted array v2.0 headers into Array output header.

        Similar to merge_mixed_headers but output AssayType='Array'.

        Parameters
        ----------
        header_a : dict
            First converted array v2.0 header.
        header_b : dict
            Second converted array v2.0 header.
        ctx_a : ArrayConversionContext or V2SourceContext
            Conversion context for first array (with source IDs).
        ctx_b : ArrayConversionContext or V2SourceContext
            Conversion context for second array (with source IDs).

        Returns
        -------
        dict
            A new v2.0-compliant header dict with AssayType='Array'.
        """
        from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES

        out: dict = {key: '' for key in V2_HEADER_FIELD_TYPES}

        out['FileVersion'] = '2.0'
        out['AssayType'] = 'Array'
        out['FileCreatedDate'] = datetime.datetime.now(datetime.timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        out['AdatId'] = generate_guid()

        sf_a = header_a.get('SourceFile') or {}
        sf_b = header_b.get('SourceFile') or {}
        merged_sf: dict = {}
        for _key, val in sf_a.items():
            merged_sf[ctx_a.source_file_id] = val
        for _key, val in sf_b.items():
            merged_sf[ctx_b.source_file_id] = val
        out['SourceFile'] = merged_sf

        ps_a = header_a.get('ProcessSteps') or {}
        ps_b = header_b.get('ProcessSteps') or {}
        merged_ps: dict = {}
        for _key, val in ps_a.items():
            merged_ps[ctx_a.process_steps_id] = val
        for _key, val in ps_b.items():
            merged_ps[ctx_b.process_steps_id] = val
        out['ProcessSteps'] = merged_ps

        rc_a = header_a.get('ReportConfig') or {}
        rc_b = header_b.get('ReportConfig') or {}
        merged_rc: dict = {}
        for _key, val in rc_a.items():
            merged_rc[ctx_a.report_config_id] = val
        for _key, val in rc_b.items():
            merged_rc[ctx_b.report_config_id] = val
        if merged_rc:
            out['ReportConfig'] = merged_rc

        _PIPE_FIELDS = (
            'Title',
            'StudyOrganism',
            'StudyMatrix',
            'SOMAmerReferenceSource',
            'UseRestriction',
        )
        for field in _PIPE_FIELDS:
            merged = merge_pipe_delimited(
                header_a.get(field, ''), header_b.get(field, '')
            )
            if merged:
                out[field] = merged

        _PLATE_JSON_FIELDS = (
            'PlateScaleScalar',
            'CalibrateTailPercent',
            'CalibrateTailPercentStatus',
            'QCCheckTailPercent',
            'QCCheckTailPercentStatus',
            'PlateScaleStatus',
        )
        for field in _PLATE_JSON_FIELDS:
            dict_a = header_a.get(field) or {}
            dict_b = header_b.get(field) or {}
            if not isinstance(dict_a, dict):
                dict_a = {}
            if not isinstance(dict_b, dict):
                dict_b = {}
            merged_plates = merge_plate_json(dict_a, dict_b, field_name=field)
            if merged_plates:
                out[field] = merged_plates

        return out

    @staticmethod
    def merge_v2_headers(
        header_a: dict,
        header_b: dict,
        assay_type: str,
    ) -> dict:
        """Merge two v2.0 headers into a single v2.0 output header.

        Simplified version of merge_mixed_headers for v2 + v2 case where both
        sources already have v2.0 structure.

        Parameters
        ----------
        header_a : dict
            First v2.0 header.
        header_b : dict
            Second v2.0 header.
        assay_type : str
            Output AssayType ('Array', 'NGS', or 'Mixed').

        Returns
        -------
        dict
            A new v2.0-compliant header dict.
        """
        from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES

        out: dict = {key: '' for key in V2_HEADER_FIELD_TYPES}

        out['FileVersion'] = '2.0'
        out['AssayType'] = assay_type
        out['FileCreatedDate'] = datetime.datetime.now(datetime.timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        out['AdatId'] = generate_guid()

        sf_a = header_a.get('SourceFile') or {}
        sf_b = header_b.get('SourceFile') or {}
        if not isinstance(sf_a, dict):
            sf_a = {}
        if not isinstance(sf_b, dict):
            sf_b = {}

        merged_sf: dict = {}
        next_id = 1
        for _key, val in sorted(sf_a.items()):
            merged_sf[str(next_id)] = val
            next_id += 1
        for _key, val in sorted(sf_b.items()):
            merged_sf[str(next_id)] = val
            next_id += 1
        out['SourceFile'] = merged_sf

        ps_a = header_a.get('ProcessSteps') or {}
        ps_b = header_b.get('ProcessSteps') or {}
        if not isinstance(ps_a, dict):
            ps_a = {}
        if not isinstance(ps_b, dict):
            ps_b = {}

        merged_ps: dict = {}
        next_id = 1
        for _key, val in sorted(ps_a.items()):
            merged_ps[str(next_id)] = val
            next_id += 1
        for _key, val in sorted(ps_b.items()):
            merged_ps[str(next_id)] = val
            next_id += 1
        out['ProcessSteps'] = merged_ps

        rc_a = header_a.get('ReportConfig') or {}
        rc_b = header_b.get('ReportConfig') or {}
        if not isinstance(rc_a, dict):
            rc_a = {}
        if not isinstance(rc_b, dict):
            rc_b = {}

        merged_rc: dict = {}
        next_id = 1
        for _key, val in sorted(rc_a.items()):
            merged_rc[str(next_id)] = val
            next_id += 1
        for _key, val in sorted(rc_b.items()):
            merged_rc[str(next_id)] = val
            next_id += 1
        if merged_rc:
            out['ReportConfig'] = merged_rc

        _PIPE_FIELDS = (
            'Title',
            'StudyOrganism',
            'StudyMatrix',
            'SOMAmerReferenceSource',
            'UseRestriction',
        )
        for field in _PIPE_FIELDS:
            merged = merge_pipe_delimited(
                header_a.get(field, ''), header_b.get(field, '')
            )
            if merged:
                out[field] = merged

        _PLATE_JSON_FIELDS = (
            'PlateScaleScalar',
            'CalibrateTailPercent',
            'CalibrateTailPercentStatus',
            'QCCheckTailPercent',
            'QCCheckTailPercentStatus',
            'PlateScaleStatus',
        )
        for field in _PLATE_JSON_FIELDS:
            dict_a = header_a.get(field) or {}
            dict_b = header_b.get(field) or {}
            if not isinstance(dict_a, dict):
                dict_a = {}
            if not isinstance(dict_b, dict):
                dict_b = {}
            merged_plates = merge_plate_json(dict_a, dict_b, field_name=field)
            if merged_plates:
                out[field] = merged_plates

        reads_a = header_a.get('PlateSOMAmerNormReadsStatus') or {}
        reads_b = header_b.get('PlateSOMAmerNormReadsStatus') or {}
        if not isinstance(reads_a, dict):
            reads_a = {}
        if not isinstance(reads_b, dict):
            reads_b = {}
        merged_reads = merge_plate_json(
            reads_a, reads_b, field_name='PlateSOMAmerNormReadsStatus'
        )
        if merged_reads:
            out['PlateSOMAmerNormReadsStatus'] = merged_reads

        return out


# ---------------------------------------------------------------------------
# Row Index Alignment
# ---------------------------------------------------------------------------


def _split_by_sample_readout(adat: Adat) -> tuple[Adat | None, Adat | None]:
    """Split a v2.0 ADAT into Array and NGS parts by SampleReadout.

    Parameters
    ----------
    adat : Adat
        v2.0 ADAT to split (may be Array-only, NGS-only, or Mixed).

    Returns
    -------
    tuple[Adat | None, Adat | None]
        (array_part, ngs_part) where each is None if that readout type is absent.
    """
    if 'SampleReadout' not in adat.index.names:
        return adat, None

    readouts = set(adat.index.get_level_values('SampleReadout'))

    if readouts == {'Array'}:
        return adat, None
    elif readouts == {'NGS'}:
        return None, adat
    elif readouts == {'Array', 'NGS'}:
        array_mask = adat.index.get_level_values('SampleReadout') == 'Array'
        ngs_mask = adat.index.get_level_values('SampleReadout') == 'NGS'
        return adat[array_mask], adat[ngs_mask]
    else:
        return adat, None


def align_row_indexes(
    index_a: pd.MultiIndex,
    index_b: pd.MultiIndex,
) -> tuple[pd.MultiIndex, pd.MultiIndex]:
    """Return both MultiIndexes reordered to a shared, canonical level set.

    Array and NGS row converters build their output MultiIndexes via
    insertion-order dicts, so the level ordering can differ even when both
    indexes carry stubs for the other platform's fields. This function
    computes the canonical union of all level names (``index_a`` order first,
    then any ``index_b``-exclusive names appended), then reindexes each
    MultiIndex to that canonical set — inserting blank (empty-string) levels
    for any fields that a source does not have.

    Parameters
    ----------
    index_a : pd.MultiIndex
        Row index from first source.
    index_b : pd.MultiIndex
        Row index from second source.

    Returns
    -------
    tuple[pd.MultiIndex, pd.MultiIndex]
        ``(index_a_aligned, index_b_aligned)`` — both share the same level
        names in the same order and can be safely passed to
        ``pd.MultiIndex.append``.
    """
    names_a = list(index_a.names)
    names_b = list(index_b.names)

    seen: set[str] = set(names_a)
    canonical: list[str] = list(names_a)
    for name in names_b:
        if name not in seen:
            canonical.append(name)
            seen.add(name)

    def _reorder(idx: pd.MultiIndex, ordered_names: list[str]) -> pd.MultiIndex:
        existing = set(idx.names)
        n = len(idx)
        arrays: list[list] = []
        for name in ordered_names:
            if name in existing:
                arrays.append(list(idx.get_level_values(name)))
            else:
                arrays.append([''] * n)
        return pd.MultiIndex.from_arrays(arrays, names=ordered_names)

    return _reorder(index_a, canonical), _reorder(index_b, canonical)


def remap_row_index_ids(
    index: pd.MultiIndex,
    old_to_new_mapping: dict[str, str],
) -> pd.MultiIndex:
    """Remap SourceFileId, ProcessStepsId, and ReportConfigId levels to new header keys.

    When merging headers, SourceFile/ProcessSteps/ReportConfig keys are renumbered.
    This function updates the corresponding *Id levels in the row index to match
    the new header structure.

    Parameters
    ----------
    index : pd.MultiIndex
        Row index with SourceFileId, ProcessStepsId, and/or ReportConfigId levels.
    old_to_new_mapping : dict[str, str]
        Mapping from old header keys to new header keys for each JSON field.
        Example: {'1': '2', '2': '3'} when renumbering IDs during merge.

    Returns
    -------
    pd.MultiIndex
        A new MultiIndex with *Id levels remapped according to the mapping.

    Examples
    --------
    >>> # After merge_v2_headers renumbers SourceFile keys from '1' to '1', '2' to '2'
    >>> # but v2 input had SourceFileId='1', we need to remap it to '2'
    >>> remapped = remap_row_index_ids(v2_index, {'1': '2'})
    """
    id_levels = {'SourceFileId', 'ProcessStepsId', 'ReportConfigId'}
    remap_needed = id_levels & set(index.names)

    if not remap_needed:
        return index

    arrays: list[list] = []
    for name in index.names:
        level_values = list(index.get_level_values(name))
        if name in remap_needed:
            level_values = [
                old_to_new_mapping.get(str(val), str(val)) for val in level_values
            ]
        arrays.append(level_values)

    return pd.MultiIndex.from_arrays(arrays, names=index.names)

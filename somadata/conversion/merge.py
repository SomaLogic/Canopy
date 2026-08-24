"""Merge logic for ADAT v2.0 Mixed conversion (bridged array + native NGS).

Public API
----------
compute_seqid_union(array_adat, ngs_adat) -> tuple[pd.DataFrame, pd.MultiIndex]
    Build the union SeqId RFU DataFrame and merged COL_DATA MultiIndex.

validate_mednorm_compatibility(array_adat, ngs_adat) -> None
    Validate that the two raw (pre-conversion) ADATs are compatible for merging.
    Raises MedNormMismatchError if Ref.MedNormExt values differ,
    or ProcessStepsMismatchError if ProcessSteps are not bridged-compatible.

validate_dilution_alignment(array_adat, ngs_adat) -> None
    Validate that all shared SeqIds have identical Dilution values.
    Array Dilution must already be converted to fractions (÷100) before calling.

merge_mixed_headers(array_header, ngs_header, array_ctx, ngs_ctx) -> dict
    Combine two converted v2.0 header dicts into the final Mixed header.
"""

from __future__ import annotations

import datetime
import logging
import math
from typing import TYPE_CHECKING, Literal

import pandas as pd

from somadata.conversion._helpers import (
    generate_guid,
    lookup_header,
    merge_pipe_delimited,
    merge_plate_json,
    parse_process_steps,
)
from somadata.conversion.errors import DilutionMismatchError, MedNormMismatchError, ProcessStepsMismatchError
from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES

if TYPE_CHECKING:
    from somadata.adat import Adat
    from somadata.conversion.array import ArrayConversionContext
    from somadata.conversion.ngs import NGSConversionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Expected ProcessSteps for merge validation (Section 3.4)
# ---------------------------------------------------------------------------

# Array bridged terminal triple (last 3 steps must match exactly).
_ARRAY_TERMINAL_TRIPLE = [
    'CrossPlatformPlateScale',
    'CrossPlatformCalibrate',
    'MedNormExt',
]


# NGS exact ProcessSteps sequence
_NGS_REQUIRED_STEPS = [
    'Raw',
    'HybNorm',
    'MedNormInt',
    'PlatformSpecificPlateScale',
    'PlatformSpecificCalibrate',
    'CrossPlatformPlateScale',
    'CrossPlatformCalibrate',
    'MedNormExt',
]


# ---------------------------------------------------------------------------
# Task 1.8: MedNorm Reference Validation
# ---------------------------------------------------------------------------


def validate_mednorm_compatibility(
    array_adat: Adat,
    ngs_adat: Adat,
) -> None:
    """Validate that two raw ADATs are compatible for a Mixed merge.

    Checks ProcessSteps for both sources and verifies that shared
    ``Ref.MedNormExt.*`` reference vectors are identical.  Operates on
    the **raw** (pre-conversion) ADATs.

    Parameters
    ----------
    array_adat : Adat
        The bridged array source ADAT (before conversion).
    ngs_adat : Adat
        The native NGS source ADAT (before conversion).

    Raises
    ------
    ProcessStepsMismatchError
        If the array's terminal ProcessSteps do not end with the required
        bridged triple, or if the NGS ProcessSteps do not match the
        required exact sequence.
    MedNormMismatchError
        If the ``Ref.MedNormExt.*`` vectors for shared SeqIds are not
        identical across both sources.
    """
    _validate_array_process_steps(array_adat)
    _validate_ngs_process_steps(ngs_adat)
    _validate_mednorm_vectors(array_adat, ngs_adat)


def _validate_array_process_steps(adat: Adat) -> None:
    hdr = getattr(adat, 'header_metadata', {})
    raw = lookup_header(hdr, 'ProcessSteps')
    steps = parse_process_steps(raw)
    if steps[-3:] != _ARRAY_TERMINAL_TRIPLE:
        raise ProcessStepsMismatchError(
            f'Array ADAT ProcessSteps do not end with the required bridged '
            f'terminal triple {_ARRAY_TERMINAL_TRIPLE!r}. '
            f'Got last 3 steps: {steps[-3:]!r}. '
            f'The array source must be bridged before merging.'
        )


def _validate_ngs_process_steps(adat: Adat) -> None:
    hdr = getattr(adat, 'header_metadata', {})
    raw = lookup_header(hdr, 'ProcessSteps')
    steps = parse_process_steps(raw)
    if steps != _NGS_REQUIRED_STEPS:
        raise ProcessStepsMismatchError(
            f'NGS ADAT ProcessSteps do not match the required exact sequence. '
            f'Expected: {_NGS_REQUIRED_STEPS!r}. '
            f'Got: {steps!r}.'
        )


def _get_mednorm_ext_vectors(adat: Adat) -> dict[str, dict[str, float | None]]:
    """Extract Ref.MedNormExt.* column values keyed by (field, SeqId).

    Returns
    -------
    dict
        ``{field_name: {seq_id: value}}`` for all ``Ref.MedNormExt.*`` levels.
        Values are floats; ``None`` indicates a missing/NA value or a
        non-numeric legacy identifier (logged as a warning).
    """
    columns = getattr(adat, 'columns', None)
    if columns is None or not hasattr(columns, 'names'):
        return {}

    result: dict[str, dict[str, float | None]] = {}
    seq_id_level = None
    if 'SeqId' in columns.names:
        seq_id_level = columns.get_level_values('SeqId')

    for name in columns.names:
        if name.startswith('Ref.MedNormExt.'):
            values = columns.get_level_values(name)
            if seq_id_level is not None:
                result[name] = {}
                for sid, val in zip(seq_id_level, values):
                    # Recognise missing/NA sentinels → None
                    if val is None or val == '' or str(val).upper() in ('NA', 'NAN'):
                        result[name][str(sid)] = None
                        continue

                    try:
                        float_val = float(val)
                        result[name][str(sid)] = None if math.isnan(float_val) else float_val
                    except (ValueError, TypeError):
                        logger.warning(
                            'Non-numeric value %r in %s for SeqId %r; skipping comparison.',
                            val, name, sid,
                        )
                        result[name][str(sid)] = None
            else:
                result[name] = {}

    return result


def _validate_mednorm_vectors(
    array_adat: Adat,
    ngs_adat: Adat,
) -> None:
    """Check Ref.MedNormExt.* vector identity; raise on any mismatch.

    Raises
    ------
    MedNormMismatchError
        If any shared ``Ref.MedNormExt.*`` values differ between sources.
    """
    array_vecs = _get_mednorm_ext_vectors(array_adat)
    ngs_vecs = _get_mednorm_ext_vectors(ngs_adat)

    # Determine which Ref.MedNormExt.* fields are shared between both sources
    shared_fields = set(array_vecs) & set(ngs_vecs)
    if not shared_fields:
        # No shared Ref.MedNormExt fields — nothing to validate
        return

    # Find shared SeqIds between the two sources
    array_cols = getattr(array_adat, 'columns', None)
    ngs_cols = getattr(ngs_adat, 'columns', None)
    if array_cols is None or ngs_cols is None:
        return

    if 'SeqId' in array_cols.names and 'SeqId' in ngs_cols.names:
        array_seqids = set(array_cols.get_level_values('SeqId'))
        ngs_seqids = set(ngs_cols.get_level_values('SeqId'))
        shared_seqids = array_seqids & ngs_seqids
    else:
        return

    if not shared_seqids:
        return

    # Check element-wise equivalence for shared fields and shared SeqIds.
    # Per updated spec §3.4: |a − b| ≤ 0.1 RFU (absolute tolerance).
    # Skip comparisons where either value is None/missing — SeqIds missing on
    # either side are excluded from the check entirely.
    mismatches: list[str] = []
    for field in sorted(shared_fields):
        for seq_id in sorted(shared_seqids):
            array_val = array_vecs[field].get(seq_id)
            ngs_val = ngs_vecs[field].get(seq_id)

            # Skip comparison if either value is missing/None.
            if array_val is None or ngs_val is None:
                continue

            # Both values are guaranteed floats at this point.
            # Spec §3.4 (updated): equivalent = |a − b| ≤ 0.1 RFU.
            if abs(array_val - ngs_val) > 0.1:
                mismatches.append(
                    f'{field}[{seq_id}]: array={array_val!r} vs ngs={ngs_val!r} '
                    f'(diff={abs(array_val - ngs_val):.2e})'
                )

    if not mismatches:
        return

    detail = '\n  '.join(mismatches[:10])
    if len(mismatches) > 10:
        detail += f'\n  ... and {len(mismatches) - 10} more'
    raise MedNormMismatchError(
        f'Ref.MedNormExt reference vectors are not equivalent for shared SeqIds '
        f'(spec §3.4 requires |a − b| ≤ 0.1 RFU for common non-missing SeqIds). '
        f'Mismatches ({len(mismatches)} total):\n  {detail}\n'
        f'Ensure both source ADATs were normalized to the same reference.'
    )


# ---------------------------------------------------------------------------
# Dilution Alignment Validation (spec §3.4)
# ---------------------------------------------------------------------------


def validate_dilution_alignment(array_adat: Adat, ngs_adat: Adat) -> None:
    """Validate that shared SeqIds have identical Dilution values across sources.

    Must be called **after** array Dilution values have been converted to
    fractions (÷100), so both sources use the NGS-convention fractions.
    Per spec §3.4: if any shared SeqId has differing Dilution values, raise.

    Parameters
    ----------
    array_adat : Adat
        Converted v2.0 array intermediate (Dilution already ÷100).
    ngs_adat : Adat
        Converted v2.0 NGS intermediate.

    Raises
    ------
    DilutionMismatchError
        If any shared SeqId has a different Dilution value between sources.
    """
    array_cols = getattr(array_adat, 'columns', None)
    ngs_cols = getattr(ngs_adat, 'columns', None)
    if array_cols is None or ngs_cols is None:
        return
    if 'Dilution' not in array_cols.names or 'Dilution' not in ngs_cols.names:
        return
    if 'SeqId' not in array_cols.names or 'SeqId' not in ngs_cols.names:
        return

    array_seqids = list(array_cols.get_level_values('SeqId'))
    ngs_seqids = list(ngs_cols.get_level_values('SeqId'))
    shared_seqids = set(array_seqids) & set(ngs_seqids)
    if not shared_seqids:
        return

    # Build SeqId → Dilution lookup for each source
    array_dil = {
        str(sid): str(dil)
        for sid, dil in zip(
            array_cols.get_level_values('SeqId'),
            array_cols.get_level_values('Dilution'),
        )
    }
    ngs_dil = {
        str(sid): str(dil)
        for sid, dil in zip(
            ngs_cols.get_level_values('SeqId'),
            ngs_cols.get_level_values('Dilution'),
        )
    }

    mismatches: list[str] = []
    for seq_id in sorted(shared_seqids):
        a_val = array_dil.get(seq_id, '')
        n_val = ngs_dil.get(seq_id, '')

        # Treat blank/zero as missing-dilution sentinels (control probes, randomers,
        # monospikes, etc. don't carry meaningful Dilution groups).  If either source
        # has a missing value, skip the comparison — the analyte is acting as a control
        # in at least one assay and cross-source Dilution agreement is not required.
        def _is_missing_dil(v: str) -> bool:
            if not v or v.strip() == '':
                return True
            try:
                return float(v) == 0.0
            except (ValueError, TypeError):
                return False

        if _is_missing_dil(a_val) or _is_missing_dil(n_val):
            continue

        # Compare as floats to avoid formatting differences (e.g. '0.2' vs '0.20')
        try:
            if not math.isclose(float(a_val), float(n_val), rel_tol=1e-9, abs_tol=1e-12):
                mismatches.append(
                    f'{seq_id}: array={a_val!r} vs ngs={n_val!r}'
                )
        except (TypeError, ValueError):
            if a_val != n_val:
                mismatches.append(
                    f'{seq_id}: array={a_val!r} vs ngs={n_val!r}'
                )

    if mismatches:
        detail = '\n  '.join(mismatches[:10])
        if len(mismatches) > 10:
            detail += f'\n  ... and {len(mismatches) - 10} more'
        raise DilutionMismatchError(
            f'Dilution values differ for {len(mismatches)} shared SeqId(s) '
            f'(spec §3.4 requires all shared SeqIds to have identical Dilution '
            f'after converting array percentages to fractions).\n  {detail}'
        )
# ---------------------------------------------------------------------------


def compute_seqid_union(
    array_adat: Adat,
    ngs_adat: Adat,
) -> tuple[pd.DataFrame, pd.MultiIndex]:
    """Build the union SeqId RFU matrix and merged COL_DATA MultiIndex.

    Takes two already-converted v2.0 intermediate Adats and combines their
    RFU matrices and column annotations via SeqId union.  Array rows appear
    first, NGS rows below.

    Parameters
    ----------
    array_adat : Adat
        The converted v2.0 array intermediate (``AssayType='Mixed'``).
    ngs_adat : Adat
        The converted v2.0 NGS intermediate (``AssayType='Mixed'``).

    Returns
    -------
    tuple[pd.DataFrame, pd.MultiIndex]
        A 2-tuple of:
        - ``rfu_df`` — combined RFU DataFrame (rows = all samples, columns = union SeqIds)
        - ``merged_columns`` — combined COL_DATA MultiIndex over the union SeqIds
    """
    array_columns: pd.MultiIndex = array_adat.columns
    ngs_columns: pd.MultiIndex = ngs_adat.columns

    # Extract SeqId sets
    if 'SeqId' not in array_columns.names or 'SeqId' not in ngs_columns.names:
        raise ValueError('Both converted ADATs must have a "SeqId" level in columns.')

    array_seqids = list(array_columns.get_level_values('SeqId'))
    ngs_seqids = list(ngs_columns.get_level_values('SeqId'))

    # Compute sorted union with control SOMAmers (SeqId starting with "0") at end.
    # Per CAN-56: lexicographic sort, but push all SeqIds starting with "0"
    # (e.g. "0000-00" control probes) to the end of the column order.
    _all_seqids = set(array_seqids) | set(ngs_seqids)
    union_seqids: list[str] = sorted(
        s for s in _all_seqids if not s.startswith('0')
    ) + sorted(s for s in _all_seqids if s.startswith('0'))

    # Build flat DataFrames with SeqId as the (simple) column index for reindexing
    array_df = pd.DataFrame(
        array_adat.values,
        index=array_adat.index,
        columns=array_seqids,
    )
    ngs_df = pd.DataFrame(
        ngs_adat.values,
        index=ngs_adat.index,
        columns=ngs_seqids,
    )

    # Reindex to union SeqId set, filling missing positions with NaN
    array_df = array_df.reindex(columns=union_seqids)
    ngs_df = ngs_df.reindex(columns=union_seqids)

    # Concatenate rows (array on top, NGS below)
    rfu_df = pd.concat([array_df, ngs_df], axis=0)

    # Build merged COL_DATA MultiIndex
    merged_columns = _merge_col_data(
        array_columns, ngs_columns, union_seqids
    )

    return rfu_df, merged_columns


def _merge_col_data(
    array_columns: pd.MultiIndex,
    ngs_columns: pd.MultiIndex,
    union_seqids: list[str],
) -> pd.MultiIndex:
    """Merge two v2.0 COL_DATA MultiIndexes over the union SeqId set.

    For each SeqId in the union:
    - Shared SeqIds: array values are preferred for fields present in both;
      NGS-specific fields are filled from the NGS source.
    - Array-only SeqIds: NGS-specific annotation fields are blank.
    - NGS-only SeqIds: array-specific annotation fields are blank.

    Parameters
    ----------
    array_columns : pd.MultiIndex
        Column MultiIndex of the converted array intermediate.
    ngs_columns : pd.MultiIndex
        Column MultiIndex of the converted NGS intermediate.
    union_seqids : list[str]
        The sorted union SeqId set.

    Returns
    -------
    pd.MultiIndex
        Merged COL_DATA MultiIndex over ``union_seqids``.
    """
    # Build lookup: SeqId → {level_name: value} for each source
    array_lookup = _build_seqid_lookup(array_columns)
    ngs_lookup = _build_seqid_lookup(ngs_columns)

    # Determine all level names — union of both sources
    array_level_names = list(array_columns.names)
    ngs_level_names = list(ngs_columns.names)

    # Preserve ordering: array fields first, then NGS-exclusive fields
    seen: set[str] = set()
    all_level_names: list[str] = []
    for name in array_level_names:
        if name not in seen:
            all_level_names.append(name)
            seen.add(name)
    for name in ngs_level_names:
        if name not in seen:
            all_level_names.append(name)
            seen.add(name)

    # For each level, build per-SeqId values across the union
    level_arrays: dict[str, list[str]] = {name: [] for name in all_level_names}

    for seq_id in union_seqids:
        array_row = array_lookup.get(seq_id, {})
        ngs_row = ngs_lookup.get(seq_id, {})
        is_shared = bool(array_row) and bool(ngs_row)

        for name in all_level_names:
            # HybControl: NGS is always authoritative for shared SeqIds.
            # The array converter synthesises HybControl as all-False (array ADATs
            # carry no hybridisation control analytes), so array wins would
            # incorrectly erase any True values coming from the NGS source.
            if is_shared and name == 'HybControl' and name in ngs_row:
                level_arrays[name].append(ngs_row[name])
            elif name in array_row:
                # Prefer array value for fields present in array
                level_arrays[name].append(array_row[name])
            elif name in ngs_row:
                # Fall back to NGS value (NGS-exclusive fields or NGS-only SeqId)
                level_arrays[name].append(ngs_row[name])
            else:
                level_arrays[name].append('')

    return pd.MultiIndex.from_arrays(
        [level_arrays[name] for name in all_level_names],
        names=all_level_names,
    )


def _build_seqid_lookup(columns: pd.MultiIndex) -> dict[str, dict[str, str]]:
    """Return ``{seq_id: {level_name: value}}`` for a COL_DATA MultiIndex."""
    seq_ids = columns.get_level_values('SeqId')

    # Extract all level values upfront
    level_arrays = [columns.get_level_values(name) for name in columns.names]

    # Build lookup dict: iterate once over SeqIds, once over levels
    result: dict[str, dict[str, str]] = {}
    for i, seq_id in enumerate(seq_ids):
        row: dict[str, str] = {}
        for j, name in enumerate(columns.names):
            row[name] = str(level_arrays[j][i])
        result[str(seq_id)] = row
    return result


# ---------------------------------------------------------------------------
# Task 1.9: Mixed Header & Metadata Combination
# ---------------------------------------------------------------------------


def merge_mixed_headers(
    array_header: dict,
    ngs_header: dict,
    array_ctx: ArrayConversionContext,
    ngs_ctx: NGSConversionContext,
) -> dict:
    """Combine two converted v2.0 header dicts into the final Mixed header.

    Implements the Mixed header merge rules from spec Section 3.4.
    The two inputs should already be the **converted** v2.0 headers (output
    of :func:`~somadata.conversion.array.header.convert_array_header` and
    :func:`~somadata.conversion.ngs.header.convert_ngs_header` called with
    ``assay_type='Mixed'``).

    Parameters
    ----------
    array_header : dict
        The converted v2.0 array intermediate header.
    ngs_header : dict
        The converted v2.0 NGS intermediate header.
    array_ctx : ArrayConversionContext
        Conversion context for the array source (must have
        ``source_file_id='1'``, ``process_steps_id='1'``).
    ngs_ctx : NGSConversionContext
        Conversion context for the NGS source (must have
        ``source_file_id='2'``, ``process_steps_id='2'``).

    Returns
    -------
    dict
        A new v2.0-compliant header dict with ``AssayType='Mixed'``.

    Raises
    ------
    ValueError
        If both sources have a PlateId key in any plate-keyed JSON field
        that would cause a duplicate.
    """
    out: dict = {key: '' for key in V2_HEADER_FIELD_TYPES}

    # ------------------------------------------------------------------
    # 1. Static / generated fields
    # ------------------------------------------------------------------
    out['FileVersion'] = '2.0'
    out['AssayType'] = 'Mixed'
    out['FileCreatedDate'] = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ'
    )
    out['AdatId'] = generate_guid()

    # ------------------------------------------------------------------
    # 2. SourceFile — Merge both: {"1": array_entry, "2": ngs_entry}
    # ------------------------------------------------------------------
    array_sf = array_header.get('SourceFile') or {}
    ngs_sf = ngs_header.get('SourceFile') or {}
    merged_sf: dict = {}
    # Map from the per-source IDs in the intermediate headers to the final IDs
    for _key, val in array_sf.items():
        merged_sf[array_ctx.source_file_id] = val
    for _key, val in ngs_sf.items():
        merged_sf[ngs_ctx.source_file_id] = val
    out['SourceFile'] = merged_sf

    # ------------------------------------------------------------------
    # 4. ProcessSteps — Merge: {"1": array_steps, "2": ngs_steps}
    # ------------------------------------------------------------------
    array_ps = array_header.get('ProcessSteps') or {}
    ngs_ps = ngs_header.get('ProcessSteps') or {}
    merged_ps: dict = {}
    for _key, val in array_ps.items():
        merged_ps[array_ctx.process_steps_id] = val
    for _key, val in ngs_ps.items():
        merged_ps[ngs_ctx.process_steps_id] = val
    out['ProcessSteps'] = merged_ps

    # ------------------------------------------------------------------
    # 5. ReportConfig — Array's value only (keep key "1")
    # ------------------------------------------------------------------
    array_rc = array_header.get('ReportConfig') or ''
    if array_rc:
        out['ReportConfig'] = array_rc

    # ------------------------------------------------------------------
    # 6. Pipe-delimited merge of unique values for study-level string fields
    # ------------------------------------------------------------------
    _PIPE_FIELDS = (
        'Title',
        'StudyOrganism',
        'StudyMatrix',
        'SOMAmerReferenceSource',
        'UseRestriction',
    )
    for field in _PIPE_FIELDS:
        merged = merge_pipe_delimited(
            array_header.get(field, ''), ngs_header.get(field, '')
        )
        if merged:
            out[field] = merged

    # ------------------------------------------------------------------
    # 7. Plate-keyed JSON fields — combine all PlateId keys; error on duplicates
    # ------------------------------------------------------------------
    _PLATE_JSON_FIELDS = (
        'PlateScaleScalar',
        'CalibrateTailPercent',
        'CalibrateTailPercentStatus',
        'QCCheckTailPercent',
        'QCCheckTailPercentStatus',
        'PlateScaleStatus',
    )
    for field in _PLATE_JSON_FIELDS:
        dict_a = array_header.get(field) or {}
        dict_b = ngs_header.get(field) or {}
        if not isinstance(dict_a, dict):
            dict_a = {}
        if not isinstance(dict_b, dict):
            dict_b = {}
        merged_plates = merge_plate_json(dict_a, dict_b, field_name=field)
        if merged_plates:
            out[field] = merged_plates

    # ------------------------------------------------------------------
    # 8. PlateSOMAmerNormReadsStatus — NGS's value only
    # ------------------------------------------------------------------
    ngs_reads_status = ngs_header.get('PlateSOMAmerNormReadsStatus') or ''
    if ngs_reads_status:
        out['PlateSOMAmerNormReadsStatus'] = ngs_reads_status

    return out

"""Merge logic for ADAT v2.0 Mixed conversion (bridged array + native NGS).

Public API
----------
compute_seqid_union(array_adat, ngs_adat) -> tuple[pd.DataFrame, pd.MultiIndex]
    Build the union SeqId RFU DataFrame and merged COL_DATA MultiIndex.

validate_mednorm_compatibility(array_adat, ngs_adat, med_norm_ref=None) -> None
    Validate that the two raw (pre-conversion) ADATs are compatible for merging.

merge_mixed_headers(array_header, ngs_header, array_ctx, ngs_ctx) -> dict
    Combine two converted v2.0 header dicts into the final Mixed header.
"""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import pandas as pd

from somadata.conversion._helpers import (
    generate_guid,
    lookup_header,
    merge_pipe_delimited,
    merge_plate_json,
    parse_process_steps,
)
from somadata.conversion.errors import MedNormMismatchError, ProcessStepsMismatchError
from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES

if TYPE_CHECKING:
    from somadata.adat import Adat
    from somadata.conversion.array import ArrayConversionContext
    from somadata.conversion.ngs import NGSConversionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Expected ProcessSteps for merge validation (Section 3.4)
# ---------------------------------------------------------------------------

# Array bridged terminal triple (last 3 steps must match exactly)
_ARRAY_TERMINAL_TRIPLE = [
    'CrossPlatformPlateScaling',
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
    med_norm_ref: str | None = None,
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
    med_norm_ref : str or None, optional
        If provided and the ``Ref.MedNormExt`` vectors differ between the two
        sources, the reference values are taken from whichever source's
        ``Ref.MedNorm.Id`` level matches this identifier.  Raises
        :class:`~somadata.conversion.errors.MedNormMismatchError` if the
        identifier matches neither source.

    Raises
    ------
    ProcessStepsMismatchError
        If the array's terminal ProcessSteps do not end with the required
        bridged triple, or if the NGS ProcessSteps do not match the
        required exact sequence.
    MedNormMismatchError
        If the ``Ref.MedNormExt.*`` vectors for shared SeqIds are not
        identical and no ``med_norm_ref`` override resolves the mismatch.
    """
    _validate_array_process_steps(array_adat)
    _validate_ngs_process_steps(ngs_adat)
    _validate_mednorm_vectors(array_adat, ngs_adat, med_norm_ref=med_norm_ref)


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


def _get_mednorm_ext_vectors(adat: Adat) -> dict[str, dict[str, str]]:
    """Extract Ref.MedNormExt.* column values keyed by (field, SeqId).

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


def _get_mednorm_id_set(adat: Adat) -> set[str]:
    """Return the set of Ref.MedNorm.Id values present in COL_DATA."""
    columns = getattr(adat, 'columns', None)
    if columns is None or 'Ref.MedNorm.Id' not in columns.names:
        return set()
    return set(str(v) for v in columns.get_level_values('Ref.MedNorm.Id') if v)


def _validate_mednorm_vectors(
    array_adat: Adat,
    ngs_adat: Adat,
    med_norm_ref: str | None,
) -> None:
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

    # Check element-wise exact string identity for shared fields and shared SeqIds
    mismatches: list[str] = []
    for field in sorted(shared_fields):
        for seq_id in sorted(shared_seqids):
            array_val = array_vecs[field].get(seq_id, '')
            ngs_val = ngs_vecs[field].get(seq_id, '')
            if array_val != ngs_val:
                mismatches.append(
                    f'{field}[{seq_id}]: array={array_val!r} vs ngs={ngs_val!r}'
                )

    if not mismatches:
        return

    # Mismatches found — try to resolve with med_norm_ref override
    if med_norm_ref is not None:
        array_ids = _get_mednorm_id_set(array_adat)
        ngs_ids = _get_mednorm_id_set(ngs_adat)
        if med_norm_ref in array_ids or med_norm_ref in ngs_ids:
            logger.info(
                'Ref.MedNormExt mismatch resolved by med_norm_ref=%r', med_norm_ref
            )
            return
        raise MedNormMismatchError(
            f'med_norm_ref={med_norm_ref!r} does not match any Ref.MedNorm.Id '
            f'value in either source. '
            f'Array IDs: {sorted(array_ids)!r}. NGS IDs: {sorted(ngs_ids)!r}.'
        )

    detail = '\n  '.join(mismatches[:10])
    if len(mismatches) > 10:
        detail += f'\n  ... and {len(mismatches) - 10} more'
    raise MedNormMismatchError(
        f'Ref.MedNormExt reference vectors are not identical for shared SeqIds. '
        f'Mismatches ({len(mismatches)} total):\n  {detail}\n'
        f'Provide med_norm_ref to override.'
    )


# ---------------------------------------------------------------------------
# Task 1.7: SeqId Union & Missing Value Fill
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

    # Compute sorted union
    union_seqids: list[str] = sorted(set(array_seqids) | set(ngs_seqids))

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
    merged_columns = _merge_col_data(array_columns, ngs_columns, union_seqids)

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

        for name in all_level_names:
            if name in array_row:
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
    result: dict[str, dict[str, str]] = {}
    for i, seq_id in enumerate(seq_ids):
        row: dict[str, str] = {}
        for j, name in enumerate(columns.names):
            # Use positional index to avoid ambiguity when level names repeat
            row[name] = str(columns.get_level_values(j)[i])
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
    # 2. AssayVersion — Array's value
    # ------------------------------------------------------------------
    if array_header.get('AssayVersion'):
        out['AssayVersion'] = array_header['AssayVersion']

    # ------------------------------------------------------------------
    # 3. SourceFile — Merge both: {"1": array_entry, "2": ngs_entry}
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

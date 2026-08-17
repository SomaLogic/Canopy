from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from somadata.adat import Adat as AdatClass
from somadata.conversion._helpers import _compute_adat_md5sum, _compute_file_md5sum
from somadata.conversion.array import ArrayConversionContext
from somadata.conversion.array.col_data import convert_array_col_data
from somadata.conversion.array.header import convert_array_header
from somadata.conversion.array.row_data import convert_array_row_data
from somadata.conversion.array.validation import validate_source_array_adat
from somadata.conversion.detection import InputType, detect_input_type, diagnose_bridging
from somadata.conversion.errors import (
    AssayVersionError,
    ConversionError,
    UnsupportedCombinationError,
)
from somadata.conversion.merge import (
    _merge_col_data,
    compute_seqid_union,
    merge_mixed_headers,
    validate_dilution_alignment,
    validate_mednorm_compatibility,
)
from somadata.conversion.ngs import NGSConversionContext
from somadata.conversion.ngs.col_data import convert_ngs_col_data
from somadata.conversion.ngs.header import convert_ngs_header
from somadata.conversion.ngs.row_data import convert_ngs_row_data
from somadata.conversion.ngs.validation import validate_source_ngs_adat
from somadata.conversion.utils import (
    HeaderMerger,
    MedNormValidator,
    V2SourceContext,
    align_row_indexes,
    remap_row_index_ids,
    validate_v2_ngs_process_steps,
)
from somadata.io.adat.v2_fields import validate_v2_header_fields

if TYPE_CHECKING:
    from somadata.adat import Adat

logger = logging.getLogger(__name__)

# NGS-space input types that cannot be combined with native_array.
_NGS_SPACE_TYPES: frozenset[InputType] = frozenset(
    {InputType.NATIVE_NGS, InputType.V2_COMBINED}
)


def to_v2_adat(
    adats: list[str | Adat],
) -> Adat:
    """Convert one or two pre-v2.0 ADATs (or file paths) into a single v2.0 Adat.

    Parameters
    ----------
    adats : list of str or Adat
        One or two items. Each element is either a file-system path to an
        ``.adat`` file or an already-loaded :class:`~somadata.adat.Adat`
        object (mixed allowed).  Paths are read via the existing
        :func:`~somadata.io.adat.file.read_adat` function.

    Returns
    -------
    Adat
        A single v2.0 combined-format Adat.

    Raises
    ------
    ValueError
        If *adats* is empty or contains more than 2 items.
    UnsupportedCombinationError
        If the detected input-type combination does not have an approved
        conversion.

    Examples
    --------
    >>> result = to_v2_adat(['bridged_array.adat', 'ngs_sample.adat'])
    >>> somadata.write_adat(result, 'output_v2.adat')
    """
    if not adats:
        raise ValueError('adats must contain at least one ADAT.')
    if len(adats) > 2:
        raise ValueError(f'to_v2_adat() accepts max 2 inputs. Received: {len(adats)}.')

    loaded = [_load(adat) for adat in adats]

    if len(loaded) == 1:
        adat, md5sum = loaded[0]
        input_type = detect_input_type(adat)

        if input_type is InputType.V2_COMBINED:
            logger.warning('Input already v2.0. Returning as-is.')
            return adat

        handler = _APPROVED_SINGLE_CONVERSIONS.get(input_type)
        if handler is None:
            raise UnsupportedCombinationError(
                f'Unsupported input combination: {input_type.value}.'
            )
        return handler(adat, md5sum=md5sum)

    # Two inputs
    adat_a, md5_a = loaded[0]
    adat_b, md5_b = loaded[1]
    type_a = detect_input_type(adat_a)
    type_b = detect_input_type(adat_b)

    # native_array cannot be combined with any NGS-space input; the array
    # must be bridged first.
    input_types = {type_a, type_b}
    if InputType.NATIVE_ARRAY in input_types and input_types & _NGS_SPACE_TYPES:
        ngs_type = next(t for t in input_types if t in _NGS_SPACE_TYPES)
        array_adat = adat_a if type_a is InputType.NATIVE_ARRAY else adat_b
        diag = diagnose_bridging(array_adat)
        msg = (
            f'Native array data cannot be combined with NGS-space data '
            f'({ngs_type.value}). '
            f'The array input was not detected as bridged.'
        )
        if diag:
            msg += f'\n{diag}'
        raise UnsupportedCombinationError(msg)

    # Same-type pairs use a canonical tuple key; mixed-type pairs use a frozenset.
    key = (type_a, type_b) if type_a is type_b else frozenset({type_a, type_b})

    handler = _APPROVED_PAIR_CONVERSIONS.get(key)
    if handler is None:
        raise UnsupportedCombinationError(
            f'Unsupported input combination: {type_a.value} + {type_b.value}.'
        )
    return handler(
        adat_a, adat_b, md5sum_a=md5_a, md5sum_b=md5_b
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(adat: str | Adat) -> tuple[Adat, str | None]:
    """Return an Adat and optional md5sum, reading from disk if a path string was supplied.

    Returns
    -------
    tuple[Adat, str | None]
        The loaded Adat and the md5sum of the source file (if loaded from file).
        Returns None for the md5sum when an in-memory Adat object is passed.
    """
    # Import here to avoid circular dependency
    from somadata.io.adat.file import read_adat

    if isinstance(adat, str):
        md5sum = _compute_file_md5sum(adat)
        loaded_adat = read_adat(adat)
        return loaded_adat, md5sum
    if isinstance(adat, AdatClass):
        return adat, None
    raise TypeError(
        f'Each element of adats must be a file path (str) or an Adat object; '
        f'got {type(adat).__name__!r}.'
    )


# ---------------------------------------------------------------------------
# Conversion handlers
# ---------------------------------------------------------------------------


def _merge_bridged_array_and_ngs(
    adat_a: Adat,
    adat_b: Adat,
    *,
    md5sum_a: str | None,
    md5sum_b: str | None,
) -> Adat:
    """Merge a bridged array ADAT and a native NGS ADAT into a Mixed v2.0 output."""
    # 1. Identify which input is array and which is NGS (order-independent)
    type_a = detect_input_type(adat_a)
    if type_a is InputType.BRIDGED_ARRAY:
        raw_array, raw_ngs = adat_a, adat_b
        md5_array, md5_ngs = md5sum_a, md5sum_b
    else:
        raw_array, raw_ngs = adat_b, adat_a
        md5_array, md5_ngs = md5sum_b, md5sum_a

    # 2. Validate MedNorm compatibility on raw (pre-conversion) inputs;
    # Ref.MedNormExt.* values must be identical across both sources (no override).
    validate_mednorm_compatibility(raw_array, raw_ngs)

    # 3. Build conversion contexts; assign source IDs for Mixed output
    array_ctx = ArrayConversionContext.from_adat(
        raw_array, source_file_md5sum=md5_array
    )
    array_ctx.source_file_id = '1'
    array_ctx.process_steps_id = '1'
    array_ctx.report_config_id = '1'

    ngs_ctx = NGSConversionContext.from_adat(raw_ngs, source_file_md5sum=md5_ngs)
    ngs_ctx.source_file_id = '2'
    ngs_ctx.process_steps_id = '2'

    # 4. Run per-source conversions with assay_type='Mixed'
    validate_source_array_adat(raw_array)
    array_header_v2 = convert_array_header(raw_array, array_ctx, assay_type='Mixed')
    array_columns_v2 = convert_array_col_data(
        raw_array, calibrator_id=array_ctx.calibrator_id
    )
    array_index_v2 = convert_array_row_data(raw_array, array_ctx)

    validate_source_ngs_adat(raw_ngs)
    ngs_header_v2 = convert_ngs_header(raw_ngs, ngs_ctx, assay_type='Mixed')
    ngs_columns_v2 = convert_ngs_col_data(raw_ngs, matrix=ngs_ctx.matrix)
    ngs_index_v2 = convert_ngs_row_data(raw_ngs, ngs_ctx)

    # Assemble temporary intermediate Adats to pass into SeqId union
    array_intermediate = AdatClass(
        data=raw_array.values,
        index=array_index_v2,
        columns=array_columns_v2,
        header_metadata=array_header_v2,
    )
    ngs_intermediate = AdatClass(
        data=raw_ngs.values,
        index=ngs_index_v2,
        columns=ngs_columns_v2,
        header_metadata=ngs_header_v2,
    )

    # 4b. Validate Dilution alignment: after array ÷100 conversion all shared
    # SeqIds must have matching Dilution values (spec §3.4).
    validate_dilution_alignment(array_intermediate, ngs_intermediate)

    # 5. Compute SeqId union and merged COL_DATA
    rfu_df, merged_columns = compute_seqid_union(
        array_intermediate, ngs_intermediate
    )

    # 6. Merge headers into final Mixed header
    mixed_header = merge_mixed_headers(
        array_header_v2, ngs_header_v2, array_ctx, ngs_ctx
    )

    # 7. Assemble final Mixed Adat
    # Row index: align both indexes to a shared ordered level set, then concatenate.
    array_index_v2, ngs_index_v2 = align_row_indexes(array_index_v2, ngs_index_v2)
    merged_index = array_index_v2.append(ngs_index_v2)

    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=mixed_header,
    )

    if not validate_v2_header_fields(mixed_header):
        raise ConversionError(
            'Mixed header metadata is not compliant with the v2.0 closed field set. '
            'See logged warnings above for details.'
        )

    return result


def _merge_bridged_array_and_v2(
    adat_a: Adat,
    adat_b: Adat,
    *,
    md5sum_a: str | None,
    md5sum_b: str | None,
) -> Adat:
    """Merge a bridged array ADAT and an existing v2.0 ADAT into a Mixed v2.0 output.

    The v2.0 input can be Array, NGS, or Mixed. MedNorm validation is applied
    based on the v2.0's AssayType.
    """
    # 1. Identify which input is array and which is v2.0 (order-independent)
    type_a = detect_input_type(adat_a)
    if type_a is InputType.BRIDGED_ARRAY:
        raw_array, v2_adat = adat_a, adat_b
        md5_array, md5_v2 = md5sum_a, md5sum_b
    else:
        raw_array, v2_adat = adat_b, adat_a
        md5_array, md5_v2 = md5sum_b, md5sum_a

    # 2. Determine v2.0 input's AssayType and derive output AssayType
    v2_assay_type = v2_adat.header_metadata.get('AssayType', '')
    # Adding array to any v2.0 type always results in Mixed (unless v2.0 was Array-only)
    if v2_assay_type == 'Array':
        output_assay_type = 'Array'
    else:
        output_assay_type = 'Mixed'

    # 3. MedNorm validation based on ProcessSteps
    array_has_mednorm = MedNormValidator.has_mednorm_ext(raw_array.header_metadata)
    v2_has_mednorm = MedNormValidator.has_mednorm_ext_v2(v2_adat.header_metadata)

    if array_has_mednorm and v2_has_mednorm:
        MedNormValidator.validate_with_v2(
            raw_array, v2_adat, med_norm_ref=None
        )

    # 4. Convert array source to v2.0
    array_ctx = ArrayConversionContext.from_adat(
        raw_array, source_file_md5sum=md5_array
    )
    array_ctx.source_file_id = '1'
    array_ctx.process_steps_id = '1'
    array_ctx.report_config_id = '1'

    validate_source_array_adat(raw_array)
    array_header_v2 = convert_array_header(
        raw_array, array_ctx, assay_type=output_assay_type
    )
    array_columns_v2 = convert_array_col_data(
        raw_array, calibrator_id=array_ctx.calibrator_id
    )
    array_index_v2 = convert_array_row_data(raw_array, array_ctx)

    array_intermediate = AdatClass(
        data=raw_array.values,
        index=array_index_v2,
        columns=array_columns_v2,
        header_metadata=array_header_v2,
    )

    # 5. Remap v2 ADAT row index *Id levels to match assigned context IDs
    # The v2 input's row index stores SourceFileId/ProcessStepsId/ReportConfigId
    # from its original header keys. We assign it new IDs ('2', '2', '2') in v2_ctx,
    # so we must remap the index levels to match.
    v2_ctx = V2SourceContext(
        source_file_id='2', process_steps_id='2', report_config_id='2'
    )

    # Build mapping from v2's original keys to the new IDs we're assigning
    v2_original_sf_keys = list((v2_adat.header_metadata.get('SourceFile') or {}).keys())
    v2_original_ps_keys = list(
        (v2_adat.header_metadata.get('ProcessSteps') or {}).keys()
    )
    v2_original_rc_keys = list(
        (v2_adat.header_metadata.get('ReportConfig') or {}).keys()
    )

    id_mapping: dict[str, str] = {}
    for old_key in v2_original_sf_keys:
        id_mapping[old_key] = v2_ctx.source_file_id
    for old_key in v2_original_ps_keys:
        id_mapping[old_key] = v2_ctx.process_steps_id
    for old_key in v2_original_rc_keys:
        id_mapping[old_key] = v2_ctx.report_config_id

    v2_index_remapped = remap_row_index_ids(v2_adat.index, id_mapping)

    # 6. Compute SeqId union with correct argument ordering
    # compute_seqid_union expects array-first + ngs-second and applies array-prefers
    # COL_DATA rules. When v2_adat contains Array rows, we need to ensure array rows
    # come first in both arguments and final output.

    v2_readouts = set(v2_adat.index.get_level_values('SampleReadout'))

    if output_assay_type == 'Array' or v2_readouts == {'NGS'}:
        # Simple case: array_intermediate is array, v2_adat is NGS (or both array)
        # Order is correct: array first, NGS second
        rfu_df, merged_columns = compute_seqid_union(
            array_intermediate, v2_adat
        )
    else:
        # v2_adat is Mixed: contains both Array and NGS rows
        # We need to split v2 by SampleReadout, merge the array parts first,
        # then merge with NGS parts to maintain array-first order

        v2_array_mask = v2_adat.index.get_level_values('SampleReadout') == 'Array'
        v2_ngs_mask = ~v2_array_mask

        v2_array_part = v2_adat[v2_array_mask]
        v2_ngs_part = v2_adat[v2_ngs_mask]

        v2_array_index = v2_index_remapped[v2_array_mask]
        v2_ngs_index = v2_index_remapped[v2_ngs_mask]

        # Merge array parts: array_intermediate + v2_array_part
        # Use simple concatenation since both are array data
        array_seqids = list(array_intermediate.columns.get_level_values('SeqId'))
        v2_array_seqids = list(v2_array_part.columns.get_level_values('SeqId'))
        union_array_seqids = sorted(set(array_seqids) | set(v2_array_seqids))

        array_df = pd.DataFrame(
            array_intermediate.values,
            index=array_intermediate.index,
            columns=array_seqids,
        ).reindex(columns=union_array_seqids)

        v2_array_df = pd.DataFrame(
            v2_array_part.values,
            index=v2_array_part.index,
            columns=v2_array_seqids,
        ).reindex(columns=union_array_seqids)

        combined_array_df = pd.concat([array_df, v2_array_df], axis=0)

        # For COL_DATA, prefer array_intermediate values for shared SeqIds
        # (similar to compute_seqid_union's array-prefers logic)
        combined_array_columns = _merge_col_data(
            array_intermediate.columns,
            v2_array_part.columns,
            union_array_seqids,
        )

        # Build combined array Adat
        combined_array = AdatClass(
            data=combined_array_df.values,
            index=combined_array_df.index,
            columns=combined_array_columns,
            header_metadata={},
        )

        # Now merge combined array with NGS part using compute_seqid_union
        rfu_df, merged_columns = compute_seqid_union(
            combined_array, v2_ngs_part
        )

        # Update row indexes to reflect the split
        array_index_v2 = combined_array.index
        v2_index_remapped = v2_ngs_index

    # 7. Merge headers
    if output_assay_type == 'Array':
        merged_header = HeaderMerger.merge_array_headers(
            array_header_v2, v2_adat.header_metadata, array_ctx, v2_ctx
        )
    else:
        merged_header = merge_mixed_headers(
            array_header_v2, v2_adat.header_metadata, array_ctx, v2_ctx
        )

    # 8. Align row indexes and concatenate
    array_index_v2, v2_index_remapped = align_row_indexes(
        array_index_v2, v2_index_remapped
    )
    merged_index = array_index_v2.append(v2_index_remapped)

    # 9. Assemble result
    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=merged_header,
    )

    if not validate_v2_header_fields(merged_header):
        raise ConversionError(
            'Merged header metadata is not compliant with the v2.0 closed field set. '
            'See logged warnings above for details.'
        )

    return result


def _merge_ngs_and_v2(
    adat_a: Adat,
    adat_b: Adat,
    *,
    md5sum_a: str | None,
    md5sum_b: str | None,
) -> Adat:
    """Merge a native NGS ADAT and an existing v2.0 ADAT into a Mixed or NGS v2.0 output.

    Output AssayType depends on v2.0's content:
    - If v2.0 is NGS-only → output is NGS
    - Otherwise → output is Mixed
    """
    # 1. Identify which input is NGS and which is v2.0 (order-independent)
    type_a = detect_input_type(adat_a)
    if type_a is InputType.NATIVE_NGS:
        raw_ngs, v2_adat = adat_a, adat_b
        md5_ngs, md5_v2 = md5sum_a, md5sum_b
    else:
        raw_ngs, v2_adat = adat_b, adat_a
        md5_ngs, md5_v2 = md5sum_b, md5sum_a

    # 2. Determine output AssayType based on v2.0's content
    v2_assay_type = v2_adat.header_metadata.get('AssayType', '')
    if v2_assay_type == 'NGS':
        output_assay_type = 'NGS'
    else:
        output_assay_type = 'Mixed'

    # 3. MedNorm validation based on ProcessSteps
    ngs_has_mednorm = MedNormValidator.has_mednorm_ext(raw_ngs.header_metadata)
    v2_has_mednorm = MedNormValidator.has_mednorm_ext_v2(v2_adat.header_metadata)

    if ngs_has_mednorm and v2_has_mednorm:
        MedNormValidator.validate_with_v2(
            raw_ngs, v2_adat, med_norm_ref=None
        )

    # 4. Convert NGS source to v2.0
    ngs_ctx = NGSConversionContext.from_adat(raw_ngs, source_file_md5sum=md5_ngs)
    ngs_ctx.source_file_id = '1'
    ngs_ctx.process_steps_id = '1'

    validate_source_ngs_adat(raw_ngs)
    ngs_header_v2 = convert_ngs_header(raw_ngs, ngs_ctx, assay_type=output_assay_type)
    ngs_columns_v2 = convert_ngs_col_data(raw_ngs, matrix=ngs_ctx.matrix)
    ngs_index_v2 = convert_ngs_row_data(raw_ngs, ngs_ctx)

    ngs_intermediate = AdatClass(
        data=raw_ngs.values,
        index=ngs_index_v2,
        columns=ngs_columns_v2,
        header_metadata=ngs_header_v2,
    )

    # 5. Remap v2 ADAT row index *Id levels to match assigned context IDs
    # The v2 input's row index stores SourceFileId/ProcessStepsId/ReportConfigId
    # from its original header keys. We assign it new IDs ('2', '2', '2') in v2_ctx,
    # so we must remap the index levels to match.
    v2_ctx = V2SourceContext(
        source_file_id='2', process_steps_id='2', report_config_id='2'
    )

    # Build mapping from v2's original keys to the new IDs we're assigning
    v2_original_sf_keys = list((v2_adat.header_metadata.get('SourceFile') or {}).keys())
    v2_original_ps_keys = list(
        (v2_adat.header_metadata.get('ProcessSteps') or {}).keys()
    )
    v2_original_rc_keys = list(
        (v2_adat.header_metadata.get('ReportConfig') or {}).keys()
    )

    id_mapping: dict[str, str] = {}
    for old_key in v2_original_sf_keys:
        id_mapping[old_key] = v2_ctx.source_file_id
    for old_key in v2_original_ps_keys:
        id_mapping[old_key] = v2_ctx.process_steps_id
    for old_key in v2_original_rc_keys:
        id_mapping[old_key] = v2_ctx.report_config_id

    v2_index_remapped = remap_row_index_ids(v2_adat.index, id_mapping)

    # 6. Compute SeqId union with correct argument ordering
    # compute_seqid_union expects array-first + ngs-second. When v2_adat contains
    # Array rows, we need to split it and ensure array rows come first.

    v2_readouts = set(v2_adat.index.get_level_values('SampleReadout'))

    if output_assay_type == 'NGS':
        # Both inputs are NGS-only: use compute_seqid_union normally
        # (parameter names are misleading but function works for same-type merges)
        rfu_df, merged_columns = compute_seqid_union(
            ngs_intermediate, v2_adat
        )
    elif v2_readouts == {'NGS'}:
        # v2 is NGS-only, output is Mixed: ngs_intermediate + v2_adat (both NGS)
        # We have no array data, so use compute_seqid_union with ngs first
        rfu_df, merged_columns = compute_seqid_union(
            ngs_intermediate, v2_adat
        )
    elif 'Array' in v2_readouts:
        # v2 contains Array rows (could be Array-only or Mixed)
        # compute_seqid_union needs array-first ordering, so we must split v2
        # and call it with array rows first, NGS rows second

        v2_array_mask = v2_adat.index.get_level_values('SampleReadout') == 'Array'
        v2_ngs_mask = ~v2_array_mask

        v2_array_part = v2_adat[v2_array_mask]
        v2_ngs_part = v2_adat[v2_ngs_mask] if v2_ngs_mask.any() else None

        v2_array_index = v2_index_remapped[v2_array_mask]
        v2_ngs_index = v2_index_remapped[v2_ngs_mask] if v2_ngs_mask.any() else None

        if v2_ngs_part is not None and len(v2_ngs_part) > 0:
            # v2 is Mixed: has both Array and NGS rows
            # Merge NGS parts first (ngs_intermediate + v2_ngs_part)
            ngs_seqids = list(ngs_intermediate.columns.get_level_values('SeqId'))
            v2_ngs_seqids = list(v2_ngs_part.columns.get_level_values('SeqId'))
            union_ngs_seqids = sorted(set(ngs_seqids) | set(v2_ngs_seqids))

            ngs_df = pd.DataFrame(
                ngs_intermediate.values,
                index=ngs_intermediate.index,
                columns=ngs_seqids,
            ).reindex(columns=union_ngs_seqids)

            v2_ngs_df = pd.DataFrame(
                v2_ngs_part.values,
                index=v2_ngs_part.index,
                columns=v2_ngs_seqids,
            ).reindex(columns=union_ngs_seqids)

            combined_ngs_df = pd.concat([ngs_df, v2_ngs_df], axis=0)

            # For COL_DATA, prefer ngs_intermediate values for shared SeqIds
            combined_ngs_columns = _merge_col_data(
                ngs_intermediate.columns,
                v2_ngs_part.columns,
                union_ngs_seqids,
            )

            combined_ngs = AdatClass(
                data=combined_ngs_df.values,
                index=combined_ngs_df.index,
                columns=combined_ngs_columns,
                header_metadata={},
            )

            # Now merge v2_array_part with combined_ngs using compute_seqid_union
            # (array first, NGS second)
            rfu_df, merged_columns = compute_seqid_union(
                v2_array_part, combined_ngs
            )

            # Update row indexes: array first (v2_array_index), then NGS (combined_ngs.index)
            ngs_index_v2 = combined_ngs.index
            v2_index_remapped = v2_array_index
            # Swap order for final concatenation since we put array first above
            ngs_index_v2, v2_index_remapped = v2_index_remapped, ngs_index_v2
        else:
            # v2 is Array-only: call compute_seqid_union(v2_array_part, ngs_intermediate)
            rfu_df, merged_columns = compute_seqid_union(
                v2_array_part, ngs_intermediate
            )
            # Update row indexes: array first, NGS second
            v2_index_remapped = v2_array_index
            # Swap for final concatenation
            ngs_index_v2, v2_index_remapped = v2_index_remapped, ngs_index_v2
    else:
        # Shouldn't reach here, but handle gracefully
        rfu_df, merged_columns = compute_seqid_union(
            ngs_intermediate, v2_adat
        )

    # 7. Merge headers
    if output_assay_type == 'Mixed':
        merged_header = merge_mixed_headers(
            ngs_header_v2, v2_adat.header_metadata, ngs_ctx, v2_ctx
        )
    else:
        merged_header = HeaderMerger.merge_v2_headers(
            ngs_header_v2, v2_adat.header_metadata, 'NGS'
        )

    # 8. Align row indexes and concatenate
    ngs_index_v2, v2_index_remapped = align_row_indexes(ngs_index_v2, v2_index_remapped)
    merged_index = ngs_index_v2.append(v2_index_remapped)

    # 9. Assemble result
    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=merged_header,
    )

    if not validate_v2_header_fields(merged_header):
        raise ConversionError(
            'Merged header metadata is not compliant with the v2.0 closed field set. '
            'See logged warnings above for details.'
        )

    return result


def _merge_native_arrays(
    adat_a: Adat, adat_b: Adat, *, md5sum_a: str | None, md5sum_b: str | None
) -> Adat:
    """Merge two native array ADATs into an Array v2.0 output.

    Both inputs must have the same AssayVersion. Converts both arrays to v2.0
    format, then merges them into an Array-type output.
    """
    # 1. Extract and validate AssayVersion
    header_a = getattr(adat_a, 'header_metadata', {})
    header_b = getattr(adat_b, 'header_metadata', {})
    assay_version_a = header_a.get('!AssayVersion', '') or header_a.get(
        'AssayVersion', ''
    )
    assay_version_b = header_b.get('!AssayVersion', '') or header_b.get(
        'AssayVersion', ''
    )

    if assay_version_a != assay_version_b:
        raise AssayVersionError(
            f'Both array ADATs must have the same AssayVersion. '
            f'Got: {assay_version_a!r} and {assay_version_b!r}.'
        )

    # 2. Build conversion contexts; assign source IDs for Array output
    ctx_a = ArrayConversionContext.from_adat(adat_a, source_file_md5sum=md5sum_a)
    ctx_a.source_file_id = '1'
    ctx_a.process_steps_id = '1'
    ctx_a.report_config_id = '1'

    ctx_b = ArrayConversionContext.from_adat(adat_b, source_file_md5sum=md5sum_b)
    ctx_b.source_file_id = '2'
    ctx_b.process_steps_id = '2'
    ctx_b.report_config_id = '2'

    # 3. Convert both arrays to v2.0 with assay_type='Array'
    validate_source_array_adat(adat_a)
    header_v2_a = convert_array_header(adat_a, ctx_a, assay_type='Array')
    columns_v2_a = convert_array_col_data(adat_a, calibrator_id=ctx_a.calibrator_id)
    index_v2_a = convert_array_row_data(adat_a, ctx_a)

    validate_source_array_adat(adat_b)
    header_v2_b = convert_array_header(adat_b, ctx_b, assay_type='Array')
    columns_v2_b = convert_array_col_data(adat_b, calibrator_id=ctx_b.calibrator_id)
    index_v2_b = convert_array_row_data(adat_b, ctx_b)

    # Assemble temporary intermediate Adats
    intermediate_a = AdatClass(
        data=adat_a.values,
        index=index_v2_a,
        columns=columns_v2_a,
        header_metadata=header_v2_a,
    )
    intermediate_b = AdatClass(
        data=adat_b.values,
        index=index_v2_b,
        columns=columns_v2_b,
        header_metadata=header_v2_b,
    )

    # 4. Compute SeqId union
    rfu_df, merged_columns = compute_seqid_union(
        intermediate_a, intermediate_b
    )

    # 5. Merge headers (Array + Array → Array output)
    merged_header = HeaderMerger.merge_array_headers(
        header_v2_a, header_v2_b, ctx_a, ctx_b
    )

    # 6. Align row indexes and concatenate
    index_v2_a, index_v2_b = align_row_indexes(index_v2_a, index_v2_b)
    merged_index = index_v2_a.append(index_v2_b)

    # 7. Assemble result
    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=merged_header,
    )

    if not validate_v2_header_fields(merged_header):
        raise ConversionError(
            'Merged array header metadata is not compliant with the v2.0 closed field set. '
            'See logged warnings above for details.'
        )

    return result


def _merge_v2_combined_adats(
    adat_a: Adat,
    adat_b: Adat,
    *,
    md5sum_a: str | None,
    md5sum_b: str | None,
) -> Adat:
    """Merge two existing v2.0 ADATs into a single v2.0 output.

    Both inputs are already in v2.0 format. Derive output AssayType from
    the union of SampleReadout values. For NGS-only pairs, validate that
    ProcessSteps are identical.
    """
    # 1. Derive output AssayType from SampleReadout union
    readout_a = set(adat_a.index.get_level_values('SampleReadout'))
    readout_b = set(adat_b.index.get_level_values('SampleReadout'))
    readout_union = readout_a | readout_b

    if readout_union == {'Array'}:
        output_assay_type = 'Array'
    elif readout_union == {'NGS'}:
        output_assay_type = 'NGS'
    else:
        output_assay_type = 'Mixed'

    # 2. For NGS-only pairs, validate ProcessSteps match
    if output_assay_type == 'NGS':
        validate_v2_ngs_process_steps(adat_a, adat_b)

    # 3. MedNorm validation - check if both have MedNormExt
    a_has_mednorm = MedNormValidator.has_mednorm_ext_v2(adat_a.header_metadata)
    b_has_mednorm = MedNormValidator.has_mednorm_ext_v2(adat_b.header_metadata)

    if a_has_mednorm and b_has_mednorm:
        MedNormValidator.validate_v2_pair(
            adat_a, adat_b, med_norm_ref=None
        )

    # 4. Compute SeqId union and merged COL_DATA
    rfu_df, merged_columns = compute_seqid_union(
        adat_a, adat_b
    )

    # 4. Merge headers - this renumbers SourceFile/ProcessSteps/ReportConfig keys
    merged_header = HeaderMerger.merge_v2_headers(
        adat_a.header_metadata,
        adat_b.header_metadata,
        output_assay_type,
    )

    # 5. Remap row index *Id levels to match the renumbered header keys
    # HeaderMerger.merge_v2_headers renumbers keys sequentially (1, 2, 3, ...)
    # We need to build a mapping from original keys to new keys for both inputs

    # Extract original keys from both inputs
    sf_a_keys = list((adat_a.header_metadata.get('SourceFile') or {}).keys())
    sf_b_keys = list((adat_b.header_metadata.get('SourceFile') or {}).keys())
    ps_a_keys = list((adat_a.header_metadata.get('ProcessSteps') or {}).keys())
    ps_b_keys = list((adat_b.header_metadata.get('ProcessSteps') or {}).keys())
    rc_a_keys = list((adat_a.header_metadata.get('ReportConfig') or {}).keys())
    rc_b_keys = list((adat_b.header_metadata.get('ReportConfig') or {}).keys())

    # Build mappings following HeaderMerger.merge_v2_headers logic (lines 571-612 in utils.py)
    # SourceFile keys are renumbered: a's keys → 1, 2, ...; b's keys → next, next+1, ...
    id_mapping_a: dict[str, str] = {}
    id_mapping_b: dict[str, str] = {}

    # SourceFile mapping
    next_id = 1
    for old_key in sorted(sf_a_keys):
        id_mapping_a[old_key] = str(next_id)
        next_id += 1
    for old_key in sorted(sf_b_keys):
        id_mapping_b[old_key] = str(next_id)
        next_id += 1

    # ProcessSteps mapping
    next_id = 1
    for old_key in sorted(ps_a_keys):
        id_mapping_a[old_key] = str(next_id)
        next_id += 1
    for old_key in sorted(ps_b_keys):
        id_mapping_b[old_key] = str(next_id)
        next_id += 1

    # ReportConfig mapping
    next_id = 1
    for old_key in sorted(rc_a_keys):
        id_mapping_a[old_key] = str(next_id)
        next_id += 1
    for old_key in sorted(rc_b_keys):
        id_mapping_b[old_key] = str(next_id)
        next_id += 1

    # Remap both row indexes
    index_a_remapped = remap_row_index_ids(adat_a.index, id_mapping_a)
    index_b_remapped = remap_row_index_ids(adat_b.index, id_mapping_b)

    # 6. Align row indexes and concatenate
    aligned_index_a, aligned_index_b = align_row_indexes(
        index_a_remapped, index_b_remapped
    )
    merged_index = aligned_index_a.append(aligned_index_b)

    # 6. Assemble result
    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=merged_header,
    )

    if not validate_v2_header_fields(merged_header):
        raise ConversionError(
            'Merged v2.0 header metadata is not compliant with the v2.0 closed field set. '
            'See logged warnings above for details.'
        )

    return result


def _convert_bridged_array(
    adat: Adat, *, md5sum: str | None
) -> Adat:
    """Convert a single bridged array ADAT to Array v2.0 format."""
    return _run_array_conversion(adat, md5sum=md5sum)


def _convert_native_array(
    adat: Adat, *, md5sum: str | None
) -> Adat:
    """Convert a single native array ADAT to Array v2.0 format."""
    return _run_array_conversion(adat, md5sum=md5sum)


def _run_array_conversion(
    adat: Adat, *, md5sum: str | None = None, assay_type: str = 'Array'
) -> Adat:
    """Shared array conversion pipeline used by both native and bridged paths.

    Parameters
    ----------
    adat : Adat
        The source array ADAT to convert.
    md5sum : str or None, optional
        MD5 checksum of the source ADAT file, if available. Used as a
        fallback identifier when the source ADAT lacks an AdatId.
    assay_type : str, optional
        ``'Array'`` for single-array conversions (default); callers that are
        merging two sources pass ``'Mixed'``.

    Returns
    -------
    Adat
        A new Adat in v2.0 format with ``AssayType = assay_type``.
    """
    validate_source_array_adat(adat)
    ctx = ArrayConversionContext.from_adat(adat, source_file_md5sum=md5sum)
    new_header = convert_array_header(adat, ctx, assay_type=assay_type)
    new_columns = convert_array_col_data(adat, calibrator_id=ctx.calibrator_id)
    new_index = convert_array_row_data(adat, ctx)
    return _assemble_v2_adat(adat, new_header, new_columns, new_index)


def _assemble_v2_adat(
    source: Adat,
    header: dict,
    columns: pd.MultiIndex,
    index: pd.MultiIndex,
) -> Adat:
    """Construct a v2.0 Adat from converted components.

    Parameters
    ----------
    source : Adat
        The original ADAT; only its RFU matrix values are used.
    header : dict
        The converted v2.0 header_metadata dict.
    columns : pd.MultiIndex
        The converted v2.0 column MultiIndex.
    index : pd.MultiIndex
        The converted v2.0 row MultiIndex.

    Returns
    -------
    Adat
        A new Adat with the converted structure.
    """
    result = AdatClass(
        data=source.values,
        index=index,
        columns=columns,
        header_metadata=header,
    )
    if not validate_v2_header_fields(header):
        raise ConversionError(
            'Converted header metadata is not compliant with the v2.0 closed field set. '
            'See logged warnings above for details.'
        )
    return result


def _convert_native_ngs(
    adat: Adat, *, md5sum: str | None
) -> Adat:
    """Convert a single native NGS ADAT to NGS v2.0 format."""
    return _run_ngs_conversion(adat, md5sum=md5sum)


def _run_ngs_conversion(
    adat: Adat, *, md5sum: str | None = None, assay_type: str = 'NGS'
) -> Adat:
    """Shared NGS conversion pipeline used by single-NGS and merge paths.

    Parameters
    ----------
    adat : Adat
        The source NGS ADAT to convert.
    md5sum : str or None, optional
        MD5 checksum of the source ADAT file, if available. Used as a
        fallback identifier when the source ADAT lacks an AdatId.
    assay_type : str, optional
        ``'NGS'`` for single-NGS conversions (default); callers that are
        merging two sources pass ``'Mixed'``.

    Returns
    -------
    Adat
        A new Adat in v2.0 format with ``AssayType = assay_type``.
    """
    validate_source_ngs_adat(adat)
    ctx = NGSConversionContext.from_adat(adat, source_file_md5sum=md5sum)
    new_header = convert_ngs_header(adat, ctx, assay_type=assay_type)
    new_columns = convert_ngs_col_data(adat, matrix=ctx.matrix)
    new_index = convert_ngs_row_data(adat, ctx)
    return _assemble_v2_adat(adat, new_header, new_columns, new_index)


# ---------------------------------------------------------------------------
# Approved conversion lookup tables
#
# Defined after the handler functions so they can reference the callables
# directly. Two-input and single-input conversions are kept in separate
# tables so that same-type pairs (e.g. native_array + native_array) cannot
# collide with single-input entries — frozenset({X, X}) == frozenset({X}).
#
# Two-input keys: frozenset for mixed-type pairs; canonical 2-tuple for
#   same-type pairs.
# Single-input keys: InputType enum member.
# ---------------------------------------------------------------------------

_APPROVED_PAIR_CONVERSIONS: dict = {
    frozenset(
        {InputType.BRIDGED_ARRAY, InputType.NATIVE_NGS}
    ): _merge_bridged_array_and_ngs,
    frozenset(
        {InputType.BRIDGED_ARRAY, InputType.V2_COMBINED}
    ): _merge_bridged_array_and_v2,
    frozenset({InputType.NATIVE_NGS, InputType.V2_COMBINED}): _merge_ngs_and_v2,
    (InputType.NATIVE_ARRAY, InputType.NATIVE_ARRAY): _merge_native_arrays,
    # Two bridged arrays (e.g. Plasma + CSF from different studies) use the same
    # merge path as native arrays — both are converted to v2.0 then merged.
    (InputType.BRIDGED_ARRAY, InputType.BRIDGED_ARRAY): _merge_native_arrays,
    (InputType.V2_COMBINED, InputType.V2_COMBINED): _merge_v2_combined_adats,
}

_APPROVED_SINGLE_CONVERSIONS: dict[InputType, object] = {
    InputType.BRIDGED_ARRAY: _convert_bridged_array,
    InputType.NATIVE_ARRAY: _convert_native_array,
    InputType.NATIVE_NGS: _convert_native_ngs,
}

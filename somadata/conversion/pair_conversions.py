from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from somadata.adat import Adat as AdatClass
from somadata.conversion.array import ArrayConversionContext
from somadata.conversion.array.col_data import convert_array_col_data
from somadata.conversion.array.header import convert_array_header
from somadata.conversion.array.row_data import convert_array_row_data
from somadata.conversion.array.validation import validate_source_array_adat
from somadata.conversion.detection import InputType, detect_input_type
from somadata.conversion.errors import ConversionError, AssayVersionError
from somadata.conversion.merge import (
    compute_seqid_union,
    merge_col_data,
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
    V2SourceContext,
    align_row_indexes,
    remap_row_index_ids,
)
from somadata.conversion.header_merge import HeaderMerger
from somadata.conversion.validation import MedNormValidator
from somadata.io.adat.v2_fields import validate_v2_header_fields

if TYPE_CHECKING:
    from somadata.adat import Adat

logger = logging.getLogger(__name__)


def _make_multiindex(index_a: pd.MultiIndex, index_b: pd.MultiIndex) -> pd.MultiIndex:
    """Concatenate two MultiIndexes with identical level names."""
    return pd.MultiIndex.from_arrays(
        [
            list(index_a.get_level_values(n)) + list(index_b.get_level_values(n))
            for n in index_a.names
        ],
        names=index_a.names,
    )


def _merge_bridged_array_and_ngs(
    adat_a: Adat,
    adat_b: Adat,
    *,
    md5sum_a: str | None,
    md5sum_b: str | None,
) -> Adat:
    """Merge a bridged array ADAT and a native NGS ADAT into a Mixed v2.0 output."""
    type_a = detect_input_type(adat_a)
    if type_a is InputType.BRIDGED_ARRAY:
        raw_array, raw_ngs = adat_a, adat_b
        md5_array, md5_ngs = md5sum_a, md5sum_b
    else:
        raw_array, raw_ngs = adat_b, adat_a
        md5_array, md5_ngs = md5sum_b, md5sum_a

    validate_mednorm_compatibility(raw_array, raw_ngs)

    array_ctx = ArrayConversionContext.from_adat(raw_array, source_file_md5sum=md5_array)
    array_ctx.source_file_id = "1"
    array_ctx.process_steps_id = "1"
    array_ctx.report_config_id = "1"

    ngs_ctx = NGSConversionContext.from_adat(raw_ngs, source_file_md5sum=md5_ngs)
    ngs_ctx.source_file_id = "2"
    ngs_ctx.process_steps_id = "2"

    validate_source_array_adat(raw_array)
    array_header_v2 = convert_array_header(raw_array, array_ctx, assay_type="Mixed")
    array_columns_v2 = convert_array_col_data(raw_array, calibrator_id=array_ctx.calibrator_id)
    array_index_v2 = convert_array_row_data(raw_array, array_ctx)

    validate_source_ngs_adat(raw_ngs)
    ngs_header_v2 = convert_ngs_header(raw_ngs, ngs_ctx, assay_type="Mixed")
    ngs_columns_v2 = convert_ngs_col_data(raw_ngs, matrix=ngs_ctx.matrix)
    ngs_index_v2 = convert_ngs_row_data(raw_ngs, ngs_ctx)

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

    validate_dilution_alignment(array_intermediate, ngs_intermediate)

    rfu_df, merged_columns = compute_seqid_union(array_intermediate, ngs_intermediate)

    mixed_header = merge_mixed_headers(array_header_v2, ngs_header_v2, array_ctx, ngs_ctx)

    array_index_v2, ngs_index_v2 = align_row_indexes(array_index_v2, ngs_index_v2)
    merged_index = _make_multiindex(array_index_v2, ngs_index_v2)

    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=mixed_header,
    )

    if not validate_v2_header_fields(mixed_header):
        raise ConversionError(
            "Mixed header metadata is not compliant with the v2.0 closed field set. "
            "See logged warnings above for details."
        )

    return result


def _merge_bridged_array_and_v2(
    adat_a: Adat,
    adat_b: Adat,
    *,
    md5sum_a: str | None,
    md5sum_b: str | None,
) -> Adat:
    """Merge a bridged array ADAT and an existing v2.0 ADAT into a Mixed v2.0 output."""
    type_a = detect_input_type(adat_a)
    if type_a is InputType.BRIDGED_ARRAY:
        raw_array, v2_adat = adat_a, adat_b
        md5_array, md5_v2 = md5sum_a, md5sum_b
    else:
        raw_array, v2_adat = adat_b, adat_a
        md5_array, md5_v2 = md5sum_b, md5sum_a

    v2_assay_type = v2_adat.header_metadata.get("AssayType", "")
    if v2_assay_type == "Array":
        output_assay_type = "Array"
    else:
        output_assay_type = "Mixed"

    array_has_mednorm = MedNormValidator.has_mednorm_ext(raw_array.header_metadata)
    v2_has_mednorm = MedNormValidator.has_mednorm_ext_v2(v2_adat.header_metadata)

    if array_has_mednorm and v2_has_mednorm:
        MedNormValidator.validate_with_v2(raw_array, v2_adat, med_norm_ref=None)

    array_ctx = ArrayConversionContext.from_adat(raw_array, source_file_md5sum=md5_array)
    array_ctx.source_file_id = "1"
    array_ctx.process_steps_id = "1"
    array_ctx.report_config_id = "1"

    validate_source_array_adat(raw_array)
    array_header_v2 = convert_array_header(raw_array, array_ctx, assay_type=output_assay_type)
    array_columns_v2 = convert_array_col_data(raw_array, calibrator_id=array_ctx.calibrator_id)
    array_index_v2 = convert_array_row_data(raw_array, array_ctx)

    array_intermediate = AdatClass(
        data=raw_array.values,
        index=array_index_v2,
        columns=array_columns_v2,
        header_metadata=array_header_v2,
    )

    v2_ctx = V2SourceContext(source_file_id="2", process_steps_id="2", report_config_id="2")

    v2_original_sf_keys = list((v2_adat.header_metadata.get("SourceFile") or {}).keys())
    v2_original_ps_keys = list((v2_adat.header_metadata.get("ProcessSteps") or {}).keys())
    v2_original_rc_keys = list((v2_adat.header_metadata.get("ReportConfig") or {}).keys())

    id_mapping: dict[str, str] = {}
    for old_key in v2_original_sf_keys:
        id_mapping[old_key] = v2_ctx.source_file_id
    for old_key in v2_original_ps_keys:
        id_mapping[old_key] = v2_ctx.process_steps_id
    for old_key in v2_original_rc_keys:
        id_mapping[old_key] = v2_ctx.report_config_id

    v2_index_remapped = remap_row_index_ids(v2_adat.index, id_mapping)

    v2_readouts = set(v2_adat.index.get_level_values("SampleReadout"))

    if output_assay_type == "Array" or v2_readouts == {"NGS"}:
        rfu_df, merged_columns = compute_seqid_union(array_intermediate, v2_adat)
    else:
        v2_array_mask = v2_adat.index.get_level_values("SampleReadout") == "Array"
        v2_ngs_mask = ~v2_array_mask

        v2_array_part = v2_adat[v2_array_mask]
        v2_ngs_part = v2_adat[v2_ngs_mask]

        v2_array_index = v2_index_remapped[v2_array_mask]
        v2_ngs_index = v2_index_remapped[v2_ngs_mask]

        array_seqids = list(array_intermediate.columns.get_level_values("SeqId"))
        v2_array_seqids = list(v2_array_part.columns.get_level_values("SeqId"))
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

        combined_array_columns = merge_col_data(
            array_intermediate.columns, v2_array_part.columns, union_array_seqids
        )

        combined_array = AdatClass(
            data=combined_array_df.values,
            index=combined_array_df.index,
            columns=combined_array_columns,
            header_metadata={},
        )

        rfu_df, merged_columns = compute_seqid_union(combined_array, v2_ngs_part)

        array_index_v2 = combined_array.index
        v2_index_remapped = v2_ngs_index

    if output_assay_type == "Array":
        merged_header = HeaderMerger.merge_array_headers(
            array_header_v2, v2_adat.header_metadata, array_ctx, v2_ctx
        )
    else:
        merged_header = merge_mixed_headers(
            array_header_v2, v2_adat.header_metadata, array_ctx, v2_ctx
        )

    array_index_v2, v2_index_remapped = align_row_indexes(array_index_v2, v2_index_remapped)
    merged_index = _make_multiindex(array_index_v2, v2_index_remapped)

    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=merged_header,
    )

    if not validate_v2_header_fields(merged_header):
        raise ConversionError(
            "Merged header metadata is not compliant with the v2.0 closed field set. "
            "See logged warnings above for details."
        )

    return result


def _merge_ngs_and_v2(
    adat_a: Adat,
    adat_b: Adat,
    *,
    md5sum_a: str | None,
    md5sum_b: str | None,
) -> Adat:
    """Merge a native NGS ADAT and an existing v2.0 ADAT into a Mixed or NGS v2.0 output."""
    type_a = detect_input_type(adat_a)
    if type_a is InputType.NATIVE_NGS:
        raw_ngs, v2_adat = adat_a, adat_b
        md5_ngs, md5_v2 = md5sum_a, md5sum_b
    else:
        raw_ngs, v2_adat = adat_b, adat_a
        md5_ngs, md5_v2 = md5sum_b, md5sum_a

    v2_assay_type = v2_adat.header_metadata.get("AssayType", "")
    if v2_assay_type == "NGS":
        output_assay_type = "NGS"
    else:
        output_assay_type = "Mixed"

    ngs_has_mednorm = MedNormValidator.has_mednorm_ext(raw_ngs.header_metadata)
    v2_has_mednorm = MedNormValidator.has_mednorm_ext_v2(v2_adat.header_metadata)

    if ngs_has_mednorm and v2_has_mednorm:
        MedNormValidator.validate_with_v2(raw_ngs, v2_adat, med_norm_ref=None)

    ngs_ctx = NGSConversionContext.from_adat(raw_ngs, source_file_md5sum=md5_ngs)
    ngs_ctx.source_file_id = "1"
    ngs_ctx.process_steps_id = "1"

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

    v2_ctx = V2SourceContext(source_file_id="2", process_steps_id="2", report_config_id="2")

    v2_original_sf_keys = list((v2_adat.header_metadata.get("SourceFile") or {}).keys())
    v2_original_ps_keys = list((v2_adat.header_metadata.get("ProcessSteps") or {}).keys())
    v2_original_rc_keys = list((v2_adat.header_metadata.get("ReportConfig") or {}).keys())

    id_mapping: dict[str, str] = {}
    for old_key in v2_original_sf_keys:
        id_mapping[old_key] = v2_ctx.source_file_id
    for old_key in v2_original_ps_keys:
        id_mapping[old_key] = v2_ctx.process_steps_id
    for old_key in v2_original_rc_keys:
        id_mapping[old_key] = v2_ctx.report_config_id

    v2_index_remapped = remap_row_index_ids(v2_adat.index, id_mapping)
    v2_readouts = set(v2_adat.index.get_level_values("SampleReadout"))

    if output_assay_type == "NGS":
        rfu_df, merged_columns = compute_seqid_union(ngs_intermediate, v2_adat)
    elif v2_readouts == {"NGS"}:
        rfu_df, merged_columns = compute_seqid_union(ngs_intermediate, v2_adat)
    elif "Array" in v2_readouts:
        v2_array_mask = v2_adat.index.get_level_values("SampleReadout") == "Array"
        v2_ngs_mask = ~v2_array_mask

        v2_array_part = v2_adat[v2_array_mask]
        v2_ngs_part = v2_adat[v2_ngs_mask] if v2_ngs_mask.any() else None

        v2_array_index = v2_index_remapped[v2_array_mask]
        v2_ngs_index = v2_index_remapped[v2_ngs_mask] if v2_ngs_mask.any() else None

        if v2_ngs_part is not None and len(v2_ngs_part) > 0:
            ngs_seqids = list(ngs_intermediate.columns.get_level_values("SeqId"))
            v2_ngs_seqids = list(v2_ngs_part.columns.get_level_values("SeqId"))
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
            combined_ngs_columns = merge_col_data(
                ngs_intermediate.columns, v2_ngs_part.columns, union_ngs_seqids
            )
            combined_ngs = AdatClass(
                data=combined_ngs_df.values,
                index=combined_ngs_df.index,
                columns=combined_ngs_columns,
                header_metadata={},
            )
            rfu_df, merged_columns = compute_seqid_union(v2_array_part, combined_ngs)
            ngs_index_v2 = combined_ngs.index
            v2_index_remapped = v2_array_index
            ngs_index_v2, v2_index_remapped = v2_index_remapped, ngs_index_v2
        else:
            rfu_df, merged_columns = compute_seqid_union(v2_array_part, ngs_intermediate)
            v2_index_remapped = v2_array_index
            ngs_index_v2, v2_index_remapped = v2_index_remapped, ngs_index_v2
    else:
        rfu_df, merged_columns = compute_seqid_union(ngs_intermediate, v2_adat)

    if output_assay_type == "Mixed":
        merged_header = merge_mixed_headers(
            ngs_header_v2, v2_adat.header_metadata, ngs_ctx, v2_ctx
        )
    else:
        merged_header = HeaderMerger.merge_v2_headers(
            ngs_header_v2, v2_adat.header_metadata, "NGS"
        )

    ngs_index_v2, v2_index_remapped = align_row_indexes(ngs_index_v2, v2_index_remapped)
    merged_index = _make_multiindex(ngs_index_v2, v2_index_remapped)

    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=merged_header,
    )

    if not validate_v2_header_fields(merged_header):
        raise ConversionError(
            "Merged header metadata is not compliant with the v2.0 closed field set. "
            "See logged warnings above for details."
        )

    return result


def _merge_native_arrays(
    adat_a: Adat, adat_b: Adat, *, md5sum_a: str | None, md5sum_b: str | None
) -> Adat:
    """Merge two native array ADATs into an Array v2.0 output."""
    header_a = getattr(adat_a, "header_metadata", {})
    header_b = getattr(adat_b, "header_metadata", {})
    assay_version_a = header_a.get("!AssayVersion", "") or header_a.get("AssayVersion", "")
    assay_version_b = header_b.get("!AssayVersion", "") or header_b.get("AssayVersion", "")

    if assay_version_a != assay_version_b:
        raise AssayVersionError(
            f"Both array ADATs must have the same AssayVersion. "
            f"Got: {assay_version_a!r} and {assay_version_b!r}."
        )

    ctx_a = ArrayConversionContext.from_adat(adat_a, source_file_md5sum=md5sum_a)
    ctx_a.source_file_id = "1"
    ctx_a.process_steps_id = "1"
    ctx_a.report_config_id = "1"

    ctx_b = ArrayConversionContext.from_adat(adat_b, source_file_md5sum=md5sum_b)
    ctx_b.source_file_id = "2"
    ctx_b.process_steps_id = "2"
    ctx_b.report_config_id = "2"

    validate_source_array_adat(adat_a)
    header_v2_a = convert_array_header(adat_a, ctx_a, assay_type="Array")
    columns_v2_a = convert_array_col_data(adat_a, calibrator_id=ctx_a.calibrator_id)
    index_v2_a = convert_array_row_data(adat_a, ctx_a)

    validate_source_array_adat(adat_b)
    header_v2_b = convert_array_header(adat_b, ctx_b, assay_type="Array")
    columns_v2_b = convert_array_col_data(adat_b, calibrator_id=ctx_b.calibrator_id)
    index_v2_b = convert_array_row_data(adat_b, ctx_b)

    intermediate_a = AdatClass(
        data=adat_a.values, index=index_v2_a, columns=columns_v2_a, header_metadata=header_v2_a
    )
    intermediate_b = AdatClass(
        data=adat_b.values, index=index_v2_b, columns=columns_v2_b, header_metadata=header_v2_b
    )

    rfu_df, merged_columns = compute_seqid_union(intermediate_a, intermediate_b)

    merged_header = HeaderMerger.merge_array_headers(header_v2_a, header_v2_b, ctx_a, ctx_b)

    index_v2_a, index_v2_b = align_row_indexes(index_v2_a, index_v2_b)
    merged_index = _make_multiindex(index_v2_a, index_v2_b)

    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=merged_header,
    )

    if not validate_v2_header_fields(merged_header):
        raise ConversionError(
            "Merged array header metadata is not compliant with the v2.0 closed field set. "
            "See logged warnings above for details."
        )

    return result


def _merge_v2_combined_adats(
    adat_a: Adat,
    adat_b: Adat,
    *,
    md5sum_a: str | None,
    md5sum_b: str | None,
) -> Adat:
    """Merge two existing v2.0 ADATs into a single v2.0 output."""
    readout_a = set(adat_a.index.get_level_values("SampleReadout"))
    readout_b = set(adat_b.index.get_level_values("SampleReadout"))
    readout_union = readout_a | readout_b

    if readout_union == {"Array"}:
        output_assay_type = "Array"
    elif readout_union == {"NGS"}:
        output_assay_type = "NGS"
    else:
        output_assay_type = "Mixed"

    a_has_mednorm = MedNormValidator.has_mednorm_ext_v2(adat_a.header_metadata)
    b_has_mednorm = MedNormValidator.has_mednorm_ext_v2(adat_b.header_metadata)

    if a_has_mednorm and b_has_mednorm:
        MedNormValidator.validate_v2_pair(adat_a, adat_b, med_norm_ref=None)

    rfu_df, merged_columns = compute_seqid_union(adat_a, adat_b)

    merged_header = HeaderMerger.merge_v2_headers(
        adat_a.header_metadata, adat_b.header_metadata, output_assay_type
    )

    sf_a_keys = list((adat_a.header_metadata.get("SourceFile") or {}).keys())
    sf_b_keys = list((adat_b.header_metadata.get("SourceFile") or {}).keys())
    ps_a_keys = list((adat_a.header_metadata.get("ProcessSteps") or {}).keys())
    ps_b_keys = list((adat_b.header_metadata.get("ProcessSteps") or {}).keys())
    rc_a_keys = list((adat_a.header_metadata.get("ReportConfig") or {}).keys())
    rc_b_keys = list((adat_b.header_metadata.get("ReportConfig") or {}).keys())

    id_mapping_a: dict[str, str] = {}
    id_mapping_b: dict[str, str] = {}

    next_id = 1
    for old_key in sorted(sf_a_keys):
        id_mapping_a[old_key] = str(next_id)
        next_id += 1
    for old_key in sorted(sf_b_keys):
        id_mapping_b[old_key] = str(next_id)
        next_id += 1

    next_id = 1
    for old_key in sorted(ps_a_keys):
        id_mapping_a[old_key] = str(next_id)
        next_id += 1
    for old_key in sorted(ps_b_keys):
        id_mapping_b[old_key] = str(next_id)
        next_id += 1

    next_id = 1
    for old_key in sorted(rc_a_keys):
        id_mapping_a[old_key] = str(next_id)
        next_id += 1
    for old_key in sorted(rc_b_keys):
        id_mapping_b[old_key] = str(next_id)
        next_id += 1

    index_a_remapped = remap_row_index_ids(adat_a.index, id_mapping_a)
    index_b_remapped = remap_row_index_ids(adat_b.index, id_mapping_b)

    aligned_index_a, aligned_index_b = align_row_indexes(index_a_remapped, index_b_remapped)
    merged_index = _make_multiindex(aligned_index_a, aligned_index_b)

    result = AdatClass(
        data=rfu_df.values,
        index=merged_index,
        columns=merged_columns,
        header_metadata=merged_header,
    )

    if not validate_v2_header_fields(merged_header):
        raise ConversionError(
            "Merged v2.0 header metadata is not compliant with the v2.0 closed field set. "
            "See logged warnings above for details."
        )

    return result

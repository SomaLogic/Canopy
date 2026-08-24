"""Backward-compatibility shim — all helpers have moved to somadata.conversion.utils."""
from somadata.conversion.utils import (  # noqa: F401
    coerce_numeric as _coerce_numeric,
    compute_adat_md5sum as _compute_adat_md5sum,
    compute_file_md5sum as _compute_file_md5sum,
    consolidate_plate_fields,
    derive_hyb_norm_status,
    derive_hyb_norm_status_vectorized,
    generate_guid,
    lookup_header,
    match_cal_plate,
    match_cal_qc_ratio,
    match_qc_reference,
    merge_pipe_delimited,
    merge_plate_json,
    parse_process_steps,
    strip_bang_prefix,
    try_float,
)

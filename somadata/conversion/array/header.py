"""Array v1.x → v2.0 header field conversion.

Public API
----------
convert_array_header(adat, ctx) -> dict
    Convert a legacy array header_metadata dict to a v2.0-compliant dict.
"""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from somadata.conversion._helpers import (
    consolidate_plate_fields,
    generate_guid,
    lookup_header,
    parse_process_steps,
    strip_bang_prefix,
)
from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES

if TYPE_CHECKING:
    from somadata.conversion.array import ArrayConversionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fields that copy straight across (canonical name, no bang).
# ---------------------------------------------------------------------------
_PASS_THROUGH_FIELDS = (
    'Title',
    'StudyOrganism',
    'StudyMatrix',
    'UseRestriction',
    'AssayVersion',
)

# ---------------------------------------------------------------------------
# Plate-keyed field consolidation config
#
# Each entry: (legacy_prefix, v2_field_name, stage_key_or_None)
# stage_key=None  →  flat  {"PlateId": value}
# stage_key=str   →  nested {"PlateId": {"<stage>": value}}
# ---------------------------------------------------------------------------
_PLATE_FIELD_SPECS: list[tuple[str, str, str | None]] = [
    ('PlateScale_Scalar_', 'PlateScaleScalar', 'PlatformSpecific'),
    ('CalPlateTailPercent_', 'CalibrateTailPercent', 'PlatformSpecific'),
    ('CalPlateTailTest_', 'CalibrateTailPercentStatus', 'PlatformSpecific'),
    ('PlateScale_PassFlag_', 'PlateScaleStatus', None),
    ('PlateTailPercent_', 'QCCheckTailPercent', 'PlatformSpecific'),
    ('PlateTailTest_', 'QCCheckTailPercentStatus', 'PlatformSpecific'),
]


def convert_array_header(
    adat: object,
    ctx: ArrayConversionContext,
    *,
    assay_type: str = 'Array',
) -> dict:
    """Convert array v1.x ``header_metadata`` to a v2.0-compliant header dict.

    Parameters
    ----------
    adat : Adat
        The source array ADAT.  Only ``adat.header_metadata`` is read.
    ctx : ArrayConversionContext
        Shared conversion state; the new ``AdatId`` is written back into
        *ctx* is **not** done here — callers should use the returned dict's
        ``'AdatId'`` value.
    assay_type : str, optional
        ``'Array'`` for single-array conversions (default); callers that are
        merging two sources pass ``'Mixed'``.

    Returns
    -------
    dict
        A new dict whose keys are exactly those of
        :data:`~somadata.io.adat.v2_fields.V2_HEADER_FIELD_TYPES`.
    """
    hdr = getattr(adat, 'header_metadata', {})

    # Initialise every v2.0 field to '' (guarantees closed key set).
    out: dict = {key: '' for key in V2_HEADER_FIELD_TYPES}

    # ------------------------------------------------------------------
    # Field assignment convention
    #
    # Unconditional assignments  →  fields that are spec-required AND
    #   validated upstream by validate_source_array_adat().  By the time
    #   execution reaches here the source value is guaranteed non-blank.
    #
    # Conditional  (if val)  →  fields that are genuinely optional in the
    #   v2.0 spec ("Value Required = False") or have a valid blank state.
    #   Leaving them as '' is the correct output; no error is raised.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 1. Static / generated fields
    # ------------------------------------------------------------------
    out['FileVersion'] = '2.0'
    out['AssayType'] = assay_type
    out['FileCreatedDate'] = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ'
    )
    out['AdatId'] = generate_guid()

    # ------------------------------------------------------------------
    # 2. Pass-through fields — optional in spec; keep conditional
    # ------------------------------------------------------------------
    for field in _PASS_THROUGH_FIELDS:
        val = lookup_header(hdr, field)
        if val:
            out[field] = val

    # ------------------------------------------------------------------
    # 3. SourceFile JSON  {"1": {"AdatId": "<old>"}}
    #    Optional in spec (False); source may legitimately have no AdatId.
    # ------------------------------------------------------------------
    old_adat_id = ctx.source_adat_id or lookup_header(hdr, 'AdatId')
    if old_adat_id:
        out['SourceFile'] = {'1': {'AdatId': old_adat_id}}

    # ------------------------------------------------------------------
    # 4. SOMAmerReferenceSource  ← ProteinEffectiveDate
    #    Required (True); validated upstream — assign unconditionally.
    # ------------------------------------------------------------------
    out['SOMAmerReferenceSource'] = lookup_header(hdr, 'ProteinEffectiveDate')

    # ------------------------------------------------------------------
    # 5. ProcessSteps  →  {"1": ["step1", "step2", ...]}
    #    Required (True); validated upstream — assign unconditionally.
    # ------------------------------------------------------------------
    out['ProcessSteps'] = {
        ctx.process_steps_id: parse_process_steps(lookup_header(hdr, 'ProcessSteps'))
    }

    # ------------------------------------------------------------------
    # 6. ReportConfig  →  {"1": <value>}
    #    Required for Array-only; optional (blank) for NGS.  Keep
    #    conditional — not all array ADATs carry a ReportConfig value.
    # ------------------------------------------------------------------
    raw_rc = lookup_header(hdr, 'ReportConfig')
    if raw_rc:
        out['ReportConfig'] = {ctx.report_config_id: raw_rc}

    # ------------------------------------------------------------------
    # 7. Plate-keyed field consolidation — all optional in spec
    # ------------------------------------------------------------------
    for legacy_prefix, v2_field, stage in _PLATE_FIELD_SPECS:
        consolidated = consolidate_plate_fields(hdr, legacy_prefix, stage=stage)
        if consolidated:
            out[v2_field] = consolidated

    # ------------------------------------------------------------------
    # 8. NGS-only fields — blank for array-only output
    # ------------------------------------------------------------------
    out['PlateSOMAmerNormReadsStatus'] = ''

    return out

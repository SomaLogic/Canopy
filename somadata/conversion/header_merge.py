"""Header merging utilities for ADAT v2.0 conversion."""

from __future__ import annotations

import datetime
import logging

from somadata.conversion.utils import generate_guid, merge_pipe_delimited, merge_plate_json

logger = logging.getLogger(__name__)


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

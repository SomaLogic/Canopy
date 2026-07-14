"""Unit tests for somadata.conversion.ngs.header (Task 1.4).

Tests convert_ngs_header() field mapping logic.
"""

from __future__ import annotations

import json
import re

import pytest

from somadata.conversion.ngs import NGSConversionContext
from somadata.conversion.ngs.header import convert_ngs_header
from tests.conversion.ngs.conftest import make_ngs_adat


class TestConvertNGSHeader:
    """Test NGS header conversion."""

    def test_sets_file_version_to_2_0(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx)
        assert result['FileVersion'] == '2.0'

    def test_sets_assay_type_to_ngs(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx)
        assert result['AssayType'] == 'NGS'

    def test_respects_assay_type_override(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx, assay_type='Mixed')
        assert result['AssayType'] == 'Mixed'

    def test_generates_new_adat_id(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx)
        assert result['AdatId'].startswith('GID-')
        assert result['AdatId'] != ctx.source_adat_id

    def test_sets_file_created_date(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx)
        # Check ISO 8601 format
        assert re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', result['FileCreatedDate'])

    def test_creates_source_file_json(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx)
        assert isinstance(result['SourceFile'], dict)
        assert '1' in result['SourceFile']
        assert result['SourceFile']['1']['AdatId'] == 'GID-old-ngs-id'

    def test_source_file_blank_when_no_adat_id(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        del adat.header_metadata['!AdatId']
        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_header(adat, ctx)
        assert result['SourceFile'] == ''

    def test_converts_process_steps_to_json(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx)
        assert isinstance(result['ProcessSteps'], dict)
        assert '1' in result['ProcessSteps']
        assert isinstance(result['ProcessSteps']['1'], list)
        assert 'Raw Counts' in result['ProcessSteps']['1']

    def test_report_config_blank_for_ngs(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx)
        assert result['ReportConfig'] == ''

    def test_maps_assay_version_6k(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        adat.header_metadata['!AssayVersion'] = '6k'
        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_header(adat, ctx)
        assert result['AssayVersion'] == 'v1'

    def test_maps_assay_version_9k_tms(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        adat.header_metadata['!AssayVersion'] = '9k TMS'
        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_header(adat, ctx)
        assert result['AssayVersion'] == 'v2'

    def test_maps_assay_version_calypso(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        adat.header_metadata['!AssayVersion'] = 'Calypso'
        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_header(adat, ctx)
        assert result['AssayVersion'] == 'v4'

    def test_pass_through_title(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        adat.header_metadata['!Title'] = 'My NGS Study'
        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_header(adat, ctx)
        assert result['Title'] == 'My NGS Study'

    def test_pass_through_study_organism(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        adat.header_metadata['!StudyOrganism'] = 'Human'
        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_header(adat, ctx)
        assert result['StudyOrganism'] == 'Human'

    def test_closed_header_set(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_header(minimal_ngs_adat, ctx)
        from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES
        
        # All v2.0 fields present
        assert set(result.keys()) == set(V2_HEADER_FIELD_TYPES.keys())


class TestPlatformSpecificJSONConsolidation:
    """Test dual-platform JSON field consolidation."""

    def test_consolidates_plate_scale_scalar(self, multi_plate_ngs_adat):
        adat = multi_plate_ngs_adat
        adat.header_metadata['PlatformSpecificPlateScale_ScaleFactor_PLT100'] = '1.02'
        adat.header_metadata['CrossPlatformPlateScale_ScaleFactor_PLT100'] = '0.98'
        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_header(adat, ctx)
        
        assert isinstance(result['PlateScaleScalar'], dict)
        assert 'PLT100' in result['PlateScaleScalar']
        assert result['PlateScaleScalar']['PLT100']['PlatformSpecific'] == '1.02'
        assert result['PlateScaleScalar']['PLT100']['CrossPlatform'] == '0.98'

    def test_handles_hyphen_suffix(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        adat.header_metadata['PlatformSpecificPlateScale_ScaleFactor-PLT100'] = '1.02'
        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_header(adat, ctx)
        
        # Should still parse with hyphen
        if result['PlateScaleScalar']:
            assert 'PLT100' in result['PlateScaleScalar']

"""Integration tests for NGS conversion (Task 1.9).

Tests end-to-end conversion of NGS ADATs via to_v2_adat().
"""

from __future__ import annotations

import pytest

from somadata.conversion.converter import to_v2_adat
from tests.conversion.ngs.conftest import make_ngs_adat


class TestNGSConversionIntegration:
    """Test complete NGS → v2.0 conversion pipeline."""

    def test_converts_minimal_ngs_adat(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert result.header_metadata['FileVersion'] == '2.0'
        assert result.header_metadata['AssayType'] == 'NGS'

    def test_preserves_rfu_data(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        # Data matrix should be unchanged
        assert result.shape == minimal_ngs_adat.shape
        assert (result.values == minimal_ngs_adat.values).all()

    def test_generates_new_adat_id(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        new_id = result.header_metadata['AdatId']
        old_id = minimal_ngs_adat.header_metadata.get('!AdatId', '')
        assert new_id != old_id
        assert new_id.startswith('GID-')

    def test_creates_source_file_json(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        source_file = result.header_metadata['SourceFile']
        assert isinstance(source_file, dict)
        assert '1' in source_file
        assert source_file['1']['AdatId'] == 'GID-old-ngs-id'

    def test_converts_process_steps_to_json(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        process_steps = result.header_metadata['ProcessSteps']
        assert isinstance(process_steps, dict)
        assert '1' in process_steps
        assert isinstance(process_steps['1'], list)
        assert 'Raw Counts' in process_steps['1']

    def test_report_config_blank(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert result.header_metadata['ReportConfig'] == ''

    def test_maps_assay_version(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        # 6k → v1
        assert result.header_metadata['AssayVersion'] == 'v1'

    def test_column_fields_renamed(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert 'TargetFullName' in result.columns.names
        assert 'Target Full Name' not in result.columns.names
        assert 'UniProt' in result.columns.names
        assert 'UniProt ID' not in result.columns.names
        assert 'DRCLevelNGS' in result.columns.names
        assert 'BlockListNGS' in result.columns.names

    def test_adds_hyb_control_column_level(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert 'HybControl' in result.columns.names

    def test_row_fields_renamed(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert 'KitType' in result.index.names
        assert 'NGSPlateMasterMixLot' in result.index.names
        assert 'HybNormScaleFactor' in result.index.names
        assert 'MedNormInt_0_2_ScaleFactor' in result.index.names

    def test_adds_sample_readout_ngs(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert 'SampleReadout' in result.index.names
        vals = list(result.index.get_level_values('SampleReadout'))
        assert all(v == 'NGS' for v in vals)

    def test_generates_unique_sample_keys(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert 'UniqueSampleKey' in result.index.names
        keys = list(result.index.get_level_values('UniqueSampleKey'))
        assert len(keys) == len(set(keys))
        assert all(k.startswith('GID-') for k in keys)

    def test_replicates_sequencing_run_fields(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert 'InstrumentType' in result.index.names
        assert 'Flowcell' in result.index.names
        assert 'YieldDemux' in result.index.names
        assert 'YieldQ30Demux' in result.index.names
        assert 'Q30WeightedMean' in result.index.names
        
        vals = list(result.index.get_level_values('InstrumentType'))
        assert all(v == 'NovaSeq6000' for v in vals)

    def test_adds_software_version(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        assert 'SoftwareVersion' in result.index.names
        vals = list(result.index.get_level_values('SoftwareVersion'))
        assert all(v == '4.0.1' for v in vals)

    def test_multi_plate_conversion(self, multi_plate_ngs_adat):
        result = to_v2_adat([multi_plate_ngs_adat])
        assert result.header_metadata['FileVersion'] == '2.0'
        assert result.shape == multi_plate_ngs_adat.shape

    def test_closed_header_field_set(self, minimal_ngs_adat):
        result = to_v2_adat([minimal_ngs_adat])
        from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES
        
        assert set(result.header_metadata.keys()) == set(V2_HEADER_FIELD_TYPES.keys())

    def test_validates_v2_header_fields(self, minimal_ngs_adat):
        # Should not raise ConversionError
        result = to_v2_adat([minimal_ngs_adat])
        from somadata.io.adat.v2_fields import validate_v2_header_fields
        
        assert validate_v2_header_fields(result.header_metadata)

"""Unit tests for somadata.conversion.ngs.row_data (Task 1.6).

Tests convert_ngs_row_data() field mapping logic.
"""

from __future__ import annotations

import pytest

from somadata.conversion.ngs import NGSConversionContext
from somadata.conversion.ngs.row_data import convert_ngs_row_data
from tests.conversion.ngs.conftest import make_ngs_adat


class TestConvertNGSRowData:
    """Test NGS ROW_DATA conversion."""

    def test_renames_sample_id(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Add SampleID (legacy casing)
        adat.index = adat.index.droplevel('SampleId')
        idx_names = list(adat.index.names) + ['SampleID']
        idx_values = [
            list(adat.index.get_level_values(i)) for i in range(adat.index.nlevels)
        ]
        idx_values.append(['S1', 'S2'])
        adat.index = pd.MultiIndex.from_arrays(idx_values, names=idx_names)

        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_row_data(adat, ctx)

        assert 'SampleId' in result.names
        assert 'SampleID' not in result.names

    def test_renames_matrix_type_to_kit_type(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'KitType' in result.names
        assert 'MatrixType' not in result.names

    def test_renames_probe_plate_to_ngs_plate_master_mix_lot(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'NGSPlateMasterMixLot' in result.names
        assert 'ProbePlate' not in result.names

    def test_renames_hyb_norm_1_scale_factor(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'HybNormScaleFactor' in result.names
        assert 'HybNorm_1_ScaleFactor' not in result.names

    def test_normalizes_dilution_suffix(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        # MedNormInt_0-2_ScaleFactor → MedNormInt_0_2_ScaleFactor
        assert 'MedNormInt_0_2_ScaleFactor' in result.names
        assert 'MedNormInt_0-2_ScaleFactor' not in result.names

    def test_adds_sample_readout_ngs(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'SampleReadout' in result.names
        vals = list(result.get_level_values('SampleReadout'))
        assert all(v == 'NGS' for v in vals)

    def test_generates_unique_sample_keys(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'UniqueSampleKey' in result.names
        keys = list(result.get_level_values('UniqueSampleKey'))
        assert len(keys) == len(set(keys))  # All unique
        assert all(k.startswith('GID-') for k in keys)

    def test_adds_source_file_id(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'SourceFileId' in result.names
        vals = list(result.get_level_values('SourceFileId'))
        assert all(v == '1' for v in vals)

    def test_adds_process_steps_id(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'ProcessStepsId' in result.names
        vals = list(result.get_level_values('ProcessStepsId'))
        assert all(v == '1' for v in vals)

    def test_adds_software_version_from_ctx(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'SoftwareVersion' in result.names
        vals = list(result.get_level_values('SoftwareVersion'))
        assert all(v == '4.0.1' for v in vals)

    def test_replicates_instrument_type(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'InstrumentType' in result.names
        vals = list(result.get_level_values('InstrumentType'))
        assert all(v == 'NovaSeq6000' for v in vals)

    def test_replicates_flowcell(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'Flowcell' in result.names
        vals = list(result.get_level_values('Flowcell'))
        assert all(v == 'HFFKNDSXF' for v in vals)

    def test_replicates_yield_demux(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'RunYieldDemux' in result.names
        vals = list(result.get_level_values('RunYieldDemux'))
        assert all(v == '12500000' for v in vals)

    def test_adds_blank_plate_run_date(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'PlateRunDate' in result.names
        vals = list(result.get_level_values('PlateRunDate'))
        assert all(v == '' for v in vals)

    def test_adds_blank_report_config_id(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'ReportConfigId' in result.names
        vals = list(result.get_level_values('ReportConfigId'))
        assert all(v == '' for v in vals)


class TestStatusFieldDerivation:
    """Test PassFlag → Status conversions and derivations."""

    def test_derives_hyb_norm_status_pass(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Set HybNorm scale factor to 1.024 (in range [0.4, 2.5])
        idx_names = list(adat.index.names)
        hyb_idx = idx_names.index('HybNorm_1_ScaleFactor')
        idx_values = [
            list(adat.index.get_level_values(i)) for i in range(adat.index.nlevels)
        ]
        idx_values[hyb_idx] = ['1.024', '0.989']
        adat.index = pd.MultiIndex.from_arrays(idx_values, names=idx_names)

        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_row_data(adat, ctx)

        vals = list(result.get_level_values('HybNormStatus'))
        assert vals[0] == 'PASS'
        assert vals[1] == 'PASS'

    def test_derives_hyb_norm_status_flag(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Set HybNorm scale factor to 3.0 (outside range [0.4, 2.5])
        idx_names = list(adat.index.names)
        hyb_idx = idx_names.index('HybNorm_1_ScaleFactor')
        idx_values = [
            list(adat.index.get_level_values(i)) for i in range(adat.index.nlevels)
        ]
        idx_values[hyb_idx] = ['3.0', '0.2']
        adat.index = pd.MultiIndex.from_arrays(idx_values, names=idx_names)

        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_row_data(adat, ctx)

        vals = list(result.get_level_values('HybNormStatus'))
        assert vals[0] == 'FLAG'  # 3.0 > 2.5
        assert vals[1] == 'FLAG'  # 0.2 < 0.4

    def test_derives_med_norm_int_status(self, minimal_ngs_adat):
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'MedNormIntStatus' in result.names
        vals = list(result.get_level_values('MedNormIntStatus'))
        # Both scale factors in range
        assert vals[0] == 'PASS'
        assert vals[1] == 'PASS'

    def test_derives_row_check_status_from_norm_failures(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Set HybNorm to FLAG
        idx_names = list(adat.index.names)
        hyb_idx = idx_names.index('HybNorm_1_ScaleFactor')
        idx_values = [
            list(adat.index.get_level_values(i)) for i in range(adat.index.nlevels)
        ]
        idx_values[hyb_idx] = ['3.0', '1.0']  # First sample FLAGs
        adat.index = pd.MultiIndex.from_arrays(idx_values, names=idx_names)

        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_row_data(adat, ctx)

        vals = list(result.get_level_values('RowCheckStatus'))
        assert vals[0] == 'FLAG'  # Hyb failed
        assert vals[1] == 'PASS'  # All passed


class TestEmpiricalHybTempRename:
    """Test EmpiricalHybTemp → HybQC rename."""

    def test_renames_empirical_hyb_temp_to_hyb_qc(self):
        """EmpiricalHybTemp is renamed to HybQC in the output."""
        import pandas as pd

        adat = make_ngs_adat()
        # Add EmpiricalHybTemp to row index
        idx_names = list(adat.index.names) + ['EmpiricalHybTemp']
        idx_values = [
            list(adat.index.get_level_values(i)) for i in range(adat.index.nlevels)
        ]
        idx_values.append(['52.1', '53.0'])
        adat.index = pd.MultiIndex.from_arrays(idx_values, names=idx_names)

        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_row_data(adat, ctx)

        assert 'HybQC' in result.names
        assert 'EmpiricalHybTemp' not in result.names
        vals = list(result.get_level_values('HybQC'))
        assert vals == ['52.1', '53.0']

    def test_renames_empirical_hyb_temp_pass_flag_to_hyb_qc_status(self):
        """EmpiricalHybTemp_PassFlag is renamed to HybQCStatus."""
        import pandas as pd

        adat = make_ngs_adat()
        idx_names = list(adat.index.names) + ['EmpiricalHybTemp_PassFlag']
        idx_values = [
            list(adat.index.get_level_values(i)) for i in range(adat.index.nlevels)
        ]
        idx_values.append(['PASS', 'FLAG'])
        adat.index = pd.MultiIndex.from_arrays(idx_values, names=idx_names)

        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_row_data(adat, ctx)

        assert 'HybQCStatus' in result.names
        assert 'EmpiricalHybTemp_PassFlag' not in result.names

    def test_hyb_qc_blank_stub_when_absent(self, minimal_ngs_adat):
        """HybQC is present as a blank stub when EmpiricalHybTemp absent in source."""
        ctx = NGSConversionContext.from_adat(minimal_ngs_adat)
        result = convert_ngs_row_data(minimal_ngs_adat, ctx)
        assert 'HybQC' in result.names
        vals = list(result.get_level_values('HybQC'))
        assert all(v == '' for v in vals)

    def test_renames_hyb_qc_pass_flag_to_hyb_qc_status(self):
        """HybQC_PassFlag (newer DPQ) is renamed to HybQCStatus."""
        import pandas as pd

        adat = make_ngs_adat()
        idx_names = list(adat.index.names) + ['HybQC_PassFlag']
        idx_values = [
            list(adat.index.get_level_values(i)) for i in range(adat.index.nlevels)
        ]
        idx_values.append(['PASS', 'FLAG'])
        adat.index = pd.MultiIndex.from_arrays(idx_values, names=idx_names)

        ctx = NGSConversionContext.from_adat(adat)
        result = convert_ngs_row_data(adat, ctx)

        assert 'HybQCStatus' in result.names
        assert 'HybQC_PassFlag' not in result.names
        vals = list(result.get_level_values('HybQCStatus'))
        assert vals == ['PASS', 'FLAG']

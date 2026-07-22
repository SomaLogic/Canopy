"""Unit tests for somadata.conversion.ngs.col_data (Task 1.5).

Tests convert_ngs_col_data() field mapping logic.
"""

from __future__ import annotations

import pytest

from somadata.conversion.ngs.col_data import convert_ngs_col_data
from tests.conversion.ngs.conftest import make_ngs_adat


class TestConvertNGSColData:
    """Test NGS COL_DATA conversion."""

    def test_renames_target_full_name(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'TargetFullName' in result.names
        assert 'Target Full Name' not in result.names

    def test_renames_uniprot_id(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'UniProt' in result.names
        assert 'UniProt ID' not in result.names

    def test_renames_entrez_gene_id(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'EntrezGeneId' in result.names
        assert 'Entrez Gene ID' not in result.names

    def test_renames_entrez_gene_symbol(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'EntrezGeneSymbol' in result.names
        assert 'Entrez Gene Symbol' not in result.names

    def test_renames_drc_level_to_drc_level_ngs(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'DRCLevelNGS' in result.names
        assert 'DRC_Level' not in result.names

    def test_drc_level_preserves_matrix_suffix(self):
        """DRC_Level.<MatrixType> is renamed to DRCLevelNGS.<MatrixType>."""
        import pandas as pd

        adat = make_ngs_adat()
        # Replace bare DRC_Level with DRC_Level.Serum in column MultiIndex
        col_names = list(adat.columns.names)
        drc_idx = col_names.index('DRC_Level')
        col_names[drc_idx] = 'DRC_Level.Serum'
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)

        result = convert_ngs_col_data(adat)
        assert 'DRCLevelNGS.Serum' in result.names
        assert 'DRC_Level.Serum' not in result.names
        assert 'DRCLevelNGS' not in result.names  # bare name must not appear

    def test_drc_level_plasma_suffix(self):
        """DRC_Level.Plasma is renamed to DRCLevelNGS.Plasma."""
        import pandas as pd

        adat = make_ngs_adat()
        col_names = list(adat.columns.names)
        drc_idx = col_names.index('DRC_Level')
        col_names[drc_idx] = 'DRC_Level.Plasma'
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)

        result = convert_ngs_col_data(adat)
        assert 'DRCLevelNGS.Plasma' in result.names
        assert 'DRC_Level.Plasma' not in result.names

    def test_renames_block_list_to_block_list_ngs(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'BlockListNGS' in result.names
        assert 'BlockList' not in result.names

    def test_block_list_absent_when_not_in_source(self):
        """BlockList is optional — absent in source means absent in output."""
        import pandas as pd

        adat = make_ngs_adat()
        # Remove BlockList from column MultiIndex
        col_names = [n for n in adat.columns.names if n != 'BlockList']
        col_values = [list(adat.columns.get_level_values(n)) for n in col_names]
        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)

        result = convert_ngs_col_data(adat)

        # Neither the original nor the renamed field should be present
        assert 'BlockList' not in result.names
        assert 'BlockListNGS' not in result.names

    def test_pass_through_seqid(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'SeqId' in result.names

    def test_pass_through_target(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'Target' in result.names

    def test_pass_through_type(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'Type' in result.names

    def test_pass_through_organism(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'Organism' in result.names

    def test_pass_through_dilution(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'Dilution' in result.names

    def test_removes_somaid(self):
        adat = make_ngs_adat()
        # Add SomaId to columns
        import pandas as pd

        col_names = list(adat.columns.names) + ['SomaId']
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        col_values.append(['SOMA-001', 'SOMA-002'])

        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)
        result = convert_ngs_col_data(adat)
        assert 'SomaId' not in result.names

    def test_adds_hyb_control_level(self, minimal_ngs_adat):
        result = convert_ngs_col_data(minimal_ngs_adat)
        assert 'HybControl' in result.names
        # All should be 'False' since Type='Protein'
        hyb_vals = list(result.get_level_values('HybControl'))
        assert all(v == 'False' for v in hyb_vals)

    def test_hyb_control_true_for_hyb_control_type(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Modify Type level to include a Hybridization Control
        type_idx = adat.columns.names.index('Type')
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        col_values[type_idx][0] = 'Hybridization Control'

        adat.columns = pd.MultiIndex.from_arrays(col_values, names=adat.columns.names)
        result = convert_ngs_col_data(adat)

        hyb_vals = list(result.get_level_values('HybControl'))
        assert hyb_vals[0] == 'True'
        assert hyb_vals[1] == 'False'


class TestQCCheckRename:
    """Test QCCheck → QCRatio conversion."""

    def test_renames_qc_check_to_qc_ratio(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Add QCCheck_PLT100_ScaleFactor
        col_names = list(adat.columns.names) + ['QCCheck_PLT100_ScaleFactor']
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        col_values.append(['0.95', '0.92'])

        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)
        result = convert_ngs_col_data(adat)

        assert 'QCRatio_PLT100' in result.names
        assert 'QCCheck_PLT100_ScaleFactor' not in result.names

    def test_removes_qc_check_pass_flag(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Add QCCheck_PLT100_PassFlag
        col_names = list(adat.columns.names) + ['QCCheck_PLT100_PassFlag']
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        col_values.append(['PASS', 'PASS'])

        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)
        result = convert_ngs_col_data(adat)

        assert 'QCCheck_PLT100_PassFlag' not in result.names


class TestReferencePrefixing:
    """Test Ref.NGS.* prefix enforcement."""

    def test_adds_ngs_prefix_to_ref_fields(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Add Ref.Bridging.params field
        col_names = list(adat.columns.names) + ['Ref.Bridging.params']
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        col_values.append(['123.4', '234.5'])

        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)
        result = convert_ngs_col_data(adat)

        assert 'Ref.NGS.Bridging.params' in result.names
        assert 'Ref.Bridging.params' not in result.names

    def test_preserves_ref_ngs_prefix(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Add Ref.NGS.MedNormExt.Matrix field
        col_names = list(adat.columns.names) + ['Ref.NGS.MedNormExt.Matrix']
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        col_values.append(['300.1', '310.2'])

        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)
        result = convert_ngs_col_data(adat)

        assert 'Ref.NGS.MedNormExt.Matrix' in result.names

    def test_preserves_ref_mednorm_id(self):
        adat = make_ngs_adat()
        import pandas as pd

        # Add Ref.MedNorm.Id field (shared between Array and NGS)
        col_names = list(adat.columns.names) + ['Ref.MedNorm.Id']
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        col_values.append(['REF001', 'REF001'])

        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)
        result = convert_ngs_col_data(adat)

        # Should NOT add NGS prefix
        assert 'Ref.MedNorm.Id' in result.names
        assert 'Ref.NGS.MedNorm.Id' not in result.names

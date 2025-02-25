import os
from unittest import TestCase

import pytest

import somadata
from somadata import Adat


class AdatReadingTest(TestCase):
    """Tests if adat can be read in."""

    filename = './tests/data/control_data.adat'

    def test_somadata_read_adat(self):
        adat = somadata.read_adat(self.filename)
        self.assertIsInstance(adat, Adat)


class AdatAttrTest(TestCase):
    """Tests that the data integrity is maintained after loading into the dataframe format."""

    filename = './tests/data/control_data.adat'

    def setUp(self):
        self.adat = somadata.read_adat(self.filename)
        self.adat_compatibility = somadata.read_adat(
            self.filename, compatibility_mode=True
        )

    def test_adat_size(self):
        self.assertEqual(self.adat.shape, (11, 5284))

    def test_row_metadata_width(self):
        self.assertEqual(len(self.adat.index.names), 32)

    def test_column_metadata_height(self):
        self.assertEqual(len(self.adat.columns.names), 22)

    def test_row_metadata_names(self):
        self.assertEqual(
            self.adat.index.names,
            [
                'PlateId',
                'PlateRunDate',
                'ScannerID',
                'PlatePosition',
                'SlideId',
                'Subarray',
                'SampleId',
                'SampleType',
                'PercentDilution',
                'SampleMatrix',
                'Barcode',
                'Barcode2d',
                'SampleName',
                'SampleNotes',
                'AliquotingNotes',
                'SampleDescription',
                'AssayNotes',
                'TimePoint',
                'ExtIdentifier',
                'SsfExtId',
                'SampleGroup',
                'SiteId',
                'TubeUniqueID',
                'CLI',
                'HybControlNormScale',
                'RowCheck',
                'NormScale_20',
                'NormScale_0_005',
                'NormScale_0_5',
                'ANMLFractionUsed_20',
                'ANMLFractionUsed_0_005',
                'ANMLFractionUsed_0_5',
            ],
        )

    def test_column_metadata_names(self):
        self.assertEqual(
            self.adat.columns.names,
            [
                'SeqId',
                'SeqIdVersion',
                'SomaId',
                'TargetFullName',
                'Target',
                'UniProt',
                'EntrezGeneID',
                'EntrezGeneSymbol',
                'Organism',
                'Units',
                'Type',
                'Dilution',
                'PlateScale_Reference',
                'CalReference',
                'Cal_P0024405',
                'ColCheck',
                'CalQcRatio_P0024405_170255',
                'QcReference_170255',
                'CalQcRatio_P0024405_170259',
                'QcReference_170259',
                'CalQcRatio_P0024405_170260',
                'QcReference_170260',
            ],
        )

    def test_header_metadata_size(self):
        self.assertEqual(len(self.adat.header_metadata.keys()), 38)

    def test_header_metadata_spot_check(self):
        self.assertEqual(self.adat.header_metadata['HybNormReference'], 'intraplate')
        self.assertEqual(self.adat.header_metadata['StudyOrganism'], '')
        self.assertEqual(
            self.adat.header_metadata['PlateScale_Scalar_P0024405'], '0.78797188'
        )
        self.assertIsInstance(self.adat.header_metadata["ReportConfig"], dict)
        self.assertIsInstance(
            self.adat_compatibility.header_metadata["ReportConfig"], str
        )

    def test_row_metadata_spot_check(self):
        self.assertEqual(
            list(self.adat.index.get_level_values('SampleId')),
            [
                '170261',
                '190063',
                '170255',
                '170261',
                '190063',
                '170255',
                '170261',
                '190063',
                '170261',
                '170255',
                '170261',
            ],
        )


class WrittenAdatAttrTest(AdatAttrTest):
    """Reruns the same tests from AdatAttrTest but with a written file."""

    filename = './tests/data/control_data_written.adat'
    filename_compatibility_mode = './tests/data/control_data_written_compatible.adat'

    def setUp(self):
        first_adat = somadata.read_adat('./tests/data/control_data.adat')
        first_adat.to_adat(self.filename)
        self.adat = somadata.read_adat(self.filename)
        second_adat = somadata.read_adat(
            './tests/data/control_data.adat', compatibility_mode=True
        )
        second_adat.to_adat(self.filename_compatibility_mode)
        self.adat_compatibility = somadata.read_adat(
            self.filename_compatibility_mode, compatibility_mode=True
        )

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        if os.path.exists(self.filename_compatibility_mode):
            os.remove(self.filename_compatibility_mode)


class ConvertV3SeqIdsReadTestCase(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['12345-6_7', '23456-7_8', '34567-8_9'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
        }
        adat = Adat.from_features(rfu_data, row_metadata, col_metadata, header_metadata)
        adat.to_adat('tests/data/v3_test.adat')

    def tearDown(self):
        filename = 'tests/data/v3_test.adat'
        if os.path.exists(filename):
            os.remove(filename)

    def test_v3_seq_id_file_read_warning(self):
        with pytest.warns(UserWarning) as record:
            somadata.read_adat('tests/data/v3_test.adat')

        # check that only one warning was raised
        self.assertEqual(len(record), 1)
        # check that the message matches
        self.assertEqual(
            record[0].message.args[0],
            'V3 style seqIds (i.e., 12345-6_7). Converting to V4 Style. The adat file writer has an option to write using the V3 style',
        )

    @pytest.mark.filterwarnings('ignore:V3 style seqIds')
    def test_v3_seq_id_file_read_conversion(self):
        adat = somadata.read_adat('tests/data/v3_test.adat')

        # check that the adat has the correct column metadata names and data
        self.assertEqual(
            ['SeqId', 'SeqIdVersion', 'ColCheck'], list(adat.columns.names)
        )
        self.assertEqual(
            ['12345-6', '23456-7', '34567-8'],
            list(adat.columns.get_level_values('SeqId')),
        )
        self.assertEqual(
            ['7', '8', '9'], list(adat.columns.get_level_values('SeqIdVersion'))
        )

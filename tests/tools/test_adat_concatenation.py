import logging
from unittest import TestCase

import pytest

from somadata import Adat
from somadata.tools.adat_concatenation import (
    concatenate_adats,
    smart_adat_concatenation,
)
from somadata.tools.errors import AdatConcatError


class ConcatHeadersTest(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'FLAG', 'FLAG']}
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
        }
        adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'PASS', 'FLAG']}
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )
        self.adats = [adat1, adat2]

    def test_set_addition(self):
        concat_adat = concatenate_adats(self.adats)
        self.assertEqual(concat_adat.header_metadata['!AssayRobot'], 'Tecan1, Tecan2')

    def test_null(self):
        concat_adat = concatenate_adats(self.adats)
        self.assertIsNone(concat_adat.header_metadata['AdatId'])

    def test_str_pipe_append(self):
        concat_adat = concatenate_adats(self.adats)
        self.assertEqual(
            concat_adat.header_metadata['RunNotes'], 'run note 1 | run note 2'
        )

    def test_mismatch_raises(self):
        self.adats[0].header_metadata['CalibratorId'] = '123'
        self.adats[1].header_metadata['CalibratorId'] = '234'
        self.assertRaises(AdatConcatError, concatenate_adats, self.adats)


class ConcatRowsTest(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'FLAG', 'FLAG']}
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
        }
        adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'PASS', 'FLAG']}
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )
        self.adats = [adat1, adat2]

    def test_row_metadata_accuracy(self):
        concat_adat = concatenate_adats(self.adats)

        barcodes = list(concat_adat.index.get_level_values('Barcode'))
        self.assertEqual(barcodes, ['SL1234', 'SL1235', 'SL1236', 'SL1237'])
        plate_ids = list(concat_adat.index.get_level_values('PlateId'))
        self.assertEqual(plate_ids, ['A12', 'A12', 'A13', 'A13'])

    def test_row_metadata_mismatch(self):
        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'PASS', 'FLAG']}
        row_metadata = {
            'PlateId': ['A13', 'A13'],
            'Barcode': ['SL1236', 'SL1237'],
            'ExtraData': ['foo', 'bar'],
        }
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        adat3 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        self.adats.append(adat3)
        self.assertRaises(AdatConcatError, concatenate_adats, self.adats)


class ConcatColumnsTest(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'FLAG', 'FLAG']}
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
        }
        adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'PASS', 'FLAG']}
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )
        self.adats = [adat1, adat2]

    def test_column_accuracy(self):
        concat_adat = concatenate_adats(self.adats)

        seq_ids = list(concat_adat.columns.get_level_values('SeqId'))
        self.assertEqual(seq_ids, ['A', 'B', 'C'])
        col_checks = list(concat_adat.columns.get_level_values('ColCheck'))
        self.assertEqual(col_checks, ['PASS', 'FLAG', 'FLAG'])

    def test_column_mismatch(self):
        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {'SeqId': ['A', 'B', 'D'], 'ColCheck': ['PASS', 'PASS', 'FLAG']}
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        adat3 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )
        self.adats.append(adat3)

        self.assertRaises(AdatConcatError, concatenate_adats, self.adats)

    def test_calreference_platescale_concatenation(self):
        """Test that CalReference and PlateScale_Reference are concatenated with pipe delimiter."""
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
            'CalReference': ['ref1', 'ref2', 'ref1'],
            'PlateScale_Reference': ['scale1', 'scale2', 'scale1'],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {'AdatId': '1a2b3c'}
        adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
            'CalReference': ['ref2', 'ref3', 'ref1'],
            'PlateScale_Reference': ['scale2', 'scale3', 'scale2'],
        }
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {'AdatId': '1a2b3d'}
        adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        with self.assertLogs(level=logging.WARNING) as cm:
            concat_adat = concatenate_adats([adat1, adat2])

        # CalReference should have unique values concatenated with pipe delimiter, sorted
        cal_refs = list(concat_adat.columns.get_level_values('CalReference'))
        self.assertEqual(cal_refs, ['ref1 | ref2', 'ref2 | ref3', 'ref1'])

        # PlateScale_Reference should have unique values concatenated with pipe delimiter, sorted
        plate_scales = list(
            concat_adat.columns.get_level_values('PlateScale_Reference')
        )
        self.assertEqual(
            plate_scales, ['scale1 | scale2', 'scale2 | scale3', 'scale1 | scale2']
        )

        # Verify warnings about differing values (should be one warning per field)
        cal_ref_warnings = [
            msg for msg in cm.output if 'CalReference values differ' in msg
        ]
        plate_scale_warnings = [
            msg for msg in cm.output if 'PlateScale_Reference values differ' in msg
        ]

        self.assertEqual(len(cal_ref_warnings), 1)
        self.assertEqual(len(plate_scale_warnings), 1)
        self.assertTrue('unintended consequences downstream' in cal_ref_warnings[0])
        self.assertTrue('unintended consequences downstream' in plate_scale_warnings[0])

    def test_calreference_platescale_with_blanks(self):
        """Test that blank CalReference and PlateScale_Reference values are not pipe delimited."""
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
            'CalReference': ['ref1', '', 'ref1'],
            'PlateScale_Reference': ['', 'scale2', ''],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {'AdatId': '1a2b3c'}
        adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
            'CalReference': ['', 'ref3', ''],
            'PlateScale_Reference': ['scale1', '', 'scale2'],
        }
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {'AdatId': '1a2b3d'}
        adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        concat_adat = concatenate_adats([adat1, adat2])

        # CalReference: blanks should be filtered out
        cal_refs = list(concat_adat.columns.get_level_values('CalReference'))
        self.assertEqual(cal_refs, ['ref1', 'ref3', 'ref1'])

        # PlateScale_Reference: blanks should be filtered out
        plate_scales = list(
            concat_adat.columns.get_level_values('PlateScale_Reference')
        )
        self.assertEqual(plate_scales, ['scale1', 'scale2', 'scale2'])


class ConcatRfuTest(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'FLAG', 'FLAG']}
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
        }
        adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'ColCheck': ['PASS', 'PASS', 'FLAG']}
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )
        self.adats = [adat1, adat2]

    def test_rfu_accuracy(self):
        concat_adat = concatenate_adats(self.adats)
        self.assertTrue(
            (concat_adat.values == [[1, 2, 3], [4, 5, 6], [5, 6, 7], [6, 5, 4]]).all()
        )


class SmartConcatTestCase(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {
            'PlateId': ['A12', 'A12'],
            'Barcode': ['SL1234', 'SL1235'],
            'NewColumn': ['1', '2'],
        }
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
            '!Title': 'stuff',
        }
        self.adat0 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {
            'SeqId': ['A', 'B', 'D'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
        }
        row_metadata = {
            'PlateId': ['A13', 'A13'],
            'Barcode': ['SL1236', 'SL1237'],
            'RowCheck': ['PASS', 'FLAG'],
        }
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
            '!Title': 'morestuff',
        }
        self.adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[8, 9, 1], [1, 4, 8]]
        col_metadata = {'SeqId': ['A', 'D', 'E'], 'SeqIdVersion': ['1', '2', '3']}
        row_metadata = {'PlateId': ['A14', 'A14'], 'Barcode': ['SL1238', 'SL1239']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
            '!Title': 'evenmorestuff',
        }
        self.adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[12, 23, 34], [45, 56, 67]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['2', '3', '4'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
            '!Title': 'whatstuff',
        }
        self.adat0a = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

    @pytest.mark.filterwarnings('ignore:Removing seqIds from')
    @pytest.mark.filterwarnings('ignore:Standard column,')
    @pytest.mark.filterwarnings('ignore:Adding column to adat')
    def test_smart_adat_concat_seq_id_merge(self):
        concat_adat = smart_adat_concatenation([self.adat0, self.adat1, self.adat2])
        self.assertEqual(['A'], list(concat_adat.columns.get_level_values('SeqId')))

    @pytest.mark.filterwarnings('ignore:Removing seqIds from')
    @pytest.mark.filterwarnings('ignore:Standard column,')
    @pytest.mark.filterwarnings('ignore:Adding column to adat')
    def test_smart_adat_concat_header_meta(self):
        concat_adat = smart_adat_concatenation([self.adat0, self.adat1, self.adat2])
        expected_header = {
            'AdatId': None,
            '!AssayRobot': [
                {'adat_ids': ['stuff_A12'], 'value': 'Tecan1, Tecan2'},
                {'adat_ids': ['morestuff_A13', 'evenmorestuff_A14'], 'value': 'Tecan2'},
            ],
            'RunNotes': [
                {'adat_ids': ['stuff_A12'], 'value': 'run note 1'},
                {
                    'adat_ids': ['morestuff_A13', 'evenmorestuff_A14'],
                    'value': 'run note 2',
                },
            ],
            '!Title': [
                {'adat_ids': ['stuff_A12'], 'value': 'stuff'},
                {'adat_ids': ['morestuff_A13'], 'value': 'morestuff'},
                {'adat_ids': ['evenmorestuff_A14'], 'value': 'evenmorestuff'},
            ],
        }
        self.assertEqual(expected_header, concat_adat.header_metadata)

    @pytest.mark.filterwarnings('ignore:Removing seqIds from')
    @pytest.mark.filterwarnings('ignore:Standard column,')
    @pytest.mark.filterwarnings('ignore:Adding column to adat')
    def test_smart_adat_concat_row_meta(self):
        concat_adat = smart_adat_concatenation([self.adat0, self.adat1, self.adat2])
        expected_row_names = ['PlateId', 'Barcode', 'NewColumn', 'RowCheck']
        self.assertEqual(expected_row_names, concat_adat.index.names)

    def test_smart_adat_warnings(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            smart_adat_concatenation([self.adat0, self.adat1, self.adat2])

        # Check that we have the expected warnings
        warning_messages = cm.output
        expected_patterns = ['Adding column to adat:', 'Removing seqIds from']

        # Verify we have warnings matching our expected patterns
        matching_warnings = [
            msg
            for msg in warning_messages
            if any(pattern in msg for pattern in expected_patterns)
        ]
        self.assertEqual(7, len(matching_warnings))

    @pytest.mark.filterwarnings('ignore:Removing seqIds from')
    @pytest.mark.filterwarnings('ignore:Standard column,')
    @pytest.mark.filterwarnings('ignore:Adding column to adat')
    def test_smart_concat_adat_col_overwrite(self):
        concat_adat = smart_adat_concatenation([self.adat0, self.adat0a], self.adat0a)
        self.assertEqual(
            list(concat_adat.columns.get_level_values('SeqIdVersion')), ['2', '3', '4']
        )

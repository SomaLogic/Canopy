import logging
from unittest import TestCase

import pandas as pd
import pytest

from somadata import Adat
from somadata.errors import AdatMetaError
from somadata.tools import adat_concatenation_utils
from somadata.tools.adat_concatenation import concatenate_adats


class AdatColMetaReplaceTestCase(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
        }
        adat0 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['4', '5', '6'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )
        self.adats = [adat0, adat1]

    @pytest.mark.filterwarnings('ignore:Standard column')
    def test_col_meta_replaced(self):
        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        truth_meta_replaced_adat_1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        meta_replaced_adats = (
            adat_concatenation_utils.convert_somamer_metadata_to_source(
                self.adats, self.adats[0]
            )
        )
        pd.testing.assert_frame_equal(self.adats[0], meta_replaced_adats[0])
        pd.testing.assert_frame_equal(
            truth_meta_replaced_adat_1, meta_replaced_adats[1]
        )

    def test_missing_col_meta_warns(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            adat_concatenation_utils.convert_somamer_metadata_to_source(
                self.adats, self.adats[0]
            )

        self.assertTrue(
            any(
                'Standard column' in message
                and 'not found in column metadata' in message
                for message in cm.output
            ),
            "Expected warning about missing column metadata not found.",
        )

    @pytest.mark.filterwarnings('ignore:Standard column')
    def test_seq_ids_mismatch_error(self):
        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {
            'SeqId': ['A', 'B', 'D'],
            'SeqIdVersion': ['4', '5', '6'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        mismatch_seq_id_adat = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        with self.assertRaises(AdatMetaError):
            adat_concatenation_utils.convert_somamer_metadata_to_source(
                self.adats + [mismatch_seq_id_adat], self.adats[1]
            )

    @pytest.mark.filterwarnings('ignore:Standard column')
    def test_modified_adats_can_be_concatenated(self):
        meta_replaced_adats = (
            adat_concatenation_utils.convert_somamer_metadata_to_source(
                self.adats, self.adats[0]
            )
        )
        concat_adat = concatenate_adats(meta_replaced_adats)
        self.assertEqual(concat_adat.shape, (4, 3))


class AdatHeaderMetaMergeTestCase(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {
            'PlateId': ['P0012345', 'P0012345'],
            'Barcode': ['SL1234', 'SL1235'],
        }
        header_metadata = {}
        self.adat0 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
        }
        row_metadata = {
            'PlateId': ['Set 01', 'Set 02'],
            'Barcode': ['SL1236', 'SL1237'],
        }
        header_metadata = {}
        self.adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

    def test_get_adat_ids_v3(self):
        self.adat1.header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': 'Fluent 2',
            'PlateTailPercent_V4-19-021_Set_01': '2.56',
            '!Title': 'V4-19-021',
        }
        adat_ids = adat_concatenation_utils._get_adat_ids(self.adat1)
        expected_adat_ids = ['V4-19-021_Set 01', 'V4-19-021_Set 02']
        self.assertEqual(adat_ids, expected_adat_ids)

    def test_get_adat_ids_v4(self):
        self.adat0.header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': 'Fluent 1',
            'PlateTailPercent_P0012345': '1.25',
            '!Title': 'P0012345',
        }
        adat_ids = adat_concatenation_utils._get_adat_ids(self.adat0)
        expected_adat_ids = ['P0012345']
        self.assertEqual(adat_ids, expected_adat_ids)

    def test_get_adat_ids_previously_concatenated(self):
        self.adat1.header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': 'Fluent 2',
            'PlateTailPercent_V4-19-021_Set_01': '2.56',
            '!Title': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'V4-19-021',
                },
                {
                    'adat_ids': ['V4-19-021_Set 03'],
                    'value': 'V4-19-022',
                },
            ],
        }
        adat_ids = adat_concatenation_utils._get_adat_ids(self.adat1)
        expected_adat_ids = ['V4-19-021_Set 01', 'V4-19-021_Set 02', 'V4-19-021_Set 03']
        self.assertEqual(adat_ids, expected_adat_ids)

    def test_header_metadata_adat_id_converted(self):
        header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': 'Fluent 2',
            'PlateTailPercent_V4-19-021_Set_01': '2.56',
            '!Title': 'V4-19-021',
        }
        adat_ids = ['V4-19-021_Set 01', 'V4-19-021_Set 02']
        mod_header_metadata = (
            adat_concatenation_utils._convert_header_meta_to_contain_adat_id(
                header_metadata, adat_ids
            )
        )
        expected_mod_header_metadata = {
            '!AssayVersion': [
                {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': 'V4'}
            ],
            '!AssayRobot': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'Fluent 2',
                }
            ],
            'PlateTailPercent_V4-19-021_Set_01': [
                {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': '2.56'}
            ],
            '!Title': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'V4-19-021',
                }
            ],
        }
        self.assertEqual(mod_header_metadata, expected_mod_header_metadata)

    def test_header_metadata_adat_id_converted_previously_concatenated(self):
        header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': [
                {'adat_ids': ['V4-19-021_Set 01'], 'value': 'Fluent 2'},
                {
                    'adat_ids': ['V4-19-021_Set 02'],
                    'value': 'Fluent 1',
                },
            ],
            'PlateTailPercent_V4-19-021_Set_01': '2.56',
            '!Title': 'V4-19-021',
        }
        adat_ids = ['V4-19-021_Set 01', 'V4-19-021_Set 02']
        mod_header_metadata = (
            adat_concatenation_utils._convert_header_meta_to_contain_adat_id(
                header_metadata, adat_ids
            )
        )
        expected_mod_header_metadata = {
            '!AssayVersion': [
                {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': 'V4'}
            ],
            '!AssayRobot': [
                {'adat_ids': ['V4-19-021_Set 01'], 'value': 'Fluent 2'},
                {
                    'adat_ids': ['V4-19-021_Set 02'],
                    'value': 'Fluent 1',
                },
            ],
            'PlateTailPercent_V4-19-021_Set_01': [
                {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': '2.56'}
            ],
            '!Title': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'V4-19-021',
                }
            ],
        }
        self.assertEqual(mod_header_metadata, expected_mod_header_metadata)

    def test_merge_subheader_match(self):
        master_subheader = [
            {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': 'V4'}
        ]
        to_be_merged_subheader = [{'adat_ids': ['P0012345'], 'value': 'V4'}]
        merged_subheader = adat_concatenation_utils._merge_subheader(
            master_subheader, to_be_merged_subheader
        )
        expected_merged_subheader = [
            {
                'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02', 'P0012345'],
                'value': 'V4',
            }
        ]
        self.assertEqual(merged_subheader, expected_merged_subheader)

    def test_merge_subheader_unique(self):
        master_subheader = [
            {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': 'V4'}
        ]
        to_be_merged_subheader = [{'adat_ids': ['P0012345'], 'value': 'V3'}]
        merged_subheader = adat_concatenation_utils._merge_subheader(
            master_subheader, to_be_merged_subheader
        )
        expected_merged_subheader = [
            {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': 'V4'},
            {'adat_ids': ['P0012345'], 'value': 'V3'},
        ]
        self.assertEqual(merged_subheader, expected_merged_subheader)

    def test_merge_headers(self):
        header0 = {
            '!AssayVersion': [
                {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': 'V4'}
            ],
            '!AssayRobot': [
                {'adat_ids': ['V4-19-021_Set 01'], 'value': 'Fluent 2'},
                {
                    'adat_ids': ['V4-19-021_Set 02'],
                    'value': 'Fluent 1',
                },
            ],
            'CalibratorId': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': '160100',
                }
            ],
            'PlateTailPercent_V4-19-021_Set_01': [
                {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': '2.56'}
            ],
            '!Title': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'V4-19-021',
                }
            ],
        }
        header1 = {
            '!AssayVersion': [{'adat_ids': ['P0012345'], 'value': 'V4'}],
            '!AssayRobot': [{'adat_ids': ['P0012345'], 'value': 'Fluent 1'}],
            'CalibratorId': [{'adat_ids': ['P0012345'], 'value': '170999'}],
            'PlateTailPercent_P0012345': [{'adat_ids': ['P0012345'], 'value': '1.25'}],
            '!Title': [
                {
                    'adat_ids': ['P0012345'],
                    'value': 'P0012345',
                }
            ],
        }
        merged_header = adat_concatenation_utils._merge_headers([header0, header1])
        expected_merged_header = {
            '!AssayVersion': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02', 'P0012345'],
                    'value': 'V4',
                }
            ],
            '!AssayRobot': [
                {'adat_ids': ['V4-19-021_Set 01'], 'value': 'Fluent 2'},
                {
                    'adat_ids': ['V4-19-021_Set 02', 'P0012345'],
                    'value': 'Fluent 1',
                },
            ],
            'CalibratorId': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': '160100',
                },
                {'adat_ids': ['P0012345'], 'value': '170999'},
            ],
            'PlateTailPercent_V4-19-021_Set_01': [
                {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': '2.56'}
            ],
            '!Title': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'V4-19-021',
                },
                {
                    'adat_ids': ['P0012345'],
                    'value': 'P0012345',
                },
            ],
            'PlateTailPercent_P0012345': [{'adat_ids': ['P0012345'], 'value': '1.25'}],
        }
        self.assertEqual(merged_header, expected_merged_header)

    def test_header_simplify(self):
        adat_id_header = {
            '!AssayVersion': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02', 'P0012345'],
                    'value': 'V4',
                }
            ],
            '!AssayRobot': [
                {'adat_ids': ['V4-19-021_Set 01'], 'value': 'Fluent 2'},
                {
                    'adat_ids': ['V4-19-021_Set 02', 'P0012345'],
                    'value': 'Fluent 1',
                },
            ],
            'CalibratorId': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': '160100',
                },
                {'adat_ids': ['P0012345'], 'value': '170999'},
            ],
            'PlateTailPercent_V4-19-021_Set_01': [
                {'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'], 'value': '2.56'}
            ],
            '!Title': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'V4-19-021',
                },
                {
                    'adat_ids': ['P0012345'],
                    'value': 'P0012345',
                },
            ],
            'PlateTailPercent_P0012345': [{'adat_ids': ['P0012345'], 'value': '1.25'}],
        }
        simplified_header = adat_concatenation_utils._simplify_header_metadata(
            adat_id_header
        )
        expected_simplified_header = {
            '!AssayVersion': 'V4',
            '!AssayRobot': [
                {'adat_ids': ['V4-19-021_Set 01'], 'value': 'Fluent 2'},
                {
                    'adat_ids': ['V4-19-021_Set 02', 'P0012345'],
                    'value': 'Fluent 1',
                },
            ],
            'CalibratorId': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': '160100',
                },
                {'adat_ids': ['P0012345'], 'value': '170999'},
            ],
            'PlateTailPercent_V4-19-021_Set_01': '2.56',
            '!Title': [
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'V4-19-021',
                },
                {
                    'adat_ids': ['P0012345'],
                    'value': 'P0012345',
                },
            ],
            'PlateTailPercent_P0012345': '1.25',
        }
        self.assertEqual(simplified_header, expected_simplified_header)

    def test_adat_header_merge(self):
        self.adat0.header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': 'Fluent 1',
            'PlateTailPercent_P0012345': '1.25',
            '!Title': 'P0012345',
        }
        self.adat1.header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': 'Fluent 2',
            'PlateTailPercent_V4-19-021_Set_01': '2.56',
            '!Title': 'V4-19-021',
        }
        adat2 = self.adat1.copy()
        adat2.header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': 'Fluent 1',
            'PlateTailPercent_V4-19-025_Set_01': '3.5',
            '!Title': 'V4-19-025',
        }
        modified_header_metadata_adats = (
            adat_concatenation_utils.robust_merge_adat_headers(
                [self.adat0, self.adat1, adat2]
            )
        )

        expected_header_metadata = {
            '!AssayVersion': 'V4',
            '!AssayRobot': [
                {
                    'adat_ids': ['P0012345', 'V4-19-025_Set 01', 'V4-19-025_Set 02'],
                    'value': 'Fluent 1',
                },
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'Fluent 2',
                },
            ],
            'PlateTailPercent_P0012345': '1.25',
            '!Title': [
                {
                    'adat_ids': ['P0012345'],
                    'value': 'P0012345',
                },
                {
                    'adat_ids': ['V4-19-021_Set 01', 'V4-19-021_Set 02'],
                    'value': 'V4-19-021',
                },
                {
                    'adat_ids': ['V4-19-025_Set 01', 'V4-19-025_Set 02'],
                    'value': 'V4-19-025',
                },
            ],
            'PlateTailPercent_V4-19-021_Set_01': '2.56',
            'PlateTailPercent_V4-19-025_Set_01': '3.5',
        }
        for adat in modified_header_metadata_adats:
            self.assertEqual(expected_header_metadata, adat.header_metadata)


class RowMetaMergeTestCase(TestCase):
    def setUp(self):
        pass

    def test_row_meta_merge_simple(self):
        meta0 = [
            'PlateId',
            'PlateRunDate',
            'ScannerID',
            'PlatePosition',
            'SlideId',
            'Subarray',
            'HybControlNormScale',
            'RowCheck',
        ]
        meta1 = [
            'PlateId',
            'PlateRunDate',
            'TimePoint',
            'SiteId',
            'TubeUniqueID',
            'CLI',
            'RowCheck',
            'NormScale_0_2',
        ]
        meta2 = [
            'PlateId',
            'PlateRunDate',
            'TimePoint',
            'SiteId',
            'TubeUniqueID',
            'CLI',
            'RowCheck',
            'NormScale_20',
        ]
        ordered_merged_meta = adat_concatenation_utils.order_merge_row_meta_names(
            [meta0, meta1, meta2]
        )
        expected_ordered_merged_meta = [
            'PlateId',
            'PlateRunDate',
            'ScannerID',
            'PlatePosition',
            'SlideId',
            'Subarray',
            'TimePoint',
            'SiteId',
            'TubeUniqueID',
            'CLI',
            'HybControlNormScale',
            'RowCheck',
            'NormScale_0_2',
            'NormScale_20',
        ]
        print(ordered_merged_meta)
        self.assertEqual(ordered_merged_meta, expected_ordered_merged_meta)


class RowMetaAdatMergeTestCase(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
        }
        self.adat0 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5, 6, 7], [6, 5, 4]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
        }
        row_metadata = {
            'PlateId': ['A13', 'A13'],
            'Barcode': ['SL1236', 'SL1237'],
            'HybControlNormScale': ['1.2', '5'],
            'RowCheck': ['PASS', 'PASS'],
        }
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        self.adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[8, 9, 1], [1, 4, 8]]
        col_metadata = {'SeqId': ['A', 'B', 'C'], 'SeqIdVersion': ['1', '2', '3']}
        row_metadata = {
            'PlateId': ['A14', 'A14'],
            'Barcode': ['SL1238', 'SL1239'],
            'Stuff': ['foo', 'bar'],
        }
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
        }
        self.adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

    def test_merge_norm_data(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            new_adats = adat_concatenation_utils.unify_row_meta_column_names(
                [self.adat0, self.adat1]
            )

        self.assertTrue(
            any('Adding column to adat:' in message for message in cm.output),
            "Expected warning about adding column to adat not found.",
        )
        expected_row_names = ['PlateId', 'Barcode', 'HybControlNormScale', 'RowCheck']
        for adat in new_adats:
            self.assertEqual(expected_row_names, list(adat.index.names))

    def test_merge_three_adats(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            new_adats = adat_concatenation_utils.unify_row_meta_column_names(
                [self.adat0, self.adat1, self.adat2]
            )

        self.assertTrue(
            any('Adding column to adat:' in message for message in cm.output),
            "Expected warning about adding column to adat not found.",
        )
        expected_row_names = [
            'PlateId',
            'Barcode',
            'Stuff',
            'HybControlNormScale',
            'RowCheck',
        ]
        for adat in new_adats:
            self.assertEqual(expected_row_names, list(adat.index.names))


class SeqIdInnerMergeTestCase(TestCase):
    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
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
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
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
        }
        self.adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

    @pytest.mark.filterwarnings('ignore:Removing seqIds from')
    def test_inner_merge_two_adats(self):
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_inner_merge(
            [self.adat0, self.adat1]
        )
        expected_seq_ids = ['A', 'B']
        for adat in mod_adats:
            self.assertEqual(
                expected_seq_ids, list(adat.columns.get_level_values('SeqId'))
            )

    def test_inner_merge_two_adats_warning(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            adat_concatenation_utils.prepare_rfu_matrix_for_inner_merge(
                [self.adat0, self.adat1]
            )

        self.assertTrue(
            any('Removing seqIds from' in message for message in cm.output),
            "Expected warning about removing seqIds not found.",
        )

    @pytest.mark.filterwarnings('ignore:Removing seqIds from')
    def test_inner_merge_three_adats(self):
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_inner_merge(
            [self.adat0, self.adat1, self.adat2]
        )
        expected_seq_ids = ['A']
        for adat in mod_adats:
            self.assertEqual(
                expected_seq_ids, list(adat.columns.get_level_values('SeqId'))
            )

    def test_inner_merge_three_adats_warning(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            adat_concatenation_utils.prepare_rfu_matrix_for_inner_merge(
                [self.adat0, self.adat1, self.adat2]
            )

        self.assertTrue(
            any('Removing seqIds from' in message for message in cm.output),
            "Expected warning about removing seqIds not found.",
        )


class SeqIdOuterMergeTestCase(TestCase):
    def setUp(self):
        rfu_data = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        col_metadata = {
            'SeqId': ['A', 'B', 'C'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
            '!Title': 'TestAdat0',
        }
        self.adat0 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[5.0, 6.0, 7.0], [6.0, 5.0, 4.0]]
        col_metadata = {
            'SeqId': ['A', 'B', 'D'],
            'SeqIdVersion': ['1', '2', '3'],
            'ColCheck': ['PASS', 'PASS', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A13', 'A13'], 'Barcode': ['SL1236', 'SL1237']}
        header_metadata = {
            'AdatId': '1a2b3d',
            '!AssayRobot': 'Tecan2',
            'RunNotes': 'run note 2',
            '!Title': 'TestAdat1',
        }
        self.adat1 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

        rfu_data = [[8.0, 9.0, 1.0], [1.0, 4.0, 8.0]]
        col_metadata = {'SeqId': ['A', 'D', 'E'], 'SeqIdVersion': ['1', '2', '3']}
        row_metadata = {'PlateId': ['A14', 'A14'], 'Barcode': ['SL1238', 'SL1239']}
        header_metadata = {
            'AdatId': '1a2b3e',
            '!AssayRobot': 'Tecan3',
            'RunNotes': 'run note 3',
            '!Title': 'TestAdat2',
        }
        self.adat2 = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

    @pytest.mark.filterwarnings('ignore:Adding .* SeqIds to')
    def test_outer_merge_two_adats(self):
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
            [self.adat0, self.adat1]
        )
        expected_seq_ids = ['A', 'B', 'C', 'D']
        for adat in mod_adats:
            self.assertEqual(
                expected_seq_ids, sorted(adat.columns.get_level_values('SeqId'))
            )
            # Check that all adats have the same number of columns
            self.assertEqual(4, len(adat.columns))

    def test_outer_merge_two_adats_warning(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
                [self.adat0, self.adat1]
            )

        self.assertTrue(
            any(
                'Adding' in message and 'SeqIds to' in message for message in cm.output
            ),
            "Expected warning about adding SeqIds not found.",
        )

    @pytest.mark.filterwarnings('ignore:Adding .* SeqIds to')
    def test_outer_merge_three_adats(self):
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
            [self.adat0, self.adat1, self.adat2]
        )
        expected_seq_ids = ['A', 'B', 'C', 'D', 'E']
        for adat in mod_adats:
            self.assertEqual(
                expected_seq_ids, sorted(adat.columns.get_level_values('SeqId'))
            )
            # Check that all adats have the same number of columns
            self.assertEqual(5, len(adat.columns))

    def test_outer_merge_three_adats_warning(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
                [self.adat0, self.adat1, self.adat2]
            )

        self.assertTrue(
            any(
                'Adding' in message and 'SeqIds to' in message for message in cm.output
            ),
            "Expected warning about adding SeqIds not found.",
        )

    @pytest.mark.filterwarnings('ignore:Adding .* SeqIds to')
    def test_outer_merge_preserves_column_structure(self):
        """Test that outer merge preserves each adat's original column metadata structure."""
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
            [self.adat0, self.adat1]
        )

        # Check that column metadata structure is preserved
        self.assertEqual(self.adat0.columns.names, mod_adats[0].columns.names)
        self.assertEqual(self.adat1.columns.names, mod_adats[1].columns.names)

    @pytest.mark.filterwarnings('ignore:Adding .* SeqIds to')
    def test_outer_merge_fills_nan(self):
        """Test that missing columns are filled with NaN values."""
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
            [self.adat0, self.adat1]
        )

        # adat0 should have NaN for SeqId 'D' (which was only in adat1)
        d_col_idx = mod_adats[0].columns.get_level_values('SeqId').tolist().index('D')
        self.assertTrue(pd.isna(mod_adats[0].iloc[0, d_col_idx]))
        self.assertTrue(pd.isna(mod_adats[0].iloc[1, d_col_idx]))

        # adat1 should have NaN for SeqId 'C' (which was only in adat0)
        c_col_idx = mod_adats[1].columns.get_level_values('SeqId').tolist().index('C')
        self.assertTrue(pd.isna(mod_adats[1].iloc[0, c_col_idx]))
        self.assertTrue(pd.isna(mod_adats[1].iloc[1, c_col_idx]))

    @pytest.mark.filterwarnings('ignore:Adding .* SeqIds to')
    def test_outer_merge_preserves_existing_data(self):
        """Test that existing data is preserved after outer merge."""
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
            [self.adat0, self.adat1]
        )

        # Check that original data in adat0 is preserved
        a_col_idx = mod_adats[0].columns.get_level_values('SeqId').tolist().index('A')
        self.assertEqual(1.0, mod_adats[0].iloc[0, a_col_idx])
        self.assertEqual(4.0, mod_adats[0].iloc[1, a_col_idx])

    @pytest.mark.filterwarnings('ignore:Adding .* SeqIds to')
    def test_outer_merge_sorted_by_seqid(self):
        """Test that columns are sorted by SeqId after outer merge."""
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
            [self.adat0, self.adat1, self.adat2]
        )

        for adat in mod_adats:
            seq_ids = list(adat.columns.get_level_values('SeqId'))
            self.assertEqual(sorted(seq_ids), seq_ids)

    @pytest.mark.filterwarnings('ignore:Adding .* SeqIds to')
    def test_outer_merge_empty_metadata_for_new_columns(self):
        """Test that new columns have empty strings for non-SeqId metadata."""
        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
            [self.adat0, self.adat1]
        )

        # Find a column that was added to adat0 (e.g., SeqId 'D')
        d_col_idx = mod_adats[0].columns.get_level_values('SeqId').tolist().index('D')

        # Check that non-SeqId metadata is empty string
        col_tuple = mod_adats[0].columns[d_col_idx]
        seqid_idx = mod_adats[0].columns.names.index('SeqId')

        for i, value in enumerate(col_tuple):
            if i == seqid_idx:
                self.assertEqual('D', value)  # SeqId should be 'D'
            else:
                self.assertEqual('', value)  # Other metadata should be empty string

    @pytest.mark.filterwarnings('ignore:Adding .* SeqIds to')
    def test_outer_merge_no_changes_when_seqids_match(self):
        """Test that no changes are made when SeqIds already match."""
        # Create two adats with identical SeqIds
        adat_a = self.adat0.copy()
        adat_b = self.adat0.copy()

        mod_adats = adat_concatenation_utils.prepare_rfu_matrix_for_outer_merge(
            [adat_a, adat_b]
        )

        # Both should have the same SeqIds as original
        for adat in mod_adats:
            self.assertEqual(
                list(self.adat0.columns.get_level_values('SeqId')),
                list(adat.columns.get_level_values('SeqId')),
            )

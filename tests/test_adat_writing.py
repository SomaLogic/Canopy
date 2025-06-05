import hashlib
import os
from unittest import TestCase, mock

import somadata
from somadata import Adat


def require_side_effect(*args, **kwargs):
    version = '0.2.1'
    return version


class AdatWritingTest(TestCase):
    """Tests if writing can occur and if the written file matches expectation (via md5)."""

    filename = './tests/data/control_data_written.adat'
    filename_compatibility_mode = './tests/data/control_data_written_compatible.adat'
    source_filename = './tests/data/control_data.adat'

    def setUp(self):
        self.source_md5 = hashlib.md5()
        with open(self.source_filename, 'rb') as f:
            self.source_md5.update(f.read())
        self.adat = somadata.read_adat('./tests/data/control_data.adat')
        self.adat_compatibility_mode = somadata.read_adat(
            './tests/data/control_data.adat', compatibility_mode=True
        )
        self.original_report_config = self.adat.header_metadata.get(
            'ReportConfig', None
        )

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        if os.path.exists(self.filename_compatibility_mode):
            os.remove(self.filename_compatibility_mode)

    def test_adat_write(self):
        self.adat.to_adat(self.filename)
        self.assertTrue(os.path.exists(self.filename))

    def test_adat_write_header_various_types(self):
        # Test various data types in header metadata
        self.adat.header_metadata['HeaderString'] = "test_string"
        self.adat.header_metadata['HeaderNumeric'] = 123456789
        self.adat.header_metadata['HeaderFloat'] = 1.23456789
        self.adat.header_metadata['HeaderBoolean'] = True
        self.adat.header_metadata['HeaderNone'] = None
        self.adat.header_metadata['HeaderList'] = [1, 2, 3]
        self.adat.header_metadata['HeaderDict'] = {
            ('key1', 'key2'): 'value1',
            'key3': 'value2',
        }

        self.adat.to_adat(self.filename)
        _, _, _, header_metadata = somadata.parse_file(self.filename)

        self.assertEqual(header_metadata['HeaderString'], 'test_string')
        self.assertEqual(header_metadata['HeaderNumeric'], '123456789')
        self.assertEqual(header_metadata['HeaderFloat'], '1.23456789')
        self.assertEqual(header_metadata['HeaderBoolean'], 'True')
        self.assertEqual(header_metadata['HeaderNone'], '')
        self.assertEqual(header_metadata['HeaderList'], '[1, 2, 3]')
        self.assertEqual(
            header_metadata['HeaderDict'],
            "{('key1', 'key2'): 'value1', 'key3': 'value2'}",
        )

    @mock.patch('somadata.io.adat.file.version', require_side_effect)
    def test_adat_md5(self):
        self.adat.to_adat(self.filename)
        hash_md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            hash_md5.update(f.read())
        self.assertEqual(hash_md5.hexdigest(), 'ff0f3b40b210999093d55e129276201e')

    @mock.patch('somadata.io.adat.file.version', require_side_effect)
    def test_adat_md5_compatibility(self):
        self.adat_compatibility_mode.to_adat(self.filename_compatibility_mode)
        _, _, _, header_metadata = somadata.parse_file(self.filename_compatibility_mode)
        self.assertEqual(header_metadata['ReportConfig'], self.original_report_config)


def require_side_effect_0_2(*args, **kwargs):
    version = '0.2'
    return version


class ConvertV3SeqIdsWriteTestCase(TestCase):
    filename = 'tests/data/v3_style_seq_id.adat'

    def setUp(self):
        rfu_data = [[1, 2, 3], [4, 5, 6]]
        col_metadata = {
            'SeqId': ['12345-6', '23456-7', '34567-8'],
            'SeqIdVersion': ['7', '8', '9'],
            'ColCheck': ['PASS', 'FLAG', 'FLAG'],
        }
        row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
        header_metadata = {
            'AdatId': '1a2b3c',
            '!AssayRobot': 'Tecan1, Tecan2',
            'RunNotes': 'run note 1',
        }
        self.adat = Adat.from_features(
            rfu_data, row_metadata, col_metadata, header_metadata
        )

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    @mock.patch('somadata.io.adat.file.version', require_side_effect_0_2)
    def test_adat_writing(self):
        self.adat.to_adat(self.filename, convert_to_v3_seq_ids=True)
        hash_md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            hash_md5.update(f.read())
        self.assertEqual(hash_md5.hexdigest(), '0d94aad767bb4af52a1ea93d41a48d79')

import hashlib
import os
from unittest import TestCase, mock

import canopy
from canopy import Adat


def require_side_effect(*args, **kwargs):
    version = '0.2.1'
    return version


class AdatWritingTest(TestCase):
    """Tests if writing can occur and if the written file matches expectation (via md5)."""

    filename = './tests/data/control_data_written.adat'
    source_filename = './tests/data/control_data.adat'

    def setUp(self):
        self.source_md5 = hashlib.md5()
        with open(self.source_filename, 'rb') as f:
            self.source_md5.update(f.read())
        self.adat = canopy.read_adat('./tests/data/control_data.adat')

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_adat_write(self):
        self.adat.to_adat(self.filename)
        self.assertTrue(os.path.exists(self.filename))

    @mock.patch('canopy.io.adat.file.version', require_side_effect)
    def test_adat_md5(self):
        self.adat.to_adat(self.filename)
        hash_md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            hash_md5.update(f.read())
        self.assertEqual(hash_md5.hexdigest(), 'e288d94404e1e30a2138b188daa9a7e9')


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

    @mock.patch('canopy.io.adat.file.version', require_side_effect_0_2)
    def test_adat_writing(self):
        self.adat.to_adat(self.filename, convert_to_v3_seq_ids=True)
        hash_md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            hash_md5.update(f.read())
        self.assertEqual(hash_md5.hexdigest(), 'd47957bafb2ef8b8b70bf0efd9705c11')

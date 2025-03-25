import io
import logging

import pytest

from somadata.io.adat.file import parse_file


def test_parse_file_with_missing_row_metadata(missing_rfu_adat_path: str, caplog):
    with caplog.at_level(logging.WARNING):
        rfu_matrix, row_metadata, column_metadata, header_metadata = parse_file(
            missing_rfu_adat_path
        )

    # Assert that the warning was logged about missing row metadata
    warning_message = (
        "Row metadata has 3 missing values. Filling missing entries with empty strings."
    )
    assert any(
        warning_message in record.message for record in caplog.records
    ), "Expected warning about missing row metadata not found."

    # Verify row_metadata structure is correctly filled
    # First row is fine
    assert row_metadata["ANMLFractionUsed_20"] == [
        '',
        '',
        '0.817',
        '',
        '',
        '0.791',
        '',
        '',
        '',
        '0.832',
        '',
    ]
    assert row_metadata["ANMLFractionUsed_0_5"] == [
        '',
        '',
        '0.836',
        '',
        '',
        '0.829',
        '',
        '',
        '',
        '0.840',
        '',
    ]

import csv
from pathlib import Path

import numpy as np
import pytest

import somadata as sd


@pytest.fixture(scope="session")
def control_data_path() -> str:
    return str(Path(__file__).parent / 'data' / 'control_data.adat')


@pytest.fixture(scope="session")
def control_data(control_data_path: str) -> sd.Adat:
    return sd.read_adat(control_data_path)


@pytest.fixture(scope="session")
def missing_rfu_adat_path(control_data_path: str, tmp_path_factory) -> str:
    fn = str(tmp_path_factory.mktemp("data") / "missing_rfu_test.adat")
    # Read ADAT as TSV
    with open(control_data_path, "r", newline="", encoding="utf-8") as f:
        reader = [row for row in csv.reader(f, delimiter="\t")]
    # Modify only the last row
    if reader:
        reader[-1] = reader[-1][:33]  # Keep only the first 33 columns (up to column AG)
    # Write back to the file while preserving tab delimiters
    with open(fn, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerows(reader)
    return fn

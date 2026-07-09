"""Shared fixtures and Adat factory helpers for tests/conversion/."""

from __future__ import annotations

import pandas as pd
import pytest

from somadata.adat import Adat

# ---------------------------------------------------------------------------
# ProcessSteps constants
# ---------------------------------------------------------------------------

BRIDGED_STEPS = (
    'Raw RFU, Hyb Normalization, medNormInt, plateScale, Calibration, '
    'CrossPlatformPlateScaling, CrossPlatformCalibrate, MedNormExt'
)

NATIVE_STEPS = 'Raw RFU, Hyb Normalization, medNormInt, plateScale, Calibration'

# ---------------------------------------------------------------------------
# Minimal Adat factory helpers
# ---------------------------------------------------------------------------


def make_adat(
    header: dict | None = None,
    row_names: list[str] | None = None,
    row_values: list[list] | None = None,
    col_names: list[str] | None = None,
) -> Adat:
    """Build a minimal Adat for testing without needing real file fixtures."""
    header = header or {}
    row_names = row_names or ['SampleId', 'SampleType']
    row_values = row_values or [['S1', 'S2'], ['Sample', 'Sample']]
    col_names = col_names or ['10000-01', '10001-02']

    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    columns = pd.MultiIndex.from_arrays([col_names], names=['SeqId'])
    data = [[1.0] * len(col_names)] * len(row_values[0])
    return Adat(data=data, index=index, columns=columns, header_metadata=header)


def make_array_adat(
    assay_version: str = 'V4',
    process_steps: str = NATIVE_STEPS,
    n_samples: int = 2,
) -> Adat:
    """Minimal array Adat with SlideId and Subarray row metadata."""
    return make_adat(
        header={
            '!AssayVersion': assay_version,
            '!ProcessSteps': process_steps,
        },
        row_names=['SampleId', 'SampleType', 'SlideId', 'Subarray'],
        row_values=[
            [f'S{i}' for i in range(n_samples)],
            ['Sample'] * n_samples,
            ['258740110837'] * n_samples,
            ['3'] * n_samples,
        ],
    )


def make_bridged_array_adat() -> Adat:
    """Minimal bridged array Adat (ProcessSteps end with the bridged terminal triple)."""
    return make_array_adat(process_steps=BRIDGED_STEPS)


def make_native_array_adat() -> Adat:
    """Minimal native array Adat (no bridged terminal steps)."""
    return make_array_adat(process_steps=NATIVE_STEPS)


def make_ngs_adat() -> Adat:
    """Minimal NGS Adat with SOMAmerReads row metadata."""
    return make_adat(
        header={'!AssayVersion': 'v1'},
        row_names=['SampleId', 'SampleType', 'SOMAmerReads'],
        row_values=[['S1', 'S2'], ['Sample', 'Sample'], ['14250000', '13800000']],
    )


def make_v2_combined_adat() -> Adat:
    """Minimal Adat already in v2.0 combined format."""
    return make_adat(header={'FileVersion': '2.0'})

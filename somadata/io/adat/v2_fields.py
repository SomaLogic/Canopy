"""v2.0 ADAT format field-type registries.

Defines the static type mappings for every field in the ^HEADER, ^COL_DATA,
and ^ROW_DATA sections of an ADAT v2.0 file.

These are used by the v2.0 writer to emit correct Type rows and to serialize
JSON-typed header values.  They are kept separate from the writer so that
conversion code (somadata/conversion/) can import them without pulling in I/O
dependencies.
"""

from __future__ import annotations

import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class FieldType(str, Enum):
    """The five value types defined in the ADAT v2.0 spec.

    Inheriting from ``str`` means each member is also a plain string, so
    ``FieldType.STRING == 'String'`` is ``True`` and members can be passed
    directly to ``csv.writer.writerow()`` without calling ``.value``.
    """

    STRING = 'String'
    INTEGER = 'Integer'
    DECIMAL = 'Decimal'
    DATE = 'Date'
    JSON = 'JSON'


# ---------------------------------------------------------------------------
# ^HEADER field types  (Section 2.3)
# ---------------------------------------------------------------------------
# The v2.0 header is a closed, static set.  All fields listed here must be
# present in every v2.0 ADAT; no additional fields are permitted.

V2_HEADER_FIELD_TYPES: dict[str, FieldType] = {
    'FileVersion': FieldType.STRING,
    'AdatId': FieldType.STRING,
    'AssayType': FieldType.STRING,
    'AssayVersion': FieldType.STRING,
    'UseRestriction': FieldType.STRING,
    'SourceFile': FieldType.JSON,
    'SOMAmerReferenceSource': FieldType.STRING,
    'FileCreatedDate': FieldType.DATE,
    'Title': FieldType.STRING,
    'StudyOrganism': FieldType.STRING,
    'StudyMatrix': FieldType.STRING,
    'ProcessSteps': FieldType.JSON,
    'ReportConfig': FieldType.JSON,
    'PlateScaleScalar': FieldType.JSON,
    'CalibrateTailPercent': FieldType.JSON,
    'CalibrateTailPercentStatus': FieldType.JSON,
    'QCCheckTailPercent': FieldType.JSON,
    'QCCheckTailPercentStatus': FieldType.JSON,
    'PlateScaleStatus': FieldType.JSON,
    'PlateSOMAmerNormReadsStatus': FieldType.JSON,
}

# ---------------------------------------------------------------------------
# ^COL_DATA field types  (Section 2.6.1)
# ---------------------------------------------------------------------------
# Static fields are looked up by exact name; plate/calibrator-keyed dynamic
# fields are matched by the prefix tuples below.

V2_COL_FIELD_TYPES: dict[str, FieldType] = {
    'SeqId': FieldType.STRING,
    'Target': FieldType.STRING,
    'TargetFullName': FieldType.STRING,
    'Type': FieldType.STRING,
    'Organism': FieldType.STRING,
    'UniProt': FieldType.STRING,
    'EntrezGeneId': FieldType.STRING,
    'EntrezGeneSymbol': FieldType.STRING,
    'HybControl': FieldType.STRING,
    'Dilution': FieldType.STRING,
    'DRCLevelNGS': FieldType.STRING,
    'BlockListNGS': FieldType.STRING,
    'Ref.MedNorm.Id': FieldType.STRING,
}

# (prefix, type) — matched in order; first match wins.
V2_COL_DYNAMIC_PREFIX_TYPES: list[tuple[str, FieldType]] = [
    ('PlatformSpecificCalibrate_', FieldType.DECIMAL),
    ('CrossPlatformCalibrate_', FieldType.DECIMAL),
    ('QCRatio_', FieldType.DECIMAL),
    ('Ref.Array.', FieldType.DECIMAL),
    ('Ref.NGS.', FieldType.DECIMAL),
]

# ---------------------------------------------------------------------------
# ^ROW_DATA field types
# ---------------------------------------------------------------------------

V2_ROW_FIELD_TYPES: dict[str, FieldType] = {
    'SampleId': FieldType.STRING,
    'SampleReadout': FieldType.STRING,
    'UniqueSampleKey': FieldType.STRING,
    'SampleType': FieldType.STRING,
    'SourceFileId': FieldType.STRING,
    'ProcessStepsId': FieldType.STRING,
    'ReportConfigId': FieldType.STRING,
    'SoftwareVersion': FieldType.STRING,
    'SequencingRunId': FieldType.STRING,
    'PlateId': FieldType.STRING,
    'PlateRunDate': FieldType.DATE,
    'WellPosition': FieldType.STRING,
    'SlideId': FieldType.STRING,
    'Subarray': FieldType.INTEGER,
    'MatrixTubeBarcode': FieldType.STRING,
    'ControlId': FieldType.STRING,
    'BatchId': FieldType.STRING,
    'InputType': FieldType.STRING,
    'KitType': FieldType.STRING,
    'SampleMatrix': FieldType.STRING,
    'Project': FieldType.STRING,
    'SubjectId': FieldType.STRING,
    'SOMAmerBeadPlate': FieldType.STRING,
    'NGSPlateMasterMixLot': FieldType.STRING,
    'SOMAmerReads': FieldType.INTEGER,
    'SOMAmerReadsStatus': FieldType.STRING,
    'SOMAmerNormReads': FieldType.DECIMAL,
    'SOMAmerNormReadsStatus': FieldType.STRING,
    'RefCorr': FieldType.DECIMAL,
    'EmpericalHybTemp': FieldType.DECIMAL,
    'EmpiricalHybTempStatus': FieldType.STRING,
    'HybNormScaleFactor': FieldType.DECIMAL,
    'HybNormStatus': FieldType.STRING,
    'MedNormIntStatus': FieldType.STRING,
    'MedNormExtStatus': FieldType.STRING,
    'RowCheckStatus': FieldType.STRING,
    'CrossPlateMedNormIntScaleFactor': FieldType.DECIMAL,
    'InstrumentType': FieldType.STRING,
    'Flowcell': FieldType.STRING,
    'YieldDemux': FieldType.INTEGER,
    'YieldQ30Demux': FieldType.INTEGER,
    'Q30WeightedMean': FieldType.DECIMAL,
}

# (prefix, type) — matched in order; first match wins.
V2_ROW_DYNAMIC_PREFIX_TYPES: list[tuple[str, FieldType]] = [
    ('NormScale_', FieldType.DECIMAL),
    ('MedNormInt_', FieldType.DECIMAL),
    ('MedNormExt_', FieldType.DECIMAL),
    ('ANMLFractionUsed_', FieldType.DECIMAL),
]

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def v2_col_field_type(name: str) -> FieldType:
    """Return the v2.0 type annotation for a COL_DATA field name."""
    if name in V2_COL_FIELD_TYPES:
        return V2_COL_FIELD_TYPES[name]
    for prefix, ftype in V2_COL_DYNAMIC_PREFIX_TYPES:
        if name.startswith(prefix):
            return ftype
    return FieldType.STRING


def v2_row_field_type(name: str) -> FieldType:
    """Return the v2.0 type annotation for a ROW_DATA field name."""
    if name in V2_ROW_FIELD_TYPES:
        return V2_ROW_FIELD_TYPES[name]
    for prefix, ftype in V2_ROW_DYNAMIC_PREFIX_TYPES:
        if name.startswith(prefix):
            return ftype
    return FieldType.STRING


def serialize_header_value_v2(key: str, value) -> str:
    """Serialize a v2.0 header value to its on-disk string representation.

    JSON-typed fields are serialized as single-line minified JSON.  All other
    types are converted to ``str``.  ``None`` becomes an empty string.
    """
    expected_type = V2_HEADER_FIELD_TYPES.get(key, FieldType.STRING)
    if expected_type is FieldType.JSON:
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(',', ':'))
        return str(value) if value is not None else ''
    return str(value) if value is not None else ''


def validate_v2_header_fields(header_metadata: dict) -> bool:
    """Validate that a v2.0 header conforms to the closed field set.

    Logs a warning for each category of violation and returns ``False`` if any
    violation is found so that callers can decide whether to raise an exception:

    - **Extra fields** — keys present in *header_metadata* that are not part of
      the closed v2.0 field set.  These will be written to the file but violate
      the spec; downstream parsers that enforce the closed set may reject them.
    - **Missing fields** — keys defined by the spec that are absent from
      *header_metadata*.  A compliant v2.0 file must contain all defined fields.

    Parameters
    ----------
    header_metadata : dict
        The ``header_metadata`` dict from an ``Adat`` object.

    Returns
    -------
    bool
        ``True`` if the header is fully compliant; ``False`` if extra or
        missing fields were detected.
    """
    defined = set(V2_HEADER_FIELD_TYPES)
    present = set(header_metadata)

    extra = present - defined
    missing = defined - present

    if extra:
        logger.warning(
            'v2.0 ADAT header contains fields not permitted by the closed field set: '
            '%s. '
            'These fields will be written but may be rejected by strict v2.0 parsers.',
            sorted(extra),
        )

    if missing:
        logger.warning(
            'v2.0 ADAT header is missing required fields: '
            '%s. '
            'All defined fields must be present in a compliant v2.0 file.',
            sorted(missing),
        )

    return not extra and not missing

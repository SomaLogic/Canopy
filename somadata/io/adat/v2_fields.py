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
from datetime import date, datetime
from enum import Enum
from typing import Dict, List

import pandas as pd

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
# ^HEADER field types
# ---------------------------------------------------------------------------
# The v2.0 header is a closed, static set.  All fields listed here must be
# present in every v2.0 ADAT; no additional fields are permitted.

V2_HEADER_FIELD_TYPES: dict[str, FieldType] = {
    'FileVersion': FieldType.STRING,
    'AdatId': FieldType.STRING,
    'AssayType': FieldType.STRING,
    # NOTE: AssayVersion was removed from the header in v2.0 (spec §3.2.1 / §3.3.1).
    # It is now a per-sample ROW_DATA field populated from source ADAT header.
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
# ^COL_DATA field types
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
    'BlockList': FieldType.STRING,
    'Ref.MedNorm.Id': FieldType.STRING,
}

# (prefix, type) — matched in order; first match wins.
V2_COL_DYNAMIC_PREFIX_TYPES: list[tuple[str, FieldType]] = [
    ('DRCLevel_', FieldType.DECIMAL),
    ('PlatformSpecificCalibrate_', FieldType.DECIMAL),
    ('CrossPlatformCalibrate_', FieldType.DECIMAL),
    ('QCRatio_', FieldType.DECIMAL),
    ('Ref.Array.', FieldType.DECIMAL),
    ('Ref.NGS.', FieldType.DECIMAL),
    ('Ref.Bridging.', FieldType.DECIMAL),
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
    'AssayVersion': FieldType.STRING,
    'MasterMixVersion': FieldType.STRING,
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
    'HybQC': FieldType.DECIMAL,
    'HybQCStatus': FieldType.STRING,
    'HybNormScaleFactor': FieldType.DECIMAL,
    'HybNormStatus': FieldType.STRING,
    'MedNormIntStatus': FieldType.STRING,
    'MedNormExtStatus': FieldType.STRING,
    'RowCheckStatus': FieldType.STRING,
    'CrossPlateMedNormIntScaleFactor': FieldType.DECIMAL,
    'InstrumentType': FieldType.STRING,
    'Flowcell': FieldType.STRING,
    'RunYieldDemux': FieldType.INTEGER,
    'RunYieldQ30Demux': FieldType.INTEGER,
    'RunQ30WeightedMean': FieldType.DECIMAL,
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


# ---------------------------------------------------------------------------
# Field-value validation (used during v2.0 read)
# ---------------------------------------------------------------------------


def _is_valid_iso8601_date(val: str) -> bool:
    """Return True if *val* is a valid ISO 8601 date or datetime string.

    Accepts ``YYYY-MM-DD`` and ``YYYY-MM-DDTHH:MM:SS[Z]``.  Uses
    ``datetime.fromisoformat()`` so calendar validity is enforced (e.g.
    ``2026-02-30`` correctly returns False).

    The trailing ``Z`` suffix is normalised to ``+00:00`` before parsing
    because ``fromisoformat()`` only accepts ``Z`` natively on Python 3.11+,
    while this project requires Python 3.9+.
    """
    normalised = val[:-1] + '+00:00' if val.endswith('Z') else val
    for parser in (date.fromisoformat, datetime.fromisoformat):
        try:
            parser(normalised)
            return True
        except ValueError:
            continue
    return False


def parse_file(
    f: Union[str, io.TextIOWrapper], compatibility_mode: bool = False
) -> Tuple[List[List[float]], Dict[str, List[str]], Dict[str, List], Dict[str, str]]:
    """Returns component pieces of an adat given an adat file object.

    Parameters
    ----------
    f : Union[str, io.TextIOWrapper]
        An open adat file object or path to an adat file.
    compatibility_mode : bool
        If True, the function will attempt to parse the file where header metadata values are strings.

    Returns
    -------
    rfu_matrix : List[List[float]]
        An nSample x nSomamer matrix of the RFU data (by row) where each sub-array corresponds to a sample.

    row_metadata : Dict[str, List[str]]
        A dictionary of each column of the row metadata where the key-value
        pairs are column-name and an array of each sample's corresponding metadata

    column_metadata : Dict[str, List]
        A dictionary of each row of the adat column metadata where the key-value pairs are
        row-name and an array of each somamer's corresponding metadata (mixed types).

    header_metadata : Dict[str, str]
        A dictionary of each row of the header_metadata corresponds to a key-value pair.
    """
    _opened_here = False
    if isinstance(f, str):
        f = open(f, 'r')
        _opened_here = True
    elif not hasattr(f, 'read'):
        raise AdatReadError('File must be a string or file-like object.')

    current_section = None

    header_metadata = {}
    column_metadata = {}
    row_metadata = {}
    rfu_matrix = []

    matrix_depth = 0

    try:
        reader = csv.reader(f, delimiter='\t')
        for line in reader:
            # Check for trailing Nones
            for index, cell in enumerate(reversed(line)):
                if cell:
                    break
                del line[-1]

            # If we see a new section set which portion of the adat we are in & continue to next line
            if '^HEADER' in line[0]:
                current_section = 'HEADER'
                continue
            elif '^TABLE_BEGIN' in line[0]:
                current_section = 'TABLE'
                continue
            elif '^COL_DATA' in line[0]:
                current_section = 'COL_DATA'
                continue
            elif '^ROW_DATA' in line[0]:
                current_section = 'ROW_DATA'
                continue

            # Parse the data according to which section of the adat we're reading

            if current_section == 'HEADER':
                # Not every key in the header has a value
                if len(line) == 1:
                    header_metadata[line[0]] = ''
                # Should be the typical case
                elif len(line) == 2 and compatibility_mode:
                    header_metadata[line[0]] = line[1]
                elif len(line) == 2 and not compatibility_mode:
                    try:
                        header_metadata[line[0]] = json.loads(line[1])
                        if type(header_metadata[line[0]]) != dict:
                            header_metadata[line[0]] = line[1]
                    except json.JSONDecodeError:
                        header_metadata[line[0]] = line[1]
                    # If we have the report config section, check to see if it was loaded as a dict
                    if line[0] == "ReportConfig" and type(header_metadata[line[0]]) != dict:
                        warnings.warn(
                            'Malformed ReportConfig section in header.  Setting to an empty dictionary.'
                        )
                        header_metadata[line[0]] = {}
                # More than 2 values to a key should never ever happen
                else:
                    raise AdatReadError('Unexpected size of header: ' + '|'.join(line))

            elif current_section == 'COL_DATA':
                # Get the height of the column metadata section & skip the rest of the section
                col_metadata_length = len(line)
                current_section = None

            elif current_section == 'ROW_DATA':
                # Get the index of the end of the row metadata section & skip the rest of the section
                row_metadata_offset = len(line) - 1
                current_section = None

            elif current_section == 'TABLE':
                # matrix_depth is used to identify if we are in the column
                # metadata section or the row metadata/rfu section
                matrix_depth += 1

                # Column Metadata Section
                if matrix_depth < col_metadata_length:
                    column_metadata_name = line[row_metadata_offset]
                    column_metadata_data = line[row_metadata_offset + 1 :]

                    if column_metadata_name == 'SeqId' and re.match(
                        r'\d{3,}-\d{1,3}_\d+', column_metadata_data[0]
                    ):
                        warnings.warn(
                            'V3 style seqIds (i.e., 12345-6_7). Converting to V4 Style. The adat file writer has an option to write using the V3 style'
                        )
                        seq_id_data = [x.split('_')[0] for x in column_metadata_data]
                        version_data = [x.split('_')[1] for x in column_metadata_data]
                        column_metadata[column_metadata_name] = seq_id_data
                        column_metadata['SeqIdVersion'] = version_data
                    else:
                        column_metadata[column_metadata_name] = column_metadata_data

                # Perform a check to ensure all column metadata is the same length and if not, extend it to the maximum length
                col_meta_lengths = [len(values) for values in column_metadata.values()]
                if len(set(col_meta_lengths)) > 1:
                    max_length = max(col_meta_lengths)
                    for name, values in column_metadata.items():
                        if len(values) == max_length:
                            continue
                        warnings.warn(f'Adding empty values to column metadata: "{name}"')
                        n_missing_elements = max_length - len(values)
                        append_array = [''] * n_missing_elements
                        new_values = values + append_array
                        column_metadata[name] = new_values

                # Row Metadata Titles
                elif matrix_depth == col_metadata_length:
                    row_metadata_names = line[:row_metadata_offset]
                    row_metadata = {name: [] for name in row_metadata_names}

                # Row Metadata & RFU Section
                elif matrix_depth > col_metadata_length:
                    # Store in row metadata into dictionary
                    row_metadata_data = line[:row_metadata_offset]
                    # Check for missing metadata and handle it
                    if len(row_metadata_data) < len(row_metadata_names):
                        missing_count = len(row_metadata_names) - len(row_metadata_data)
                        logging.warning(
                            f"Row metadata has {missing_count} missing values. "
                            f"Filling missing entries with empty strings."
                        )
                        row_metadata_data = list(row_metadata_data) + [""] * missing_count
                    for name, data in zip(row_metadata_names, row_metadata_data):
                        row_metadata[name].append(data)
                    # Store the RFU data
                    rfu_row_data = line[row_metadata_offset + 1 :]
                    converted_rfu_row_data = [
                        float('nan') if v == 'NA' else float(v) for v in rfu_row_data
                    ]
                    rfu_matrix.append(converted_rfu_row_data)
    finally:
        if _opened_here:
            f.close()

    return rfu_matrix, row_metadata, column_metadata, header_metadata


def read_file(filepath: str) -> Adat:
    """DEPRECATED: SEE somadata.read_adat

    WILL BE REMOVED IN A FUTURE RELEASE
    """
    logging.warning(
        'THIS FUNCTION IS DEPRECATED AND WILL BE REMOVED IN A FUTURE RELEASE.\n PLEASE USE `somadata.read_adat` instead.'
    )
    return read_adat(filepath)


def _validate_v2_field_values(
    row_metadata: Dict[str, List],
    column_metadata: Dict[str, List],
) -> None:
    """Emit warnings for v2.0 field values that violate their declared type.

    Called after parsing when ``FileVersion == "2.0"``.  Violations produce
    ``warnings.warn`` calls (not exceptions) to remain lenient during early
    adoption of the v2.0 format.

    Detection is vectorized using pandas/numpy so that large COL_DATA sections
    (thousands of analytes) are checked efficiently.  A single warning is
    emitted per violating field, listing all offending indices, rather than
    one warning per value.

    Checks performed per FieldType:

    - **Integer** — value must be a whole-number integer (or a recognised
      missing-value sentinel: empty string, ``"NA"``, or ``"N/A"``).
    - **Decimal** — value must be parseable as a float (or missing).
    - **Date** — value must be a valid ISO 8601 date/datetime (or missing).
    - **JSON** — value must be parseable as valid JSON (or be empty/missing).
    - **String** — value must be ≤ 1 024 characters.

    Parameters
    ----------
    row_metadata : dict
        ``{field_name: [value, ...]}`` from ``parse_file``.
    column_metadata : dict
        ``{field_name: [value, ...]}`` from ``parse_file``.
    """
    _MISSING = {'', 'na', 'n/a'}

    def _check_section(
        metadata: Dict[str, List],
        type_fn,
        section: str,
    ) -> None:
        for field_name, values in metadata.items():
            if not values:
                continue

            ftype = type_fn(field_name)
            series = pd.Series(values, dtype=object).fillna('').astype(str)
            missing_mask = series.str.strip().str.lower().isin(_MISSING)
            non_missing = series[~missing_mask]

            if non_missing.empty:
                continue

            bad_indices: list[int] = []

            if ftype is FieldType.INTEGER:
                numeric = pd.to_numeric(non_missing, errors='coerce')
                bad_mask = numeric.isna() | (numeric % 1 != 0)
                bad_indices = list(non_missing.index[bad_mask])

            elif ftype is FieldType.DECIMAL:
                numeric = pd.to_numeric(non_missing, errors='coerce')
                bad_indices = list(non_missing.index[numeric.isna()])

            elif ftype is FieldType.DATE:
                valid_mask = non_missing.str.strip().map(_is_valid_iso8601_date)
                bad_indices = list(non_missing.index[~valid_mask])

            elif ftype is FieldType.JSON:

                def _invalid_json(v: str) -> bool:
                    try:
                        json.loads(v)
                        return False
                    except (json.JSONDecodeError, ValueError):
                        return True

                bad_mask = non_missing.map(_invalid_json)
                bad_indices = list(non_missing.index[bad_mask])

            elif ftype is FieldType.STRING:
                bad_mask = non_missing.str.len() > 1024
                bad_indices = list(non_missing.index[bad_mask])

            if bad_indices:
                sample = bad_indices[:5]
                suffix = ', ...' if len(bad_indices) > 5 else ''
                logger.warning(
                    'v2.0 type violation in %s field "%s": '
                    'expected %s, found %d invalid value(s) at indices %s%s.',
                    section,
                    field_name,
                    ftype.value,
                    len(bad_indices),
                    sample,
                    suffix,
                )

    _check_section(row_metadata, v2_row_field_type, '^ROW_DATA')
    _check_section(column_metadata, v2_col_field_type, '^COL_DATA')

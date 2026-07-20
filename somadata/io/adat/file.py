from __future__ import annotations

import csv
import io
import json
import logging
import re
import warnings
from datetime import date, datetime
from importlib.metadata import version
from typing import Dict, List, Tuple, Union

import pandas as pd

from somadata import Adat
from somadata.io.adat.errors import AdatReadError, AdatWriteError
from somadata.io.adat.v2_fields import FieldType
from somadata.io.adat.v2_fields import (
    serialize_header_value_v2 as _serialize_header_value_v2,
)
from somadata.io.adat.v2_fields import v2_col_field_type as _v2_col_field_type
from somadata.io.adat.v2_fields import v2_row_field_type as _v2_row_field_type
from somadata.io.adat.v2_fields import (
    validate_v2_header_fields as _validate_v2_header_fields,
)
from somadata.tools.math import jround

logger = logging.getLogger(__name__)


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
    if type(f) == str:
        f = open(f, 'r')
    elif not hasattr(f, 'read'):
        raise AdatReadError('File must be a string or file-like object.')

    current_section = None

    header_metadata = {}
    column_metadata = {}
    row_metadata = {}
    rfu_matrix = []

    matrix_depth = 0

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
                converted_rfu_row_data = list(map(float, rfu_row_data))
                rfu_matrix.append(converted_rfu_row_data)

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

    _check_section(row_metadata, _v2_row_field_type, '^ROW_DATA')
    _check_section(column_metadata, _v2_col_field_type, '^COL_DATA')


def read_adat(path_or_buf: Union[str, io.TextIOWrapper], *args, **kwargs) -> Adat:
    """Returns an Adat from the filepath/name.

    For v2.0 ADATs (``FileVersion == "2.0"``), field values in ``^ROW_DATA``
    and ``^COL_DATA`` are validated against their declared v2.0 types.
    Type mismatches are logged as warnings rather than raising errors.

    Parameters
    ----------
    path_or_buf : Union[str, io.TextIOWrapper]
        Path or buffer that the file will be read from

    Examples
    --------
    >>> adat = read_adat('path/to/file.adat')

    Returns
    -------
    adat : Adat
    """
    rfu_matrix, row_metadata, column_metadata, header_metadata = parse_file(
        path_or_buf, *args, **kwargs
    )

    if header_metadata.get('FileVersion') == '2.0':
        _validate_v2_field_values(row_metadata, column_metadata)

    return Adat.from_features(
        rfu_matrix=rfu_matrix,
        row_metadata=row_metadata,
        column_metadata=column_metadata,
        header_metadata=header_metadata,
    )


def write_adat(
    adat,
    f: io.TextIOWrapper,
    round_rfu: bool = True,
    convert_to_v3_seq_ids: bool = False,
) -> None:
    """Write this Adat to an adat format data source.

    Parameters
    ----------
    adat : Adat
        Adat Pandas dataframe to be written.

    f : io.TextIOWrapper
        The file path or open file object to write to.

    round_rfu : bool
        Rounds the RFU matrix to one decimal place if True,
        otherwise leaves the matrix as-is. (Default = True)

    convert_to_v3_seq_ids : bool
        Combines the column metadata for SeqId and
        SeqIdVersion to the V3 style (12345-6_7).  Ignored for v2.0 ADATs.

    Examples
    --------
    >>> import somadata as sd
    >>> adat = sd.read_adat('path/to/file.adat')
    >>> sd.write_adat(adat, 'path/to/out/filename.adat')
    >>> sd.write_adat(adat, 'path/to/out/filename.adat', round_rfu=False)

    Returns
    -------
    None
    """
    if adat.header_metadata.get('FileVersion') == '2.0':
        _write_adat_v2(adat, f, round_rfu=round_rfu)
    else:
        _write_adat(
            adat, f, round_rfu=round_rfu, convert_to_v3_seq_ids=convert_to_v3_seq_ids
        )


def _write_adat(
    adat,
    f: io.TextIOWrapper,
    round_rfu: bool = True,
    convert_to_v3_seq_ids: bool = False,
) -> None:
    """Write a pre-v2.0 ADAT file.

    Parameters
    ----------
    adat : Adat
        Adat Pandas dataframe to be written.
    f : io.TextIOWrapper
        Open writable file object.
    round_rfu : bool
        Round RFU values to one decimal place when True (default).
    convert_to_v3_seq_ids : bool
        Combine SeqId and SeqIdVersion columns into V3 style (12345-6_7).
    """
    # Add version number to header_metadata.  If the field already exists, append to it.
    pkg_version = 'SomaData_' + version('somadata')
    if '!GeneratedBy' not in adat.header_metadata:
        adat.header_metadata['!GeneratedBy'] = pkg_version
    elif pkg_version not in adat.header_metadata['!GeneratedBy']:
        adat.header_metadata['!GeneratedBy'] += ', ' + pkg_version

    # Create COL_DATA & ROW_DATA sections
    column_names = adat.columns.names
    column_types = ['String' for name in column_names]

    row_names = adat.index.names
    row_types = ['String' for name in row_names]

    # Start writing the adat using the csv writer
    writer = csv.writer(f, delimiter='\t', lineterminator='\r\n')

    # Checksum must be added with blank value
    writer.writerow(['!Checksum'])

    # Write HEADER section
    writer.writerow(['^HEADER'])
    for row in adat.header_metadata.items():
        # We need to handle the reportconfig in a special way since it has double quotes
        if row[0] == 'ReportConfig' and type(row[1]) == dict:
            f.write(row[0] + '\t' + json.dumps(row[1], separators=(',', ':')) + '\r\n')
        else:
            writer.writerow([x for x in row if x is not None])

    # Write COL_DATA section
    writer.writerow(['^COL_DATA'])
    writer.writerow(['!Name'] + column_names)
    writer.writerow(['!Type'] + column_types)

    # Write ROW_DATA section
    writer.writerow(['^ROW_DATA'])
    writer.writerow(['!Name'] + row_names)
    writer.writerow(['!Type'] + row_types)

    # Begin the main section of the adat
    writer.writerow(['^TABLE_BEGIN'])

    # Write the column metadata
    column_offset = [None for i in range(len(row_names))]
    for column_name in column_names:
        # Prep the data
        column_data = adat.columns.get_level_values(column_name)

        # Check if we are converting to the V3 style of adat seqIds
        if column_name == 'SeqId' and convert_to_v3_seq_ids:
            version_data = adat.columns.get_level_values('SeqIdVersion')
            column_data = [
                seq_id + '_' + version
                for seq_id, version in zip(column_data, version_data)
            ]
        if column_name == 'SeqIdVersion' and convert_to_v3_seq_ids:
            continue

        # Create and write the row
        row = []
        row += column_offset
        row += [column_name]
        row += list(column_data)
        writer.writerow(row)

    # Write the row metadata column titles.  Additional tabs added to conform to PX adat structure.
    extra_nones = len(adat.columns.get_level_values(column_names[0])) + 1
    writer.writerow(row_names + [None for x in range(extra_nones)])

    # Write the row metadata and rfu matrix simultaneously
    for i, rfu_row in enumerate(adat.values):
        # Prep the data
        row_metadata = [
            adat.index.get_level_values(row_name)[i] for row_name in row_names
        ]
        if round_rfu:
            rfu_row = [jround(rfu, 1) for rfu in rfu_row]
        else:
            rfu_row = list(rfu_row)

        # Create and write the row
        row = []
        row += row_metadata
        row += [None]
        row += rfu_row
        writer.writerow(row)


def _write_adat_v2(adat, f: io.TextIOWrapper, round_rfu: bool = True) -> None:
    """Write an ADAT v2.0 file.

    Implements the v2.0 format rules:
    - No ``!Checksum`` line
    - No ``!`` prefix on Name/Type rows in ^COL_DATA / ^ROW_DATA
    - JSON header values serialized as single-line minified JSON
    - Sections in order: ^HEADER, ^COL_DATA, ^ROW_DATA, ^TABLE_BEGIN
    - Validates the closed header field set before writing

    Parameters
    ----------
    adat : Adat
        Adat with ``FileVersion == "2.0"`` in its header metadata.
    f : io.TextIOWrapper
        Open writable file object.
    round_rfu : bool
        Round RFU values to one decimal place when True (default).
    """
    if not _validate_v2_header_fields(adat.header_metadata):
        raise AdatWriteError(
            'v2.0 ADAT header metadata is not compliant with the closed field set '
            'See logged warnings above for details.'
        )

    writer = csv.writer(f, delimiter='\t', lineterminator='\r\n')

    # --- ^HEADER ---
    writer.writerow(['^HEADER'])
    for key, value in adat.header_metadata.items():
        serialized = _serialize_header_value_v2(key, value)
        if serialized:
            f.write(key + '\t' + serialized + '\r\n')
        else:
            writer.writerow([key])

    # --- ^COL_DATA ---
    column_names = list(adat.columns.names)
    column_types = [_v2_col_field_type(name) for name in column_names]

    writer.writerow(['^COL_DATA'])
    writer.writerow(['Name'] + column_names)
    writer.writerow(['Type'] + column_types)

    # --- ^ROW_DATA ---
    row_names = list(adat.index.names)
    row_types = [_v2_row_field_type(name) for name in row_names]

    writer.writerow(['^ROW_DATA'])
    writer.writerow(['Name'] + row_names)
    writer.writerow(['Type'] + row_types)

    # --- ^TABLE_BEGIN ---
    writer.writerow(['^TABLE_BEGIN'])

    # Write column metadata rows (one row per COL_DATA field)
    column_offset = [None] * len(row_names)
    for column_name in column_names:
        column_data = list(adat.columns.get_level_values(column_name))
        writer.writerow(column_offset + [column_name] + column_data)

    # Write the row metadata header line
    extra_nones = len(adat.columns.get_level_values(column_names[0])) + 1
    writer.writerow(list(row_names) + [None] * extra_nones)

    # Write row metadata + RFU data
    for i, rfu_row in enumerate(adat.values):
        row_meta = [adat.index.get_level_values(name)[i] for name in row_names]
        if round_rfu:
            rfu_values = [jround(v, 1) for v in rfu_row]
        else:
            rfu_values = list(rfu_row)
        writer.writerow(row_meta + [None] + rfu_values)

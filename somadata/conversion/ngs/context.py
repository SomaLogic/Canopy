"""NGSConversionContext — shared state for NGS v1.x → v2.0 conversion."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from somadata.conversion._helpers import lookup_header

if TYPE_CHECKING:
    from somadata.adat import Adat


def _safe_int(val: str) -> int:
    """Safely parse an integer from a string, returning 0 on failure."""
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


def _safe_float(val: str) -> float:
    """Safely parse a float from a string, returning 0.0 on failure."""
    try:
        return float(val) if val else 0.0
    except (ValueError, TypeError):
        return 0.0


@dataclasses.dataclass
class NGSConversionContext:
    """Shared state across header / col / row NGS conversion steps.

    Parameters
    ----------
    source_adat_id : str or None
        The legacy ``AdatId`` value extracted from the source header.
        May be ``None`` if the source ADAT lacks an AdatId.
    dpq_version : str
        The legacy ``Version`` header value (DPQ software version);
        becomes ``SoftwareVersion`` in the output ROW_DATA.
    sequencing_run_id : str
        The legacy ``RunId`` header value; becomes ``SequencingRunId``
        in the output ROW_DATA.
    instrument_type : str
        The sequencing instrument type (e.g., ``'NovaSeq6000'``).
        Moved from header to ROW_DATA in v2.0.
    flowcell : str
        The flowcell identifier. Moved from header to ROW_DATA in v2.0.
    yield_demux : int or None
        Demultiplexed yield value. Moved from header to ROW_DATA in v2.0.
        ``None`` when the source ADAT lacks this field (e.g. multi-run DPQ outputs).
    yield_q30_demux : int or None
        Q30 demultiplexed yield value. Moved from header to ROW_DATA in v2.0.
        ``None`` when absent.
    q30_weighted_mean : float or None
        Weighted mean Q30 score. Moved from header to ROW_DATA in v2.0.
        ``None`` when absent.
    plate_ids : list[str]
        List of unique PlateId values present in the source ADAT.
        Used for plate-keyed JSON field consolidation.
    process_steps : str
        Raw comma-separated ProcessSteps string from header.
        Converted to JSON in v2.0 header.
    process_steps_id : str
        The JSON key assigned to the ProcessSteps list (always ``'1'`` for
        single-input conversions).
    source_file_id : str
        The JSON key assigned to the SourceFile JSON entry.
    source_file_md5sum : str or None
        MD5 checksum of the source ADAT file, if available. Used as the
        second-priority identifier when the source ADAT lacks an AdatId.
        When absent, an in-memory checksum is computed and prefixed with
        ``"mem."`` to distinguish it from a file-based checksum.
    matrix : str
        The study matrix type (e.g., ``'Plasma'``, ``'Serum'``), derived from
        the ``StudyMatrix`` header field.  Used to resolve bare ``DRC_Level``
        column fields to ``DRCLevel_<Matrix>_NGS`` in the output.
    """

    source_adat_id: str | None = None
    dpq_version: str = ''
    sequencing_run_id: str = ''
    instrument_type: str = ''
    flowcell: str = ''
    yield_demux: int | None = None
    yield_q30_demux: int | None = None
    q30_weighted_mean: float | None = None
    plate_ids: list[str] = dataclasses.field(default_factory=list)
    process_steps: str = ''
    process_steps_id: str = '1'
    source_file_id: str = '1'
    source_file_md5sum: str | None = None
    matrix: str = ''

    @classmethod
    def from_adat(
        cls, adat: Adat, source_file_md5sum: str | None = None
    ) -> NGSConversionContext:
        """Build a context by extracting values from *adat.header_metadata*.

        Parameters
        ----------
        adat : Adat
            The source NGS ADAT.
        source_file_md5sum : str or None, optional
            MD5 checksum of the source ADAT file, if available.

        Returns
        -------
        NGSConversionContext

        Examples
        --------
        >>> ctx = NGSConversionContext.from_adat(ngs_adat)
        >>> ctx.dpq_version
        '4.0.1'
        >>> ctx.sequencing_run_id
        'RUN12345'
        """
        hdr = getattr(adat, 'header_metadata', {})

        # Extract PlateIds from row metadata
        plate_ids = []
        if hasattr(adat, 'index'):
            # Get PlateId from multi-index if present
            if hasattr(adat.index, 'names') and 'PlateId' in adat.index.names:
                plate_ids = sorted(set(adat.index.get_level_values('PlateId')))
            elif hasattr(adat, 'PlateId'):
                # Fallback: try as a column accessor
                try:
                    plate_ids = sorted(set(adat.PlateId))
                except (AttributeError, KeyError):
                    pass

        adat_id = lookup_header(hdr, 'AdatId')

        raw_yield_demux = lookup_header(hdr, 'YieldDemux')
        raw_yield_q30_demux = lookup_header(hdr, 'YieldQ30Demux')
        raw_q30_weighted_mean = lookup_header(hdr, 'Q30WeightedMean')

        return cls(
            source_adat_id=adat_id if adat_id else None,
            dpq_version=lookup_header(hdr, 'Version'),
            sequencing_run_id=lookup_header(hdr, 'RunId'),
            instrument_type=lookup_header(hdr, 'InstrumentType'),
            flowcell=lookup_header(hdr, 'Flowcell'),
            yield_demux=_safe_int(raw_yield_demux) if raw_yield_demux else None,
            yield_q30_demux=_safe_int(raw_yield_q30_demux) if raw_yield_q30_demux else None,
            q30_weighted_mean=_safe_float(raw_q30_weighted_mean) if raw_q30_weighted_mean else None,
            plate_ids=plate_ids,
            process_steps=lookup_header(hdr, 'ProcessSteps'),
            source_file_md5sum=source_file_md5sum,
            matrix=lookup_header(hdr, 'StudyMatrix'),
        )

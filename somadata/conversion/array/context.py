"""ArrayConversionContext — shared state for array v1.x → v2.0 conversion."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from somadata.conversion._helpers import lookup_header

if TYPE_CHECKING:
    from somadata.adat import Adat


@dataclasses.dataclass
class ArrayConversionContext:
    """Shared state across header / col / row array conversion steps.

    Parameters
    ----------
    source_adat_id : str
        The legacy ``AdatId`` value extracted from the source header.
    generated_by : str
        The legacy ``GeneratedBy`` header value; becomes ``SoftwareVersion``
        in the output ROW_DATA.
    process_steps_id : str
        The JSON key assigned to the ProcessSteps list (always ``'1'`` for
        single-input conversions).
    report_config_id : str
        The JSON key assigned to the ReportConfig value.
    source_file_id : str
        The JSON key assigned to the SourceFile JSON entry.
    created_date : str
        The legacy ``CreatedDate`` header value; used as a fallback for
        blank ``PlateRunDate`` values in ROW_DATA.
    source_file_md5sum : str or None
        MD5 checksum of the source ADAT file, if available. Used as the
        second-priority identifier when the source ADAT lacks an AdatId.
        When absent, an in-memory checksum is computed and prefixed with
        ``"mem."`` to distinguish it from a file-based checksum.
    """

    source_adat_id: str = ''
    generated_by: str = ''
    process_steps_id: str = '1'
    report_config_id: str = '1'
    source_file_id: str = '1'
    created_date: str = ''
    source_file_md5sum: str | None = None
    calibrator_id: str = ''

    @classmethod
    def from_adat(
        cls, adat: Adat, source_file_md5sum: str | None = None
    ) -> ArrayConversionContext:
        """Build a context by extracting values from *adat.header_metadata*.

        Parameters
        ----------
        adat : Adat
            The source array ADAT.
        source_file_md5sum : str or None, optional
            MD5 checksum of the source ADAT file, if available.

        Returns
        -------
        ArrayConversionContext
        """
        hdr = getattr(adat, 'header_metadata', {})
        return cls(
            source_adat_id=lookup_header(hdr, 'AdatId'),
            generated_by=lookup_header(hdr, 'GeneratedBy'),
            created_date=lookup_header(hdr, 'CreatedDate'),
            calibrator_id=lookup_header(hdr, 'CalibratorId'),
            source_file_md5sum=source_file_md5sum,
        )

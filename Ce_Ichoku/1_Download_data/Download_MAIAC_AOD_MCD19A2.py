#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download MODIS Collection 6.1 MCD19A2 MAIAC AOD HDF granules using
NASA's Common Metadata Repository (CMR).

The script:
  1. Finds the MCD19A2 Version 061 collection in CMR.
  2. Searches daily granules for selected years and months.
  3. Keeps only the requested MODIS sinusoidal tiles.
  4. Downloads each HDF file using Earthdata Login credentials in ~/.netrc.
  5. Skips completed files and resumes interrupted downloads through .part files.

Required package:
    conda install requests
or:
    python -m pip install requests

Earthdata Login setup (~/.netrc):
    machine urs.earthdata.nasa.gov
        login YOUR_EARTHDATA_USERNAME
        password YOUR_EARTHDATA_PASSWORD

Protect the credential file:
    chmod 600 ~/.netrc
"""

from __future__ import annotations

import calendar
import re
import time
from datetime import date
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import requests


# ============================================================
# USER SETTINGS
# ============================================================
START_YEAR = 2015
END_YEAR = 2020

# Download only July through November.
KEEP_MONTHS = [7, 8, 9, 10, 11]

# Requested MODIS sinusoidal tiles in Indonesia!!!
# h27-h32 and v08-v09, matching the original Perl script.
HORIZONTAL_TILES = range(27, 33)
VERTICAL_TILES = range(8, 10)
TILES = {
    f"h{horizontal:02d}v{vertical:02d}"
    for horizontal in HORIZONTAL_TILES
    for vertical in VERTICAL_TILES
}

OUTPUT_ROOT = Path("/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/MAIAC_AOD_Inni")

# Set True to download completed files again.
OVERWRITE = False

# Request and retry settings.
REQUEST_TIMEOUT_SECONDS = 120
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
MAX_RETRIES = 5
RETRY_WAIT_SECONDS = 20

# NASA CMR settings.
CMR_ROOT = "https://cmr.earthdata.nasa.gov/search"
SHORT_NAME = "MCD19A2"
VERSION = "061"
PROVIDER = "LPCLOUD"
CMR_PAGE_SIZE = 2000

USER_AGENT = (
    "MCD19A2-Python-Downloader/1.0 "
    "(contact: replace-with-your-email@example.com)"
)


# ============================================================
# VALIDATION
# ============================================================
def validate_settings() -> None:
    if START_YEAR > END_YEAR:
        raise ValueError("START_YEAR must be less than or equal to END_YEAR.")

    if not KEEP_MONTHS:
        raise ValueError("KEEP_MONTHS cannot be empty.")

    invalid_months = [m for m in KEEP_MONTHS if m < 1 or m > 12]
    if invalid_months:
        raise ValueError(
            f"KEEP_MONTHS contains invalid values: {invalid_months}"
        )

    if not TILES:
        raise ValueError("At least one MODIS tile must be requested.")

    if MAX_RETRIES < 1:
        raise ValueError("MAX_RETRIES must be at least 1.")


# ============================================================
# SESSION AND AUTHENTICATION
# ============================================================
def create_session() -> requests.Session:
    """
    Create a session that uses ~/.netrc automatically.

    requests reads ~/.netrc when trust_env is True, which is the default.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.trust_env = True
    return session


# ============================================================
# DATE HELPERS
# ============================================================
def iter_requested_dates() -> Iterator[date]:
    """Yield every requested date in chronological order."""
    for year in range(START_YEAR, END_YEAR + 1):
        for month in sorted(set(KEEP_MONTHS)):
            last_day = calendar.monthrange(year, month)[1]
            for day in range(1, last_day + 1):
                yield date(year, month, day)


# ============================================================
# CMR HELPERS
# ============================================================
def request_json(
    session: requests.Session,
    url: str,
    params: dict[str, object],
) -> dict:
    """Request JSON with retries and useful error messages."""
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()

        except (requests.RequestException, ValueError) as error:
            last_error = error
            print(
                f"  CMR request attempt {attempt}/{MAX_RETRIES} failed: "
                f"{error}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)

    raise RuntimeError(
        f"CMR request failed after {MAX_RETRIES} attempts."
    ) from last_error


def find_collection_concept_id(
    session: requests.Session,
) -> str:
    """Find the CMR collection concept ID for MCD19A2 Version 061."""
    url = f"{CMR_ROOT}/collections.json"
    params = {
        "short_name": SHORT_NAME,
        "version": VERSION,
        "provider": PROVIDER,
        "page_size": 100,
    }

    data = request_json(session, url, params)
    entries = data.get("feed", {}).get("entry", [])

    exact_matches = [
        entry
        for entry in entries
        if entry.get("short_name") == SHORT_NAME
        and str(entry.get("version_id")) == VERSION
        and entry.get("data_center") == PROVIDER
    ]

    matches = exact_matches or entries

    if not matches:
        raise RuntimeError(
            f"CMR did not return a collection for "
            f"{SHORT_NAME} Version {VERSION} from {PROVIDER}."
        )

    if len(matches) > 1:
        print(
            "Warning: CMR returned multiple matching collections; "
            "using the first result."
        )

    concept_id = matches[0].get("id")
    if not concept_id:
        raise RuntimeError(
            "The matching CMR collection does not contain a concept ID."
        )

    return str(concept_id)


def extract_tile(filename: str) -> str | None:
    """Extract a MODIS tile name such as h27v08 from a granule filename."""
    match = re.search(r"\.(h\d{2}v\d{2})\.", filename)
    return match.group(1) if match else None


def is_hdf_data_link(link: dict) -> bool:
    """Return True for a downloadable HDF data link."""
    href = str(link.get("href", ""))
    rel = str(link.get("rel", "")).lower()
    title = str(link.get("title", "")).lower()
    link_type = str(link.get("type", "")).lower()

    if not href:
        return False

    clean_path = urlparse(href).path.lower()
    if not clean_path.endswith(".hdf"):
        return False

    rejected_text = f"{href} {rel} {title} {link_type}".lower()
    rejected_terms = (
        "opendap",
        "browse",
        "metadata",
        "documentation",
        "s3credentials",
    )
    if any(term in rejected_text for term in rejected_terms):
        return False

    # CMR data links normally use a relation ending in /data#.
    # Keep an HDF link even if a provider omits this relation.
    return not rel or rel.endswith("/data#") or "data#" in rel


def choose_download_url(entry: dict) -> str | None:
    """
    Select the preferred HTTPS HDF link from one CMR granule entry.

    HTTPS links are preferred over S3 URLs because requests can use
    Earthdata Login credentials from ~/.netrc.
    """
    candidates = [
        str(link["href"])
        for link in entry.get("links", [])
        if is_hdf_data_link(link)
    ]

    if not candidates:
        return None

    https_candidates = [
        url for url in candidates if url.lower().startswith("https://")
    ]
    return (https_candidates or candidates)[0]


def find_daily_granules(
    session: requests.Session,
    collection_concept_id: str,
    current_date: date,
) -> list[tuple[str, str, str]]:
    """
    Find requested granules for one date.

    Returns:
        A sorted list of (tile, filename, download_url).
    """
    start_time = current_date.strftime("%Y-%m-%dT00:00:00Z")
    end_time = current_date.strftime("%Y-%m-%dT23:59:59Z")

    url = f"{CMR_ROOT}/granules.json"
    page_number = 1
    results: dict[str, tuple[str, str, str]] = {}

    while True:
        params = {
            "concept_id": collection_concept_id,
            "temporal": f"{start_time},{end_time}",
            "downloadable": "true",
            "page_size": CMR_PAGE_SIZE,
            "page_num": page_number,
            "sort_key[]": "producer_granule_id",
        }

        data = request_json(session, url, params)
        entries = data.get("feed", {}).get("entry", [])

        if not entries:
            break

        for entry in entries:
            filename = str(
                entry.get("producer_granule_id")
                or entry.get("title")
                or ""
            )

            tile = extract_tile(filename)
            if tile not in TILES:
                continue

            download_url = choose_download_url(entry)
            if not download_url:
                print(
                    f"  Warning: no downloadable HDF URL found for "
                    f"{filename}"
                )
                continue

            # Keying by filename removes any duplicate CMR records.
            results[filename] = (tile, filename, download_url)

        if len(entries) < CMR_PAGE_SIZE:
            break

        page_number += 1

    return sorted(
        results.values(),
        key=lambda item: (item[0], item[1]),
    )


# ============================================================
# DOWNLOAD HELPERS
# ============================================================
def format_bytes(number_of_bytes: int | None) -> str:
    if number_of_bytes is None:
        return "unknown size"

    value = float(number_of_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024.0

    return f"{value:.1f} TB"


def download_file(
    session: requests.Session,
    url: str,
    destination: Path,
) -> bool:
    """
    Download one file.

    Returns True if downloaded and False if an existing file was skipped.
    Interrupted downloads are stored as *.part and resumed when supported.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not OVERWRITE:
        print(f"    Exists, skipping: {destination.name}")
        return False

    partial_file = destination.with_suffix(destination.suffix + ".part")

    if OVERWRITE:
        destination.unlink(missing_ok=True)
        partial_file.unlink(missing_ok=True)

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        resume_from = (
            partial_file.stat().st_size
            if partial_file.exists()
            else 0
        )

        headers = {}
        if resume_from > 0:
            headers["Range"] = f"bytes={resume_from}-"

        try:
            with session.get(
                url,
                headers=headers,
                stream=True,
                allow_redirects=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                # An expired redirect or missing credentials may return an
                # HTML login page rather than an HDF file.
                response.raise_for_status()

                content_type = response.headers.get(
                    "Content-Type", ""
                ).lower()

                if "text/html" in content_type:
                    raise RuntimeError(
                        "The server returned HTML instead of an HDF file. "
                        "Check your Earthdata Login credentials in ~/.netrc "
                        "and confirm that you have accepted the LP DAAC "
                        "data-use agreement."
                    )

                # If the server ignored Range and sent HTTP 200, start over
                # rather than appending a complete file to a partial file.
                resumed = resume_from > 0 and response.status_code == 206
                if resume_from > 0 and not resumed:
                    resume_from = 0
                    partial_file.unlink(missing_ok=True)

                write_mode = "ab" if resumed else "wb"

                remaining_size_text = response.headers.get(
                    "Content-Length"
                )
                remaining_size = (
                    int(remaining_size_text)
                    if remaining_size_text
                    else None
                )
                expected_final_size = (
                    resume_from + remaining_size
                    if remaining_size is not None
                    else None
                )

                action = "Resuming" if resumed else "Downloading"
                print(
                    f"    {action}: {destination.name} "
                    f"({format_bytes(expected_final_size)})"
                )

                with partial_file.open(write_mode) as output:
                    for chunk in response.iter_content(
                        chunk_size=DOWNLOAD_CHUNK_BYTES
                    ):
                        if chunk:
                            output.write(chunk)

            final_size = partial_file.stat().st_size
            if (
                expected_final_size is not None
                and final_size != expected_final_size
            ):
                raise RuntimeError(
                    f"Incomplete download: expected "
                    f"{expected_final_size} bytes but received "
                    f"{final_size} bytes."
                )

            partial_file.replace(destination)
            print(
                f"    Completed: {destination.name} "
                f"({format_bytes(destination.stat().st_size)})"
            )
            return True

        except (
            requests.RequestException,
            OSError,
            RuntimeError,
        ) as error:
            last_error = error
            print(
                f"    Download attempt {attempt}/{MAX_RETRIES} failed "
                f"for {destination.name}: {error}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)

    raise RuntimeError(
        f"Failed to download {destination.name} after "
        f"{MAX_RETRIES} attempts."
    ) from last_error


# ============================================================
# PROCESSING
# ============================================================
def process_date(
    session: requests.Session,
    collection_concept_id: str,
    current_date: date,
) -> tuple[int, int]:
    """
    Search and download one date.

    Returns:
        (number_found, number_newly_downloaded)
    """
    day_of_year = current_date.timetuple().tm_yday
    print(
        f"\nDATE={current_date:%Y.%m.%d} | "
        f"DOY={day_of_year:03d}"
    )

    granules = find_daily_granules(
        session=session,
        collection_concept_id=collection_concept_id,
        current_date=current_date,
    )

    if not granules:
        print("  No requested MCD19A2 granules found in CMR.")
        return 0, 0

    found_tiles = sorted({tile for tile, _, _ in granules})
    missing_tiles = sorted(TILES.difference(found_tiles))

    print(f"  Matching granules: {len(granules)}")
    print(f"  Available requested tiles: {', '.join(found_tiles)}")

    if missing_tiles:
        print(
            "  Requested tiles absent for this date: "
            + ", ".join(missing_tiles)
        )

    year_directory = OUTPUT_ROOT / str(current_date.year)
    downloaded_count = 0

    for _, filename, download_url in granules:
        destination = year_directory / filename
        was_downloaded = download_file(
            session=session,
            url=download_url,
            destination=destination,
        )
        downloaded_count += int(was_downloaded)

    return len(granules), downloaded_count


def main() -> None:
    validate_settings()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("MCD19A2 MAIAC AOD downloader")
    print(f"Product: {SHORT_NAME} Version {VERSION}")
    print(f"Provider: {PROVIDER}")
    print(f"Years: {START_YEAR}-{END_YEAR}")
    print(f"Months: {sorted(set(KEEP_MONTHS))}")
    print(f"Tiles: {', '.join(sorted(TILES))}")
    print(f"Output root: {OUTPUT_ROOT}")
    print("=" * 72)

    session = create_session()

    print("\nFinding the collection in NASA CMR...")
    collection_concept_id = find_collection_concept_id(session)
    print(f"Collection concept ID: {collection_concept_id}")

    total_found = 0
    total_downloaded = 0
    dates_with_data = 0
    dates_without_data = 0

    for current_date in iter_requested_dates():
        found, downloaded = process_date(
            session=session,
            collection_concept_id=collection_concept_id,
            current_date=current_date,
        )

        total_found += found
        total_downloaded += downloaded

        if found:
            dates_with_data += 1
        else:
            dates_without_data += 1

    print("\n" + "=" * 72)
    print("Finished.")
    print(f"Dates with matching granules: {dates_with_data}")
    print(f"Dates without matching granules: {dates_without_data}")
    print(f"Matching granules found: {total_found}")
    print(f"New files downloaded: {total_downloaded}")
    print(f"Files saved under: {OUTPUT_ROOT.resolve()}")
    print("=" * 72)


if __name__ == "__main__":
    main()

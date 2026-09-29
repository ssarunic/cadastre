"""GIS data cache manager for municipality ZIP files."""

import shutil
import threading
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

#: Name of a municipality's cache directory and ZIP: ``ko-<registration number>``.
MUNICIPALITY_PREFIX = "ko-"


def _tree_size(path: Path) -> int:
    """Total size in bytes of the files under ``path``."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


@dataclass(frozen=True)
class CachedMunicipality:
    """One municipality's entry in the GIS cache."""

    municipality_reg_num: str
    path: Path
    size_bytes: int
    #: When the ZIP was downloaded (None when only extracted files remain).
    downloaded_at: datetime | None


class GISCache:
    """
    Manages local caching of municipality GIS ZIP files.

    Downloads and caches ZIP files containing GML data for municipalities.
    Automatically extracts files when needed.
    """

    DEFAULT_BASE_URL = "http://localhost:8000"
    DEFAULT_CACHE_DIR = Path.home() / ".cadastral_api_cache"

    #: Marker written next to each ZIP with the base URL it was downloaded from.
    #: A ZIP whose marker does not match the configured base URL is never
    #: served; it is downloaded again, so data from one server (for example
    #: the mock server's synthetic geometry) cannot leak into another setup.
    SOURCE_FILENAME = "source.txt"

    def __init__(
        self, cache_dir: Path | str | None = None, base_url: str | None = None
    ) -> None:
        """
        Initialize GIS cache.

        Args:
            cache_dir: Directory for caching files. Defaults to ~/.cadastral_api_cache
            base_url: API base URL whose ``/atom/ko-<code>.zip`` endpoint serves
                the municipality downloads. Defaults to the mock server so that
                no download ever reaches a production system by accident.
        """
        if cache_dir is None:
            cache_dir = self.DEFAULT_CACHE_DIR
        self.cache_dir = Path(cache_dir)
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Writes to the cache directory happen one at a time: two threads
        # fetching the same municipality would otherwise purge or truncate
        # each other's files mid-write. Reentrant, since get_parcel_data
        # holds it across the download and the extraction.
        self._lock = threading.RLock()

    def get_municipality_dir(self, municipality_reg_num: str) -> Path:
        """
        Get cache directory for a specific municipality.

        Args:
            municipality_reg_num: Municipality registration number

        Returns:
            Path to municipality cache directory
        """
        muni_dir = self.cache_dir / f"{MUNICIPALITY_PREFIX}{municipality_reg_num}"
        muni_dir.mkdir(exist_ok=True)
        return muni_dir

    def get_zip_path(self, municipality_reg_num: str) -> Path:
        """
        Get path to cached ZIP file.

        Args:
            municipality_reg_num: Municipality registration number

        Returns:
            Path to ZIP file
        """
        muni_dir = self.get_municipality_dir(municipality_reg_num)
        return muni_dir / f"{MUNICIPALITY_PREFIX}{municipality_reg_num}.zip"

    def get_gml_path(self, municipality_reg_num: str, filename: str) -> Path:
        """
        Get path to extracted GML file.

        Args:
            municipality_reg_num: Municipality registration number
            filename: GML filename (e.g., "katastarske_cestice.gml")

        Returns:
            Path to GML file
        """
        muni_dir = self.get_municipality_dir(municipality_reg_num)
        return muni_dir / filename

    def get_source_path(self, municipality_reg_num: str) -> Path:
        """
        Get path to the marker file recording where the ZIP was downloaded from.

        Args:
            municipality_reg_num: Municipality registration number

        Returns:
            Path to the ``source.txt`` marker
        """
        return self.get_municipality_dir(municipality_reg_num) / self.SOURCE_FILENAME

    def get_source(self, municipality_reg_num: str) -> str | None:
        """
        Get the base URL the cached ZIP was downloaded from.

        Args:
            municipality_reg_num: Municipality registration number

        Returns:
            Base URL, or None if the marker is missing (cache written by an
            older version, or seeded by hand)
        """
        source_path = self.get_source_path(municipality_reg_num)
        if not source_path.exists():
            return None
        return source_path.read_text(encoding="utf-8").strip() or None

    def downloaded_at(self, municipality_reg_num: str) -> datetime | None:
        """When the municipality's ZIP was downloaded (aware, UTC), or None without a ZIP.

        Reads the file's modification time; creates nothing.
        """
        name = f"{MUNICIPALITY_PREFIX}{municipality_reg_num}"
        zip_path = self.cache_dir / name / f"{name}.zip"
        if not zip_path.exists():
            return None
        return datetime.fromtimestamp(zip_path.stat().st_mtime, tz=timezone.utc)

    def is_cached(self, municipality_reg_num: str) -> bool:
        """
        Check if municipality data is cached for the configured server.

        Args:
            municipality_reg_num: Municipality registration number

        Returns:
            True if the ZIP file exists and was downloaded from this cache's
            base URL. A ZIP from another server, or one without a source
            marker, does not count as cached.
        """
        zip_path = self.get_zip_path(municipality_reg_num)
        return zip_path.exists() and self.get_source(municipality_reg_num) == self.base_url

    def _purge_municipality_dir(self, municipality_reg_num: str) -> None:
        """Remove every cached file for a municipality (ZIP, GML, marker)."""
        muni_dir = self.get_municipality_dir(municipality_reg_num)
        for item in muni_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    def download_municipality(
        self, municipality_reg_num: str, force: bool = False
    ) -> Path:
        """
        Download municipality GIS data ZIP file.

        A ZIP that is already cached from this cache's base URL is returned
        as is. A ZIP from another server, or one without a source marker, is
        downloaded again and everything previously cached for the
        municipality (including extracted GML files) is discarded.

        Args:
            municipality_reg_num: Municipality registration number
            force: Force re-download even if cached

        Returns:
            Path to downloaded ZIP file

        Raises:
            httpx.HTTPError: Download failed (the previous cache is left as it was)
        """
        zip_path = self.get_zip_path(municipality_reg_num)

        with self._lock:
            # Checked under the lock: a thread that waited for another's
            # download of the same municipality finds it cached.
            if self.is_cached(municipality_reg_num) and not force:
                return zip_path

            # Download from the ATOM feed of the configured API (mock server by default)
            url = f"{self.base_url}/atom/ko-{municipality_reg_num}.zip"

            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                content = response.content

            # Only after a successful download: drop whatever was cached before so
            # that no stale ZIP or extracted GML from another server is served.
            self._purge_municipality_dir(municipality_reg_num)
            zip_path.write_bytes(content)
            self.get_source_path(municipality_reg_num).write_text(
                self.base_url + "\n", encoding="utf-8"
            )

        return zip_path

    def extract_gml(self, municipality_reg_num: str, filename: str) -> Path:
        """
        Extract specific GML file from ZIP.

        Args:
            municipality_reg_num: Municipality registration number
            filename: GML filename to extract (e.g., "katastarske_cestice.gml")

        Returns:
            Path to extracted GML file

        Raises:
            FileNotFoundError: ZIP file not in cache
            KeyError: GML file not found in ZIP
        """
        zip_path = self.get_zip_path(municipality_reg_num)

        if not zip_path.exists():
            raise FileNotFoundError(
                f"ZIP file not cached for municipality {municipality_reg_num}. "
                "Call download_municipality() first."
            )

        gml_path = self.get_gml_path(municipality_reg_num, filename)

        # Extract if not already extracted (checked under the lock: a thread
        # that waited for another's extraction finds the file).
        with self._lock:
            if not gml_path.exists():
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extract(filename, self.get_municipality_dir(municipality_reg_num))

        return gml_path

    def get_parcel_data(self, municipality_reg_num: str, auto_download: bool = True) -> Path:
        """
        Get path to cadastral parcels GML file.

        Args:
            municipality_reg_num: Municipality registration number
            auto_download: Automatically download if not cached

        Returns:
            Path to katastarske_cestice.gml file

        Raises:
            FileNotFoundError: Not cached and auto_download=False
        """
        with self._lock:
            if auto_download and not self.is_cached(municipality_reg_num):
                self.download_municipality(municipality_reg_num)
            return self.extract_gml(municipality_reg_num, "katastarske_cestice.gml")

    def cached_municipalities(self) -> list[CachedMunicipality]:
        """Every municipality with a cache directory, with its size on disk.

        Reads the directory only; nothing is created.
        """
        if not self.cache_dir.exists():
            return []
        entries: list[CachedMunicipality] = []
        for item in sorted(self.cache_dir.iterdir()):
            if not item.is_dir() or not item.name.startswith(MUNICIPALITY_PREFIX):
                continue
            code = item.name[len(MUNICIPALITY_PREFIX):]
            zip_path = item / f"{item.name}.zip"
            downloaded_at = (
                datetime.fromtimestamp(zip_path.stat().st_mtime) if zip_path.exists() else None
            )
            entries.append(CachedMunicipality(code, item, _tree_size(item), downloaded_at))
        return entries

    def size_bytes(self, municipality_reg_num: str | None = None) -> int:
        """Bytes on disk of one municipality's cache, or of the whole cache."""
        path = self.cache_dir
        if municipality_reg_num is not None:
            path = self.cache_dir / f"{MUNICIPALITY_PREFIX}{municipality_reg_num}"
        return _tree_size(path) if path.exists() else 0

    def clear_municipality(self, municipality_reg_num: str) -> None:
        """
        Clear cached data for a municipality.

        Args:
            municipality_reg_num: Municipality registration number
        """

        muni_dir = self.get_municipality_dir(municipality_reg_num)
        if muni_dir.exists():
            shutil.rmtree(muni_dir)

    def clear_all(self) -> None:
        """Clear entire cache directory."""

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

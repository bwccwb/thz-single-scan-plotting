"""Finding and loading THz spectrometer "Scan Data" files.

The data always lives on Google Drive. This module finds the Drive data
folder automatically:

* In Google Colab it mounts Drive and uses ``/content/drive/MyDrive/Data``.
  If mounting fails (e.g. Colab's "credential propagation was unsuccessful"
  bug), it falls back to the Google Drive API: it signs in with
  ``google.colab.auth`` and downloads only the scan files you ask for into
  ``/content/thz_data``.
* On your own computer it looks for Google Drive for Desktop
  (macOS: ``~/Library/CloudStorage/GoogleDrive-*/My Drive/Data``,
  Windows: ``G:/My Drive/Data``).
* You can always override it with the ``THZ_DATA_DIR`` environment variable
  or by calling ``set_data_dir(...)``.
"""

from __future__ import annotations

import csv
import glob
import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DRIVE_SUBFOLDER = "Data"  # folder inside "My Drive" that holds the date folders
API_CACHE_DIR = Path("/content/thz_data")  # where the Colab API fallback stores downloads

_data_dir: Path | None = None
_remote: "_DriveAPI | None" = None  # set when Colab's Drive mount failed

_FOLDER = "application/vnd.google-apps.folder"
_SHORTCUT = "application/vnd.google-apps.shortcut"


class _DriveAPI:
    """Read-only access to ``My Drive/Data`` through the Drive API (Colab fallback).

    Used only when ``drive.mount`` fails. Files are downloaded on demand into
    ``API_CACHE_DIR/<date>/`` so the rest of thzplot can read them like normal files.
    """

    def __init__(self):
        from google.colab import auth
        from googleapiclient.discovery import build

        auth.authenticate_user()
        self.service = build("drive", "v3", cache_discovery=False)
        self._folder_ids: dict[str, str] = {}
        data = self._find(self._children("root"), DRIVE_SUBFOLDER, folder=True)
        if data is None:
            raise FileNotFoundError(
                f"Signed in to Google Drive, but there is no '{DRIVE_SUBFOLDER}' folder "
                "(or shortcut to one) directly inside My Drive."
            )
        self.data_id = data["id"]

    @staticmethod
    def _quote(s: str) -> str:
        return s.replace("\\", "\\\\").replace("'", "\\'")

    def _children(self, parent_id: str) -> list[dict]:
        """All non-trashed items in a folder, with shortcuts resolved to their targets."""
        items, token = [], None
        while True:
            resp = self.service.files().list(
                q=f"'{self._quote(parent_id)}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, shortcutDetails)",
                pageSize=1000, pageToken=token,
                supportsAllDrives=True, includeItemsFromAllDrives=True,
            ).execute()
            for f in resp.get("files", []):
                if f.get("mimeType") == _SHORTCUT and f.get("shortcutDetails"):
                    d = f["shortcutDetails"]
                    f = {"id": d["targetId"], "name": f["name"], "mimeType": d["targetMimeType"]}
                items.append(f)
            token = resp.get("nextPageToken")
            if not token:
                return items

    @staticmethod
    def _find(items: list[dict], name: str, folder: bool) -> dict | None:
        for f in items:
            if f["name"] == name and (f["mimeType"] == _FOLDER) == folder:
                return f
        return None

    def _date_id(self, date: str) -> str | None:
        if date not in self._folder_ids:
            f = self._find(self._children(self.data_id), date, folder=True)
            if f is None:
                return None
            self._folder_ids[date] = f["id"]
        return self._folder_ids[date]

    def list_dates(self) -> list[str]:
        return [f["name"] for f in self._children(self.data_id) if f["mimeType"] == _FOLDER]

    def list_files(self, date: str) -> list[str]:
        folder = self._date_id(date)
        if folder is None:
            return []
        return [f["name"] for f in self._children(folder) if f["mimeType"] != _FOLDER]

    def download(self, date: str, name: str, dest: Path) -> bool:
        """Download ``Data/<date>/<name>`` to ``dest``. Returns False if it doesn't exist."""
        folder = self._date_id(date)
        f = self._find(self._children(folder), name, folder=False) if folder else None
        if f is None:
            return False
        content = self.service.files().get_media(fileId=f["id"], supportsAllDrives=True).execute()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return True


def _mount_or_fallback() -> None:
    """In Colab: mount Drive, or switch to the Drive API if mounting fails."""
    global _data_dir, _remote
    try:
        from google.colab import drive
        drive.mount("/content/drive")
        return
    except Exception as e:  # e.g. MessageError: credential propagation was unsuccessful
        print(f"Mounting Google Drive failed ({e}).\n"
              "Falling back to the Google Drive API: scan files will be downloaded "
              f"on demand into {API_CACHE_DIR}.")
    _remote = _DriveAPI()
    API_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _data_dir = API_CACHE_DIR


def in_colab() -> bool:
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def set_data_dir(path: str | os.PathLike) -> Path:
    """Manually set the folder that contains the date folders (e.g. ``2026.11.02``)."""
    global _data_dir
    _data_dir = Path(path).expanduser()
    if not _data_dir.is_dir():
        raise FileNotFoundError(f"Data folder does not exist: {_data_dir}")
    return _data_dir


def _candidate_dirs() -> list[Path]:
    home = Path.home()
    patterns = [
        home / "Library/CloudStorage/GoogleDrive-*/My Drive",  # macOS Drive for Desktop
        home / "Library/CloudStorage/GoogleDrive-*/MyDrive",
        home / "Google Drive/My Drive",                       # older installs
        home / "Google Drive",
        Path("G:/My Drive"),                                  # Windows default
        Path("/content/drive/MyDrive"),                       # Colab
    ]
    out = []
    for p in patterns:
        out += [Path(m) / DRIVE_SUBFOLDER for m in sorted(glob.glob(str(p)))]
    return out


def get_data_dir() -> Path:
    """Return the Drive data folder, mounting Drive first if running in Colab."""
    global _data_dir
    if _data_dir is not None:
        return _data_dir

    env = os.environ.get("THZ_DATA_DIR")
    if env:
        return set_data_dir(env)

    if in_colab() and not Path("/content/drive/MyDrive").exists():
        _mount_or_fallback()
        if _remote is not None:
            return _data_dir

    for cand in _candidate_dirs():
        if cand.is_dir():
            _data_dir = cand
            return cand

    raise FileNotFoundError(
        "Could not find the Google Drive data folder.\n"
        "  - In Colab this should be automatic.\n"
        "  - Locally, install Google Drive for Desktop "
        "(https://www.google.com/drive/download/), or\n"
        "  - set it yourself: export THZ_DATA_DIR='/path/to/My Drive/Data' "
        "or call thzplot.set_data_dir('...')."
    )


@dataclass
class Scan:
    """One spectrometer scan: its data table plus the parsed file header."""
    date: str
    time: str
    df: pd.DataFrame
    header: dict = field(default_factory=dict)
    path: Path | None = None

    # Column positions match the instrument's "Scan Data.csv" layout.
    @property
    def freq(self):
        return self.df.iloc[:, 0]   # Frequency (GHz)

    @property
    def volt(self):
        return self.df.iloc[:, 2]   # Average Voltage (arb)

    @property
    def power(self):
        return self.df.iloc[:, 3]   # Average Power (arb)

    def get(self, what: str = "power", smooth: float = 0):
        """Return "voltage" or "power", Gaussian-smoothed by ``smooth`` σ (0 = raw).

        Same smoothing method as the original notebook (astropy Gaussian1DKernel).
        """
        y = {"voltage": self.volt, "power": self.power}[what]
        if not smooth:
            return y
        from astropy.convolution import Gaussian1DKernel, convolve
        return convolve(y, Gaussian1DKernel(smooth))

    def summary(self) -> str:
        h = self.header
        keys = ["Start Frequency(GHz)", "Stop Frequency(GHz)", "Resolution(MHz)",
                "Time Constant(mS)", "Number of Scans", "Note"]
        parts = [f"{k}: {h[k]}" for k in keys if h.get(k)]
        return f"{self.date} {self.time} | " + ", ".join(parts)


def _parse_header(path: Path, n_lines: int = 6) -> dict:
    """Turn the 6-line instrument header into a dict like {'Resolution(MHz)': '1000', ...}."""
    header = {}
    with open(path, newline="") as f:
        for i, row in enumerate(csv.reader(f)):
            if i >= n_lines:
                break
            cells = [c.strip() for c in row if c.strip()]
            for key, val in zip(cells[::2], cells[1::2]):
                if key.endswith(":"):
                    header[key[:-1]] = val
            # "Note:" with an empty value
            for c in cells:
                if c.endswith(":") and c[:-1] not in header:
                    header[c[:-1]] = ""
    return header


def _normalize(date: str, time: str) -> tuple[str, str]:
    """Accept 2026.11.02 / 2026-11-02 and 13.34.03 / 13:34:03 / 13-34-03."""
    return date.strip().replace("-", "."), time.strip().replace(":", ".").replace("-", ".")


def load_scan(date: str, time: str, verbose: bool = True) -> Scan:
    """Load ``<data dir>/<date>/<time> Scan Data.csv``."""
    date, time = _normalize(date, time)
    name = f"{time} Scan Data.csv"
    path = get_data_dir() / date / name
    if _remote is not None and not path.exists():
        _remote.download(date, name, path)
    if not path.exists():
        available = list_scans(date)
        hint = f" Scans on {date}: {', '.join(available)}" if available else ""
        raise FileNotFoundError(f"No scan file at {path}.{hint}")
    df = pd.read_csv(path, skiprows=6)
    scan = Scan(date=date, time=time, df=df, header=_parse_header(path), path=path)
    if verbose:
        print(scan.summary())
    return scan


def list_scans(date: str) -> list[str]:
    """List the scan times available on a given date, e.g. ``list_scans('2026.11.02')``."""
    date, _ = _normalize(date, "")
    folder = get_data_dir() / date
    suffix = " Scan Data.csv"
    if _remote is not None:
        names = _remote.list_files(date)
    else:
        names = [p.name for p in folder.glob("*" + suffix)]
    return sorted(n[: -len(suffix)] for n in names if n.endswith(suffix))


def list_dates() -> list[str]:
    """List all date folders in the data directory."""
    data_dir = get_data_dir()
    if _remote is not None:
        return sorted(_remote.list_dates())
    return sorted(p.name for p in data_dir.iterdir() if p.is_dir())

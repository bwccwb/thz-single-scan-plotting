"""Finding and loading THz spectrometer "Scan Data" files.

The data always lives on Google Drive. This module finds the Drive data
folder automatically:

* In Google Colab it mounts Drive and uses ``/content/drive/MyDrive/Data``.
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

_data_dir: Path | None = None


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
        from google.colab import drive
        drive.mount("/content/drive")

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

    def smoothed_power(self, sigma: float = 2):
        """Gaussian-smoothed average power (same method as the original notebook)."""
        from astropy.convolution import Gaussian1DKernel, convolve
        return convolve(self.power, Gaussian1DKernel(sigma))

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
    path = get_data_dir() / date / f"{time} Scan Data.csv"
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
    return sorted(p.name.replace(" Scan Data.csv", "") for p in folder.glob("* Scan Data.csv"))


def list_dates() -> list[str]:
    """List all date folders in the data directory."""
    return sorted(p.name for p in get_data_dir().iterdir() if p.is_dir())

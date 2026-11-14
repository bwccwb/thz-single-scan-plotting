"""thzplot: quick, consistent plots of THz spectrometer scans stored on Google Drive."""

from .io import Scan, get_data_dir, list_dates, list_scans, load_scan, set_data_dir
from .plotting import (DEFAULT_SUBTITLE, DEFAULT_TITLE, apply_style, plot_scans,
                       plot_water)

__all__ = [
    "Scan", "load_scan", "list_scans", "list_dates", "get_data_dir", "set_data_dir",
    "plot_scans", "plot_water", "apply_style", "DEFAULT_TITLE", "DEFAULT_SUBTITLE",
]

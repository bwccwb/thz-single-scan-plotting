"""Plotting THz scans, in the same style as the original notebook."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from .io import Scan, load_scan

# ---------------------------------------------------------------- defaults
DEFAULT_TITLE = "Benchtop Test w/ Copper Waveguide"
# "{smoothing}" is filled in automatically, e.g. "2σ Smoothing" or "No Smoothing"
DEFAULT_SUBTITLE = "Resolution 1000 MHz, Time Constant 100 ms, {smoothing}, ~12cm Distance"
DEFAULT_SMOOTH = 2
DEFAULT_COLORS = ["hotpink", "dodgerblue", "green", "darkred",
                  "darkorange", "purple", "goldenrod", "teal", "black"]
DEFAULT_XLIM = (100, 1400)
DEFAULT_FIGSIZE = (9, 7)

# what= option -> (y-axis label, log scale by default?)
KINDS = {
    "power":   ("Average Power (arb)", True),
    "voltage": ("Voltage (arb)", False),
}

WATER_LINES_STRONG = [556.936, 752.033, 1097.364, 1113.342, 1162.911, 1207.638, 1228.788]
WATER_LINES_WEAK = [1410.618, 1602.219, 1661.007, 1669.904, 1716.769,
                    1794.788, 1797.158, 1867.748, 1919.359]


def apply_style():
    """Serif fonts, and keep text editable in PDF/SVG exports."""
    plt.rcParams["font.family"] = "serif"
    mpl.rcParams["pdf.fonttype"] = 42
    mpl.rcParams["svg.fonttype"] = "none"


def plot_water(ax):
    """Overlay water-vapour THz absorption lines."""
    for i, f in enumerate(WATER_LINES_STRONG):
        ax.axvline(f, color="red", lw=3, ls="dotted", label="water vapor" if i == 0 else None)
    for f in WATER_LINES_WEAK:
        ax.axvline(f, color="grey", lw=0.5, ls="dotted")


def _to_entry(item, i):
    """Turn one user-supplied scan spec into (Scan, label, color).

    Accepted forms:
        ("2026.11.02", "13.34.03")
        ("2026.11.02", "13.34.03", "my label")
        ("2026.11.02", "13.34.03", "my label", "green")
        "2026.11.02 13.34.03"          (or "2026.11.02/13.34.03")
        {"date": ..., "time": ..., "label": ..., "color": ...}
        a Scan object you already loaded
    """
    label = color = None
    if isinstance(item, Scan):
        scan = item
    else:
        if isinstance(item, str):
            item = tuple(item.replace("/", " ").split())
        if isinstance(item, dict):
            date, time = item["date"], item["time"]
            label, color = item.get("label"), item.get("color")
        else:
            date, time, *rest = item
            label = rest[0] if len(rest) > 0 else None
            color = rest[1] if len(rest) > 1 else None
        scan = load_scan(date, time)
    if label is None:
        label = f"{scan.date} {scan.time}"
    if color is None:
        color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
    return scan, label, color


def plot_scans(
    scans,
    what: str = "power",
    smooth: float = DEFAULT_SMOOTH,
    title: str | None = DEFAULT_TITLE,
    subtitle: str | None = DEFAULT_SUBTITLE,
    publication: bool = False,
    xlim=DEFAULT_XLIM,
    ylim=None,
    logy: bool | None = None,
    water: bool = False,
    grid: bool = True,
    legend: bool = True,
    figsize=DEFAULT_FIGSIZE,
    save: str | Path | None = None,
    show: bool = True,
):
    """Overlay several scans on one plot.

    Parameters
    ----------
    scans : list of scan specs, e.g. ``[("2026.11.02", "13.34.03", "4 K, ungrounded")]``
    what : "power" (default) or "voltage"
    smooth : Gaussian smoothing σ in points, applied to whichever quantity is
        plotted. 0 = no smoothing. Default 2.
    title, subtitle : text above the plot. Pass ``None`` or ``""`` to drop one.
        ``{smoothing}`` in either is replaced by e.g. "2σ Smoothing".
    publication : if True, no title or subtitle at all (for papers).
    xlim, ylim : axis limits (``None`` = automatic).
    logy : force log/linear y axis; default is log for power, linear for voltage.
    water : overlay water-vapour absorption lines.
    save : file path to save to (``.pdf``, ``.png``, ``.svg``...).
    show : call ``plt.show()`` at the end.

    Returns the matplotlib ``(fig, ax)`` so you can tweak further.
    """
    if what not in KINDS:
        raise ValueError(f"what must be one of {list(KINDS)}, got {what!r}")
    ylabel, default_log = KINDS[what]
    if smooth:
        ylabel = "Smoothed " + ylabel
    smoothing = f"{smooth:g}σ Smoothing" if smooth else "No Smoothing"
    apply_style()

    fig, ax = plt.subplots(figsize=figsize)
    for i, item in enumerate(scans):
        scan, label, color = _to_entry(item, i)
        ax.plot(scan.freq, scan.get(what, smooth), label=label, color=color, lw=1)

    if water:
        plot_water(ax)
    ax.set_xlim(*xlim) if xlim else None
    ax.set_ylim(*ylim) if ylim else None
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel(ylabel)
    if default_log if logy is None else logy:
        ax.set_yscale("log")
    if grid:
        ax.grid(True)
    if legend:
        ax.legend()

    if publication:
        title = subtitle = None
    title = title.replace("{smoothing}", smoothing) if title else title
    subtitle = subtitle.replace("{smoothing}", smoothing) if subtitle else subtitle
    if subtitle:
        ax.set_title(subtitle, size=10)
    suptitle = fig.suptitle(title, fontweight="bold") if title else None

    fig.tight_layout()
    if suptitle is not None:
        # centre the bold title over the plot area (not the whole figure)
        pos = ax.get_position()
        suptitle.set_x((pos.x0 + pos.x1) / 2)

    if save:
        save = Path(save)
        save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save, dpi=300, bbox_inches="tight")
        print(f"Saved {save}")
    if show:
        plt.show()
    return fig, ax

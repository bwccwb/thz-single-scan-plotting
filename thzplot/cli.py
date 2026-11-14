"""Command-line interface.

Examples
--------
    thzplot 2026.10.02/15.52.35 2026.11.02/13.34.03
    thzplot "2026.11.02/13.34.03=4 K, ungrounded" --what voltage --smooth 0
    thzplot 2026.11.02/13.34.03 --publication --save figs/fig1.pdf
    thzplot --list 2026.11.02
"""

import argparse

from . import plotting
from .io import list_dates, list_scans


def _parse_scan(spec: str):
    # "DATE/TIME", "DATE TIME", optionally "=label" and "@color"
    spec, _, color = spec.partition("@")
    spec, _, label = spec.partition("=")
    date, time = spec.replace("/", " ").split()
    return (date, time, label or None, color or None)


def main(argv=None):
    p = argparse.ArgumentParser(prog="thzplot", description="Plot THz scans from Google Drive.")
    p.add_argument("scans", nargs="*",
                   help='DATE/TIME[=label][@color], e.g. "2026.11.02/13.34.03=4 K@green"')
    p.add_argument("--what", choices=list(plotting.KINDS), default="power")
    p.add_argument("--smooth", type=float, default=plotting.DEFAULT_SMOOTH,
                   help="Gaussian smoothing σ in points (0 = none, default 2)")
    p.add_argument("--title", default=plotting.DEFAULT_TITLE)
    p.add_argument("--subtitle", default=plotting.DEFAULT_SUBTITLE)
    p.add_argument("--publication", action="store_true", help="no title/subtitle")
    p.add_argument("--xlim", type=float, nargs=2, default=plotting.DEFAULT_XLIM)
    p.add_argument("--water", action="store_true", help="overlay water vapour lines")
    p.add_argument("--save", help="save figure to this path (.pdf/.png/.svg)")
    p.add_argument("--no-show", action="store_true", help="don't open a window")
    p.add_argument("--list", nargs="?", const="", metavar="DATE",
                   help="list date folders, or the scans on DATE")
    a = p.parse_args(argv)

    if a.list is not None:
        print("\n".join(list_scans(a.list) if a.list else list_dates()))
        return
    if not a.scans:
        p.error("give at least one scan, or use --list")

    plotting.plot_scans(
        [_parse_scan(s) for s in a.scans], what=a.what, title=a.title,
        subtitle=a.subtitle, publication=a.publication, smooth=a.smooth,
        xlim=a.xlim, water=a.water, save=a.save, show=not a.no_show,
    )


if __name__ == "__main__":
    main()

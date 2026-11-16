# thzplot

Quick, consistent plots of THz spectrometer scans. No more copy-pasting cells:
list the date/time of the scans you want, and get the standard plot.

The data **always stays on Google Drive** (`My Drive/Data/<date>/<time> Scan Data.csv`).
Nothing is copied into this repo (`.gitignore` blocks data files).

## Use in Google Colab

Open `plot_scans.ipynb` in Colab (File → Open notebook → GitHub tab, paste this repo's URL).
The first cell installs the package and Drive is mounted automatically. Edit the `scans`
list and the form fields, then run.

If mounting Drive fails (Colab sometimes breaks with *"credential propagation was
unsuccessful"*), thzplot automatically falls back to the Google Drive API: you sign in once,
and only the scans you plot are downloaded into `/content/thz_data`. Everything else works
the same, except that saving figures to `/content/drive/...` isn't possible in that mode.
Save to e.g. `/content/fig1.pdf` instead and download it from the Files panel.

## Use on your own computer

1. Install **[Google Drive for Desktop](https://www.google.com/drive/download/)**. Your Drive
   then shows up as a folder (macOS: `~/Library/CloudStorage/GoogleDrive-<you>/My Drive`),
   and files stream on demand. thzplot finds it automatically.
2. Install the package:
   ```bash
   pip install git+https://github.com/bwccwb/thz-single-scan-plotting.git
   # or, from a clone, editable:  pip install -e .
   ```
3. If your data folder is somewhere unusual, set it:
   `export THZ_DATA_DIR="/path/to/My Drive/Data"`

### In Python / a local notebook

```python
import thzplot

thzplot.plot_scans([
    ("2026.10.02", "15.52.35", "final bench config 10/02"),
    ("2026.11.02", "13.34.03", "4 K, ungrounded, 11/2"),
    ("2026.11.04", "16.19.24", "4 K, grounded, 11/4", "darkred"),  # optional colour
])

# raw (unsmoothed) voltage, custom title, no subtitle
thzplot.plot_scans(scans, what="voltage", smooth=0, title="Cryostat test", subtitle=None)

# power with heavier smoothing
thzplot.plot_scans(scans, smooth=4)

# publication: no title/subtitle, saved as an editable-text PDF
thzplot.plot_scans(scans, publication=True, save="figures/fig2.pdf")

thzplot.list_scans("2026.11.02")   # which scans exist on a date?
```

### From the terminal

```bash
thzplot "2026.10.02/15.52.35=final bench config" "2026.11.02/13.34.03=4 K@green"
thzplot 2026.11.02/13.34.03 --what voltage --smooth 0 --title "Cryostat test" --subtitle ""
thzplot 2026.11.02/13.34.03 --publication --save figures/fig2.pdf
thzplot --list               # date folders
thzplot --list 2026.11.02    # scans on that date
```

## Options (`plot_scans`)

| option | default | meaning |
|---|---|---|
| `what` | `"power"` | `"power"` or `"voltage"` (power = voltage²) |
| `smooth` | `2` | Gaussian smoothing σ in points, applied to either quantity; `0` = raw |
| `title` | `Benchtop Test w/ Copper Waveguide` | bold title; `None` to hide |
| `subtitle` | `Resolution 1000 MHz, Time Constant 100 ms, {smoothing}, ~12cm Distance` | `None` to hide; `{smoothing}` becomes "2σ Smoothing" / "No Smoothing" |
| `publication` | `False` | hide both titles |
| `xlim` / `ylim` | `(100, 1400)` / auto | axis limits |
| `logy` | log for power, linear for voltage | force y scale |
| `water` | `False` | overlay water-vapour lines |
| `save` | `None` | output path (`.pdf`, `.png`, `.svg`) |

Change the defaults once in `thzplot/plotting.py` (`DEFAULT_TITLE`, `DEFAULT_SUBTITLE`,
`DEFAULT_SMOOTH`, `DEFAULT_COLORS`, ...).

`plot_scans` returns `(fig, ax)` so you can tweak anything further with matplotlib.

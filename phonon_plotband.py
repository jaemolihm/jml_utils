#!/usr/bin/env python3

# Plot phonon band structure obtained by matdyn.x

import os.path
import argparse
import numpy as np
import matplotlib.pyplot as plt

UNIT_FACTOR = {
    "cm-1": 1.0,
    "meV": 0.12398419843320026,
    "THz": 0.0299792458,
}

parser = argparse.ArgumentParser()
parser.add_argument("--freq_file", default="matdyn.freq.gp", help="matdyn.x gnuplot-format frequency file")
parser.add_argument("--kpath_file", default="../supportInfo.kpath", help="ISODISTORT-style supportInfo.kpath file for high-symmetry tick labels (optional)")
parser.add_argument("--png", action="store_true", help="save PNG instead of showing interactively")
parser.add_argument("--unit", choices=["cm-1", "meV", "THz"], default="meV")
parser.add_argument("--yrange", nargs=2, type=float, metavar=("A", "B"), default=None, help="y-axis limits (default: automatic)")
args = parser.parse_args()

# Read band structure
data = np.loadtxt(args.freq_file)
xkplot = data[:, 0]
omega = data[:, 1:] * UNIT_FACTOR[args.unit]

nk, nmodes = omega.shape

fig = plt.figure(figsize=(5, 4))
ax = plt.gca()

for imode in range(nmodes):
    ax.plot(xkplot, omega[:, imode], "k")

# High-symmetry ticks from supportInfo.kpath (optional)
if os.path.isfile(args.kpath_file):
    with open(args.kpath_file, "r") as f:
        lines = f.readlines()
    idx = next(i for i, l in enumerate(lines) if "CARTESIAN coordinates" in l)
    kpts = []
    high_sym_label = []
    for line in lines[idx + 1:]:
        parts = line.split()
        if len(parts) < 4:
            break
        kpts.append([float(parts[0]), float(parts[1]), float(parts[2])])
        high_sym_label.append(parts[3])
    kpts = np.array(kpts)

    # Cartesian coordinates in supportInfo.kpath use a different alat
    # normalization than matdyn's x-axis, but the path shape is the same,
    # so rescale the cumulative distance to match xkplot's range.
    seg_len = np.linalg.norm(np.diff(kpts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    high_sym_k = cum / cum[-1] * (xkplot[-1] - xkplot[0]) + xkplot[0]

    high_sym_label = ["$\\Gamma$" if x.upper() == "GAMMA" else x for x in high_sym_label]

    ax.set_xticks(high_sym_k)
    ax.set_xticklabels(high_sym_label)
    for x in high_sym_k:
        ax.axvline(x=x, c="k", lw=1, ls="--")

ax.set_xlim([min(xkplot), max(xkplot)])
if args.yrange is not None:
    ax.set_ylim(args.yrange)
ax.set_ylabel(f"Frequency ({args.unit})")
ax.axhline(0, c="k", lw=1)

ax.set_title("Phonon band structure")

if args.png:
    print("Writing PNG : phonon_band.png")
    plt.savefig("phonon_band.png", dpi=300)
else:
    plt.show()

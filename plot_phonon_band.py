#!/usr/bin/env python3

# Plot phonon band structure obtained by matdyn.x

import sys
import os.path
import numpy as np
import matplotlib.pyplot as plt

def get_nk(filename):
    with open(filename, 'r') as f:
        nk = 0
        for line in f:
            if line.strip() == "":
                break
            nk += 1
    return nk

if len(sys.argv) > 1:
    prefix = sys.argv[1].strip()
else:
    prefix = None

filename_matdyn = "matdyn.freq.gp"
filename_label_pw = f"plotband.out"

# Try to find file with high-symmetry k point information
if prefix is not None:
    if (not os.path.isfile(filename_label_pw)) and os.path.isfile(f"{prefix}.{filename_label_pw}"):
        filename_label_pw = f"{prefix}.{filename_label_pw}"

fig = plt.figure(figsize=(5, 4))
ax = plt.gca()

# Read band structure
data = np.loadtxt(filename_matdyn)
xkplot = data[:, 0]
omega = data[:, 1:]

nk, nmodes = omega.shape

# Read high-symmetry k points
high_sym_k = []
high_sym_label = []
if os.path.isfile(filename_label_pw):
    # Read high-symmetry k point labels from my_qe_bands.py output
    with open(filename_label_pw, 'r') as f:
        for line in f:
            if 'high-symmetry point:' in line:
                high_sym_k += [float(line.split()[7])]
                if len(line.split()) == 9:
                    high_sym_label += [line.split()[8]]
                else:
                    high_sym_label += ['.']
else:
    # Skip high-symmetry k points
    pass
high_sym_label = ["$\Gamma$" if x.lower() in ['gamma', 'g'] else x for x in high_sym_label]
high_sym_label = ["$\Sigma$" if x.lower() == 'sigma' else x for x in high_sym_label]

for imode in range(nmodes):
    ax.plot(xkplot, omega[:, imode], "k")

if len(high_sym_k) > 0:
    ax.set_xticks(high_sym_k)
    ax.set_xticklabels(high_sym_label)
    for x in high_sym_k:
        ax.axvline(x=x, c='k', lw=1, ls='--')
ax.set_xlim([min(xkplot), max(xkplot)])
ax.set_ylabel("Energy (cm$^{-1}$)")
ax.axhline(0, c="k", lw=1)

title = "Phonon band structure"
if prefix is not None: title += f" of {prefix}"
ax.set_title(title)

plt.show()

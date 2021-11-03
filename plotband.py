#!/usr/bin/env python3

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

def parse_efermi_or_evbm(filename):
    # TODO: parse VBM & CBM
    with open(filename, 'r') as f:
        for line in f:
            if "highest occupied level" in line:
                return float(line.split()[-1])
            if "the Fermi energy is" in line:
                return float(line.split()[-2])
    return None

prefix = sys.argv[1].strip()

filename_w90 = f"{prefix}_band.dat"
filename_pw = f"{prefix}.bands.dat.gnu"
filename_label = f"{prefix}_band.labelinfo.dat"
filename_label_pw = f"plotband.out"
filename_scf = "scf.out"

fig, axes = plt.subplots(1, 2, figsize=(8, 4))

# Wannier90 bands
if os.path.isfile(filename_w90):
    nk_w90 = get_nk(filename_w90)

    data_w90 = np.loadtxt(filename_w90).reshape((-1, nk_w90, 2))
    xkplot_w90 = data_w90[0, :, 0]
    e_w90 = data_w90[:, :, 1]

    for ax in axes:
        for ib in range(e_w90.shape[0]):
            lines = ax.plot(xkplot_w90, e_w90[ib, :], 'r--', label='W90' if ib==0 else None, zorder=3)
        ax.set_xlim([min(xkplot_w90), max(xkplot_w90)])
else:
    xkplot_w90 = [1.0]

# DFT bands
if os.path.isfile(filename_pw):
    nk_pw = get_nk(filename_pw)

    data_pw = np.loadtxt(filename_pw).reshape((-1, nk_pw, 2))
    xkplot_pw = data_pw[0, :, 0]
    e_pw = data_pw[:, :, 1]
    xk_pw_to_w90_convert = xkplot_w90[-1] / xkplot_pw[-1]
    xkplot_pw *= xk_pw_to_w90_convert

    for ax in axes:
        for ib in range(e_pw.shape[0]):
            lines = ax.plot(xkplot_pw, e_pw[ib, :], 'k-', label='DFT' if ib==0 else None, zorder=1)
        ax.set_xlim([min(xkplot_pw), max(xkplot_pw)])

# Special k points
high_sym_k = []
high_sym_label = []

# Try to append prefix to filename_label_pw
if (not os.path.isfile(filename_label_pw)) and os.path.isfile(f"{prefix}.{filename_label_pw}"):
    filename_label_pw = f"{prefix}.{filename_label_pw}"

if os.path.isfile(filename_label):
    # Read high-symmetry k point labels from Wannier90 output
    with open(filename_label, 'r') as f:
        for line in f:
            if line.strip() == "":
                break
            data = line.split()
            high_sym_label += [data[0]]
            high_sym_k += [float(data[2])]
elif os.path.isfile(filename_label_pw):
    # Read high-symmetry k point labels from my_qe_bands.py output
    with open(filename_label_pw, 'r') as f:
        for line in f:
            if 'high-symmetry point:' in line:
                high_sym_k += [float(line.split()[7])]
                if len(line.split()) == 9:
                    high_sym_label += [line.split()[8]]
                else:
                    high_sym_label += ['.']
    high_sym_k = [x * xk_pw_to_w90_convert for x in high_sym_k]
else:
    # Skip high-symmetry k points
    pass
high_sym_label = ["$\Gamma$" if x.lower() in ['gamma', 'g'] else x for x in high_sym_label]
high_sym_label = ["$\Sigma$" if x.lower() == 'sigma' else x for x in high_sym_label]

if len(high_sym_k) > 0:
    for ax in axes:
        ax.set_xticks(high_sym_k)
        ax.set_xticklabels(high_sym_label)
        for x in high_sym_k:
            ax.axvline(x=x, c='k', lw=1, ls='--')

# Fermi level
if os.path.isfile(filename_scf):
    efermi = parse_efermi_or_evbm(filename_scf)
    if efermi is not None:
        for ax in axes:
            ax.axhline(y=efermi, c='b', lw=1)
        axes[1].set_ylim([efermi - 2.0, efermi + 2.0])

axes[0].set_ylabel("Energy (eV)")
axes[0].legend()
plt.show()

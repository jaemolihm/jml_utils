#!/usr/bin/env python3

import sys
import os.path
import numpy as np
import matplotlib.pyplot as plt

def get_nk(filename):
    with open(filename, 'r') as f:
        nk = 0
        for line in f:
            if line[0] == "#": continue
            if line.strip() == "":
                break
            nk += 1
    return nk

def parse_efermi_or_evbm(filename):
    # TODO: parse VBM & CBM
    with open(filename, 'r') as f:
        for line in f:
            if "highest occupied level" in line:
                return float(line.split()[-1]), None
            if "the Fermi energy is" in line:
                return float(line.split()[-2]), None
            if "highest occupied, lowest unoccupied level" in line:
                return float(line.split()[-2]), float(line.split()[-1])
    return None

def merge_multiple_high_sym_labels(high_sym_k, high_sym_label):
    high_sym_k_new = [high_sym_k[0]]
    high_sym_label_new = [high_sym_label[0]]
    for i in range(1, len(high_sym_k)):
        if abs(high_sym_k[i] - high_sym_k_new[-1]) > 1e-5:
            # label at different x
            high_sym_k_new += [high_sym_k[i]]
            high_sym_label_new += [high_sym_label[i]]
        else:
            # label at same x
            high_sym_label_new[-1] += "|" + high_sym_label[i]
    return high_sym_k_new, high_sym_label_new

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
    # Read LSDA information if present.
    with open(filename_pw, "r") as f:
        line = f.readline()
        if "# LSDA" in line:
            lsda = True
            nbnd_up, nbnd_dw = [int(x) for x in line.split()[-2:]]
        else:
            lsda = False

    nk_pw = get_nk(filename_pw)
    data_pw = np.loadtxt(filename_pw).reshape((-1, nk_pw, 2))
    xkplot_pw = data_pw[0, :, 0]
    e_pw = data_pw[:, :, 1]
    xkplot_pw *= xkplot_w90[-1] / xkplot_pw[-1]
    nbnd = e_pw.shape[0]

    for ax in axes:
        if lsda:
            for ib in range(nbnd_up):
                lines = ax.plot(xkplot_pw, e_pw[ib, :], 'k-', label='DFT spin up' if ib==0 else None, zorder=1)
            for ib in range(nbnd_up, nbnd_up + nbnd_dw):
                lines = ax.plot(xkplot_pw, e_pw[ib, :], 'b-', label='DFT spin down' if ib==nbnd_up else None, zorder=1)
        else:
            for ib in range(nbnd):
                lines = ax.plot(xkplot_pw, e_pw[ib, :], 'k-', label='DFT' if ib==0 else None, zorder=1)
        ax.set_xlim([min(xkplot_pw), max(xkplot_pw)])

# Special k points
high_sym_k = []
high_sym_label = []

if os.path.isfile(filename_label):
    # Read high-symmetry k point labels from Wannier90 output
    with open(filename_label, 'r') as f:
        for line in f:
            if line.strip() == "":
                break
            data = line.split()
            high_sym_label += [data[0]]
            high_sym_k += [float(data[2])]
    high_sym_label = ["$\Gamma$" if x.lower() in ['gamma', 'g'] else x for x in high_sym_label]
elif os.path.isfile(filename_label_pw):
    # Read high-symmetry k point labels from my_qe_bands.py output
    with open(filename_label_pw, 'r') as f:
        for line in f:
            if 'high-symmetry point:' in line:
                high_sym_k += [float(line.split()[-1])]
                high_sym_label += ['.']
else:
    # Skip high-symmetry k points
    pass

# If there are multiple high-symmetry labels on the same k, merge them
high_sym_k, high_sym_label = merge_multiple_high_sym_labels(high_sym_k, high_sym_label)

if len(high_sym_k) > 0:
    for ax in axes:
        ax.set_xticks(high_sym_k)
        ax.set_xticklabels(high_sym_label)
        for x in high_sym_k:
            ax.axvline(x=x, c='k', lw=1, ls='--')

# Fermi level
if os.path.isfile(filename_scf):
    # efermi1: E_VBM (insulator) or Fermi energy (metal)
    # efermi2: E_CBM (insulator) or None (metal)
    efermi1, efermi2 = parse_efermi_or_evbm(filename_scf)
    if efermi1 is not None:
        for ax in axes:
            ax.axhline(y=efermi1, c='b', lw=1)
        axes[1].set_ylim([efermi1 - 2.0, efermi1 + 2.0])
    if efermi2 is not None:
        for ax in axes:
            ax.axhline(y=efermi2, c='g', lw=1)

axes[0].set_ylabel("Energy (eV)")
axes[0].legend()
plt.show()

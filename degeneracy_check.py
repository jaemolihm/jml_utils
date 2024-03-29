#!/usr/bin/env python3
"""
Determines numbers of bands that can be used, compatible with the
degenerate subspaces.

Partly adapted from degeneracy_check.f90 of BerkeleyGW v2.1.
"""
import sys
import numpy as np
from qe_parse_energy import parse_energy

hartree_to_ev = lambda x: float(x) * 27.21138602
degeneracy_tol = 1E-6 # Ry

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python3 degeneracy_check.py prefix outdir')
        raise KeyError("Wrong input")

    seedname = sys.argv[1]
    if len(sys.argv) == 2:
        outdir = 'temp'
    elif len(sys.argv) == 3:
        outdir = sys.argv[2]
    else:
        raise ValueError
    xmlfile = outdir + '/' + seedname + '.xml'

    is_lsda, nbnd, nk, weight, energy, occupations, xk = parse_energy(xmlfile)
    if is_lsda:
        raise NotImplementedError
    nspin = 2 if is_lsda else 1

    print('Reading eigenvalues from file', xmlfile)
    print(f"Number of spins:{nspin:16d}")
    print(f"Number of bands:{nbnd:16d}")
    print(f"Number of k-points:{nk:13d}")

    no_degeneracy = [False] * nbnd

    for ib in range(nbnd - 1):
        gap = np.min(energy[ib+1, :] - energy[ib, :])
        if gap > degeneracy_tol:
            no_degeneracy[ib] = True


    print()
    print('== Degeneracy-allowed numbers of bands ==')
    print('number of bands / Max energy of the included bands / Min energy of the excluded bands')
    for ib in range(nbnd):
        if no_degeneracy[ib]:
            print(f"{ib + 1:8d}", end="")
            print(f"{hartree_to_ev(np.amax(energy[ib, :])):10.2f} eV", end="")
            print(f"{hartree_to_ev(np.amin(energy[ib+1, :])):10.2f} eV")
    print(f"Note: cannot assess whether or not the highest band {nbnd} is degenerate.")

    print()
    print(f"Minimum energy of the highest band = {hartree_to_ev(np.amin(energy[-1, :]))} eV")

    print()
    print(f"Minimum / Maximum energy of the bands [eV]")
    for ib in range(nbnd):
        emin = hartree_to_ev(np.amin(energy[ib, :]))
        emax = hartree_to_ev(np.amax(energy[ib, :]))
        print(f"{ib+1:5d}  {emin:10.5f}   ~ {emax:10.5f}")

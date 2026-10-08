#!/usr/bin/env python3
"""
Rotate Wannier90 .amn projections to diagonalize the local density matrix.

Usage: python rotate_amn_diag.py seedname mu temperature [--blocks BLOCKS]

Inputs:
    seedname.amn - Wannier90 projection file
    seedname.eig - Wannier90 eigenvalue file
    seedname.nnkp - (optional) for auto-detecting blocks from projection centers

Outputs:
    stdout: Original density matrix, rotated density matrix, U matrix
    seedname_diag.amn - Rotated projection file
"""

import sys
import re
import argparse
import numpy as np
from scipy.special import expit


def read_amn(filename):
    """
    Read Wannier90 .amn file.

    Returns:
        header: str, header line
        amn: ndarray of shape (Nk, Nb, Np), complex projections
             A[k, n, i] = <psi_nk | g_i>
    """
    with open(filename, 'r') as f:
        header = f.readline().strip()
        Nb, Nk, Np = map(int, f.readline().split())

        # Each line: band_idx, kpt_idx, proj_idx, real, imag (1-based indices)
        raw_data = np.loadtxt(f)

    # Reshape: data is ordered as (kpt, proj, band) in Fortran order
    raw_data = raw_data.reshape((Nk, Np, Nb, 5))
    amn = raw_data[:, :, :, 3] + 1j * raw_data[:, :, :, 4]
    # Transpose to (Nk, Nb, Np)
    amn = np.transpose(amn, axes=(0, 2, 1))

    return header, amn


def write_amn(filename, header, amn):
    """
    Write Wannier90 .amn file.

    Args:
        filename: output filename
        header: header line
        amn: ndarray of shape (Nk, Nb, Np), complex projections
    """
    Nk, Nb, Np = amn.shape

    with open(filename, 'w') as f:
        f.write(f"{header}\n")
        f.write(f"{Nb:12d}{Nk:12d}{Np:12d}\n")

        # Write in Fortran order: band fastest, then projection, then kpoint
        for ik in range(Nk):
            for ip in range(Np):
                for ib in range(Nb):
                    # 1-based indices: band, projection, kpoint
                    f.write(f"{ib+1:5d}{ip+1:5d}{ik+1:5d}"
                            f"{amn[ik, ib, ip].real:18.12f}"
                            f"{amn[ik, ib, ip].imag:18.12f}\n")


def read_eig(filename):
    """
    Read Wannier90 .eig file.

    Returns:
        eig: ndarray of shape (Nk, Nb), eigenvalues in eV
    """
    raw_data = np.loadtxt(filename)

    # Last row contains Nb in column 0, Nk in column 1
    Nb = int(raw_data[-1, 0])
    Nk = int(raw_data[-1, 1])

    eig = raw_data[:, 2].reshape((Nk, Nb))
    return eig


# Orbital names from Wannier90 documentation
# https://wannier90.readthedocs.io/en/latest/user_guide/wannier90/projections/
ORBITAL_NAMES = {
    # s, p, d, f orbitals (l >= 0)
    (0, 1): "s",
    (1, 1): "pz",
    (1, 2): "px",
    (1, 3): "py",
    (2, 1): "dz2",
    (2, 2): "dxz",
    (2, 3): "dyz",
    (2, 4): "dx2-y2",
    (2, 5): "dxy",
    (3, 1): "fz3",
    (3, 2): "fxz2",
    (3, 3): "fyz2",
    (3, 4): "fz(x2-y2)",
    (3, 5): "fxyz",
    (3, 6): "fx(x2-3y2)",
    (3, 7): "fy(3x2-y2)",
    # Hybrid orbitals (l < 0)
    (-1, 1): "sp-1",
    (-1, 2): "sp-2",
    (-2, 1): "sp2-1",
    (-2, 2): "sp2-2",
    (-2, 3): "sp2-3",
    (-3, 1): "sp3-1",
    (-3, 2): "sp3-2",
    (-3, 3): "sp3-3",
    (-3, 4): "sp3-4",
    (-4, 1): "sp3d-1",
    (-4, 2): "sp3d-2",
    (-4, 3): "sp3d-3",
    (-4, 4): "sp3d-4",
    (-4, 5): "sp3d-5",
    (-5, 1): "sp3d2-1",
    (-5, 2): "sp3d2-2",
    (-5, 3): "sp3d2-3",
    (-5, 4): "sp3d2-4",
    (-5, 5): "sp3d2-5",
    (-5, 6): "sp3d2-6",
}


def get_orbital_name(l, mr, r):
    """Get orbital name from l, mr, r quantum numbers."""
    name = ORBITAL_NAMES.get((l, mr), f"l={l},mr={mr}")
    if r == 2:
        name = f"{name}, 1 radial node"
    elif r > 2:
        name = f"{name}, {r-1} radial nodes"
    return name


def read_nnkp_projections(filename):
    """
    Read projection information from Wannier90 .nnkp file.

    Each projection has two lines:
        Line 1: center(3), l, mr, r
        Line 2: z-axis(3), x-axis(3), zona

    Returns:
        projections: list of dicts with keys 'center', 'l', 'mr', 'r'
    """
    with open(filename, 'r') as f:
        content = f.read()

    # Find projections block
    pattern = r'begin projections\s*\n(.*?)\nend projections'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find projections block in {filename}")

    lines = match.group(1).strip().split('\n')
    num_proj = int(lines[0])

    projections = []
    for i in range(num_proj):
        # Line 1 of each projection: center(3), l, mr, r
        line_idx = 1 + 2 * i
        values = list(map(float, lines[line_idx].split()))
        projections.append({
            'center': np.array(values[:3]),
            'l': int(values[3]),
            'mr': int(values[4]),
            'r': int(values[5])
        })
        # Line 2 (z-axis, x-axis, zona) is skipped

    return projections


def parse_blocks_from_string(block_string, num_proj):
    """
    Parse block definition from command-line string.

    Format: "0,1,2;3,4,5" means indices 0,1,2 form block 0, indices 3,4,5 form block 1.

    Args:
        block_string: string like "0,1,2;3,4,5"
        num_proj: total number of projections

    Returns:
        blocks: list of lists, each inner list contains projection indices for that block
    """
    blocks = []
    for block_str in block_string.split(';'):
        indices = [int(i) for i in block_str.split(',')]
        blocks.append(indices)

    # Verify all indices are covered exactly once
    all_indices = set()
    for block in blocks:
        for i in block:
            if i in all_indices:
                raise ValueError(f"Index {i} appears in multiple blocks")
            if i < 0 or i >= num_proj:
                raise ValueError(f"Index {i} out of range [0, {num_proj})")
            all_indices.add(i)

    if len(all_indices) != num_proj:
        missing = set(range(num_proj)) - all_indices
        raise ValueError(f"Indices {missing} not assigned to any block")

    return blocks


def detect_blocks_from_centers(projections, tol=1e-3):
    """
    Group projections by their center coordinates.

    Args:
        projections: list of dicts with 'center' key
        tol: tolerance for matching centers

    Returns:
        blocks: list of lists, each inner list contains projection indices with same center
    """
    Np = len(projections)
    assigned = [False] * Np
    blocks = []

    for i in range(Np):
        if assigned[i]:
            continue

        # Start a new block with projection i
        block = [i]
        assigned[i] = True

        # Find all other projections with same center
        for j in range(i + 1, Np):
            if not assigned[j]:
                if np.allclose(projections[i]['center'], projections[j]['center'], atol=tol):
                    block.append(j)
                    assigned[j] = True

        blocks.append(block)

    return blocks


def diagonalize_density_matrix_blocks(N, blocks):
    """
    Diagonalize Hermitian density matrix block by block.

    For each block, diagonalize the corresponding submatrix of N.
    The resulting U matrix is block-diagonal.

    Args:
        N: (Np, Np) Hermitian matrix
        blocks: list of lists, each inner list contains projection indices for that block

    Returns:
        eigenvalues: (Np,) eigenvalues ordered by blocks, descending within each block
        U: (Np, Np) block-diagonal unitary matrix
    """
    Np = N.shape[0]
    eigenvalues = np.zeros(Np)
    U = np.zeros((Np, Np), dtype=complex)

    for block in blocks:
        idx = np.array(block)
        # Extract submatrix
        N_block = N[np.ix_(idx, idx)]

        # Diagonalize
        eig_block, U_block = np.linalg.eigh(N_block)

        # Sort by descending eigenvalue within block
        sort_idx = np.argsort(eig_block)[::-1]
        eig_block = eig_block[sort_idx]
        U_block = U_block[:, sort_idx]

        # Place into full arrays
        eigenvalues[idx] = eig_block
        U[np.ix_(idx, idx)] = U_block

    return eigenvalues, U


def unitarize_amn(amn):
    """
    Unitarize projections at each k-point using SVD.

    For each k-point, find the closest matrix with orthonormal columns.
    If A = U @ S @ V^H (SVD), the closest unitary is U @ V^H.

    Args:
        amn: (Nk, Nb, Np) complex projections

    Returns:
        amn_unitary: (Nk, Nb, Np) unitarized projections where
                     A^H @ A = I for each k-point
    """
    Nk, Nb, Np = amn.shape
    amn_unitary = np.zeros_like(amn)

    for ik in range(Nk):
        # SVD of A[k]: (Nb, Np) = U @ S @ V^H
        # U: (Nb, Np), S: (Np,), V: (Np, Np)
        U, S, Vh = np.linalg.svd(amn[ik], full_matrices=False)
        # Closest matrix with orthonormal columns: U @ V^H
        amn_unitary[ik] = U @ Vh

    return amn_unitary


def fermi_dirac(energy, mu, temperature):
    """
    Fermi-Dirac distribution.

    f(e) = 1 / (exp((e - mu) / T) + 1)

    For T = 0, this becomes a step function:
        f = 1 if e < mu, 0 if e > mu, 0.5 if e = mu

    Args:
        energy: eigenvalues (any shape)
        mu: chemical potential
        temperature: temperature in same units as energy (can be 0)

    Returns:
        occupation numbers (same shape as energy)
    """
    if temperature == 0:
        # Step function at T = 0
        return np.where(energy < mu, 1.0, np.where(energy > mu, 0.0, 0.5))
    else:
        # expit(x) = 1 / (1 + exp(-x)), so f = expit((mu - e) / T)
        return expit((mu - energy) / temperature)


def compute_density_matrix(amn, eig, mu, temperature):
    """
    Compute local density matrix.

    N[i, j] = sum_{n, k} A[k,n,i]^* * f(e[k,n] - mu) * A[k,n,j] / Nk

    Args:
        amn: (Nk, Nb, Np) complex projections
        eig: (Nk, Nb) eigenvalues
        mu: chemical potential
        temperature: temperature

    Returns:
        N: (Np, Np) Hermitian density matrix
    """
    Nk, Nb, Np = amn.shape

    # Compute occupations: shape (Nk, Nb)
    occ = fermi_dirac(eig, mu, temperature)

    # N[i, j] = sum_{k, n} conj(A[k,n,i]) * occ[k,n] * A[k,n,j] / Nk
    # = sum_{k, n} conj(A[k,n,i]) * (sqrt(occ) * sqrt(occ)) * A[k,n,j] / Nk

    # Weighted projections: A_weighted[k, n, i] = sqrt(occ[k,n]) * A[k,n,i]
    sqrt_occ = np.sqrt(occ)[:, :, np.newaxis]  # (Nk, Nb, 1)
    A_weighted = sqrt_occ * amn  # (Nk, Nb, Np)

    # N[i, j] = sum_{k, n} conj(A_weighted[k,n,i]) * A_weighted[k,n,j] / Nk
    # Reshape to (Nk*Nb, Np) and compute A^H @ A
    A_flat = A_weighted.reshape(-1, Np)  # (Nk*Nb, Np)
    N = A_flat.conj().T @ A_flat / Nk

    return N


def compute_local_hamiltonian(amn, eig):
    """
    Compute local Hamiltonian.

    H[i, j] = sum_{n, k} A[k,n,i]^* * e[k,n] * A[k,n,j] / Nk

    Args:
        amn: (Nk, Nb, Np) complex projections
        eig: (Nk, Nb) eigenvalues

    Returns:
        H: (Np, Np) Hermitian local Hamiltonian
    """
    Nk, Nb, Np = amn.shape

    # H[i, j] = sum_{k, n} conj(A[k,n,i]) * eig[k,n] * A[k,n,j] / Nk
    # Weighted projections: A_weighted[k, n, i] = sqrt(eig[k,n]) * A[k,n,i]
    # But eigenvalues can be negative, so we compute directly

    H = np.zeros((Np, Np), dtype=complex)
    for ik in range(Nk):
        # A[ik]: (Nb, Np), eig[ik]: (Nb,)
        # H += A^H @ diag(eig) @ A
        A_weighted = eig[ik, :, np.newaxis] * amn[ik]  # (Nb, Np)
        H += amn[ik].conj().T @ A_weighted

    H /= Nk
    return H


def diagonalize_density_matrix(N):
    """
    Diagonalize Hermitian density matrix.

    Find U such that U^H @ N @ U = diag(eigenvalues)

    Args:
        N: (Np, Np) Hermitian matrix

    Returns:
        eigenvalues: (Np,) sorted in descending order
        U: (Np, Np) unitary matrix with eigenvectors as columns
    """
    eigenvalues, U = np.linalg.eigh(N)

    # Sort by descending eigenvalue
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    U = U[:, idx]

    return eigenvalues, U


def rotate_amn(amn, U):
    """
    Rotate projections by unitary matrix U.

    A'[k, n, i] = sum_j A[k, n, j] * U[j, i]

    Args:
        amn: (Nk, Nb, Np) complex projections
        U: (Np, Np) unitary matrix

    Returns:
        amn_rotated: (Nk, Nb, Np) rotated projections
    """
    # amn @ U: sum over last axis of amn with first axis of U
    return amn @ U


def print_matrix(name, matrix):
    """Print a matrix with a label. Real and imaginary parts printed separately."""
    Np = matrix.shape[0]

    # Print real part
    print(f"\n{name} (real):")
    matrix_real = matrix.real if np.iscomplexobj(matrix) else matrix
    for i in range(Np):
        row = "  ".join(f"{matrix_real[i,j]:12.6f}" for j in range(Np))
        print(f"  {row}")

    # Print imaginary part only if significant
    if np.iscomplexobj(matrix) and np.max(np.abs(matrix.imag)) > 1e-5:
        print(f"\n{name} (imag):")
        for i in range(Np):
            row = "  ".join(f"{matrix.imag[i,j]:12.6f}" for j in range(Np))
            print(f"  {row}")


def main():
    parser = argparse.ArgumentParser(
        description="Rotate Wannier90 .amn projections to diagonalize the local density matrix."
    )
    parser.add_argument("seedname", help="Prefix for .amn and .eig files")
    parser.add_argument("mu", type=float, help="Chemical potential (eV)")
    parser.add_argument("temperature", type=float, help="Temperature (eV), can be 0")
    parser.add_argument(
        "--blocks", type=str, default="auto",
        help="Block structure: '0,1,2;3,4,5', 'auto' to detect from .nnkp file (default), or 'full' for full diagonalization"
    )
    parser.add_argument(
        "--diagonalize", type=str, default="occupation", choices=["occupation", "hamiltonian"],
        help="Matrix to diagonalize: 'occupation' for density matrix (default), 'hamiltonian' for local Hamiltonian"
    )

    args = parser.parse_args()

    seedname = args.seedname
    mu = args.mu
    temperature = args.temperature

    print(f"Parameters:")
    print(f"  seedname = {seedname}")
    print(f"  mu = {mu} eV")
    print(f"  temperature = {temperature} eV")

    # Read input files
    header, amn = read_amn(f"{seedname}.amn")
    eig = read_eig(f"{seedname}.eig")

    Nk, Nb, Np = amn.shape
    print(f"\nDimensions:")
    print(f"  Nk (k-points) = {Nk}")
    print(f"  Nb (bands) = {Nb}")
    print(f"  Np (projections) = {Np}")

    # Determine block structure
    blocks = None
    if args.blocks == "full":
        print(f"\nFull diagonalization (no block structure)")
    elif args.blocks == "auto":
        # Auto-detect from nnkp file
        nnkp_file = f"{seedname}.nnkp"
        print(f"\nReading projections from {nnkp_file}")
        projections = read_nnkp_projections(nnkp_file)
        print(f"\nProjections (centers in fractional coordinates):")
        for i, proj in enumerate(projections):
            c = proj['center']
            orb_name = get_orbital_name(proj['l'], proj['mr'], proj['r'])
            print(f"  {i}: [{c[0]:10.5f}, {c[1]:10.5f}, {c[2]:10.5f}]  {orb_name}")
        blocks = detect_blocks_from_centers(projections, tol=1e-3)
        print(f"\nDetected {len(blocks)} blocks from projection centers:")
        for i, block in enumerate(blocks):
            print(f"  Block {i}: indices {block}")
    else:
        # User-provided blocks
        blocks = parse_blocks_from_string(args.blocks, Np)
        print(f"\nUser-provided {len(blocks)} blocks:")
        for i, block in enumerate(blocks):
            print(f"  Block {i}: indices {block}")

    # Unitarize A at each k-point
    amn_unitary = unitarize_amn(amn)
    print(f"\nUnitarized projections (A^H A = I at each k-point)")

    # Compute original density matrix using unitarized A
    N_orig = compute_density_matrix(amn_unitary, eig, mu, temperature)
    print_matrix("Original density matrix N", N_orig)
    print(f"\nTrace(N) = {np.trace(N_orig).real:.6f}")

    # Compute original local Hamiltonian using unitarized A
    H_orig = compute_local_hamiltonian(amn_unitary, eig)
    print_matrix("Original local Hamiltonian H - mu", H_orig - mu * np.eye(Np))

    # Diagonalize (full or block-wise)
    if args.diagonalize == "occupation":
        matrix_to_diag = N_orig
        diag_name = "density matrix N"
        eig_name = "occupations"
    else:
        matrix_to_diag = H_orig
        diag_name = "local Hamiltonian H"
        eig_name = "energies"

    print(f"\nDiagonalizing {diag_name}")

    if blocks is None:
        eigenvalues, U = diagonalize_density_matrix(matrix_to_diag)
    else:
        eigenvalues, U = diagonalize_density_matrix_blocks(matrix_to_diag, blocks)

    if blocks is None:
        print(f"\n{diag_name.capitalize()} eigenvalues ({eig_name}, descending):")
        for i, ev in enumerate(eigenvalues):
            print(f"  {i}: {ev:.6f}")
    else:
        print(f"\n{diag_name.capitalize()} eigenvalues ({eig_name}, descending within each block):")
        for block_idx, block in enumerate(blocks):
            print(f"  Block {block_idx}:")
            for i in block:
                print(f"    {i}: {eigenvalues[i]:.6f}")

    print_matrix("Unitary rotation matrix U", U)

    # Rotate original projections for output file
    amn_rotated = rotate_amn(amn, U)

    # Verify diagonalization using unitarized A (same as used to compute N)
    amn_unitary_rotated = rotate_amn(amn_unitary, U)
    N_rotated = compute_density_matrix(amn_unitary_rotated, eig, mu, temperature)
    print_matrix("Rotated density matrix N'", N_rotated)
    print(f"\nTrace(N') = {np.trace(N_rotated).real:.6f}")

    # Compute rotated local Hamiltonian
    H_rotated = compute_local_hamiltonian(amn_unitary_rotated, eig)
    print_matrix("Rotated local Hamiltonian H' - mu", H_rotated - mu * np.eye(Np))

    # Verify diagonality (or block-diagonality) of the diagonalized matrix
    M_rotated = N_rotated if args.diagonalize == "occupation" else H_rotated
    print(f"\nDiagonality check of rotated {diag_name}:")
    if blocks is None:
        off_diag = M_rotated - np.diag(np.diag(M_rotated))
        max_off_diag = np.max(np.abs(off_diag))
        print(f"  Max off-diagonal element: {max_off_diag:.2e}")
    else:
        # Check off-diagonal elements outside blocks
        mask = np.ones_like(M_rotated, dtype=bool)
        for block in blocks:
            idx = np.array(block)
            mask[np.ix_(idx, idx)] = False
        max_off_block = np.max(np.abs(M_rotated[mask])) if np.any(mask) else 0.0
        print(f"  Max off-block-diagonal element: {max_off_block:.2e}")

        # Check off-diagonal within blocks
        block_off_diag = 0.0
        for block in blocks:
            idx = np.array(block)
            M_block = M_rotated[np.ix_(idx, idx)]
            off_diag = M_block - np.diag(np.diag(M_block))
            block_off_diag = max(block_off_diag, np.max(np.abs(off_diag)))
        print(f"  Max off-diagonal within blocks: {block_off_diag:.2e}")

    # Write output file
    output_file = f"{seedname}_diag.amn"
    new_header = f"{header} | rotate_amn_diag.py: diagonalized local {args.diagonalize}"
    write_amn(output_file, new_header, amn_rotated)
    print(f"\nRotated projections written to: {output_file}")


if __name__ == "__main__":
    main()

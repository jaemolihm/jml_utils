#!/usr/bin/env python3
"""Rewrite the k-point block of a QE *.in or Wannier90 *.win file in-place.

Detects one of three cases and replaces the existing block with a new
Monkhorst-Pack grid of size Nx*Ny*Nz:

  automatic : QE `K_POINTS automatic` then one line `N1 N2 N3 0 0 0`
  crystal   : QE `K_POINTS crystal`   then count line + N k-points
  wannier90 : `mp_grid = ...` plus `begin kpoints` ... `end kpoints`

The crystal and wannier90 cases regenerate the explicit list by invoking
`kmesh.pl` on PATH (`crystal` -> `kmesh.pl Nx Ny Nz`; `wannier90` ->
`kmesh.pl Nx Ny Nz wannier`).

Exit codes:
  0  file rewritten (or already up to date)
  1  runtime error (kmesh.pl failed, write failed, etc.)
  2  could not detect a k-point block in the file
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


KPOINTS_AUTO_RE = re.compile(r"^\s*K_POINTS\s+automatic\b", re.IGNORECASE)
KPOINTS_CRYS_RE = re.compile(r"^\s*K_POINTS\s+crystal\b", re.IGNORECASE)
MP_GRID_RE = re.compile(r"^\s*mp_grid\s*=", re.IGNORECASE)
BEGIN_KPTS_RE = re.compile(r"^\s*begin\s+kpoints\b", re.IGNORECASE)
END_KPTS_RE = re.compile(r"^\s*end\s+kpoints\b", re.IGNORECASE)
INT_LINE_RE = re.compile(r"^\s*(\d+)\b")


class DetectionError(Exception):
    """Raised when no recognized k-point block is found."""


def _is_data_line(line):
    """True if `line` looks like a k-point row (non-blank, not a comment)."""
    s = line.strip()
    return bool(s) and not s.startswith(("!", "#"))


def detect_case(lines):
    """Return one of:
      ('automatic', auto_idx)
      ('crystal',   header_idx, count_idx, last_data_idx)
      ('wannier90', mp_idx, end_idx)
    Wannier90 is checked first so a stray K_POINTS in a .win file
    cannot mis-trigger.
    """
    mp_idx = next((i for i, l in enumerate(lines) if MP_GRID_RE.match(l)), None)
    begin_idx = next((i for i, l in enumerate(lines) if BEGIN_KPTS_RE.match(l)), None)
    end_idx = next((i for i, l in enumerate(lines) if END_KPTS_RE.match(l)), None)
    if mp_idx is not None and begin_idx is not None and end_idx is not None:
        if not (mp_idx < begin_idx < end_idx):
            raise DetectionError(
                f"mp_grid/begin/end out of order (got {mp_idx}/{begin_idx}/{end_idx})"
            )
        return ("wannier90", mp_idx, end_idx)

    auto_idx = next((i for i, l in enumerate(lines) if KPOINTS_AUTO_RE.match(l)), None)
    if auto_idx is not None:
        return ("automatic", auto_idx)

    header_idx = next((i for i, l in enumerate(lines) if KPOINTS_CRYS_RE.match(l)), None)
    if header_idx is not None:
        j = header_idx + 1
        while j < len(lines) and not _is_data_line(lines[j]):
            j += 1
        if j < len(lines):
            m = INT_LINE_RE.match(lines[j])
            if m:
                n = int(m.group(1))
                count_idx = j
                # consume N data lines, skipping any blanks/comments interleaved
                k = j + 1
                consumed = 0
                while k < len(lines) and consumed < n:
                    if _is_data_line(lines[k]):
                        consumed += 1
                    k += 1
                if consumed != n:
                    raise DetectionError(
                        f"K_POINTS crystal claims {n} points but only {consumed} data lines follow"
                    )
                last_data_idx = k - 1
                return ("crystal", header_idx, count_idx, last_data_idx)

    raise DetectionError("no K_POINTS automatic/crystal or mp_grid+kpoints block found")


def run_kmesh(nx, ny, nz, wannier=False):
    cmd = ["kmesh.pl", str(nx), str(ny), str(nz)]
    if wannier:
        cmd.append("wannier")
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("kmesh.pl not found on PATH")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"kmesh.pl exited with status {e.returncode}: {e.stderr.strip()}"
        ) from e
    return [l + "\n" for l in res.stdout.splitlines()]


def rewrite(lines, case, nx, ny, nz):
    tag = case[0]
    if tag == "automatic":
        idx = case[1]
        if idx + 1 >= len(lines):
            raise RuntimeError("K_POINTS automatic has no grid line after it")
        lines[idx + 1] = f" {nx} {ny} {nz} 0 0 0\n"
        return lines

    if tag == "crystal":
        _, header_idx, _count_idx, last_data_idx = case
        new_block = run_kmesh(nx, ny, nz, wannier=False)
        return lines[:header_idx] + new_block + lines[last_data_idx + 1 :]

    if tag == "wannier90":
        _, mp_idx, end_idx = case
        # mp_grid through end-kpoints (inclusive) is replaced; any content
        # in between (comments, blanks) is discarded
        new_block = run_kmesh(nx, ny, nz, wannier=True)
        return lines[:mp_idx] + new_block + lines[end_idx + 1 :]

    raise AssertionError(f"unknown case tag {tag!r}")


def atomic_write(path: Path, text: str):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("file", type=Path)
    ap.add_argument(
        "--kgrid", type=int, nargs=3, metavar=("NX", "NY", "NZ"), required=True
    )
    args = ap.parse_args()

    nx, ny, nz = args.kgrid
    path = args.file
    raw = path.read_text()
    # normalize line endings so the rewritten file is consistent LF
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines(keepends=True)

    try:
        case = detect_case(lines)
    except DetectionError as e:
        print(f"ERROR: {e}: {path}", file=sys.stderr)
        sys.exit(2)

    try:
        new_lines = rewrite(lines, case, nx, ny, nz)
    except RuntimeError as e:
        print(f"ERROR: {e}: {path}", file=sys.stderr)
        sys.exit(1)

    new_text = "".join(new_lines)
    if new_text == text:
        print(f"unchanged {case[0]}: {path}")
        return
    atomic_write(path, new_text)
    print(f"updated   {case[0]}: {path}")


if __name__ == "__main__":
    main()

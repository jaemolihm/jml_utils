# jml\_utils

Small scripts made by me or taken and modified from other scripts.
See header of each file for the detailed usage.

### First-principle calculations - utilities
* `epw_pp.py`: Modified version of EPW `pp.py`.
* `kmesh.pl`: Modified version of Wannier90 `kmesh.pl`.
* `my_qe_bands.py`: Python port of `bands.x` of Quantum ESPRESSO.
* `qe_parse_energy.py`: Parse band energies from xml file and save as numpy for Quantum ESPRESSO.
* `degeneracy\_check.py`: Check band degeneracy over all k points. (Adapted from BerkeleyGW.)

### First-principle calculations - visualization
* `plotband.py`: Plot DFT and Wannier-interpolated band structures.
* `pwscfacc`: Plot estimated accuracy of Quantum ESPRESSO SCF iterations.
* `w90dis`: Plot Delta of Wannier90 disentanglement iterations.
* `w90dlta`: Plot Delta of Wannier90 maximal localization iterations.

### Linux utilities
* `rsubl`: Remote sublime. https://github.com/randy3k/RemoteSubl
* `watchlast`: Watch last modified output file on full screen.
* `taillast`: Tail last modified file.

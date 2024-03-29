#!/usr/bin/env python3
import os
import sys
import numpy as np
import xml.etree.ElementTree as ET

def find_value_int(root, tag):
    for item in root.iter(tag):
        return int(item.text)
    raise KeyError
def find_value_logical(root, tag):
    for item in root.iter(tag):
        return item.text.strip() in ['True', 'true', 'TRUE']

def parse_energy(xmlfile):
    tree = ET.parse(xmlfile)
    root = tree.getroot()

    is_lsda = find_value_logical(root, 'lsda')

    if is_lsda:
        nbnd = find_value_int(root, 'nbnd_up')
        nbnd += find_value_int(root, 'nbnd_dw')
    else:
        nbnd = find_value_int(root, 'nbnd')
    try:
        nk = find_value_int(root, 'nk')
    except KeyError:
        nk = find_value_int(root, 'nks')

    weight = np.zeros((nk,))
    xk = np.zeros((3, nk))
    energy = np.zeros((nbnd, nk))
    occupations = np.zeros((nbnd, nk))
    ik = 0
    for supitem in root.iter('ks_energies'):
        for item in supitem.iter('k_point'):
            weight[ik] += float(item.items()[0][1])
            xk[:, ik] = [float(x) for x in item.text.split()]
        for item in supitem.iter('eigenvalues'):
            energy[:, ik] = [float(x) for x in item.text.split()]
        for item in supitem.iter('occupations'):
            occupations[:, ik] = [float(x) for x in item.text.split()]
        ik += 1
    assert ik == nk

    if is_lsda:
        energy_lsda = np.zeros((nbnd//2, nk, 2))
        energy_lsda[:,:,0] = energy[:nbnd//2,:]
        energy_lsda[:,:,1] = energy[nbnd//2:,:]
        occupations_lsda = np.zeros((nbnd//2, nk, 2))
        occupations_lsda[:,:,0] = occupations[:nbnd//2,:]
        occupations_lsda[:,:,1] = occupations[nbnd//2:,:]

    if is_lsda:
        return is_lsda, nbnd, nk, weight, energy_lsda, occupations_lsda, xk
    else:
        return is_lsda, nbnd, nk, weight, energy, occupations, xk

if __name__ == '__main__':
    print(sys.argv)
    prefix = sys.argv[1]
    if len(sys.argv) == 2:
        outdir = 'temp'
    elif len(sys.argv) == 3:
        outdir = sys.argv[2]
    else:
        raise ValueError
    #xmlfile = outdir + '/' + prefix + '.xml'
    xmlfile = os.path.join(outdir, prefix + '.save', 'data-file-schema.xml')

    is_lsda, nbnd, nk, weight, energy, occupations, xk = parse_energy(xmlfile)

    print("Is LSDA calculation: ", is_lsda)
    print("number of bands: ", nbnd)
    print("number of k points: ", nk)

    np.savez('energy_and_xk_' + prefix, energy=energy, xk=xk)
    # np.save('xk_' + prefix, xk)

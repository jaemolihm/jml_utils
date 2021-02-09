#!/usr/bin/env python3
#
# Post-processing script from of PH data in format used by EPW
# 14/07/2015 - Creation of the script - Samuel Ponce
# 14/03/2018 - Automatically reads the number of q-points - Michael Waters
# 14/03/2018 - Detect if SOC is included in the calculation - Samuel Ponce
#
import sys
import numpy as np
import os
from xml.dom import minidom

# Return the number of q-points in the IBZ
def get_nqpt(prefix, outdir):
    fname = f'{outdir}/' + '_ph0/' +prefix+'.phsave/control_ph.xml'

    fid = open(fname,'r')
    lines = fid.readlines() # these files are relatively small so reading the whole thing shouldn't be an issue
    fid.close()

    line_number_of_nqpt = 0
    while 'NUMBER_OF_Q_POINTS' not in lines[line_number_of_nqpt]: # increment to line of interest
        line_number_of_nqpt +=1
    line_number_of_nqpt +=1 # its on the next line after that text

    nqpt = int(lines[line_number_of_nqpt])

    return nqpt

# Check if the calculation include SOC
def hasSOC(prefix, outdir):
    fname = f'{outdir}/' + prefix+'.save/data-file-schema.xml'

    xmldoc = minidom.parse(fname)
    item = xmldoc.getElementsByTagName('spinorbit')[0]
    lSOC = item.childNodes[0].data

    if lSOC == 'true':
        return True
    elif lSOC == 'false':
        return False
    else:
        raise ValueError('Problem in hasSOC')


# check if calculation used xml files (irrelevant of presence of SOC)
def hasXML(prefix, dyndir):
    # check for a file named prefix.dyn1.xml
    # if it exists => return True else return False
    fname = os.path.join(dyndir, prefix + ".dyn1.xml")
    if os.path.isfile(fname):
        return True
    # check if the other without .xml extension exists
    # if not raise an error
    fname_no_xml = fname.strip(".xml")

    if not os.path.isfile(fname_no_xml):
        raise FileNotFoundError(
                "No dyn1 file found cannot tell if xml format was used.")
    return False


# Check if the calculation was done in sequential
def isSEQ(prefix, outdir):
    fname = f'{outdir}/' + '_ph0/'+str(prefix)+'.dvscf'
    if (os.path.isfile(fname)):
        lseq = True
    else:
        lseq = False

    return lseq

# run cp command to copy file_from to file_to
def do_copy(file_from, file_to, is_folder=False):
    if is_folder:
        os.system(f'cp -r {file_from} {file_to}')
    else:
        os.system(f'cp {file_from} {file_to}')

outdir = 'temp'
dyndir = 'dyn_dir'

# Enter the number of irr. q-points
if len(sys.argv) == 2:
    prefix = sys.argv[1].strip()
    # dummy = input()
else:
    user_input = input('Enter the prefix used for PH calculations (e.g. diam)\n')
    prefix = str(user_input)

# Test if SOC
SOC = hasSOC(prefix, outdir)

# Test if XML
XML = hasXML(prefix, dyndir)

# Test if seq. or parallel run
SEQ = isSEQ(prefix, outdir)

# gets nqpt from the output files
nqpt = get_nqpt(prefix, outdir)

# Delete temporary wavefunction file
os.system(f'rm -f {outdir}/_ph*/{prefix}.q_*/*wfc*')

# For image parallization
if os.path.isdir(f'{outdir}/_ph1'):
    # Move all output data to _ph0
    os.system(f'mv {outdir}/_ph[1-9]*/{prefix}.q_*/ {outdir}/_ph0/')
    # Remove image parallelized output folders
    os.system(f'rm -rf {outdir}/_ph[1-9]*/')

os.system('mkdir -p save')

# Copy dynamical matrix and force constant files
if XML:
    do_copy(f'{dyndir}/{prefix}.dyn0', f'{dyndir}/{prefix}.dyn0.xml')
    do_copy(f'{prefix}.fc.xml', 'save/ifc.q2r.xml')
else:
    do_copy(f'{prefix}.fc', 'save/ifc.q2r')

for iqpt in np.arange(1, nqpt+1):
    label = str(iqpt)
    if XML:
        do_copy(f'{dyndir}/{prefix}.dyn{iqpt}.xml', f'save/{prefix}.dyn_q{label}.xml')
    else:
        do_copy(f'{dyndir}/{prefix}.dyn{iqpt}', f'save/{prefix}.dyn_q{label}')

# Copy phsave folder
do_copy(f'{outdir}/_ph0/{prefix}.phsave', 'save/', is_folder=True)

# Copy dvscf files
if not SEQ:
    postfix = '1'
elif SEQ and SOC:
    postfix = '*'
else:
    postfix = ''

for iqpt in np.arange(1, nqpt+1):
    label = str(iqpt)

    dvscf_to = f'save/{prefix}.dvscf_q{label}'

    if iqpt == 1:
        dvscf_from = f'{outdir}/_ph0/{prefix}.dvscf' + postfix
    else:
        dvscf_from = f'{outdir}/_ph0/{prefix}.q_{iqpt}/{prefix}.dvscf' + postfix

    do_copy(dvscf_from, dvscf_to)

    # Delete temporary wavefunction file
    os.system(f'rm -f {outdir}/_ph0/{prefix}.q_{iqpt}/*wfc*')


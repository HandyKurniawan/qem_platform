import numpy as np
from pathlib import Path
from . import __tools as tls
from . import __polarcodec as codec
from .__qpolarprep import q1prep as q1prep

def get_q1prep_sr(n, lstate, results):
    # n = 4       # number of polarization steps (polar code length N = 2^n)
    # lstate = "X" # prepared logical state: may be "Z" (|0>) or "X" (|+>)
    
    # # measurement results file
    # # each line in the file contains the measurement results for one preparation experiment
    # mfile = 'polar_code_n{}_{}_simulator.txt'.format(n, lstate.lower())
    
    # zpos: last position frozen in zero, counting from zero! (0 <= zpos < N-1)
    # list of zpos values, assuming that logical |0> is prepared (lstate = "Z")
    #       n =   0   1   2  3  4  5   6   7   8   9   10 
    zpos_list = [-1, -1, -1, 3, 6, 7, 22, 15, 90, 31, 362]

    if lstate == "Z":
        # |0> is prepared: take zpos value from the list above
        zpos = zpos_list[n]
    elif lstate == "X":
        # |+> is prepared: zpos value from the list above -1
        zpos = zpos_list[n] -1
    else:
        raise TypeError("Illegal 'lstate' value")

    N     = 2**n     # polar code length
    mnum  = n*(N//2) # number of measurement results for each state preparation

    count_success = 0    # number of valid measurement results
    count_failure = 0    # number of invalid measurement results
    total_shots = sum(results.values())

    # ##################################################################
    # read measurement results from file, and check which ones are valid
    # ##################################################################
    for line, meas_counts in results.items():
        # print(line)
        # remove spaces at beginning and end of line
        mstr = line.strip()

        # init the measurement results array -- of length len(mstr)
        meas = np.zeros((len(mstr),), dtype=int) 

        # convert from string to np array
        for i in range(0, len(mstr)):
            meas[i] = ord(mstr[i]) - ord('0')	
            if meas[i] != 0 and meas[i] != 1:
                raise TypeError("Illegal measurement result: must be 0 or 1")


        # check if 'meas' are valid measurement results
        success = q1prep(n, zpos, meas)
        if success == 1:
            count_success = count_success + meas_counts
            # print(meas)
        else:
            count_failure = count_failure + meas_counts

    # print("  number of valid measurement results = ", count_success, count_success / total_shots)
    # print("number of invalid measurement results = ", count_failure, count_failure / total_shots)
    # print("")

    return count_success / total_shots



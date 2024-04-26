"""
file name: ir2dag.py
author: Handy, Laura, Fran
date: 14 September 2023

This module return intermediate representation for TriQ input. 

Base of this function is from https://github.com/prakashmurali/TriQ/blob/master/ir2dag.py. 
We fix the bug and modify it

Functions:

Example:
"""

import sys

global_gate_id = 0
prev_gate = {}
gate_names = {"cx":"CNOT", "cz":"CZ", "h":"H", "x":"X", "y":"Y", "z":"Z", "rx":"RX", "ry":"RY", "rz":"RZ", "s":"S", "sdg":"Sdag", "t":"T", "tdg":"Tdag", "sx":"SX", "sxdg":"SXdag", "measure":"MeasZ", "ccx":"CCX", "reset":"Reset"}
gset1 = ['x', 'y', 'z', 'h', 's', 'sdg', 't', 'tdg', 'sx', 'sxdg', 'measure', 'reset']
gset2 = ['rx', 'ry', 'rz']
gset3 = ['cx']
gset4 = ['ccx'] #20230907, Handy, add ccx gate to process from qasm

#20230907, Handy, to map the qubit to the correct index
qubit_mapping = {}
 
def find_dep_gate(qbit):
    if qbit in prev_gate.keys():
        return [prev_gate[qbit]]
    else:
        return []

def update_dep_gate(qbit, gate_id):
    prev_gate[qbit] = gate_id

def check_valid_gate(line):
    flag = 0
    gset = []
    gset.extend(gset1)
    gset.extend(gset2)
    gset.extend(gset3)
    gset.extend(gset4)
    for g in gset:
        if line.startswith(g):
            flag = 1
            break
    return flag

def add_qubit_mapping(qcnt, qreg):
    qno = int(qreg.split('[')[1].split(']')[0])
    for i in range(qno):
        key = qreg.split('[')[0] +"[" + str(i) + "]"
        qubit_mapping[key] = str(qcnt + i)

# Here we want to combine all the variable to one index
def map_qubit(qubit):
    return qubit_mapping[qubit]

# decompose ccx
def decompose_ccx(line, f_out, g):
    global global_gate_id
    d = []   # to keep all the decompose gates

    base = line.split(" ")
    targets = base[1].split(",")
    c1 = targets[0]
    c2 = targets[1]
    t = targets[2][:-1]

    #print(global_gate_id, g, c1, c2, t)
    
    d.append("h " + t + ";")                   # h c;
    d.append("cx " + c2 + ", " + t + ";")     # cx b,c;
    d.append("tdg " + t + ";")                 # tdg c;
    d.append("cx " + c1 + ", " + t + ";")     # cx a,c;
    d.append("t " + t + ";")                   # t c;
    d.append("cx " + c2 + ", " + t + ";")     # cx b,c;
    d.append("tdg " + t + ";")                 # tdg c;
    d.append("cx " + c1 + ", " + t + ";")     # cx a,c;
    d.append("t " + c2 + ";")                  # t b;
    d.append("t " + t + ";")                   # t c;
    d.append("h " + t + ";")                   # h c;
    d.append("cx " + c1 + ", " + c2 + ";")    # cx a,b;
    d.append("t " + c1 + ";")                  # t a;
    d.append("tdg " + c2 + ";")                # tdg b;
    d.append("cx " + c1 + ", " + c2 + ";")    # cx a,b;

    for line in d:
        process_gate_gset1(line, f_out)
        process_gate_gset2(line, f_out)
        process_gate_gset3(line, f_out)
        global_gate_id += 1

    global_gate_id -= 1 # because it has been added 1 outside
    return 

def process_gate_gset1(line, f_out):
    global gset1
    gflag = 0
    dep_gates = []

    for g in gset1:
        if line.split()[0] == g:
            # print(line.split()[0], g)
            #qbit = line.split()[1].split('[')[1].split(']')[0]
            if line.startswith("measure"):
                qbit = map_qubit(line.split()[1])
            else:
                qbit = map_qubit(line.split()[1][:-1])

            gflag = 1
            # print(global_gate_id, g, qbit)
            f_out.write(str(global_gate_id) + ' ' + gate_names[g] + ' 1 ' + qbit)
            dep_gates = find_dep_gate(qbit)
            if len(dep_gates) == 1:
                f_out.write(' 1 ' + str(dep_gates[0]) + '\n')
            elif len(dep_gates) == 0:
                f_out.write(' 0\n')
            else:
                assert(0)
            update_dep_gate(qbit, global_gate_id)

            break

def process_gate_gset2(line, f_out):
    global gset2
    gflag = 0
    dep_gates = []

    for g in gset2:
        if line[:2] == g:
            #qbit = line.split()[3].split('[')[1].split(']')[0]
            qbit = map_qubit(line.split()[1][:-1])
            angle = line.split()[0].split('(')[1].split(')')[0]
            # print(global_gate_id, g, qbit, angle)
            f_out.write(str(global_gate_id) + ' ' + gate_names[g] + ' 1 ' + qbit)
            dep_gates = find_dep_gate(qbit)
            if len(dep_gates) == 1:
                f_out.write(' 1 ' + str(dep_gates[0]) + ' ' + str(angle) + '\n')
            elif len(dep_gates) == 0:
                f_out.write(' 0 ' + str(angle) + '\n')
            else:
                assert(0)
            update_dep_gate(qbit, global_gate_id)
            gflag = 1
            break

def process_gate_gset3(line, f_out):
    global gset3
    gflag = 0
    dep_gates = []

    for g in gset3:
         if line.split()[0] == g:
            base = line.split(" ")
            
            qbit1 = 0 
            qbit2 = 0
            if (len(base) == 2):
                qbit1 = map_qubit(base[1].split(',')[0])
                qbit2 = map_qubit(base[1].split(',')[1][:-1])
            else:
                qbit1 = map_qubit(base[1][:-1])
                qbit2 = map_qubit(base[2][:-1])

            #print(global_gate_id, g, qbit1, qbit2)
            f_out.write(str(global_gate_id) + ' ' + gate_names[g] + ' 2 ' + qbit1 + ' ' + qbit2)
            dep_gates1 = find_dep_gate(qbit1)
            dep_gates2 = find_dep_gate(qbit2)
            dep_gates1.extend(dep_gates2)
            update_dep_gate(qbit1, global_gate_id)
            update_dep_gate(qbit2, global_gate_id)
            f_out.write(' ' + str(len(dep_gates1)) + ' ')
            for item in dep_gates1:
                f_out.write(str(item) + ' ')
            f_out.write('\n')
            gflag = 1
            break

def process_gate_gset4(line, f_out):
    global gset4

    #20230907, Handy, add ccx
    for g in gset4:
         if line.split()[0] == g:
            decompose_ccx(line, f_out, g)
            break

def process_gate(line, f_out):
    process_gate_gset1(line, f_out)
    process_gate_gset2(line, f_out)
    process_gate_gset3(line, f_out)
    process_gate_gset4(line, f_out)

def parse_ir(qasm_str, outfname):
    global global_gate_id
    global qubit_mapping
    global prev_gate
    
    global_gate_id = 0
    qubit_mapping = {}
    prev_gate = {}

    l = qasm_str.splitlines()
    f_out = open(outfname, 'w')

    qcnt = 0
    gcnt = 0
    for line in l:
        line = ' '.join(line.split())
        if line.startswith("OPENQASM"):
            continue
        elif line.startswith("include"):
            continue
        elif line.startswith("qreg"):
            sline = line.split()

            add_qubit_mapping(qcnt, sline[1])

            # 20230907, Handy, fix the bug to handle multiple qreg in qasm
            qcnt += int(sline[1].split('[')[1].split(']')[0])
            
        elif line.startswith("creg"):
            continue
        else:
            if check_valid_gate(line):
                if line.startswith("ccx"): # ccx gate will be decompose
                    gcnt += 15
                else:
                    gcnt += 1
    
    f_out.write(str(qcnt) + ' ' + str(gcnt) + '\n')

    for line in l:
        line = ' '.join(line.split())
        if line.startswith("OPENQASM"):
            continue
        elif line.startswith("include"):
            continue
        elif line.startswith("qreg"):
            continue
        elif line.startswith("creg"):
            continue
        else:
            if check_valid_gate(line):
                process_gate(line, f_out)
                global_gate_id += 1

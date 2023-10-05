"""
file name: triq_wrapper.py
author: Handy, Laura, Fran
date: 14 September 2023

This module provides all the function necesary to run TriQ

Functions:
- run(qasm_path, hardware_name, triq_optimization): run the optimization from TriQ

Example:
"""
import subprocess as sp
import sys
import os
from datetime import datetime
from .ir2dag import parse_ir
import time, json
import mysql.connector

triq_path = os.path.expanduser("~/qem_platform/wrappers/triq_wrapper/")
out_path = os.path.expanduser("./")
dag_path = os.path.expanduser("./")
base_name = "output"
dag_name = base_name + ".in"
out_name = base_name + ".qasm"
dag_file_path = os.path.join(dag_path, dag_name)
out_file_path = os.path.join(out_path, out_name)


def read_file(file_path):
    success = False
    while not success:
        try:
            with open(file_path, "r") as file:
                # Read the contents of the file and store them in the variable
                file_contents = file.read()
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

        success = True

    return file_contents

def create_dir(path):
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)

def generate_qasm(qasm_str, hardware_name, triq_optimization):
    tmp_hw_name = hardware_name
    if hardware_name == "ibmq_qasm_simulator":
        tmp_hw_name = "ibm_perth"

    # parse qasm into .in
    parse_ir(qasm_str, os.path.join(dag_path, dag_name))

    # call triq
    call_triq = [os.path.join(triq_path, "triq"), 
                dag_file_path, 
                out_file_path, tmp_hw_name, str(triq_optimization)]

    out_file=open("log/output.log",'w+')

    p = sp.Popen(call_triq, stdout=out_file, text=True, shell=False)    
    p.communicate()
    p.terminate()
    p.wait()
    p.kill()

    result_qasm = read_file(out_file_path)

    return result_qasm

def run(qasm_str, hardware_name, triq_optimization):
    """
    Parameters:
        qasm_path:
        hardware_name:
        triq_optimization:
    """
    
    result_qasm = generate_qasm(qasm_str, hardware_name, triq_optimization)

    if (os.path.isfile(dag_file_path)):
        os.remove(dag_file_path)

    if (os.path.isfile(out_file_path)):
        os.remove(out_file_path)


    return result_qasm

def get_mapping(qasm_str, hardware_name, triq_optimization):
    """
    Parameters:
        qasm_path:
        hardware_name:
        triq_optimization:
    """
    result_qasm = generate_qasm(qasm_str, hardware_name, triq_optimization)

    log_path = os.path.expanduser("./log/output.log")

    mapping_dict = None
    with open(log_path, "r") as file:
        mapping_dict = json.load(file)

    if (os.path.isfile(log_path)):
        os.remove(log_path)

    return mapping_dict

def generate_realtime_calibration_data(qem):
    # Connect to the MySQL database
    conn = mysql.connector.connect(**qem.mysql_config)
    cursor = conn.cursor()

    # get last calibration id
    cursor.execute('''SELECT calibration_id FROM calibration_data.ibm 
                   WHERE hw_name = %s 
                   ORDER BY calibration_datetime DESC LIMIT 0, 1;
                    ''', (qem.hardware_name, ))
    results = cursor.fetchall()
    calibration_id = results[0][0]

    # get 1 qubit gate error
    cursor.execute('''SELECT calibration_id, qubit, 1 - x_error as fidelity_1q 
                   FROM calibration_data.ibm_one_qubit_gate_spec 
                   WHERE calibration_id = %s;
                    ''', (calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/ibm_perth_S.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit, fidelity_1q = res
            f.write("{} {} \n".format(qubit, fidelity_1q))

        f.close()

    # get 2 qubit gate error
    cursor.execute('''SELECT calibration_id, qubit_control, qubit_target, 1 - cx_error as fidelity_2q
                   FROM calibration_data.ibm_two_qubit_gate_spec 
                   WHERE calibration_id = %s;
                    ''', (calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/ibm_perth_T.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit_control, qubit_target, fidelity_2q = res
            f.write("{} {} {} \n".format(qubit_control, qubit_target, fidelity_2q))

        f.close()

    # get readout error
    cursor.execute('''SELECT calibration_id, qubit, 1 - readout_error as readout_fidelity
                   FROM calibration_data.ibm_qubit_spec 
                   WHERE calibration_id = %s;;
                    ''', (calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/ibm_perth_M.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit, readout_fidelity = res
            f.write("{} {}\n".format(qubit, readout_fidelity))

        f.close()

    conn.close()
    




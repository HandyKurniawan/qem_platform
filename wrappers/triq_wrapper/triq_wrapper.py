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
import time

def read_file(file_path):
    success = False
    loop_times = 0
    while not success:
        # if loop_times > 10:
        #     break

        try:
            with open(file_path, "r") as file:
                # Read the contents of the file and store them in the variable
                file_contents = file.read()

        except FileNotFoundError:
            print(f"File not found: {file_path}")
            # time.sleep(30)
            # loop_times += 1
        except Exception as e:
            print(f"An error occurred: {str(e)}")

        success = True

    return file_contents

def create_dir(path):
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)

def run(qasm_str, hardware_name, triq_optimization):
    """
    Parameters:
        qasm_path:
        hardware_name:
        triq_optimization:
    """
    tmp_hw_name = hardware_name
    if hardware_name == "ibmq_qasm_simulator":
        tmp_hw_name = "ibm_perth"

    # triq_path = os.path.expanduser("~/TriQ/")
    triq_path = os.path.expanduser("~/qem_platform/wrappers/triq_wrapper/")
    # out_path = os.path.expanduser("./result/triq/qasm")
    # dag_path = os.path.expanduser("./result/triq/dag")
    out_path = os.path.expanduser("./")
    dag_path = os.path.expanduser("./")

    # create_dir(out_path)
    # create_dir(dag_path)

    now_time = datetime.now().strftime("%Y%m%d%H%M%S")

    file_name = now_time + ".txt"
    base_name = '.'.join(file_name.split('.')[:-1])

    # out_file=open("log/"+ base_name + "-" + hardware_name + "-" + str(triq_optimization) + ".log",'w+')
    # out_file=open("log/output.log",'w+')

    dag_name = base_name + ".in"
    out_name = base_name + ".qasm"

    dag_file_path = os.path.join(dag_path, dag_name)
    out_file_path = os.path.join(out_path, out_name)

    # print(qasm_str)

    # parse qasm into .in
    parse_ir(qasm_str, os.path.join(dag_path, dag_name))

    # call triq
    call_triq = [os.path.join(triq_path, "triq"), 
                dag_file_path, 
                out_file_path, tmp_hw_name, str(triq_optimization)]
    # print(call_triq)
    # sp.call(call_triq, stdout=out_file)
    # Run the command and wait for it to complete
    # p = sp.Popen(call_triq, stdout=out_file, text=True, shell=False)    
    p = sp.Popen(call_triq, text=False, shell=False)    
    p.communicate()
    p.terminate()
    p.wait()
    p.kill()

    result_qasm = read_file(out_file_path)

    if (os.path.isfile(dag_file_path)):
        os.remove(dag_file_path)

    if (os.path.isfile(out_file_path)):
        os.remove(out_file_path)

    return result_qasm


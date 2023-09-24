"""
file name: laura_wrapper.py
author: Handy, Laura, Fran
date: 14 September 2023

This module provides all the function necesary to run Laura's version of TriQ

Functions:
- run(qasm_path, hardware_name): run the optimization from Laura's version of TriQ

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
        if loop_times > 10:
            break
        
        try:
            with open(file_path, "r") as file:
                # Read the contents of the file and store them in the variable
                file_contents = file.read()

                success = True

        except FileNotFoundError:
            print(f"File not found: {file_path}")
            time.sleep(30)
            loop_times += 1
        except Exception as e:
            print(f"An error occurred: {str(e)}")

        return file_contents

def create_dir(path):
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)

def run(qasm_str, hardware_name):
    """
    Parameters:
        qasm_path:
        hardware_name:
        triq_optimization:
    """

    triq_path = os.path.expanduser("~/qem_platform/wrappers/laura_wrapper/")
    out_path = os.path.expanduser("./")
    dag_path = os.path.expanduser("./")

    now_time = datetime.now().strftime("%Y%m%d%H%M%S")

    file_name = now_time + ".txt"
    base_name = '.'.join(file_name.split('.')[:-1])

    # out_file=open("log/"+ base_name + "-" + hardware_name + "-" + str(triq_optimization) + ".log",'w+')
    out_file=open("log/output.log",'w+')

    dag_name = base_name + ".in"
    out_name = base_name + ".qasm"

    dag_file_path = os.path.join(dag_path, dag_name)
    out_file_path = os.path.join(out_path, out_name)

    # parse qasm into .in
    parse_ir(qasm_str, os.path.join(dag_path, dag_name))

    # call triq
    call_triq = [os.path.join(triq_path, "laura"), 
                dag_file_path, 
                out_file_path, hardware_name, "2"]
    # print(call_triq)
    # sp.call(call_triq, stdout=out_file)
    # Run the command and wait for it to complete
    p = sp.Popen(call_triq, stdout=out_file, text=True, shell=False)    
    # p = sp.Popen(call_triq, text=False, shell=False)    
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


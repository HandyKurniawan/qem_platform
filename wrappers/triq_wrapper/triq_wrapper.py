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
from commons import calibration_type_enum, sql_query, normalize_counts, Config

conf = Config()

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

    print(out_file_path)
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
    conn = mysql.connector.connect(**conf.mysql_config)
    cursor = conn.cursor()

    # get last calibration id
    cursor.execute('''SELECT calibration_id, 2q_native_gates FROM calibration_data.ibm i
INNER JOIN calibration_data.hardware h ON i.hw_name = h.hw_name
WHERE i.hw_name = %s ORDER BY calibration_datetime DESC LIMIT 0, 1;
                    ''', (conf.hardware_name, ))
    results = cursor.fetchall()
    calibration_id, native_gates_2q = results[0]

    # get 1 qubit gate error
    cursor.execute('''SELECT calibration_id, qubit, 1 - x_error as fidelity_1q 
                   FROM calibration_data.ibm_one_qubit_gate_spec 
                   WHERE calibration_id = %s;
                    ''', (calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/" + conf.hardware_name + "_real_S.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit, fidelity_1q = res
            f.write("{} {} \n".format(qubit, fidelity_1q))

        f.close()

    # get 2 qubit gate error
    cursor.execute('''SELECT calibration_id, qubit_control, qubit_target, ROUND(1 - ''' + native_gates_2q + '''_error, 6) as fidelity_2q
                   FROM calibration_data.ibm_two_qubit_gate_spec 
                   WHERE calibration_id = %s ;
                    ''', (calibration_id, ))
    # AND ''' + native_gates_2q + '''_error != 1
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/" + conf.hardware_name + "_real_T.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit_control, qubit_target, fidelity_2q = res
            f.write("{} {} {} \n".format(qubit_control, qubit_target, fidelity_2q))

        f.close()

    # get readout error
    cursor.execute('''SELECT calibration_id, qubit, 1 - readout_error as readout_fidelity
                   FROM calibration_data.ibm_qubit_spec 
                   WHERE calibration_id = %s;
                    ''', (calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/" + conf.hardware_name + "_real_M.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit, readout_fidelity = res
            f.write("{} {}\n".format(qubit, readout_fidelity))

        f.close()

    conn.close()
    
def generate_recent_average_calibration_data(qem, days):
    # Connect to the MySQL database
    conn = mysql.connector.connect(**qem.mysql_config)
    cursor = conn.cursor()

    # get last calibration id
    cursor.execute('''SELECT calibration_id, 2q_native_gates FROM calibration_data.ibm i
INNER JOIN calibration_data.hardware h ON i.hw_name = h.hw_name
WHERE i.hw_name = %s ORDER BY calibration_datetime DESC LIMIT 0, 1;
                    ''', (qem.hardware_name, ))
    results = cursor.fetchall()
    calibration_id, native_gates_2q = results[0]

    # get 1 qubit gate error
    cursor.execute('''
SELECT qubit, AVG(x_fidelity), STDDEV(x_fidelity), MAX(x_fidelity), MIN(x_fidelity) FROM (
SELECT DISTINCT qubit, 1 - x_error AS x_fidelity, x_date 
FROM calibration_data.ibm_one_qubit_gate_spec q
WHERE q.hw_name = %s
AND x_date BETWEEN date_add(now(), INTERVAL %s DAY) AND now()
) X GROUP BY qubit;
                    ''', (qem.hardware_name, days * -1))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/{}_recent_{}_S.rlb".format(qem.hardware_name, days), "w+")
        f.write("{}\n".format(count))
        for res in results:
            qubit, fidelity_1q, fidelity_1q_std, fidelity_1q_max, fidelity_1q_min = res
            f.write("{} {} \n".format(qubit, fidelity_1q))

        f.close()

    # get 2 qubit gate error
    cursor.execute('''
SELECT qubit_control, qubit_target, AVG(''' + native_gates_2q + '''_fidelity), STDDEV(''' + native_gates_2q + '''_fidelity), 
MAX(''' + native_gates_2q + '''_fidelity), MIN(''' + native_gates_2q + '''_fidelity) FROM (
SELECT DISTINCT qubit_control, qubit_target, 1 - ''' + native_gates_2q + '''_error AS ''' + native_gates_2q + '''_fidelity, 
''' + native_gates_2q + '''_date 
FROM calibration_data.ibm_two_qubit_gate_spec q
WHERE q.hw_name = %s AND ''' + native_gates_2q + '''_error != 1
AND ''' + native_gates_2q + '''_date BETWEEN date_add(now(), INTERVAL %s DAY) AND now()
) X GROUP BY qubit_control, qubit_target;
                    ''', (qem.hardware_name, days * -1))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/{}_recent_{}_T.rlb".format(qem.hardware_name, days), "w+")
        f.write("{}\n".format(count))
        for res in results:
            qubit_control, qubit_target, fidelity_2q, fidelity_2q_std, fidelity_2q_max, fidelity_2q_min = res
            f.write("{} {} {} \n".format(qubit_control, qubit_target, fidelity_2q))

        f.close()

    # get readout error
    cursor.execute('''
SELECT qubit, AVG(readout_fidelity), STDDEV(readout_fidelity), MAX(readout_fidelity), MIN(readout_fidelity) FROM (
SELECT DISTINCT qubit, 1 - readout_error AS readout_fidelity, readout_error_date FROM calibration_data.ibm_qubit_spec q
INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
WHERE i.hw_name = %s AND readout_error_date BETWEEN date_add(now(), INTERVAL %s DAY) AND now()
) X GROUP BY qubit;
                    ''', (qem.hardware_name, days * -1))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/{}_recent_{}_M.rlb".format(qem.hardware_name, days), "w+")
        f.write("{}\n".format(count))
        for res in results:
            qubit, readout_fidelity, readout_fidelity_std, readout_fidelity_max, readout_fidelity_min = res
            f.write("{} {}\n".format(qubit, readout_fidelity))

        f.close()

    conn.close()

def generate_mix_calibration_data(qem):
    # Connect to the MySQL database
    conn = mysql.connector.connect(**qem.mysql_config)
    cursor = conn.cursor()

    # get last calibration id
    cursor.execute('''SELECT calibration_id, 2q_native_gates, DATE_FORMAT(calibration_datetime, '%Y%m%d') 
FROM calibration_data.ibm i
INNER JOIN calibration_data.hardware h ON i.hw_name = h.hw_name
WHERE i.hw_name = %s ORDER BY calibration_datetime DESC LIMIT 0, 1;
''', (qem.hardware_name, ))
    results = cursor.fetchall()
    calibration_id, native_gates_2q, calibration_date = results[0]

    # get readout fidelity
    cursor.execute('''SELECT calibration_id, q.qubit, 
CASE WHEN DATE_FORMAT(q.readout_error_date , '%Y%m%d') = %s 
THEN 1 - readout_error ELSE readout_fidelity_avg - readout_fidelity_std END AS readout_fidelity
FROM calibration_data.ibm_qubit_spec q
INNER JOIN (SELECT qubit, AVG(readout_fidelity) AS readout_fidelity_avg, 
STDDEV(readout_fidelity) AS readout_fidelity_std, 
MAX(readout_fidelity) AS readout_fidelity_max, 
MIN(readout_fidelity) AS readout_fidelity_min FROM (
SELECT DISTINCT qubit, 1 - readout_error AS readout_fidelity, readout_error_date FROM calibration_data.ibm_qubit_spec q
INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
WHERE i.hw_name = %s) X GROUP BY qubit) a ON q.qubit = a.qubit
WHERE q.calibration_id = %s;
''', (calibration_date, qem.hardware_name, calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/" + qem.hardware_name + "_mix_M.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit, readout_fidelity = res
            f.write("{} {} \n".format(qubit, readout_fidelity))

        f.close()

    # get 1 qubit gate error
    cursor.execute('''SELECT calibration_id, q.qubit, 
CASE WHEN DATE_FORMAT(q.x_date , '%Y%m%d') = %s 
THEN 1 - x_error ELSE x_fidelity_avg - x_fidelity_std END AS fidelity_2q
FROM calibration_data.ibm_one_qubit_gate_spec q
INNER JOIN (SELECT qubit, AVG(x_fidelity) AS x_fidelity_avg, 
STDDEV(x_fidelity) AS x_fidelity_std, 
MAX(x_fidelity) AS x_fidelity_max, 
MIN(x_fidelity) AS x_fidelity_min FROM (
SELECT DISTINCT qubit, 1 - x_error AS x_fidelity, x_date FROM calibration_data.ibm_one_qubit_gate_spec q
INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
WHERE i.hw_name = %s) X GROUP BY qubit) a ON q.qubit = a.qubit
WHERE q.calibration_id = %s;
''', (calibration_date, qem.hardware_name, calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/" + qem.hardware_name + "_mix_S.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit, fidelity_1q = res
            f.write("{} {}\n".format(qubit, fidelity_1q))

        f.close()

# - ''' + native_gates_2q + '''_fidelity_std

    # get 2 qubit gate error
    cursor.execute('''SELECT calibration_id, q.qubit_control, q.qubit_target, 
CASE WHEN DATE_FORMAT(q.''' + native_gates_2q + '''_date , '%Y%m%d') = %s 
THEN 1 - ''' + native_gates_2q + '''_error ELSE ''' + native_gates_2q + '''_fidelity_avg END AS ''' + native_gates_2q + '''_fidelity
FROM calibration_data.ibm_two_qubit_gate_spec q
INNER JOIN (SELECT qubit_control, qubit_target, AVG(''' + native_gates_2q + '''_fidelity) AS ''' + native_gates_2q + '''_fidelity_avg, 
STDDEV(''' + native_gates_2q + '''_fidelity) AS ''' + native_gates_2q + '''_fidelity_std, 
MAX(''' + native_gates_2q + '''_fidelity) AS ''' + native_gates_2q + '''_fidelity_max, 
MIN(''' + native_gates_2q + '''_fidelity) AS ''' + native_gates_2q + '''_fidelity_min FROM (
SELECT DISTINCT qubit_control, qubit_target, 1 - ''' + native_gates_2q + '''_error AS ''' + native_gates_2q + '''_fidelity, ''' + native_gates_2q + '''_date FROM calibration_data.ibm_two_qubit_gate_spec q
INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
WHERE i.hw_name = %s) X GROUP BY qubit_control, qubit_target) a ON q.qubit_control = a.qubit_control AND q.qubit_target = a.qubit_target
WHERE q.calibration_id = %s AND ''' + native_gates_2q + '''_error != 1;
''', (calibration_date, qem.hardware_name, calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        f = open("./config/" + qem.hardware_name + "_mix_T.rlb", "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit_control, qubit_target, fidelity_2q = res
            f.write("{} {} {} \n".format(qubit_control, qubit_target, fidelity_2q))
            

        f.close()

    conn.close()


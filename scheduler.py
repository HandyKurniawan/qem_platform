import requests
import datetime
import mysql.connector
import numpy as np
import json
import math

from qiskit import *
from qiskit.result import *
from qiskit_ibm_provider import IBMProvider
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.providers import JobStatus

MY_TOKEN = "be81173902a0621551ef756bf79487c1d3c8d9860521a72758f60179feaa83ffa7d6ec24ecdf8a60acae47c1c94964dda78c278607152303cfd0a950c1cac22e"
# MY_TOKEN = "3efc1f6d5ced29bfa09060c23d32577dc5346087b8b86052cb5479652653a45a1698bec0a0ad45cd9ab255d12d8f5b47c3c1b154edab4ec6e66c52a9428a8905"
IBMProvider.save_account(MY_TOKEN,overwrite=True )
provider = IBMProvider()
backend = provider.get_backend("ibm_perth")
service = QiskitRuntimeService()

# MySQL connection parameters
mysql_config = {
    'user': 'handy',
    'password': 'handy',
    'host': 'ec2-34-228-189-223.compute-1.amazonaws.com',
    'database': 'calibration_data'
}

def get_pending_jobs():
    '''
    Returns job_id if the status in the calibration_data.result_detail table is pending (job has been sent to backend and we are waiting for the result)
    '''
    
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        # cursor.execute('SELECT id, job_id FROM calibration_data.result_detail WHERE status = %s LIMIT 0 , 500 ' , ('pending', ))
        cursor.execute('SELECT id, job_id FROM calibration_data.result_detail WHERE status = %s AND user_id = 99 LIMIT 0 , 500 ' , ('pending', ))

        #cursor.execute('SELECT id, job_id FROM calibration_data.result_detail WHERE status = %s AND header_id = %s LIMIT 0, 100 ', ('pending', 26, ))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

    except Exception as e:
        print("An error occurred:", str(e))
        
    return results

def update_result_detail_status(detail_id, new_status):
    '''
    Updates calibration_data.result_detail entries that contained prev_status to new_status
    '''
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        cursor.execute('UPDATE calibration_data.result_detail SET status= %s WHERE id = %s', (new_status, detail_id))
        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print("An error occurred:", str(e))

def check_result_availability(service, detail_id, job_id):
    print('')
    print("Checking results for: ", job_id)
    try:
        # service = QiskitRuntimeService()
        job = service.job(job_id)

        # print(job.status())

        if(job.status() == JobStatus.ERROR):
            update_result_detail_status(detail_id, "error")
            return

        if(job.status() != JobStatus.DONE):
            return 10

        result_dict = job.result().to_dict()
        result_json = json.dumps(result_dict, default=str)
        execution_time = job.result().time_taken
        #print("Execution time: ", execution_time)
        counts =json.dumps(dict(job.result().get_counts()))
        shots = job.result().results[0].shots
        #print("Shots: ", shots)
        try:
            conn = mysql.connector.connect(**mysql_config)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO calibration_data.result_backend_json (detail_id, result, execution_time, counts, shots) VALUES (%s, %s, %s, %s, %s)',
                                    (detail_id, result_json, execution_time, counts, shots))
            conn.commit()
            cursor.close()
            conn.close()
            update_result_detail_status(detail_id, 'executed')

            return 1

        except Exception as e:
            print("An error occurred:", str(e))

    except Exception as e:
        print("Result not available yet", str(e))

def get_executed_jobs():
    '''
    Returns job_id if the status in the calibration_data.result_detail table is executed (job has been executed in the backend and we have to compute metrics)
    '''
    
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        cursor.execute('SELECT id, job_id FROM calibration_data.result_detail WHERE status = %s', ('executed', ))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

    except Exception as e:
        print("An error occurred:", str(e))
        
    return results

def get_circuit(qc=None):
    if isinstance(qc, str):
        try:
            qc = QuantumCircuit.from_qasm_file(qc)
        except Exception as e:
            try: 
                qc = QuantumCircuit.from_qasm_str(qc)
            except Exception as ex:
                raise ValueError("Input circuit must be a string path to QASM file, QASM string or a QuantumCircuit object")
    if not (isinstance(qc, str) or isinstance(qc, QuantumCircuit)):
        raise ValueError("Input must be a string or a QuantumCircuit object")
    return qc

def normalize_counts(result_counts, shots=8192):
    result_counts = json.loads(result_counts)
    new_keys = []
    for key, value in result_counts.items():
        new_keys.append(str(int(key)))
   
    result_counts = dict(zip(new_keys, list(result_counts.values())))

    return {key: value / shots for key, value in result_counts.items()}

def get_metrics(detail_id, job_id):
    print("")
    print("Getting qasm for ", detail_id)
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        cursor.execute('SELECT updated_qasm FROM calibration_data.result_updated_qasm WHERE detail_id = %s', (detail_id, ))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        #print(results)

    except Exception as e:
        print("An error occurred:", str(e))
    
    for result in results:
        updated_qasm = result
        updated_qasm = updated_qasm[0]
   
    qc = get_circuit(updated_qasm)
    #print(qc)
    total_gate_count= sum(qc.count_ops().values())
    #print("total_gate_count: ", total_gate_count)
    total_gate_count_by_type = qc.count_ops()
    #print('total_gate_count_by_type: ', total_gate_count_by_type)
    
    count_1q = 0
    for key, value in dict(qc.count_ops()).items():
        if key != 'cx' and key != "cy" and key != "cz" and key != "ch" and key != "crz" and key != "cp" and key != "cu" and key != "swap":
            count_1q += value
    #print('1q gates: ', count_1q)

    count_2q = 0
    for key, value in dict(qc.count_ops()).items():
        if key == 'cx' or key == "cy" or key == "cz" or key == "ch" or key == "crz" or key == "cp" or key == "cu" or key == "swap":
            count_2q += value
    #print('2q gates: ', count_2q)
    
    qc_depth = qc.depth()
    #print('Depth: ', qc_depth)
    
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        cursor.execute('''SELECT d.id, d.header_id, d.job_id, d.status, c.gates, c.correct_output, c.qasm
                        FROM calibration_data.result_detail d
                        INNER JOIN calibration_data.result_header h ON d.header_id = h.id
                        INNER JOIN calibration_data.circuit c ON h.circuit_id = c.circuit_id
                        WHERE d.job_id = %s
                    ''', (job_id, ))
        
        results = cursor.fetchall()
        cursor.execute('SELECT shots, counts, execution_time FROM calibration_data.result_backend_json WHERE detail_id = %s', (detail_id, ))
        backend_result = cursor.fetchall()
        cursor.execute('')
        cursor.close()
        conn.close()
    except Exception as e:
        print("An error occurred:", str(e))
    
    for result in results:
        id, header_id, job_id, status, gates, correct_output, qasm = result
        #print(job_id, ': ', correct_output)

    for result in backend_result:
        shots = result[0]
        counts = result[1]
        ex_time = result[2]

    new_keys = []
    for key, value in json.loads(counts).items():
        new_keys.append(str(int(key))) 
   
    sr_nassc = 0

    correct_output = normalize_counts(correct_output)
    qc_counts = normalize_counts(counts)

    for key, value in qc_counts.items():
        if key in correct_output:
            sr_nassc = sr_nassc + value

    #print('sr_nassc: ',sr_nassc)    
    #correct_output = normalize_counts(correct_output)
    #qc_counts = normalize_counts(counts)
    #print(qc_counts)

    sr_aux = 0
    for key, value in qc_counts.items():
        if key in correct_output:
            sr_aux = sr_aux + abs(correct_output[key] - value)
        else: 
            sr_aux = sr_aux + value

    tvd=sr_aux/2
    #print('sr_tvd: ', 1-tvd)

    hd_aux = 0
    for key, value in qc_counts.items():
        if key in correct_output:
            hd_aux = hd_aux + (math.sqrt(correct_output[key]) - math.sqrt(value))**2
        else: 
            hd_aux = hd_aux + value
    hd = math.sqrt(hd_aux)/math.sqrt(2)
    #print(hd)

    #print('ex_time: ', ex_time)

    f_1q_gate = 0.8
    f_2q_gate = 0.8
    k = 0.995
    qc_cost = -np.log(k) * qc_depth - np.log(f_1q_gate) * count_1q - np.log(f_2q_gate) * count_2q

    #print(qc_cost)

    metrics_info = {
                    "total_gate_count": total_gate_count,
                    "total_gate_count_by_type": total_gate_count_by_type,
                    "1-qubit_gate_count": count_1q,
                    "2-qubit_gate_count": count_2q,
                    "circuit_depth": qc_depth,
                    "circuit_cost": qc_cost,
                    "success_rate(1-tvd)": 1 - tvd,
                    "success_rate(nassc)": sr_nassc,
                    "hellinger_distance": hd,
                    "execution_time": ex_time   
                    }
    metrics_info = json.dumps(metrics_info)
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO calibration_data.metric (detail_id, metric_json) VALUES (%s, %s)',
                                (detail_id, metrics_info))
        conn.commit()
        cursor.close()
        conn.close()
        update_result_detail_status(detail_id, 'done')

    except Exception as e:
        print("An error occurred:", str(e))

    


    
if __name__ == "__main__":
    pending_jobs = get_pending_jobs()
    print('Pending jobs: ', pending_jobs)
    service = QiskitRuntimeService()
    for result in pending_jobs:
        detail_id, job_id = result
        status = check_result_availability(service, detail_id, job_id)
        # print(status, job_id)

        if (status == 10):
            break

    executed_jobs = get_executed_jobs()
    print('Executed jobs', executed_jobs)
    for result in executed_jobs:
        detail_id, job_id = result
        try:
             get_metrics(detail_id, job_id)
        except Exception as e:
             print("Error metric:", str(e))

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
from qiskit.primitives import SamplerResult
from qiskit_ibm_runtime.utils.runner_result import RunnerResult

# MySQL connection parameters
mysql_config = {
    'user': 'handy',
    'password': 'handy',
    'host': 'localhost',
    'database': 'calibration_data'
}

#'host': 'ec2-3-80-240-233.compute-1.amazonaws.com',

ibm_perth_format = '{0:07b}'

def get_pending_jobs():
    '''
    Returns job_id if the status in the calibration_data.result_detail table is pending (job has been sent to backend and we are waiting for the result)
    '''
    
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT distinct h.id, d.job_id, qiskit_token FROM calibration_data.result_header h 
                    INNER JOIN calibration_data.result_detail d ON h.id = d.header_id
                    WHERE status = "pending" and h.user_id NOT IN (98, 99);''')
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()

    except Exception as e:
        print("An error occurred:", str(e))
        
    return results

def update_result_detail_status(conn, detail_id, new_status):
    '''
    Updates calibration_data.result_detail entries that contained prev_status to new_status
    '''
    cursor = conn.cursor()
    cursor.execute('UPDATE calibration_data.result_detail SET status= %s WHERE id = %s', (new_status, detail_id))
    conn.commit()
    cursor.close()

def update_result_detail_status_by_header_id(conn, header_id, new_status):
    '''
    Updates calibration_data.result_detail entries that contained prev_status to new_status by header_id
    '''
    cursor = conn.cursor()
    cursor.execute('UPDATE calibration_data.result_detail SET status= %s WHERE header_id = %s', (new_status, header_id))
    conn.commit()
    cursor.close()
        

def check_result_availability(service, header_id, job_id):
    print('')
    print("Checking results for: ", job_id)
    try:

        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        # service = QiskitRuntimeService()
        job = service.job(job_id)

        # print(job.status())

        if(job.status() == JobStatus.ERROR):
            update_result_detail_status_by_header_id(conn, header_id, "error")
            cursor.close()
            conn.close()
            return

        if(job.status() != JobStatus.DONE):
            cursor.close()
            conn.close()
            return 10

        # get list of detail_id here
        cursor.execute('SELECT id FROM calibration_data.result_detail WHERE status = %s AND header_id = %s LIMIT 0, 100 ', ('pending', header_id, ))
        results = cursor.fetchall()

        if (type(job.result()) is SamplerResult):
            quasi_dists = job.result().quasi_dists

            avg_result = {}
            no_of_optimization = len(results)
            no_of_result = len(quasi_dists)

            idx_1, idx_2 = 0, 0

            runs = int(no_of_result / no_of_optimization)

            for res in results:
                detail_id = res[0]
                avg_result[detail_id] = []
                sum_result = {}

                for j in range(runs):
                    res_dict = quasi_dists[idx_1]
                    
                    for key, value in res_dict.items():
                        key_bin = ibm_perth_format.format(key)
                        sum_result[key_bin] = 0
                        
                    idx_1 += 1
                    
                for j in range(runs):
                    res_dict = quasi_dists[idx_2]
                    
                    for key, value in res_dict.items():
                        key_bin = ibm_perth_format.format(key)
                        sum_result[key_bin] += value
                        
                    idx_2 += 1
                    
                for key, value in sum_result.items():
                    sum_result[key] /= runs
    
                avg_result[detail_id] = json.dumps(sum_result, default=str)
                shots = 8192

                compiled_qasm = job.inputs["circuits"][idx_2-1].qasm()
                
                #tmp_total = 0
                #for j in job.result().quasi_dists[0].keys():
                #    tmp_total += sum_result[j]
                cursor.execute('''INSERT INTO calibration_data.result_backend_json 
                               (detail_id, result, execution_time, counts, shots, quasi_dists, result_type) 
                               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                                            (detail_id, None, 0, 0, shots, avg_result[detail_id], "sampler"))
                
                cursor.execute('UPDATE calibration_data.result_updated_qasm SET updated_qasm= %s WHERE detail_id = %s', (compiled_qasm, detail_id))

                conn.commit()


                update_result_detail_status(conn, detail_id, 'executed')
        elif (type(job.result()) is RunnerResult):  

            avg_result = {}
            count_list = job.result().get_counts()
            no_of_optimization = len(results)
            no_of_result = len(count_list)
            runs = int(no_of_result / no_of_optimization)
            
            
            idx_1, idx_2 = 0, 0
            runs = int(no_of_result / no_of_optimization)
            for res in results:
                detail_id = res[0]
                avg_result[detail_id] = []

                sum_result = {}
                for j in range(runs):
                    res_dict = count_list[idx_1]
                    
                    for key, value in res_dict.items():
                        key_bin = ibm_perth_format.format(int(key, base=2))
                        sum_result[key_bin] = 0
                        
                    idx_1 += 1
                    
                for j in range(runs):
                    res_dict = count_list[idx_2]
                    
                    for key, value in res_dict.items():
                        key_bin = ibm_perth_format.format(int(key, base=2))
                        sum_result[key_bin] += value
                        
                    idx_2 += 1
                    
                for key, value in sum_result.items():
                    sum_result[key] /= runs
                        
                avg_result[detail_id] = (json.dumps(sum_result, default=str))
                
                # result_dict = job.result().to_dict()
                # result_json = json.dumps(result_dict, default=str)
                execution_time = job.result().time_taken
                #print("Execution time: ", execution_time)
                counts = avg_result[detail_id]
                shots = job.result().results[0].shots

                compiled_qasm = job.inputs["circuits"][idx_2-1].qasm()
                
                cursor.execute('INSERT INTO calibration_data.result_backend_json (detail_id, result, execution_time, counts, shots, result_type) VALUES (%s, %s, %s, %s, %s, %s)',
                                        (detail_id, None, execution_time, counts, shots, "circuit-runner"))
                
                cursor.execute('UPDATE calibration_data.result_updated_qasm SET updated_qasm= %s WHERE detail_id = %s', (compiled_qasm, detail_id))

                conn.commit()
                update_result_detail_status(conn, detail_id, 'executed')
        else:
            pass

        cursor.close()
        conn.close()

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
        new_keys.append(ibm_perth_format.format(int(key, base=2)))
   
    result_counts = dict(zip(new_keys, list(result_counts.values())))

    return {key: value / shots for key, value in result_counts.items()}

def get_count_1q(qc):
    count_1q = 0
    for key, value in dict(qc.count_ops()).items():
        if key != 'cx' and key != "cy" and key != "cz" and key != "ch" and key != "crz" and key != "cp" and key != "cu" and key != "swap":
            count_1q += value

    return count_1q

def get_count_2q(qc):
    count_2q = 0
    for key, value in dict(qc.count_ops()).items():
        if key == 'cx' or key == "cy" or key == "cz" or key == "ch" or key == "crz" or key == "cp" or key == "cu" or key == "swap":
            count_2q += value

    return count_2q

def get_metrics(detail_id, job_id):
    print("")
    print("Getting qasm for ", detail_id)
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT updated_qasm FROM calibration_data.result_updated_qasm WHERE detail_id = %s', (detail_id, ))
        results = cursor.fetchall()
        
        for result in results:
            updated_qasm = result
            updated_qasm = updated_qasm[0]
    
        qc = get_circuit(updated_qasm)
        #print(qc)
        total_gate_count= sum(qc.count_ops().values())
        #print("total_gate_count: ", total_gate_count)
        total_gate_count_by_type = qc.count_ops()
        #print('total_gate_count_by_type: ', total_gate_count_by_type)
        
        count_1q = get_count_1q(qc)
        #print('1q gates: ', count_1q)

        count_2q = get_count_2q(qc)
        #print('2q gates: ', count_2q)
        
        qc_depth = qc.depth()
        #print('Depth: ', qc_depth)
        
        cursor.execute('''SELECT d.id, d.header_id, d.job_id, d.status, c.gates, c.correct_output, c.qasm
                        FROM calibration_data.result_detail d
                        INNER JOIN calibration_data.result_header h ON d.header_id = h.id
                        INNER JOIN calibration_data.circuit c ON h.circuit_id = c.circuit_id
                        WHERE d.job_id = %s
                    ''', (job_id, ))
        
        results = cursor.fetchall()
        cursor.execute('SELECT shots, counts, execution_time, quasi_dists, result_type FROM calibration_data.result_backend_json WHERE detail_id = %s', (detail_id, ))
        backend_result = cursor.fetchall()
        
        id, header_id, job_id, status, gates, correct_output, qasm = None, None, None, None, None, None, None
        for result in results:
            id, header_id, job_id, status, gates, correct_output, qasm = result
            #print(job_id, ': ', correct_output)

        shots, counts, ex_time, quasi_dists, result_type = None, None, None, None, None
        for result in backend_result:
            shots, counts, ex_time, quasi_dists, result_type = result

        sr_nassc = 0
        sr_aux = 0
        hd_aux = 0
        tvd = 0
        hd = 0
        sr_quasi = 0
        ex_time = 0
        if (result_type == "sampler"):
            hd = 1
            tvd = 1

            correct_output = normalize_counts(correct_output)

            quasi_dists_dict = json.loads(quasi_dists) 
            for key, value in quasi_dists_dict.items():
                if key in correct_output:
                    sr_quasi = sr_quasi + value

            qc_counts = quasi_dists_dict
            # for key, value in qc_counts.items():
            #     if key in correct_output:
            #         sr_nassc = sr_nassc + value

            # print('sr_nassc: ',sr_nassc)    
            
            for key, value in qc_counts.items():
                if key in correct_output:
                    sr_aux = sr_aux + abs(correct_output[key] - value)
                else: 
                    sr_aux = sr_aux + value

            tvd=sr_aux/2
            # print('sr_tvd: ', 1-tvd)

            for key, value in qc_counts.items():
                if key in correct_output:
                    hd_aux = hd_aux + (math.sqrt(correct_output[key]) - math.sqrt(value))**2
                else: 
                    hd_aux = hd_aux + value
            hd = math.sqrt(hd_aux)/math.sqrt(2)
            # print(hd)

            # print(correct_output)
            # print("---")
            # print(quasi_dists_dict)
            # print("---")
            # print(sr_quasi)

            sr_nassc = sr_quasi

        else:
            new_keys = []
            for key, value in json.loads(counts).items():
                new_keys.append(ibm_perth_format.format(int(key,base=2))) 
        
            correct_output = normalize_counts(correct_output)
            qc_counts = normalize_counts(counts)

            # print(correct_output)
            # print("--------")
            # print(qc_counts)

            for key, value in qc_counts.items():
                if key in correct_output:
                    sr_nassc = sr_nassc + value

            # print('sr_nassc: ',sr_nassc)    
            
            for key, value in qc_counts.items():
                if key in correct_output:
                    sr_aux = sr_aux + abs(correct_output[key] - value)
                else: 
                    sr_aux = sr_aux + value

            tvd=sr_aux/2
            # print('sr_tvd: ', 1-tvd)

            for key, value in qc_counts.items():
                if key in correct_output:
                    hd_aux = hd_aux + (math.sqrt(correct_output[key]) - math.sqrt(value))**2
                else: 
                    hd_aux = hd_aux + value
            hd = math.sqrt(hd_aux)/math.sqrt(2)
            # print(hd)

            # print('ex_time: ', ex_time)

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
                        "success_rate(quasi)": sr_quasi,
                        "hellinger_distance": hd,
                        "execution_time": ex_time   
                        }
        metrics_info = json.dumps(metrics_info)
        
        # check if the metric is already there, just update
        cursor.execute('SELECT detail_id FROM calibration_data.metric WHERE detail_id = %s', (detail_id,))
        existing_row = cursor.fetchone()

        if existing_row:
            cursor.execute('UPDATE calibration_data.metric SET metric_json = %s WHERE detail_id = %s ',
                                    (metrics_info, detail_id, ))
            conn.commit()
        else:
            cursor.execute('INSERT INTO calibration_data.metric (detail_id, metric_json) VALUES (%s, %s)',
                                    (detail_id, metrics_info))
            conn.commit()
        
        update_result_detail_status(conn, detail_id, 'done')
    except:
        print("Error in getting the metrics")

    cursor.close()
    conn.close()

if __name__ == "__main__":

    # IBMProvider.save_account(token,overwrite=True )
    # # token pepe 1
    # token = "924828a6b1671411b96c27b10123849b161154290707582dc60d0b900146ccc8fb93adda735a6d0805168b3007a8ad56f626f9f207881d5055c841a58e51a7d9"

    # # token pepe 2
    # token = "2298ebebdf52aa8ef9258a07154bc62d335af0126f2bed26502a43f32a206309618c34344db22713f54bad3dc1c7569d7d1e3a0075e0421160e83b8c50967b45"

    # # # token pepe 3
    # token = "01501f074b8bc9910185d5563408e2838951163e8f55b90a338c94c58116b92a1cd88081474827667b9d907604f2dd27eaa8399a83fbb9505a24e25875819b23"

    # # token pepe 4
    # token = "055a93864810f2fc66e4de35b13027e8e591f0d019abb91b4895971fa16a991bef0ac573457c707c3d1070e5105d8f0cdd489f842cc06723d29a233c9f483e74"

    # # token untukmain
    # token = "e9dc3b4555eaceaf68dd163b187fe3f2354d0ae5032b50f2e0a01693118c83ccdd2f86f77bb37f0983244358d776defaa18614aafede58d1d8bfaea7b51c5a98"

    # # token handyokur
    # token = "d6c68cd3c7151e9499fcaf54ff7982629e20ff25d38f32aea5b64db369985c82682f63b991dc6fc8424f4ac0349882d90a5399b03194d047b3b9b2eefb4613b3"

    # # token laura 1
    # token = "3efc1f6d5ced29bfa09060c23d32577dc5346087b8b86052cb5479652653a45a1698bec0a0ad45cd9ab255d12d8f5b47c3c1b154edab4ec6e66c52a9428a8905"
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()

    pending_jobs = get_pending_jobs()
        
    tmp_qiskit_token = ""
    header_id, job_id, qiskit_token = None, None, None
    provider, backend, service = None, None, None
    
    for result in pending_jobs:
        header_id, job_id, qiskit_token = result

        if tmp_qiskit_token == "" or tmp_qiskit_token != qiskit_token:
            IBMProvider.save_account(token=qiskit_token, overwrite=True)
            provider = IBMProvider(token = qiskit_token)
            backend = provider.get_backend("ibm_perth")
            service = QiskitRuntimeService()

        # pending_jobs = get_pending_jobs()
        print('Pending jobs: ', len(pending_jobs))
        status = check_result_availability(service, header_id, job_id)

        if (status == 10):
            continue

        tmp_qiskit_token = qiskit_token

    cursor.close()
    conn.close()

    executed_jobs = get_executed_jobs()
    print('Executed jobs', len(executed_jobs))
    for result in executed_jobs:
        detail_id, job_id = result
        try:
             get_metrics(detail_id, job_id)
        except Exception as e:
             print("Error metric:", str(e))

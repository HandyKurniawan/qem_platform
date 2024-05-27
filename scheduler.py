import mysql.connector
import numpy as np
import json

from qiskit import *
from qiskit.result import *
from qiskit_ibm_provider import IBMProvider
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.providers import JobStatus
from qiskit.primitives import SamplerResult
from qiskit_ibm_runtime.utils.runner_result import RunnerResult
from commons import Config, convert_utc_to_local, calculate_time_diff, get_count_1q, get_count_2q, \
    calculate_circuit_cost, get_correct_output_dict, calculate_success_rate_nassc, calculate_success_rate_tvd, \
    calculate_success_rate_polar, calculate_hellinger_distance, calculate_success_rate_tvd_new, \
    convert_to_json, is_mitigated, get_initial_mapping_json, normalize_counts, convert_dict_int_to_binary, reverse_string_keys
import wrappers.qiskit_wrapper as qiskit_wrapper
from wrappers.qiskit_wrapper import QiskitCircuit
import wrappers.polar_wrapper as polar_wrapper

conf = Config()

def get_pending_jobs():
    '''
    Returns job_id if the status in the calibration_data.result_detail table is pending (job has been sent to backend and we are waiting for the result)
    '''
    
    try:
        conn = mysql.connector.connect(**conf.mysql_config)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT distinct h.id, h.job_id, qiskit_token, hw_name 
                       FROM framework.result_header h 
                        INNER JOIN framework.result_detail d ON h.id = d.header_id 
                        WHERE h.status = %s ''', ("pending",))
        
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()

    except Exception as e:
        print("An error occurred:", str(e))
        
    return results


def update_result_header_status_by_header_id(cursor, header_id, new_status):
    '''
    Updates result_header entries that contained prev_status to new_status by header_id
    '''

    cursor.execute('UPDATE result_header SET status = %s, updated_datetime = NOW() WHERE id = %s', (new_status, header_id))

def update_result_header(cursor, job):
    execution_time = job.metrics()["usage"]["quantum_seconds"]
    job_time = job.metrics()["timestamps"]
    created_datetime = convert_utc_to_local(job_time["created"])
    running_datetime = convert_utc_to_local(job_time["running"])
    completed_datetime = convert_utc_to_local(job_time["finished"])
    in_queue_second = calculate_time_diff(job_time["created"], job_time["running"])


    cursor.execute("""UPDATE result_header SET status = %s, execution_time = %s, job_created_datetime = %s, 
    job_in_queue_second = %s, job_running_datetime = %s, job_completed_datetime = %s, updated_datetime = NOW()  
    WHERE job_id = %s""", ("executed", execution_time, created_datetime, 
                            in_queue_second, running_datetime, completed_datetime, job_id))

    

def check_result_availability(service, header_id, job_id):
    print("Checking results for: ", job_id, "with header id :", header_id)
    try:

        conn = mysql.connector.connect(**conf.mysql_config)
        cursor = conn.cursor()

        job = service.job(job_id)

        print(job.status())

        if(job.status() == JobStatus.ERROR or job.status() == JobStatus.CANCELLED):
            update_result_header_status_by_header_id(cursor, header_id, "error")
            conn.commit()
            cursor.close()
            conn.close()
            return

        if(job.status() != JobStatus.DONE):
            cursor.close()
            conn.close()
            return 10

        # get list of detail_id here
        cursor.execute('''SELECT d.id FROM framework.result_header h 
INNER JOIN framework.result_detail d ON h.id = d.header_id
WHERE h.status = %s AND h.job_id = %s;''', ('pending', job_id, ))
        results_details = cursor.fetchall()

        if (type(job.result()) is SamplerResult):
            quasi_dists = job.result().quasi_dists

            avg_result = {}
            std_json = {}
            qasm_dict = {}
            mitigation_overhead_dict = {}
            mitigation_time_dict = {}
            no_of_optimization = len(results_details)
            no_of_result = len(quasi_dists)
            runs = int(no_of_result / no_of_optimization)
            idx_1, idx_2 = 0, 0
            shots = job.result().metadata[0]["shots"]

            for idx, res in enumerate(results_details):
                detail_id = res[0]    
                avg_result[detail_id] = []
                std_json[detail_id] = []
                qasm_dict[detail_id] = []
                mitigation_overhead_dict[detail_id] = None
                mitigation_time_dict[detail_id] = None
                sum_result = {}
                std_dev = {}
                std_dict = {}

                for j in range(runs):
                    res_dict = quasi_dists[idx_1]
                    
                    for key, value in res_dict.items():
                        key_bin = conf.bit_format.format(key)
                        key_bin = key
                        sum_result[key_bin] = 0
                        std_dict[key_bin] = 0
                        std_dev[key_bin] = []
                        
                    idx_1 += 1

                for j in range(runs):
                    res_dict = quasi_dists[idx_2]
                    
                    for key, value in res_dict.items():
                        key_bin = conf.bit_format.format(key)
                        key_bin = key
                        sum_result[key_bin] += value
                        std_dev[key_bin].append(value)
                        
                    idx_2 += 1
                    
                for key, value in sum_result.items():
                    sum_result[key] /= runs
                    std_dict[key] = np.std(std_dev[key])

                avg_result[detail_id] = convert_to_json(sum_result)
                std_json[detail_id] = convert_to_json(std_dict)
                qasm_dict[detail_id] = job.inputs["circuits"][idx_2-1].qasm()

                if is_mitigated(job):
                    mitigation_overhead_dict[detail_id] = job.result().metadata[idx_2-1]["readout_mitigation_overhead"]
                    mitigation_time_dict[detail_id] = job.result().metadata[idx_2-1]["readout_mitigation_time"]

            for idx, res in enumerate(results_details):
                detail_id = res[0] 
                quasi_dists = avg_result[detail_id]
                quasi_dists_std = std_json[detail_id]
                qasm = qasm_dict[detail_id]
                mapping_json = get_initial_mapping_json(qasm)
                mitigation_overhead = mitigation_overhead_dict[detail_id]
                mitigation_time = mitigation_time_dict[detail_id]

                # check if the result_backend_json is already there, just update
                cursor.execute('SELECT detail_id FROM result_backend_json WHERE detail_id = %s', (detail_id,))
                existing_row = cursor.fetchone()

                if existing_row:
                    cursor.execute('''UPDATE result_backend_json SET quasi_dists = %s, quasi_dists_std = %s, qasm = %s, 
                    shots = %s, mapping_json = %s, mitigation_overhead = %s, mitigation_time = %s  WHERE detail_id = %s;''',
                    (quasi_dists, quasi_dists_std, qasm, shots, mapping_json, mitigation_overhead, mitigation_time, detail_id))
                else:
                    cursor.execute('''INSERT INTO result_backend_json 
                                    (detail_id, quasi_dists, quasi_dists_std, qasm, shots, mapping_json, mitigation_overhead, mitigation_time) 
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                    (detail_id, quasi_dists, quasi_dists_std, qasm, shots, mapping_json, mitigation_overhead, mitigation_time))
                

                update_result_header(cursor, job)

            conn.commit()
        
        else:
            pass

        cursor.close()
        conn.close()

    except Exception as e:
        print("Result not available yet", str(e))

def check_result_availability_simulator(service, header_id, job_id, hw_name):
    print("Checking results for: ", job_id, "with header id :", header_id)
    try:

        conn = mysql.connector.connect(**conf.mysql_config)
        cursor = conn.cursor()

        backend = service.get_backend(hw_name)

        cursor.execute('''SELECT d.id, q.updated_qasm, d.compilation_name, d.noise_level, h.shots 
FROM result_detail d
INNER JOIN result_header h ON d.header_id = h.id
INNER JOIN result_updated_qasm q ON d.id = q.detail_id 
LEFT JOIN framework.result_backend_json j ON d.id = j.detail_id
WHERE h.status = %s AND h.job_id = %s AND d.header_id = %s AND j.quasi_dists IS NULL  ''', ('pending', job_id, header_id,))
        results_details = cursor.fetchall()

        print(len(results_details))
        for idx, res in enumerate(results_details):
            detail_id, updated_qasm, compilation_name, noise_level, shots = res

            qc = QiskitCircuit(updated_qasm, skip_simulation=True)

            circuit = None
            if compilation_name == "triq_lcd" or compilation_name == "triq+_lcd":
                circuit = qc.transpile_to_target_backend(backend, False)
            else:
                # circuit = qc.get_native_gates_circuit(self.backend, self.run_in_simulator)
                circuit = qc.transpile_to_target_backend(backend, False)
                print("transpile to target backend")

            print("preparing the noisy simulator", compilation_name, noise_level)
            noise_model, sim_noisy, coupling_map = qiskit_wrapper.get_noisy_simulator(backend, noise_level)
            # noise_model, sim_noisy, coupling_map = qiskit_wrapper.get_noisy_simulator(backend, noise_level, noiseless=True)
            job = sim_noisy.run(circuit, shots=shots)
            # print("run the job")
            result = job.result()  
            # print("get result")
            output = result.get_counts()
            # print("get counts")
            output_normalize = normalize_counts(output, shots=shots)
            # print(output_normalize)

            quasi_dists = convert_to_json(output_normalize)
            quasi_dists_std = ""
            qasm = circuit.qasm()
            mapping_json = get_initial_mapping_json(qasm)
            mitigation_overhead = 0
            mitigation_time = 0

            # check if the result_backend_json is already there, just update
            cursor.execute('SELECT detail_id FROM result_backend_json WHERE detail_id = %s', (detail_id,))
            existing_row = cursor.fetchone()

            if existing_row:
                cursor.execute('''UPDATE result_backend_json SET quasi_dists = %s, quasi_dists_std = %s, qasm = %s, 
                shots = %s, mapping_json = %s, mitigation_overhead = %s, mitigation_time = %s  WHERE detail_id = %s;''',
                (quasi_dists, quasi_dists_std, qasm, shots, mapping_json, mitigation_overhead, mitigation_time, detail_id))
            else:
                cursor.execute('''INSERT INTO result_backend_json 
                                (detail_id, quasi_dists, quasi_dists_std, qasm, shots, mapping_json, mitigation_overhead, mitigation_time) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                (detail_id, quasi_dists, quasi_dists_std, qasm, shots, mapping_json, mitigation_overhead, mitigation_time))

            

            conn.commit()

        cursor.execute('UPDATE result_header SET status = "executed", updated_datetime = NOW() WHERE id = %s', (header_id,))
        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        print("Result not available yet", str(e))


def get_executed_jobs():
    '''
    Returns job_id if the status in the result_detail table is executed (job has been executed in the backend and we have to compute metrics)
    '''
    
    try:
        conn = mysql.connector.connect(**conf.mysql_config)
        cursor = conn.cursor()

        cursor.execute('''SELECT id, job_id FROM result_header WHERE status = %s 
                       and (user_id IN (11,12,13,14,15,16,95) OR id = 2766) and id >= 697;''', ("executed", ))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

    except Exception as e:
        print("An error occurred:", str(e))
        
    return results

def get_metrics(header_id, job_id):
    print("")
    print("Getting qasm for :", header_id, job_id)
    conn = mysql.connector.connect(**conf.mysql_config)
    cursor = conn.cursor()

    try:
        cursor.execute('''SELECT j.detail_id, j.qasm, j.quasi_dists, j.quasi_dists_std, d.circuit_name, d.compilation_name, d.noise_level 
                       FROM framework.result_backend_json j
        INNER JOIN framework.result_detail d ON j.detail_id = d.id
        INNER JOIN framework.result_header h ON d.header_id = h.id
        WHERE h.status = %s AND h.job_id = %s AND h.id = %s AND j.quasi_dists IS NOT NULL;''', ("executed", job_id, header_id))
        results_details_json = cursor.fetchall()

        print(len(results_details_json))
        for idx, res in enumerate(results_details_json):
            detail_id, qasm, quasi_dists, quasi_dists_std, circuit_name, compilation_name, noise_level = res

            n = 2
            lstate = "Z"
            if "polar" in circuit_name:
                tmp = circuit_name.split("_")
                n = int(tmp[1][1])
                if len(tmp) == 3:
                    lstate = tmp[2].upper()
            
            quasi_dists_dict = json.loads(quasi_dists) 
            # quasi_dists_std_dict = json.loads(quasi_dists_std) 
            
            qc = QuantumCircuit.from_qasm_str(qasm)
            qc = qiskit_wrapper.transpile_to_basis_gate(qc)
            total_gate = sum(qc.count_ops().values())
            total_one_qubit_gate = get_count_1q(qc)
            total_two_qubit_gate = get_count_2q(qc)
            circuit_depth = qc.depth()
            circuit_cost = calculate_circuit_cost(qc)

            if "polar" in circuit_name:
                print("get metrics: n =", n, ", lstate =", lstate)
                # total_qubit = (2**n) * (n)
                if lstate == "X":
                    if n == 2:
                        total_qubit = (2**n)
                    elif n == 3:
                        total_qubit = 12
                    elif n == 4:
                        total_qubit = 24
                else:
                    if n == 2:
                        total_qubit = 0
                    elif n == 3:
                        total_qubit = 4
                    elif n == 4:
                        total_qubit = 32
                    
                quasi_dists_dict_bin = convert_dict_int_to_binary(quasi_dists_dict, total_qubit)
                tmp = reverse_string_keys(quasi_dists_dict_bin)
                # print(quasi_dists_dict_bin)
                # print("----")
                # print(tmp)
                success_rate_polar = polar_wrapper.get_q1prep_sr(n, lstate, tmp)
                print(circuit_name, noise_level, compilation_name, success_rate_polar)

                success_rate_quasi = 0
                success_rate_nassc = 0
                success_rate_tvd = 0
                success_rate_tvd_new = 0
                hellinger_distance = 0
            else:
                correct_output = get_correct_output_dict(cursor, detail_id)
                success_rate_quasi = calculate_success_rate_nassc(correct_output, quasi_dists_dict)
                success_rate_nassc = success_rate_quasi
                # success_rate_quasi_std = calculate_success_rate_nassc(correct_output, quasi_dists_std_dict)
                success_rate_tvd = calculate_success_rate_tvd(correct_output, quasi_dists_dict)
                success_rate_tvd_new = calculate_success_rate_tvd_new(correct_output, quasi_dists_dict)
                hellinger_distance = calculate_hellinger_distance(correct_output, quasi_dists_dict)
                success_rate_polar = 0

            # check if the metric is already there, just update
            cursor.execute('SELECT detail_id FROM metric WHERE detail_id = %s', (detail_id,))
            existing_row = cursor.fetchone()

            if existing_row:
                cursor.execute("""UPDATE metric SET total_gate = %s, total_one_qubit_gate = %s, total_two_qubit_gate = %s, circuit_depth = %s, 
                circuit_cost = %s, success_rate_tvd = %s, success_rate_nassc = %s, success_rate_quasi = %s, 
                success_rate_polar = %s, hellinger_distance = %s, success_rate_tvd_new = %s
                WHERE detail_id = %s; """, 
                (total_gate, total_one_qubit_gate, total_two_qubit_gate, circuit_depth, 
                circuit_cost, success_rate_tvd, success_rate_nassc, success_rate_quasi, 
                success_rate_polar, hellinger_distance, success_rate_tvd_new, detail_id))
            else:
                cursor.execute("""INSERT INTO metric(detail_id, total_gate, total_one_qubit_gate, total_two_qubit_gate, circuit_depth, 
                circuit_cost, success_rate_tvd, success_rate_nassc, success_rate_quasi, 
                success_rate_polar, hellinger_distance, success_rate_tvd_new)
                VALUES (%s, %s, %s, %s, %s,
                %s, %s, %s, %s, 
                %s, %s, %s); """, 
                (detail_id, total_gate, total_one_qubit_gate, total_two_qubit_gate, circuit_depth, 
                circuit_cost, success_rate_tvd, success_rate_nassc, success_rate_quasi, 
                success_rate_polar, hellinger_distance, success_rate_tvd_new))
                
            # update_result_header_status_by_header_id(cursor, header_id, 'done')

            conn.commit()

    except Exception as e:
        print("Error in getting the metrics : ", e)

    update_result_header_status_by_header_id(cursor, header_id, 'done')

    conn.commit()

    cursor.close()
    conn.close()

if __name__ == "__main__":
    conn = mysql.connector.connect(**conf.mysql_config)
    cursor = conn.cursor()

    pending_jobs = get_pending_jobs()
        
    tmp_qiskit_token = ""
    header_id, job_id, qiskit_token = None, None, None
    provider, backend, service = None, None, None
    
    print('Pending jobs: ', len(pending_jobs))
    for result in pending_jobs:
        header_id, job_id, qiskit_token, hw_name = result

        if tmp_qiskit_token == "" or tmp_qiskit_token != qiskit_token:
            # QiskitRuntimeService.save_account(channel="ibm_cloud", token=qiskit_token, instance="Qiskit Runtime-ucm", overwrite=True)
            # service = QiskitRuntimeService(channel="ibm_cloud", token=qiskit_token, instance="Qiskit Runtime-ucm")

            QiskitRuntimeService.save_account(channel="ibm_quantum", token=qiskit_token, overwrite=True)
            service = QiskitRuntimeService(channel="ibm_quantum", token=qiskit_token)
        
        if job_id == "simulator":
            status = check_result_availability_simulator(service, header_id, job_id, hw_name)
        else:
            status = check_result_availability(service, header_id, job_id)

        if (status == 10):
            continue

        tmp_qiskit_token = qiskit_token

    cursor.close()
    conn.close()

    executed_jobs = get_executed_jobs()
    print('Executed jobs :', len(executed_jobs))
    for result in executed_jobs:
        header_id, job_id = result
        try:
             get_metrics(header_id, job_id)
        except Exception as e:
             print("Error metric:", str(e))

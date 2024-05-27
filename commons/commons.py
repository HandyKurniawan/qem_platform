import json
from enum import Enum
import mysql.connector
import time
import configparser
import re
from dateutil import tz
from datetime import datetime
import numpy as np
import math

class Config:
    def __init__(self):
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read('config.ini')

        self.mysql_config = {
            'user': self.config_parser['MySQLConfig']['user'],
            'password': self.config_parser['MySQLConfig']['password'],
            'host': self.config_parser['MySQLConfig']['host'],
            'database': self.config_parser['MySQLConfig']['database']
        }

        self.simulator_hardware = self.config_parser['SimulationConfig']['simulator_hardware']

        self.bit_format = self.config_parser['MathConfig']['bit_format']

        self.activate_debugging_time = True if self.config_parser['GeneralConfig']['activate_debugging_time'] == "1" else False

        self.program_type = self.config_parser['TypeConfig']['program_type']

        quantum_config_name = "QuantumConfig{}".format(self.program_type)

        self.hardware_name = self.config_parser[quantum_config_name]['hardware_name']
        self.base_folder = self.config_parser[quantum_config_name]['base_folder']
        self.shots = int(self.config_parser[quantum_config_name]['shots'])
        self.ibm_cloud_instance = self.config_parser[quantum_config_name]['ibm_cloud_instance']
        # self.qiskit_token = self.config_parser[quantum_config_name]['token']
        self.qiskit_token = ""
        self.optimization_level = int(self.config_parser[quantum_config_name]['optimization_level'])
        self.resilience_level = int(self.config_parser[quantum_config_name]['resilience_level'])
        self.rep_delay = float(self.config_parser[quantum_config_name]['rep_delay'])
        self.runs = int(self.config_parser[quantum_config_name]['runs'])
        self.repetition = int(self.config_parser[quantum_config_name]['repetition'])
        self.initialized_triq = int(self.config_parser[quantum_config_name]['initialized_triq'])
        self.user_id = int(self.config_parser[quantum_config_name]['user_id'])
        self.run_in_simulator = True if self.config_parser[quantum_config_name]['run_in_simulator'] == "1" else False
        self.triq_measurement_type = self.config_parser[quantum_config_name]['triq_measurement_type']
        self.remaining = int(self.config_parser[quantum_config_name]['remaining'])
        self.token_number = int(self.config_parser[quantum_config_name]['token_number'])
        self.skip_update_simulator = True if self.config_parser[quantum_config_name]['skip_update_simulator'] == "1" else False
        self.noisy_simulator = True if self.config_parser[quantum_config_name]['noisy_simulator'] == "1" else False
        self.noise_level = list(map(float, self.config_parser[quantum_config_name]['noise_level'].split(",")))
        self.send_to_backend = True if self.config_parser[quantum_config_name]['send_to_backend'] == "1" else False
        
conf = Config()

class triq_optimization(Enum):
    CompileOpt, CompileDijsktra, CompileRevSwaps = range(3)

class qiskit_optimization(Enum):
    level_0, level_1, level_2, level_3 = range(4)

class apply_qiskit_optimization(Enum):
    no_apply, before, after = None, "before", "after"

class qiskit_compilation_enum(Enum):
    qiskit_0, qiskit_3, qiskit_NA_avg, qiskit_NA_lcd, qiskit_NA_mix, qiskit_NA_w15, \
    qiskit_NA_avg_adj, qiskit_NA_lcd_adj, qiskit_NA_mix_adj, qiskit_NA_w15_adj, \
    qiskit_NA_wn, qiskit_NA_wn_adj, mapomatic_lcd, mapomatic_avg, mapomatic_mix, \
    mapomatic_avg_adj, mapomatic_w15_adj, \
        = "qiskit_0", "qiskit_3", "qiskit_NA_avg", "qiskit_NA_lcd", "qiskit_NA_mix", "qiskit_NA_w15", \
        "qiskit_NA_avg_adj", "qiskit_NA_lcd_adj", "qiskit_NA_mix_adj", "qiskit_NA_w15_adj", \
        "qiskit_NA_wn", "qiskit_NA_wn_adj", "mapomatic_lcd", "mapomatic_avg", "mapomatic_mix", \
        "mapomatic_avg_adj", "mapomatic_w15_adj"

class calibration_type_enum(Enum):
    lcd, average, recent_15, recent_45, mix, \
        decay_r, decay_15, decay_mix, \
    lcd_adjust, average_adjust, recent_15_adjust, mix_adjust, \
    recent_n, recent_n_adjust \
     = "real", "avg", "recent_15", "recent_45", "mix", \
        "decay_r", "decay_15", "decay_mix", \
        "real_adjust", "avg_adjust", "recent_15_adjust", "mix_adjust", \
        "recent_n", "recent_n_adjust" 

# class calibration_type_enum(Enum):
#     average, mix, realtime = "avg", "mix", "real"

def read_file(file_path):
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError as e:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def convert_to_json(dictiontary):
    return json.dumps(dictiontary, indent = 0) 

def sql_query(sql, params):
    success = False

    while not success:
        try:
            with mysql.connector.connect(**conf.mysql_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                success = True

        except Exception as e:
            print(f"An error occurred: {str(e)}. Will try again in 10 seconds...")

            for i in range(10, 0, -1):
                time.sleep(1)
                print(i)

    return results


def sql_execute(cursor, sql, parms):
    cursor.execute(sql, parms)
    
def normalize_counts(result_counts, is_json=False, shots=50000):
    if is_json:
        result_counts = json.loads(result_counts)

    result_counts = convert_dict_binary_to_int(result_counts)
    
    return {key: value / shots for key, value in result_counts.items()}

def num_sort(test_string):
    return list(map(int, re.findall(r'\d+', test_string)))[0]

def is_decimal_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_binary_number(s):
    return all(char in '01' for char in s)

def convert_dict_binary_to_int(bin_dict):
    tmp = {}
    for key, value in bin_dict.items():
        if is_binary_number(key):
            new_key = "{}".format(int(key, 2))
            tmp[new_key] = value
    int_dict = tmp

    return int_dict

def convert_dict_int_to_binary(int_dict, n):
    tmp = {}
    
    bit_format = "0:0{}b".format(n)
    bit_format = "{" + bit_format + "}"
    
    for key, value in int_dict.items():
        int_key = int(key)
        new_key = bit_format.format(int_key)
        tmp[new_key] = value
    bin_dict = tmp

    return bin_dict

def reverse_string_keys(original_dict):
    reversed_dict = {}
    
    for key, value in original_dict.items():
        if isinstance(key, str):
            reversed_key = key[::-1]
        else:
            reversed_key = key  # Keep the key unchanged if it's not a string
            
        reversed_dict[reversed_key] = value

    return reversed_dict

def is_mitigated(job):
    try:
        mitigation_overhead = job.result().metadata[0]["readout_mitigation_overhead"]
        return True
    except (IndexError, KeyError):
        return False
    

def convert_utc_to_local(datetime_utc):
    to_zone = tz.tzlocal()

    datetime_local = datetime.fromisoformat(datetime_utc.replace('Z', '+00:00')).astimezone(to_zone)
    datetime_local = datetime_local.strftime("%Y%m%d%H%M%S")

    return datetime_local

def calculate_time_diff(time_start, time_end):
    start_datetime = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
    end_datetime = datetime.fromisoformat(time_end.replace('Z', '+00:00'))
    time_difference = end_datetime - start_datetime

    return time_difference.total_seconds()    

def get_measure_lines(updated_qasm):
    lines = updated_qasm.split('\n')
    measure_lines = [line for line in lines if re.match(r'^\s*measure', line)]
    return measure_lines

def get_initial_mapping_json(updated_qasm):
    initial_mappings = []
    measure_lines = get_measure_lines(updated_qasm)
    for line in measure_lines:
        qubits = re.findall(r'q\[(\d+)\] -> c\[(\d+)\]', line)
        if len(qubits) == 1:
            initial_mappings.append((int(qubits[0][0]), int(qubits[0][1])))

    mapping = {}
    for i, j in initial_mappings:
        mapping[j] = i

    mapping_json = json.dumps(mapping, default=str)

    return mapping_json

def get_count_1q(qc):
    count_1q = 0
    for key, value in dict(qc.count_ops()).items():
        if key != 'cx' and key != "cy" and key != "cz" and key != "ch" and key != "crz" and key != "cp" and key != "cu" and key != "swap" and key != "ecr" and key != "measure":
            count_1q += value

    return count_1q

def get_count_2q(qc):
    count_2q = 0
    for key, value in dict(qc.count_ops()).items():
        if key == 'cx' or key == "cy" or key == "cz" or key == "ch" or key == "crz" or key == "cp" or key == "cu" or key == "swap" or key == "ecr":
            count_2q += value

    return count_2q

def calculate_circuit_cost(qc):
    f_1q_gate = 0.8
    f_2q_gate = 0.8
    k = 0.995
    
    circuit_depth = qc.depth()
    count_1q = get_count_1q(qc)
    count_2q = get_count_2q(qc)
    
    cost = -np.log(k) * circuit_depth - np.log(f_1q_gate) * count_1q - np.log(f_2q_gate) * count_2q

    return cost

def get_correct_output_dict(cursor, detail_id):
    cursor.execute('''SELECT c.correct_output FROM framework.result_detail d
    INNER JOIN framework.circuit c ON d.circuit_name = c.name
    WHERE d.id = %s;''', (detail_id, ))
    
    result_correct = cursor.fetchall()

    correct_output = json.loads(result_correct[0][0])

    return correct_output

def calculate_success_rate_nassc(correct_output, dists):
    success_rate = 0
    for key, value in dists.items():
        if key in correct_output:
            success_rate = success_rate + value

    return success_rate

def calculate_success_rate_tvd(correct_output, dists):
    sr_aux = 0
    success_rate = 0
    for key, value in dists.items():
        if key in correct_output:
            sr_aux = sr_aux + abs(correct_output[key] - value)
        else: 
            sr_aux = sr_aux + value

    if sr_aux == 1:
        success_rate = 0
    else:
        tvd = sr_aux / 2
        success_rate = 1 - tvd

        if tvd == 0.5:
            success_rate = 0

    return success_rate

def calculate_success_rate_tvd_new(correct_output, dists):
    sr_aux = 0
    success_rate = 0
    for key, value in dists.items():
        if key in correct_output:
            sr_aux = sr_aux + abs(correct_output[key] - value)

    tvd = sr_aux
    success_rate = 1 - tvd

    return success_rate

def calculate_success_rate_polar(correct_output, dists):
    sr_aux = 0
    success_rate = 0
    count = 0
    for key, value in dists.items():
        if key in correct_output.keys():
            sr_aux = sr_aux + value
            count = count + 1 

    success_rate = sr_aux

    return success_rate

def calculate_hellinger_distance(correct_output, dists):
    hd_aux = 0
    for key, value in dists.items():
        if key in correct_output:
            if value < 0:
                value = 0
            hd_aux = hd_aux + (math.sqrt(correct_output[key]) - math.sqrt(value))**2
        else: 
            hd_aux = hd_aux + value

    if hd_aux < 0:
        hd_aux = 0

    hellinger_distance = math.sqrt(hd_aux)/math.sqrt(2)

    return hellinger_distance
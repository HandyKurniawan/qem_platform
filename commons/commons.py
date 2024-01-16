import json
from enum import Enum
import mysql.connector
import time
import configparser

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

        self.activate_debugging_time = self.config_parser['GeneralConfig']['activate_debugging_time']

        self.hardware_name = self.config_parser['QuantumConfig']['hardware_name']
        self.base_folder = self.config_parser['QuantumConfig']['base_folder']
        self.qiskit_token = self.config_parser['QuantumConfig']['token']
        


conf = Config()

class triq_optimization(Enum):
    CompileOpt, CompileDijsktra, CompileRevSwaps = range(3)

class qiskit_optimization(Enum):
    level_0, level_1, level_2, level_3 = range(4)

class apply_qiskit_optimization(Enum):
    no_apply, before, after = None, "before", "after"

class calibration_type_enum(Enum):
    realtime, average, recent_15, recent_45, mix, \
        decay_r, decay_15, decay_mix, \
    realtime_adjust, average_adjust, recent_15_adjust, mix_adjust \
     = "real", "avg", "recent_15", "recent_45", "mix", \
        "decay_r", "decay_15", "decay_mix", \
        "real_adjust", "avg_adjust", "recent_15_adjust", "mix_adjust" 

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
    
def normalize_counts(result_counts, is_json=False, shots=8192):
    if is_json:
        result_counts = json.loads(result_counts)

    new_keys = [conf.bit_format.format(int(key, base=2)) for key in result_counts.keys()]
    result_counts = dict(zip(new_keys, result_counts.values()))

    return {key: value / shots for key, value in result_counts.items()}
import json
from enum import Enum
import mysql.connector
import time

mysql_config = {
    'user': 'handy',
    'password': 'handy',
    'host': 'ec2-16-171-254-2.eu-north-1.compute.amazonaws.com',
    'database': 'calibration_data'
}

bit_format = '{0:0127b}'

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
            # Read the contents of the file and store them in the variable
            file_contents = file.read()

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return file_contents

def convert_to_json(dictiontary):
    return json.dumps(dictiontary, indent = 0) 

def sql_query(sql, parms):
    success = False

    while not success:
        try:
            # Connect to the MySQL database
            conn = mysql.connector.connect(**mysql_config)
            cursor = conn.cursor()
            
            # insert to circuit
            cursor.execute(sql, parms)
            
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()

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
    new_keys = []
    for key, value in result_counts.items():
        new_keys.append(bit_format.format(int(key, base=2)))
   
    result_counts = dict(zip(new_keys, list(result_counts.values())))

    return {key: value / shots for key, value in result_counts.items()}
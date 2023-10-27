import json
from enum import Enum

class triq_optimization(Enum):
    CompileOpt, CompileDijsktra, CompileRevSwaps = range(3)

class qiskit_optimization(Enum):
    level_0, level_1, level_2, level_3 = range(4)

class apply_qiskit_optimization(Enum):
    no_apply, before, after = None, "before", "after"

class calibration_type_enum(Enum):
    average, realtime, decay, recent = "avg", "real", "decay", "recent"

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
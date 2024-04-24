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

        self.token_list = []
        if self.program_type == "PolarRepeat":
            self.token_list = [
            # still working
            # cornice.poker_0g@icloud.com
            "bfbe3159e00973e14168671f8790ab7d2b85e8cb61160ee0b17225cf312df48e582cad577b02781ddca79d382e9e3aba3ad9c46c9c47d1b1b5ed27c8815cc2ca",
            # petrol
            "c0151c25a1bcb6e3f9274fb403cacf619f2508b2e70fcf350f1e44aba618f8d379f63f3554f58d2b6b7e04a63f20ba14895857e50b598c2c584c1b6519e6bc61",
            # mash
            "76eaa6f112f125eae669975b89d1620f8ea96cc9c28c650a2d9bed8e171d1ddf21aa685f46fa5d9377a86f7526ace1477c37f5fd5b0e8c0b0a25813a958958ce",
            # bylaw
            "30ea7c188f2b6531d2525875b7dab58f0d0091cb4c6e080472cdc76a96009aabbc3367ee1e1ac5f1aa2229941b08a7ef487066df163d47545c9524c4cad1c2ed",
            # puffs-undoing.02@icloud.com
            "266686280de68a1d68433c62d7e154391b905705041b43744a591c19528cefb7335fa425ea81855fd0ca88ae7950b726dd615c23b53bc14a99e579874aa1202f",
            # shanty
            "88fa7b6ee1ba1303c21d4a46cc6db9b44bfc1c4a86ff4d10476d5c6a28b7b2427e23c0cb7430ef103ac38310f74a71791a03aee26e2b9cdad266ef0a120d7c71",
            # pipe
            "f4376ab6435cab311bd27c6a403617cff71804667f537c72879fd68fc2e80ff8fc3c2c67509fa840f2ac39318604154319858e71434b35db9570568614c51d63",
            # lodging
            "73e5caa60d526c2122261d8b1d93d451f8e8add930a03d2ab6fe16702673ccfcdce9dd018820f5ca6bed692112c9a5d32e2d2f2b75d367d38dde3ed2a51e3c6b",
            # bionic
            "dc8be56745da5fe77438ee9a3cfc0b6fa87f219ec3e50db59788cf157ed43ed776a1986b569ad5ec57525aa5f299fdb17c90cb34d3a04be7ca4af1bfbbc85eca",
            # ales
            "7f531e9960905f9a3142ead5d8c004bf5dc39a59462dd70e5f623918bd539fecc0f7434dcbbf453aecad2cc6545595ce1f9edfbb029fc948e6e22c35ebf5e331",
            # anion
            "4bcab1e9db485961e3a583b52b04c7fd35f476751e1c0107406e7fa6b2b6ae899c65142ac5547842f02bd6c667b1ce92a790b107acf56c3e748d32dd63830a55",
            # lumbar
            "6955cf58b16e371d4b788ffd7602b6b1c134701f6a058a8ef02a71d6547b912f0602bc04f5e80a55ad67e4e64b29e0863b568760e7e7baa62159c975fe3df07b",
            # wool
            "af61c32894083127bf069fff6f0904e41f78c3a0e75cbf3619840b1b9377ac923a9a33893192dc830306e973e52a550d8c0c47fe59aa22177ba7eae45635f85a",
            # abalone
            "7df4633e575ac0094fd2a538a887002a745d2927c1c29d444c2360fc4572151001905be16ba478c41780212aa7c35593edd38f8b636bd595d8253b01dee89127",
            # 08.lessee.acts@icloud.com
            "887108cd60c926a48d330d614c31d496e5e191ef226b742a006869c5f56150c6fa8dc9e305301d6a7d85785319b484b1782bf98df106c4a899e69c7abafcdaa1",
            # salami
            "1fc316667164f5d54c56a31b43d7e9d12fa1d32c395727be69c77c733aee0f0468cc9178f357d6004fc636fd2ebb861dcf8af287493c818a70527dac50e06a25",
            # mammals
            "f45537aaef3c72fa31ce928a7eaad4b7f44930b48734f73e3276ff76273299b13b2dc8810fa53976c404641bb30926a6724dfe6b7afdfdbd68423389992cf344",
            # dopa
            "d312f1b28a7e5381dfe0754f5ff3ee055cc9cfab5b944250aaf58d5c822a513bd88b77cb19f7dfd7b7f955e5fbeaa266a552ba45ebbad0262965d35c59803734",
            # pepeucm1
            "924828a6b1671411b96c27b10123849b161154290707582dc60d0b900146ccc8fb93adda735a6d0805168b3007a8ad56f626f9f207881d5055c841a58e51a7d9",
            # pepedelft1
            "2298ebebdf52aa8ef9258a07154bc62d335af0126f2bed26502a43f32a206309618c34344db22713f54bad3dc1c7569d7d1e3a0075e0421160e83b8c50967b45",
            # # new
            # lintel-monody-0i@icloud.com
            "69d3c6f3f7241ff44a20ed8e4bcc445917394ebc7bc12442983aed7c9b52f55daa09e0bfa8572b1cd364f06b96b07686b0d39970eba8249c31c8b9ef62e281d7",
            # patter-slosh-0f@icloud.com
            "54a2dcecfe2b2efe441c23c9e1637ec2a9159b37d9938128c45c4a9a81ff1f6c3a947b5359b2bdf761158f6240d4b7369b162c108d900556c96fdd01847bcd55",
            ]
        elif self.program_type == "Calibration":
            self.token_list = [
                # # predawn08.upriver@icloud.com (finished)
                # "0beaf281e1990a86c4d07af4ba25d03b155038d308179b84278054e30c17ed82c7db3b2672738733462a734b5c00bd79915f4655e6f4e22a7ddd423de778f956",
                # 05twos-ammonia@icloud.com
                "099f0f6194dd06b395ff22689cc939aff14bee22bea12ac9e56a73dbc525da653c281524b7216d2550cf963fdf5053198ef887a1dfb58839f2794c0e4eacc446"
            ]
        elif self.program_type == "CalibrationScale":
            self.token_list = [
                # tappers_shuffle.0x@icloud.com
                "19362af21032b838765e5ec3bc3b0a4413501912b124ea3d6f88623561c3f5b2b3ec0c4038aa904f11b7fcc4e5ca38fee5f0b62763eda8bb0dbde14797666d96"
            ]
        elif self.program_type == "Polar":
            self.token_list = [
                # # # For Polar Real
                # # savants.pinto-0w@icloud.com
                "3cb9b0aedf5f4ba7228a0b437b36ce26dec28bf600da8789bae8fd24b1db265031df69e1aafbbfe92dc775f0ead94991400830b512005818eea3b9b448b371bc"
            ]
        
        # # 02_peanuts_sagas@icloud.com
        # "d2fc3f31fc7ed09ba8bb0b671697de32dcf709232be76c85de671ee92d80508237457aab2f98767d1566c07e506fb70be819d35e7b785600687a04c9c2e67646",
        # # advert.weights.0u@icloud.com
        # "ceaea54206809655f1db52eef61e2d13c087eee215dacc05b473c8c55ddddb490ca30a014fcfdb3a7725f97809f257a014f757e108873100ad59fa2196f5c11c",
        # # 01_musky_lotions@icloud.com
        # "7266698be44c4cadc223c834199903ae8d8131657642f1830e8134fcc187a8f121462b5605869f0891bac4a8fdd5ab28b29208332e33067c7b72c6c373b5cb32",
        # # clump_zingy0t@icloud.com
        # "7cdc02dde4d1ac701b6bf11e8ab30b48beb5880a010016847c7e671c850cbc523fa94d75a8c1ea37fde5ea56dce50279955a732d989bc36f486c276b1ac3429e",
        # # ropes
        # "b94c13374ae4f0b04fb2539b727e165ec695373f7fe198dd69c3b11f22a2aa380c8adca06390f201d2aa09247348aeae6f7664e0735698c9d8ad59880e58b8b8",
        # # rudder
        # "26f4ebc603700e1d56ac25c2a18c6ef196859f3a5547abe12ced49f3c16ef3c8391008db57e5bc77cd4ec3b3c62d26aeccf9983f311a279b714b5378ff4415cf",
        # # mercury
        # "243e229672da5f0a602a816c821b96ded412c2c17041da434aed04e8e225603e40093013bc1a3392566ef090a48b389c80c9c38cb3b7626046a7682f16414e84",
        # # clashes
        # "39a9660087b540bce0c4faebfa9fc5e32b7efd79b5c590a685ab4b20b4087a469dfb4e890f4308d62ebdb21be6cc421f27c5be553a42b43738aee05f02e13b48",
        # # roosts
        # "2b2c8db93b834b4ef95fc0da7d6fd70f345de16464f8037655f87c96373703e46d0b0f48f8f5dbea70c82fd06c3405d7810f2f9e14b9d4e92d6487f62dbe2269",
        # # platoon
        # "c6593b682f0a88379cdfdf83dee4399376885c04ca605d9471367d6313690772c338f4b1683af2ff9f713511f83cdf1357529882a5687fd67f7a37ec85c0e186",
        # # bobs
        # "eeaa19292016f1efc96f7dc11676fe47cbfc12a85869374e6b8ce3c225c5e8ef029d1fa912bb5def86a7b3c62ea55cf16b386d1ea0051fa26676efa2a7df1db2",
        # # bygone
        # "e62477a6e14315c89eb74f224f4aa6d44ae4fe4739bac484ab485ceedc97d4df9962b81286ead7ffe27a4b5443e8c03dd9ee516f09213a49fd3fa88976eba103",
        # # chores
        # "83fae468c72cb0e06e66c77c7520a24058a4ec4629b7e45236f7cf336237abc4cc5ce6ef9d2192ab652da68c7667143d09454687d76e42f9919f1e91ffb043a3",
        # # frisbee
        # "68d7a37e272a1a29ab8a3c767c63443fbf78fb82cfc34ac689d92f8f77f8fcdc4fd48dec46aa257a116f3194ba6532334f67d1b0a6f9feb53f1296804cb418b2"        
        # # ucm
        # "9b1a802766a56b6a51fdf73762fcf6f5c0bd33ef1f5afcef2157693593292c06b5bc92861d8758a585bd4f6d588b2155f5a45fb912f41610a1ad8bb2119f6521"        
    

        quantum_config_name = "QuantumConfig{}".format(self.program_type)

        self.hardware_name = self.config_parser[quantum_config_name]['hardware_name']
        self.base_folder = self.config_parser[quantum_config_name]['base_folder']
        self.shots = int(self.config_parser[quantum_config_name]['shots'])
        self.ibm_cloud_instance = self.config_parser[quantum_config_name]['ibm_cloud_instance']
        self.qiskit_token = self.config_parser[quantum_config_name]['token']
        self.optimization_level = int(self.config_parser[quantum_config_name]['optimization_level'])
        self.resilience_level = int(self.config_parser[quantum_config_name]['resilience_level'])
        self.rep_delay = float(self.config_parser[quantum_config_name]['rep_delay'])
        self.runs = int(self.config_parser[quantum_config_name]['runs'])
        self.repetition = int(self.config_parser[quantum_config_name]['repetition'])
        self.initialized_triq = int(self.config_parser[quantum_config_name]['initialized_triq'])
        self.user_id = int(self.config_parser[quantum_config_name]['user_id'])
        self.run_in_simulator = True if self.config_parser[quantum_config_name]['run_in_simulator'] == "1" else False
        self.triq_measurement_type = self.config_parser[quantum_config_name]['triq_measurement_type']
        


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
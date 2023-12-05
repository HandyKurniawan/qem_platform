import wrappers.nassc_wrapper as nassc_wrapper
import argparse
import mysql.connector
from qiskit import Aer, execute, QuantumCircuit, transpile
from qiskit_ibm_provider import IBMProvider
from commons import convert_to_json
from datetime import datetime

parser = argparse.ArgumentParser(description='Runs a benchmark.')
parser.add_argument('yamlfile', metavar='file.yaml', nargs=1, help='YAML configuration file')
args = parser.parse_args()
yamlfile = args.yamlfile[0]

circuit_name = yamlfile.split("/")[-1].split(".")[0]
hardware_name = "ibm_perth"
user_id = 5

print(circuit_name)

results = nassc_wrapper.run(yamlfile)

# need to process to the database here

mysql_config = {
            'user': 'handy',
            'password': 'handy',
            'host': 'ec2-16-170-224-118.eu-north-1.compute.amazonaws.com',
            'database': 'calibration_data'
        }

qc = results["circuit"]
qasm = qc.qasm()
circuit = qc
total_gate = sum(qc.count_ops().values())

backend_sim = Aer.get_backend('qasm_simulator')
job_sim = backend_sim.run(transpile(qc, backend_sim), shots=8192)
result_sim = job_sim.result()       

correct_output = dict(result_sim.get_counts(qc))
gates = dict(qc.count_ops())
depth = qc.depth()

# Connect to the MySQL database
conn = mysql.connector.connect(**mysql_config)
cursor = conn.cursor()

# insert to circuit
cursor.execute('INSERT INTO circuit (name, qasm, depth, total_gates, gates, correct_output, hw_name) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (circuit_name, qasm, depth, total_gate, convert_to_json(gates), convert_to_json(correct_output), hardware_name ))
circuit_id = cursor.lastrowid

# insert to header
now_time = datetime.now().strftime("%Y%m%d%H%M%S")
cursor.execute('INSERT INTO result_header (user_id, circuit_id, created_datetime) VALUES (%s, %s, %s)',
            (user_id, circuit_id, now_time))
header_id = cursor.lastrowid

# insert to detail
now_time = datetime.now().strftime("%Y%m%d%H%M%S")
cursor.execute('''INSERT INTO result_detail (user_id, header_id, job_id, status, 
                qiskit_optimization, apply_qiskit, triq_optimization, sabre, 
                mirage, mitiq, laura_optimization, created_datetime) 
                VALUES (
                %s, %s, %s, %s, 
                %s, %s, %s, %s, 
                %s, %s, %s, %s)''',
            (user_id, header_id, None, "pending",  
                None, None, None, None,
                None, 1, None, now_time))
detail_id = cursor.lastrowid

# insert to result_updated_qasm
cursor.execute('''INSERT INTO result_updated_qasm (detail_id, updated_qasm, qiskit_qasm, qasm_before_decomposed_final) 
                VALUES (
                %s, %s, %s, %s)''',
            (detail_id, updated_qasm, None, None))

conn.commit()
cursor.close()
conn.close()
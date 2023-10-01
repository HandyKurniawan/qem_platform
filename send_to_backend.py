import wrappers.triq_wrapper as triq_wrapper
import wrappers.qiskit_wrapper as qiskit_wrapper
import wrappers.mirage_wrapper as mirage_wrapper
import wrappers.laura_wrapper as laura_wrapper
import sys, glob, os
from commons import convert_to_json, triq_optimization, qiskit_optimization, apply_qiskit_optimization, read_file
import inspect
from qiskit import Aer, QuantumCircuit, transpile
from qiskit_ibm_provider import IBMProvider
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator, Options
from qiskit_aer.noise import NoiseModel

from datetime import datetime
import mysql.connector
import time
# MySQL connection parameters
mysql_config = {
        'user': 'handy',
        'password': 'handy',
        'host': 'ec2-34-228-189-223.compute-1.amazonaws.com',
        'database': 'calibration_data'
    }

# # token pepe 1
# token = "924828a6b1671411b96c27b10123849b161154290707582dc60d0b900146ccc8fb93adda735a6d0805168b3007a8ad56f626f9f207881d5055c841a58e51a7d9"

# # token pepe 2
# token = "2298ebebdf52aa8ef9258a07154bc62d335af0126f2bed26502a43f32a206309618c34344db22713f54bad3dc1c7569d7d1e3a0075e0421160e83b8c50967b45"

# # # token pepe 3
# token = "01501f074b8bc9910185d5563408e2838951163e8f55b90a338c94c58116b92a1cd88081474827667b9d907604f2dd27eaa8399a83fbb9505a24e25875819b23"

# token pepe 4
token = "055a93864810f2fc66e4de35b13027e8e591f0d019abb91b4895971fa16a991bef0ac573457c707c3d1070e5105d8f0cdd489f842cc06723d29a233c9f483e74"

# # token untukmain
# token = "e9dc3b4555eaceaf68dd163b187fe3f2354d0ae5032b50f2e0a01693118c83ccdd2f86f77bb37f0983244358d776defaa18614aafede58d1d8bfaea7b51c5a98"

# # token handyokur
# token = "d6c68cd3c7151e9499fcaf54ff7982629e20ff25d38f32aea5b64db369985c82682f63b991dc6fc8424f4ac0349882d90a5399b03194d047b3b9b2eefb4613b3"

# # token laura 1
# token = "3efc1f6d5ced29bfa09060c23d32577dc5346087b8b86052cb5479652653a45a1698bec0a0ad45cd9ab255d12d8f5b47c3c1b154edab4ec6e66c52a9428a8905"

class QiskitCircuit:
    def __init__(self, qasm, name = None, metadata = {}):
        qc = None
        if isinstance(qasm, str):
            try:
                qc = QuantumCircuit.from_qasm_file(qasm)
            except Exception as e:
                try: 
                    qc = QuantumCircuit.from_qasm_str(qasm)
                except Exception as ex:
                    raise ValueError("Input circuit must be a string path to QASM file, QASM string or a QuantumCircuit object")
                
        if not (isinstance(qasm, str) or isinstance(qc, QuantumCircuit)):
            raise ValueError("Input must be a string or a QuantumCircuit object")
        
        
        self.circuit = qc
        self.qasm = qc.qasm()
        self.circuit.name = name
        self.circuit.metadata = metadata

    def get_native_gates_circuit(self, backend):
        return transpile(self.circuit.decompose(), backend, basis_gates=backend.basis_gates, optimization_level=0)
    
    def get_qasm(self):
        return self.qasm

    
def send_qasm_to_real_backend(hardware_name):
    # Save account credentials.
    IBMProvider.save_account(token=token, overwrite=True)
        
    service = QiskitRuntimeService(channel="ibm_quantum", token=token)
    backend_service = service.get_backend(hardware_name)
    backend_sim = service.get_backend("ibmq_qasm_simulator")
    noise_model = NoiseModel.from_backend(backend_service)

    options = Options()
    options.simulator = {
        "noise_model": noise_model,
        "basis_gates": backend_service.configuration().basis_gates,
        "coupling_map": backend_service.configuration().coupling_map
    }
    # Set number of shots, optimization_level and resilience_level
    options.execution.shots = 8192
    options.optimization_level = 0
    options.resilience_level = 1

    run_in_simulator = True

    if (run_in_simulator):            
        session = Session(service=service, backend=backend_sim, max_time="25m")
        sampler = Sampler(backend_sim, options=options, session=session) 
    else:
        session = Session(service=service, backend=backend_sim, max_time="25m")
        sampler = Sampler(backend_sim, options=options, session=session) 

    # Connect to the MySQL database
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()

    provider = IBMProvider(token=token)
    backend = provider.get_backend("ibmq_qasm_simulator")
            
    cursor.execute('''SELECT distinct header_id FROM calibration_data.result WHERE job_id IS NULL''')
    results_1 = cursor.fetchall()

    for res_1 in results_1:
        header_id = res_1[0]

        cursor.execute('''SELECT detail_id, updated_qasm, qiskit_optimization, apply_qiskit, triq_optimization,
                    sabre, mirage, laura_optimization, circuit_name
                    FROM calibration_data.result 
                    WHERE header_id = %s AND job_id IS NULL''', (header_id,))
        results = cursor.fetchall()


        list_circuits = []

        for res in results:
            detail_id, updated_qasm, qiskit_optimization, apply_qiskit, triq_optimization,\
                    sabre, mirage, laura_optimization, circuit_name = res

            
            metadata = {"qiskit_optimization":qiskit_optimization,
                        "apply_qiskit":apply_qiskit,
                        "triq_optimization":triq_optimization,
                        "sabre":sabre,
                        "mirage":mirage,
                        "laura_optimization":laura_optimization,
                        "header_id": header_id,
                        "detail_id":detail_id
                        }

            success = False
            qc = QiskitCircuit(updated_qasm, name=circuit_name + "-" + str(detail_id), metadata=metadata)
            circuit = qc.get_native_gates_circuit(backend)

            for i in range(10):
                list_circuits.append(circuit)
            

        while not success:
            try:
                print("Sending to {} with batch id: {} ... ".format(hardware_name, header_id))

                job, job_id = None, None
                if run_in_simulator:
                    job = sampler.run(list_circuits, shots=8192)
                    job_id = job.job_id()
                else:
                    job = backend.run(list_circuits, shots=8192)
                    job_id = job.job_id()

                success = True

                # update to result detail
                cursor.execute('UPDATE calibration_data.result_detail SET job_id= %s WHERE header_id = %s', (job_id, header_id))

                conn.commit()

            except Exception as e:
                print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

                for i in range(30, 0, -1):
                    time.sleep(1)
                    print(i)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    send_qasm_to_real_backend("ibm_perth")

    

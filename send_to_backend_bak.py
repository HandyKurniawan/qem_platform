from qiskit import Aer, execute, QuantumCircuit, transpile
from qiskit_ibm_provider import IBMProvider
import mysql.connector
import time
from qiskit.assembler import assemble_circuits
from qiskit.assembler.run_config import RunConfig

# MySQL connection parameters
mysql_config = {
        'user': 'handy',
        'password': 'handy',
        'host': 'ec2-34-228-189-223.compute-1.amazonaws.com',
        'database': 'calibration_data'
    }

    
def send_qasm_to_real_backend(hardware_name):

    # Save account credentials.

    # handy ut token
    # token = "ac1d8e54395f1935c9a861e335b6bc5a8f8a53ba33f07a3f75d8e8fa076d7296ee63b3e1780b6fd2d4f05eeff5adb08066a17ce46e573662dfba3f2eaa9c6ce8"

    # handy ucm token
    # token = "9b1a802766a56b6a51fdf73762fcf6f5c0bd33ef1f5afcef2157693593292c06b5bc92861d8758a585bd4f6d588b2155f5a45fb912f41610a1ad8bb2119f6521"

    # laura token
    token = "3efc1f6d5ced29bfa09060c23d32577dc5346087b8b86052cb5479652653a45a1698bec0a0ad45cd9ab255d12d8f5b47c3c1b154edab4ec6e66c52a9428a8905"
    IBMProvider.save_account(token=token, overwrite=True)

    # if self.hardware_name != "ibmq_qasm_simulator":
    #     time.sleep(15)

     # Connect to the MySQL database
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()
            
    cursor.execute('SELECT header_id, detail_id, updated_qasm FROM calibration_data.result WHERE job_id IS NULL')
    results = cursor.fetchall()

    backend = None
    if hardware_name != "ibmq_qasm_simulator":
        provider = IBMProvider(instance="ibm-q/open/main")
        backend = provider.get_backend(hardware_name)
    else:
        # backend = Aer.get_backend('qasm_simulator')
        provider = IBMProvider(instance="ibm-q/open/main")
        backend = provider.get_backend(hardware_name)

    shots = 8192
    qc_dict = {}
    qc_list = []
    tmp_header_id = 0
    for res in results:
        header_id, detail_id, updated_qasm = res
        
        if tmp_header_id == 0 or header_id != tmp_header_id:
            qc_dict[header_id] = [] 


        print("Sending to {} with header id: {}, detail id: {} ... ".format(hardware_name, header_id, detail_id))

        success = False
        while not success:
            try:
            
                circuit = QuantumCircuit.from_qasm_str(updated_qasm)
                
                
                # keeping the qasm before get transpiled
                qasm_before_decomposed_final = circuit.qasm()

                # should i transpile before sending to the backend?
                transpiled_circuit = transpile(circuit.decompose(), basis_gates=backend.basis_gates)
                transpiled_circuit.name = detail_id

                qc_dict[header_id].append(transpiled_circuit)

                

                success = True

                # # update to result detail
                # cursor.execute('UPDATE calibration_data.result_detail SET job_id= %s WHERE id = %s', (job_id, detail_id))

                # # update to result updated qasm
                # cursor.execute('UPDATE calibration_data.result_updated_qasm SET qasm_before_decomposed_final= %s WHERE id = %s', (qasm_before_decomposed_final, detail_id))
                # # job_id = "bcd"

                conn.commit()

            except Exception as e:
                print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

                for i in range(30, 0, -1):
                    time.sleep(1)
                    print(i)

        tmp_header_id = header_id

    header = {"backend_name": hardware_name, "backend_version": "0.0.0"}
    for header_id, qc_list in qc_dict.items():
        print(header_id, len(qc_list))

        # Assemble a Qobj from the input circuit
        qobj = assemble_circuits(circuits=qc_list,
                qobj_id=header_id,
                qobj_header=header,
                run_config=RunConfig(shots=8192, memory=True, init_qubits=True))
    
        # job = execute(qobj, backend=backend, shots=shots)
        job = backend.run(qobj)
        job_id = job.job_id()

        print(job_id)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # send_qasm_to_real_backend("ibm_perth")
    send_qasm_to_real_backend("ibmq_qasm_simulator")

    

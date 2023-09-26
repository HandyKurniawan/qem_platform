from qiskit import Aer, execute, QuantumCircuit, transpile
from qiskit_ibm_provider import IBMProvider
import mysql.connector
import time

# MySQL connection parameters
mysql_config = {
        'user': 'handy',
        'password': 'handy',
        'host': 'ec2-34-228-189-223.compute-1.amazonaws.com',
        'database': 'calibration_data'
    }

    
def send_qasm_to_real_backend(hardware_name):

    # Save account credentials.
    token = "be81173902a0621551ef756bf79487c1d3c8d9860521a72758f60179feaa83ffa7d6ec24ecdf8a60acae47c1c94964dda78c278607152303cfd0a950c1cac22e"
    IBMProvider.save_account(token=token, overwrite=True)

    # if self.hardware_name != "ibmq_qasm_simulator":
    #     time.sleep(15)

     # Connect to the MySQL database
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()
            
    cursor.execute('SELECT detail_id, updated_qasm FROM calibration_data.result WHERE job_id IS NULL')
    results = cursor.fetchall()

    backend = None
    if hardware_name != "ibmq_qasm_simulator":
        provider = IBMProvider(instance="ibm-q/open/main")
        backend = provider.get_backend(hardware_name)
    else:
        # backend = Aer.get_backend('qasm_simulator')
        provider = IBMProvider(instance="ibm-q/open/main")
        backend = provider.get_backend(hardware_name)

    for res in results:
        detail_id, updated_qasm = res

        print("Sending to {} with detail id: {} ... ".format(hardware_name, detail_id))

        success = False
        while not success:
            try:
            
                circuit = QuantumCircuit.from_qasm_str(updated_qasm)
                shots = 8192
                
                # keeping the qasm before get transpiled
                qasm_before_decomposed_final = circuit.qasm()

                # should i transpile before sending to the backend?
                transpiled_circuit = transpile(circuit.decompose(), basis_gates=backend.basis_gates)

                job = execute(transpiled_circuit, backend=backend, shots=shots)
                job_id = job.job_id()

                success = True

                # update to result detail
                cursor.execute('UPDATE calibration_data.result_detail SET job_id= %s WHERE id = %s', (job_id, detail_id))

                # update to result updated qasm
                cursor.execute('UPDATE calibration_data.result_updated_qasm SET qasm_before_decomposed_final= %s WHERE id = %s', (qasm_before_decomposed_final, detail_id))
                # job_id = "bcd"

                conn.commit()

            except Exception as e:
                print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

                for i in range(30, 0, -1):
                    time.sleep(1)
                    print(i)


    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # send_qasm_to_real_backend("ibm_perth")
    # send_qasm_to_real_backend("ibm_perth")
    send_qasm_to_real_backend("ibmq_qasm_simulator")

    

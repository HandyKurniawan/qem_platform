"""
file name: qem.py
author: Handy, Laura, Fran
date: 14 September 2023

hmmm ...

Functions:
hmmm ...

Example:
"""
import wrappers.triq_wrapper as triq_wrapper
import wrappers.qiskit_wrapper as qiskit_wrapper
import wrappers.mirage_wrapper as mirage_wrapper
import os
from commons import read_file, convert_to_json, triq_optimization, qiskit_optimization, apply_qiskit_optimization
import inspect
from qiskit import Aer, execute, QuantumCircuit, transpile
from qiskit_ibm_provider import IBMProvider
from datetime import datetime
import mysql.connector


class QEM:
    def __init__(self, hardware_name = "qasm_simulator", output_name = "output"):
        self.hardware_name = hardware_name
        self.output_name = output_name
        self.qasm = None 
        self.circuit:QuantumCircuit = None       
        self.qiskit_token = None
        self.correct_output = None
        self.total_gate = None
        self.gates = None
        self.depth = None
        self.mysql_config = None
        self.header_id = None
        self.user_id = None

    def set_circuit(self, qasm):
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
        
        self.qasm = qc.qasm()
        self.circuit = qc
        self.total_gate = sum(qc.count_ops().values())

        backend_sim = Aer.get_backend('qasm_simulator')
        job_sim = backend_sim.run(transpile(qc, backend_sim), shots=8192)
        result_sim = job_sim.result()        

        self.correct_output = dict(result_sim.get_counts(qc))
        self.gates = dict(qc.count_ops())
        self.depth = qc.depth()

        # Connect to the MySQL database
        conn = mysql.connector.connect(**self.mysql_config)
        cursor = conn.cursor()

        # insert to circuit
        cursor.execute('INSERT INTO circuit (name, qasm, depth, total_gates, gates, correct_output) VALUES (%s, %s, %s, %s, %s, %s)',
                    ("circuit", self.qasm, self.depth, self.total_gate, convert_to_json(self.gates), convert_to_json(self.correct_output) ))
        circuit_id = cursor.lastrowid
        
        # insert to header
        now_time = datetime.now().strftime("%Y%m%d%H%M%S")
        cursor.execute('INSERT INTO result_header (user_id, circuit_id, created_datetime) VALUES (%s, %s, %s)',
                    (self.user_id, circuit_id, now_time))
        self.header_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

    def load_account(self, token):

        # MySQL connection parameters
        self.mysql_config = {
            'user': 'handy',
            'password': 'handy',
            'host': 'ec2-34-239-187-246.compute-1.amazonaws.com',
            'database': 'calibration_data'
        }

        self.qiskit_token = token
        self.user_id = 1

        # Save account credentials.
        IBMProvider.save_account(token=token, overwrite=True)

    def apply_triq(self, triq_optimization, qiskit_optimization_level = 0, enable_sabre = False, apply_qiskit = None):
        """
        apply_qiskit:
            "before" : before triq
            "after"  : after triq
        """    
        updated_qasm = self.qasm

        if apply_qiskit == "before":
            updated_qasm = self.apply_qiskit(updated_qasm, qiskit_optimization_level, 
                                             enable_sabre=enable_sabre, enable_mirage=False, enable_send=False)

        updated_qasm = triq_wrapper.run(updated_qasm, self.hardware_name, triq_optimization)

        if apply_qiskit == "after":
            updated_qasm = self.apply_qiskit(updated_qasm, qiskit_optimization_level, 
                                             enable_sabre=enable_sabre, enable_mirage=False, enable_send=False)

        self.send_qasm_to_real_backend(updated_qasm)

        return updated_qasm
        

    def apply_qiskit(self, 
                     updated_qasm = None,
                     qiskit_optimization_level = 0, 
                     enable_sabre = False,
                     enable_mirage = False,
                     enable_send = True
                     ):
        """
        hmmm
        """
        if enable_send:
           updated_qasm = self.qasm

        # print(updated_qasm)

        updated_qasm = qiskit_wrapper.optimize_qasm(
            updated_qasm, qiskit_optimization_level, enable_sabre=enable_sabre, enable_mirage=enable_mirage)

        # print("after qiskit")
        # print(updated_qasm)

        if enable_send:
            self.send_qasm_to_real_backend(updated_qasm)

        return updated_qasm
    
    def apply_mirage(self, qiskit_optimization_level):
        
        updated_qasm = mirage_wrapper.optimize_qasm(
            self.qasm, self.hardware_name, qiskit_optimization_level)

        self.send_qasm_to_real_backend(updated_qasm)
    
    
    def _save_result_to_db(self, job_id, updated_qasm):
        # Get the calling frame (frame of the caller)
        caller_frame = inspect.currentframe().f_back.f_back
        # Get the name of the calling function
        calling_function_name = caller_frame.f_code.co_name
        # Get the local variables (parameters) of the calling function
        calling_function_locals = caller_frame.f_locals

        now_time = datetime.now().strftime("%Y%m%d%H%M%S")

        try:
            
            p_qiskit_optimization, p_apply_qiskit, p_triq_optimization = None, None, None
            sabre, mirage, mitiq, qiskit_error_mitigation = None, None, None, None

            for i in calling_function_locals.keys():
                if i != "self" and i != "updated_qasm":
                    if i == "qiskit_optimization_level":
                        p_qiskit_optimization = calling_function_locals[i]
                    elif i == "apply_qiskit":
                        p_apply_qiskit = calling_function_locals[i]
                    elif i == "triq_optimization":
                        p_triq_optimization = calling_function_locals[i]
                    elif i == "enable_sabre":
                        sabre = 1 if calling_function_locals[i] == True else 0
                    elif i == "enable_mirage":
                        mirage = 1 if calling_function_locals[i] == True else 0

            # Connect to the MySQL database
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            # insert to detail
            now_time = datetime.now().strftime("%Y%m%d%H%M%S")
            cursor.execute('''INSERT INTO result_detail (user_id, header_id, job_id, status, 
                           qiskit_optimization, apply_qiskit, triq_optimization, sabre, 
                           mirage, mitiq, qiskit_error_mitigation, created_datetime) 
                           VALUES (
                           %s, %s, %s, %s, 
                           %s, %s, %s, %s, 
                           %s, %s, %s, %s)''',
                        (self.user_id, self.header_id, job_id, "pending",  
                         p_qiskit_optimization, p_apply_qiskit, p_triq_optimization, sabre,
                         mirage, mitiq, qiskit_error_mitigation, now_time))
            detail_id = cursor.lastrowid

            # insert to result_updated_qasm
            cursor.execute('''INSERT INTO result_updated_qasm (detail_id, updated_qasm) 
                           VALUES (
                           %s, %s)''',
                        (detail_id, updated_qasm))

            conn.commit()
            cursor.close()
            conn.close()


            # # Open the file in "append" mode
            # with open("ibm_job_id", "a") as file:
            #     file.write("\n" + str(job_id) + " - "+ calling_function_name + ": ")

            #     for i in calling_function_locals.keys():
            #         if i != "self" and i != "updated_qasm":
            #             file.write("{}={}, ".format(i,calling_function_locals[i]))
            #             file_name += "{},".format(calling_function_locals[i])

            # file_name = file_name[:-1]

            # #or maybe put into the database later
            # # with open("qasm_result/" + file_name + "-" + now_time, "w+") as file:
            # with open("qasm_result/mirage", "w+") as file:
            #     file.write(updated_qasm)

        except Exception as e:
            print(f"An error occurred: {str(e)}")
        pass

    def send_qasm_to_real_backend(self, updated_qasm):
        provider = IBMProvider(instance="ibm-q/open/main")
        backend = provider.get_backend(self.hardware_name)
        #backend = provider.get_backend("ibmq_qasm_simulator")
        circuit = QuantumCircuit.from_qasm_str(updated_qasm)
        shots = 8192
        transpiled_circuit = transpile(circuit.decompose(), basis_gates=backend.basis_gates)
        job = execute(transpiled_circuit, backend=backend, shots=shots)
        job_id = job.job_id()
        # job_id = "bcd"

        self._save_result_to_db(job_id, updated_qasm)

    def run(self):
        """
        
        """
        for qiskit_opt in qiskit_optimization:
            # print('{:15} = {}'.format(opt.name, opt.value))
            print("running qiskit:qiskit_optimization_level={}, enable_sabre=False , enable_mirage=False..".format(qiskit_opt.value))
            qem.apply_qiskit(qiskit_optimization_level=qiskit_opt.value, enable_sabre=False , enable_mirage=False)
            print("running qiskit:qiskit_optimization_level={}, enable_sabre=True , enable_mirage=False..".format(qiskit_opt.value))
            qem.apply_qiskit(qiskit_optimization_level=qiskit_opt.value, enable_sabre=True , enable_mirage=False)
            print("running qiskit:qiskit_optimization_level={}, enable_sabre=False , enable_mirage=True..".format(qiskit_opt.value))
            qem.apply_qiskit(qiskit_optimization_level=qiskit_opt.value, enable_sabre=False, enable_mirage=True)
            

        for qiskit_opt in qiskit_optimization:
            print("running apply_mirage:qiskit_optimization_level={}..".format(qiskit_opt.value))
            qem.apply_mirage(qiskit_optimization_level=qiskit_opt.value)

        for triq_opt in triq_optimization:
            for q in apply_qiskit_optimization:
                if q.value is None:
                    print("running apply_triq:triq_optimization={}, qiskit_optimization_level=0, enable_sabre=False, apply_qiskit={}..".format(triq_opt.value, q.value ))
                    qem.apply_triq(triq_optimization=triq_opt.value, qiskit_optimization_level=0, enable_sabre=False, apply_qiskit=q.value)
                else:
                    for qiskit_opt in qiskit_optimization:
                        print("running apply_triq:triq_optimization={}, qiskit_optimization_level={}, enable_sabre=False, apply_qiskit={}..".format(triq_opt.value, qiskit_opt.value, q.value ))
                        qem.apply_triq(triq_optimization=triq_opt.value, qiskit_optimization_level=qiskit_opt.value, enable_sabre=False, apply_qiskit=q.value)

                        print("running apply_triq:triq_optimization={}, qiskit_optimization_level={}, enable_sabre=True, apply_qiskit={}..".format(triq_opt.value, qiskit_opt.value, q.value ))
                        qem.apply_triq(triq_optimization=triq_opt.value, qiskit_optimization_level=qiskit_opt.value, enable_sabre=True, apply_qiskit=q.value)


if __name__ == "__main__":
    qem = QEM("ibm_perth")
    adder_qasm_path = os.path.expanduser("~/Quantum_benchmarks/TriQ/adder.qasm")
    adder_qasm = read_file(adder_qasm_path)
    qem.load_account("be81173902a0621551ef756bf79487c1d3c8d9860521a72758f60179feaa83ffa7d6ec24ecdf8a60acae47c1c94964dda78c278607152303cfd0a950c1cac22e")
    qem.set_circuit(adder_qasm)
    # qem.run()
    qem.apply_qiskit(qiskit_optimization_level=0, enable_sabre=False , enable_mirage=True)

# qem.apply_qiskit(qiskit_optimization_level=0, enable_sabre=False , enable_mirage=True)
# qem.apply_triq(triq_optimization=2, qiskit_optimization_level=3, enable_sabre=True, apply_qiskit="before")




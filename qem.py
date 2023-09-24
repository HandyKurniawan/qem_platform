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
import wrappers.laura_wrapper as laura_wrapper
import sys, glob, os
from commons import convert_to_json, triq_optimization, qiskit_optimization, apply_qiskit_optimization
import inspect
from qiskit import Aer, execute, QuantumCircuit, transpile
from qiskit_ibm_provider import IBMProvider
from datetime import datetime
import mysql.connector
import time


class QEM:
    def __init__(self, token, qasm_source, hardware_name = "qasm_simulator", circuit_name = "circuit", user_id = 99):
        self.hardware_name = hardware_name
        self.circuit_name = circuit_name
        self.qasm = None 
        self.qiskit_qasm = None
        self.qasm_before_decomposed_final = None
        self.circuit:QuantumCircuit = None       
        self.qiskit_token = None
        self.correct_output = None
        self.total_gate = None
        self.gates = None
        self.depth = None
        self.mysql_config = None
        self.header_id = None
        self.user_id = user_id
        self.list_detail_id = {}

        self.load_account(token)
        self.set_circuit(qasm_source)

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
        cursor.execute('INSERT INTO circuit (name, qasm, depth, total_gates, gates, correct_output, hw_name) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (self.circuit_name, self.qasm, self.depth, self.total_gate, convert_to_json(self.gates), convert_to_json(self.correct_output), self.hardware_name ))
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
            'host': 'ec2-34-228-189-223.compute-1.amazonaws.com',
            'database': 'calibration_data'
        }

        self.qiskit_token = token

        # Save account credentials.
        IBMProvider.save_account(token=token, overwrite=True)

    def apply_triq(self, triq_optimization, qiskit_optimization_level = 0, enable_sabre = False, apply_qiskit = None):
        """
        apply_qiskit:
            "before" : before triq
            "after"  : after triq
        """    
        updated_qasm = self.qasm
        self.qiskit_qasm = None
        self.qasm_before_decomposed_final = None

        if apply_qiskit == "before":
            updated_qasm = self.apply_qiskit(updated_qasm, qiskit_optimization_level, 
                                             enable_sabre=enable_sabre, enable_mirage=False, enable_send=False)
            
            self.qiskit_qasm = updated_qasm

        updated_qasm = triq_wrapper.run(updated_qasm, self.hardware_name, triq_optimization)

        if apply_qiskit == "after":
            updated_qasm = self.apply_qiskit(updated_qasm, qiskit_optimization_level, 
                                             enable_sabre=enable_sabre, enable_mirage=False, enable_send=False)


        detail_id = self._save_result_to_db(updated_qasm)

        # save it to the list and run later
        self.list_detail_id[detail_id] = updated_qasm


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
            detail_id = self._save_result_to_db(updated_qasm)

            # save it to the list and run later
            self.list_detail_id[detail_id] = updated_qasm
        else:
            return updated_qasm
    
    def apply_mirage(self, qiskit_optimization_level, enable_mirage = 1):
        
        updated_qasm = mirage_wrapper.optimize_qasm(
            self.qasm, self.hardware_name, qiskit_optimization_level)

        detail_id = self._save_result_to_db(updated_qasm)

        # save it to the list and run later
        self.list_detail_id[detail_id] = updated_qasm

    def apply_laura(self, laura_optimization = 2, qiskit_optimization_level = 0, enable_sabre = False, apply_qiskit = None):
        """
        apply_qiskit:
            "before" : before laura's version of triq
            "after"  : after laura's version of triq
        """    
        updated_qasm = self.qasm

        if apply_qiskit == "before":
            updated_qasm = self.apply_qiskit(updated_qasm, qiskit_optimization_level, 
                                             enable_sabre=enable_sabre, enable_mirage=False, enable_send=False)

        updated_qasm = laura_wrapper.run(updated_qasm, self.hardware_name)

        if apply_qiskit == "after":
            updated_qasm = self.apply_qiskit(updated_qasm, qiskit_optimization_level, 
                                             enable_sabre=enable_sabre, enable_mirage=False, enable_send=False)

        detail_id = self._save_result_to_db(updated_qasm)

        # save it to the list and run later
        self.list_detail_id[detail_id] = updated_qasm

        return updated_qasm
    
    
    def _save_result_to_db(self, updated_qasm):
        # Get the calling frame (frame of the caller)
        caller_frame = inspect.currentframe().f_back
        # Get the name of the calling function
        calling_function_name = caller_frame.f_code.co_name
        # Get the local variables (parameters) of the calling function
        calling_function_locals = caller_frame.f_locals

        now_time = datetime.now().strftime("%Y%m%d%H%M%S")

        detail_id = None
        job_id = None

        try:
            
            p_qiskit_optimization, p_apply_qiskit, p_triq_optimization = None, None, None
            sabre, mirage, mitiq, p_laura_optimization = None, None, None, None

            for i in calling_function_locals.keys():
                if i != "self" and i != "updated_qasm":
                    if i == "qiskit_optimization_level":
                        p_qiskit_optimization = calling_function_locals[i]
                    elif i == "apply_qiskit":
                        p_apply_qiskit = calling_function_locals[i]
                    elif i == "triq_optimization":
                        p_triq_optimization = calling_function_locals[i]
                    elif i == "laura_optimization":
                        p_laura_optimization = calling_function_locals[i]
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
                           mirage, mitiq, laura_optimization, created_datetime) 
                           VALUES (
                           %s, %s, %s, %s, 
                           %s, %s, %s, %s, 
                           %s, %s, %s, %s)''',
                        (self.user_id, self.header_id, job_id, "pending",  
                         p_qiskit_optimization, p_apply_qiskit, p_triq_optimization, sabre,
                         mirage, mitiq, p_laura_optimization, now_time))
            detail_id = cursor.lastrowid

            # insert to result_updated_qasm
            cursor.execute('''INSERT INTO result_updated_qasm (detail_id, updated_qasm, qiskit_qasm, qasm_before_decomposed_final) 
                           VALUES (
                           %s, %s, %s, %s)''',
                        (detail_id, updated_qasm, self.qiskit_qasm, self.qasm_before_decomposed_final))

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


            return detail_id
        
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        

        

    # def send_qasm_to_real_backend(self, detail_id, updated_qasm):

    #     # if self.hardware_name != "ibmq_qasm_simulator":
    #     #     time.sleep(15)

    #     success = False
    #     while not success:
    #         try:
           
    #             backend = None
    #             if self.hardware_name != "ibmq_qasm_simulator":
    #                 provider = IBMProvider(instance="ibm-q/open/main")
    #                 backend = provider.get_backend(self.hardware_name)
    #             else:
    #                 # backend = Aer.get_backend('qasm_simulator')
    #                 provider = IBMProvider(instance="ibm-q/open/main")
    #                 backend = provider.get_backend(self.hardware_name)

    #             circuit = QuantumCircuit.from_qasm_str(updated_qasm)
    #             shots = 8192
                
    #             # keeping the qasm before get transpiled
    #             self.qasm_before_decomposed_final = circuit.qasm()

    #             # should i transpile before sending to the backend?
    #             transpiled_circuit = transpile(circuit.decompose(), basis_gates=backend.basis_gates)

    #             job = execute(transpiled_circuit, backend=backend, shots=shots)
    #             job_id = job.job_id()

    #             success = True

    #             # job_id = "bcd"

    #         except Exception as e:
    #             print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

    #             for i in range(30, 0, -1):
    #                 time.sleep(1)
    #                 print(i)

        

    def run(self):
        """
        
        """
        # for qiskit_opt in qiskit_optimization:
        #     # print('{:15} = {}'.format(opt.name, opt.value))
        #     print("running qiskit:qiskit_optimization_level={}, enable_sabre=False , enable_mirage=False..".format(qiskit_opt.value))
        #     self.apply_qiskit(qiskit_optimization_level=qiskit_opt.value, enable_sabre=False , enable_mirage=False)
        #     print("running qiskit:qiskit_optimization_level={}, enable_sabre=True , enable_mirage=False..".format(qiskit_opt.value))
        #     self.apply_qiskit(qiskit_optimization_level=qiskit_opt.value, enable_sabre=True , enable_mirage=False)
        #     print("running qiskit:qiskit_optimization_level={}, enable_sabre=False , enable_mirage=True..".format(qiskit_opt.value))
        #     self.apply_qiskit(qiskit_optimization_level=qiskit_opt.value, enable_sabre=False, enable_mirage=True)
            
        # for qiskit_opt in qiskit_optimization:
        #     print("running apply_mirage:qiskit_optimization_level={}, enable_mirage = 1..".format(qiskit_opt.value))
        #     self.apply_mirage(qiskit_optimization_level=qiskit_opt.value, enable_mirage = 1)

        for triq_opt in triq_optimization:
            for q in apply_qiskit_optimization:
                if q.value is None:
                    print("running apply_triq:triq_optimization={}, qiskit_optimization_level=None, enable_sabre=False, apply_qiskit={}..".format(triq_opt.value, q.value ))
                    self.apply_triq(triq_optimization=triq_opt.value, qiskit_optimization_level=None, enable_sabre=False, apply_qiskit=q.value)
                else:
                    for qiskit_opt in qiskit_optimization:
                        # if (qiskit_opt.value == 3 and q.value == "before"):
                        #     continue

                        print("running apply_triq:triq_optimization={}, qiskit_optimization_level={}, enable_sabre=False, apply_qiskit={}..".format(triq_opt.value, qiskit_opt.value, q.value ))
                        self.apply_triq(triq_optimization=triq_opt.value, qiskit_optimization_level=qiskit_opt.value, enable_sabre=False, apply_qiskit=q.value)

                        print("running apply_triq:triq_optimization={}, qiskit_optimization_level={}, enable_sabre=True, apply_qiskit={}..".format(triq_opt.value, qiskit_opt.value, q.value ))
                        self.apply_triq(triq_optimization=triq_opt.value, qiskit_optimization_level=qiskit_opt.value, enable_sabre=True, apply_qiskit=q.value)

        # for q in apply_qiskit_optimization:
        #     if q.value is None:
        #         print("running apply_triq:laura_optimization={}, qiskit_optimization_level=None, enable_sabre=False, apply_qiskit={}..".format(2, q.value ))
        #         self.apply_laura(laura_optimization=2, qiskit_optimization_level=None, enable_sabre=False, apply_qiskit=q.value)
        #     else:
        #         for qiskit_opt in qiskit_optimization:
        #             if (qiskit_opt.value == 3 and q.value == "before"):
        #                 continue
                    
        #             print("running apply_triq:laura_optimization={}, qiskit_optimization_level={}, enable_sabre=False, apply_qiskit={}..".format(2, qiskit_opt.value, q.value ))
        #             self.apply_laura(laura_optimization=2, qiskit_optimization_level=qiskit_opt.value, enable_sabre=False, apply_qiskit=q.value)

        #             print("running apply_triq:laura_optimization={}, qiskit_optimization_level={}, enable_sabre=True, apply_qiskit={}..".format(2, qiskit_opt.value, q.value ))
        #             self.apply_laura(laura_optimization=2, qiskit_optimization_level=qiskit_opt.value, enable_sabre=True, apply_qiskit=q.value)


if __name__ == "__main__":
    # arglist = sys.argv[1:]
    # print(arglist)
    # if not sys.stdin.isatty():
    #     query = sys.stdin.read(1)
    #     print(query)
    #     arglist.append(query) #or perhaps "--query "+query

    # print(arglist)
    
    token = "be81173902a0621551ef756bf79487c1d3c8d9860521a72758f60179feaa83ffa7d6ec24ecdf8a60acae47c1c94964dda78c278607152303cfd0a950c1cac22e"
    # hardware_name = "ibmq_qasm_simulator"
    hardware_name = "ibm_perth"

    # Define the base folder path
    # base_folder = "~/Quantum_benchmarks/Paper_circuits/n_7/"
    base_folder = "~/Quantum_benchmarks/Paper_circuits/error-triq/"

    # List all files in the base folder with the .qasm extension
    qasm_files = glob.glob(os.path.expanduser(os.path.join(base_folder, "*.qasm")))
    qasm_files = sorted(qasm_files)

    for i in qasm_files:
        qasm_source = i
        circuit_name = i.split("/")[-1].split(".")[0]
        print("========== {}  ===========".format(circuit_name))
        q = None
        q = QEM(token, qasm_source, hardware_name, circuit_name, 99)
        q.run()
        # q.apply_triq(triq_optimization=2, qiskit_optimization_level=1, enable_sabre=True , apply_qiskit="before") 

        # Send to backend

        # for id, updated_qasm in q.list_detail_id.items():
        #     print(id, updated_qasm)
            

        # q.apply_triq(triq_optimization=0, qiskit_optimization_level=1, enable_sabre=False , apply_qiskit="before")

        # break
# # qem.apply_qiskit(qiskit_optimization_level=0, enable_sabre=False , enable_mirage=True)
# # 




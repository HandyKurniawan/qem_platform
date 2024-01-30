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
from commons import convert_to_json, triq_optimization, qiskit_optimization, \
    calibration_type_enum, normalize_counts, Config
import inspect
from qiskit import Aer, QuantumCircuit, transpile
from wrappers.qiskit_wrapper import QiskitCircuit
from qiskit_ibm_provider import IBMProvider
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator, Options
from qiskit_aer.noise import NoiseModel

from datetime import datetime
import mysql.connector
import time

print("masuk duluan")

conf = Config()

print("terus masuk sini", conf.hardware_name)


class QEM:
    def __init__(self, qasm_source, runs=2, 
                 fixed_initial_layout = False, 
                 run_in_simulator = False, 
                 calibration_type = calibration_type_enum.realtime,
                 circuit_name = "circuit", user_id = 99):
        self.run_in_simulator = run_in_simulator
        self.session = None
        self.provider = None
        self.service = None
        self.backend = None
        self.backend_service = None
        self.sampler = None
        self.fixed_initial_layout = fixed_initial_layout
        self.initial_layout_qiskit = None
        self.initial_layout_triq = None
        self.calibration_type = calibration_type
        
        self.circuit_name = circuit_name

        self.qasm = None 
        self.qiskit_qasm = None
        self.qasm_before_decomposed_final = None
        
        self.runs = runs
        self.correct_output = None
        self.total_gate = None
        self.gates = None
        self.depth = None
        
        self.header_id = None
        self.user_id = user_id

        self.load_account()

        self.initial_circuit = QiskitCircuit(qasm_source, name="initial circuit")

        self.set_variables()

        # self.init_result_header()

        # self.set_sampler_options()

        # if self.calibration_type == calibration_type_enum.realtime:
        #     triq_wrapper.generate_realtime_calibration_data(self)
        if self.calibration_type == calibration_type_enum.realtime:
            triq_wrapper.generate_realtime_calibration_data(self)
            triq_wrapper.generate_mix_calibration_data(self)
            triq_wrapper.generate_recent_average_calibration_data(self, 45)
            triq_wrapper.generate_recent_average_calibration_data(self, 15)

        if fixed_initial_layout:
            self.set_initial_layout()

    def set_initial_layout(self):
        tmp_start_time = time.perf_counter()

        initial_layout_dict = triq_wrapper.get_mapping(self.qasm, 
                                                       conf.hardware_name + "_" + self.calibration_type.value, 
                                                       "2")

        self.initial_layout_qiskit = []
        self.initial_layout_triq = []
        # for virtual, physical in initial_layout_dict.items():
        #     self.initial_layout.append(physical)

        for i in range(len(initial_layout_dict)):
            self.initial_layout_qiskit.append(initial_layout_dict[str(i)])
            self.initial_layout_triq.append(initial_layout_dict[str(i)])

        for i in range(self.backend.n_qubits):
            if i not in self.initial_layout_triq:
                self.initial_layout_triq.append(i)

        print("Initial Layout qiskit: ", self.initial_layout_qiskit )
        print("Initial Layout triq: ", self.initial_layout_triq )

        tmp_end_time = time.perf_counter()

        print("Time for initial layout: {} seconds".format(tmp_end_time - tmp_start_time))
        

    def set_variables(self):
        self.qasm = self.initial_circuit.qasm
        
        qc = self.initial_circuit.circuit
        self.total_gate = sum(qc.count_ops().values())

        # set backend
        # self.provider = IBMProvider(token=conf.qiskit_token)
        # self.backend = self.provider.get_backend(conf.hardware_name)

        if conf.hardware_name == "ibm_algiers":
            self.service = QiskitRuntimeService(channel="ibm_cloud", token=conf.qiskit_token, instance=conf.ibm_cloud_instance)
        else:
            self.service = QiskitRuntimeService(channel="ibm_quantum", token=conf.qiskit_token)
        self.backend = self.service.get_backend(conf.hardware_name)

        if conf.simulator_hardware != "ibmq_qasm_simulator":
            backend_sim = self.service.get_backend(conf.simulator_hardware)
            sampler = Sampler(backend_sim) 
            job_sim = sampler.run(transpile(qc, backend_sim, basis_gates=["u3", "cx"]), shots=conf.shots)
            result_sim = job_sim.result()  
            self.correct_output = dict(result_sim.quasi_dists[0])  
        else:
            backend_sim = Aer.get_backend('qasm_simulator')
            job_sim = backend_sim.run(transpile(qc, backend_sim), shots=conf.shots)
            result_sim = job_sim.result()  
            self.correct_output = normalize_counts(dict(result_sim.get_counts(qc)))
        
        self.gates = dict(qc.count_ops())
        self.depth = qc.depth()

    def set_sampler_options(self):
        start_time = time.perf_counter()

        service = None
        if conf.hardware_name == "ibm_algiers":
            service = QiskitRuntimeService(channel="ibm_cloud", token=conf.qiskit_token, instance=conf.ibm_cloud_instance)
        else:
            service = QiskitRuntimeService(channel="ibm_quantum", token=conf.qiskit_token)

        self.backend_service = service.get_backend(conf.hardware_name)
        backend_sim = service.get_backend(conf.simulator_hardware)
        noise_model = NoiseModel.from_backend(self.backend_service)

        end_time = time.perf_counter()

        print("Time for loading qiskit service : {} seconds".format(end_time - start_time))


        if (self.run_in_simulator):            
            options = Options()
            options.simulator = {
                "noise_model": noise_model,
                # "basis_gates": self.backend_service.configuration().basis_gates,
                "coupling_map": self.backend_service.configuration().coupling_map
            }
            # options.transpilation.initial_layout = "noise_adaptive"
            # options.transpilation.routing_method = "sabre"
            # Set number of shots, optimization_level and resilience_level
            options.execution.shots = conf.shots
            options.optimization_level = 0
            options.resilience_level = 0

            #self.session = Session(service=service, backend=backend_sim, max_time="25m")
            self.sampler = Sampler(backend_sim, options=options) 
        else:
            options = Options()
            options.execution.shots = conf.shots
            options.optimization_level = 0
            # options.resilience_level = 0
            options.resilience_level = 1
            self.sampler = Sampler(self.backend_service, options=options) 

    def init_result_header(self):
        
        # Connect to the MySQL database
        conn = mysql.connector.connect(**conf.mysql_config)
        cursor = conn.cursor()

        # insert to circuit
        cursor.execute('INSERT INTO circuit (name, qasm, depth, total_gates, gates, correct_output, hw_name) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (self.circuit_name, self.qasm, self.depth, self.total_gate, convert_to_json(self.gates), convert_to_json(self.correct_output), conf.hardware_name ))
        circuit_id = cursor.lastrowid
        
        # insert to header
        now_time = datetime.now().strftime("%Y%m%d%H%M%S")
        cursor.execute('INSERT INTO result_header (user_id, circuit_id, created_datetime, qiskit_token) VALUES (%s, %s, %s, %s)',
                    (self.user_id, circuit_id, now_time, conf.qiskit_token))
        self.header_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

    def load_account(self):

        # MySQL connection parameters
        self.mysql_config = conf.mysql_config

        start_time = time.perf_counter()

        # Save account credentials.
        # IBMProvider.save_account(token=conf.qiskit_token, overwrite=True)
        QiskitRuntimeService.save_account(channel="ibm_quantum", token=conf.qiskit_token, overwrite=True)

        end_time = time.perf_counter()

        print("Time for save account: {} seconds".format(end_time - start_time))    

    def apply_qiskit(self, 
                     updated_qasm = None,
                     qiskit_optimization_level = 3, 
                     enable_noise_adaptive = False,
                     enable_mirage = False,
                     calibration_type = None,
                     initial_layout = None
                     ):
        """
        hmmm
        """

        if qiskit_optimization_level == 99:
            updated_qasm = self.qasm
        else:
            updated_qasm = qiskit_wrapper.optimize_qasm(
                self.qasm, self.backend, qiskit_optimization_level,
                enable_noise_adaptive=enable_noise_adaptive, enable_mirage=enable_mirage, 
                calibration_type=calibration_type, initial_layout=initial_layout)
        
        detail_id = self._save_result_to_db(updated_qasm)

    
    def apply_mirage(self, qiskit_optimization_level, enable_mirage = 1):
        
        updated_qasm = mirage_wrapper.optimize_qasm(
            self.qasm, conf.hardware_name, qiskit_optimization_level)

        detail_id = self._save_result_to_db(updated_qasm)

    def apply_triq(self, triq_optimization, calibration_type = calibration_type_enum.realtime.value):
        """
        """    
        updated_qasm = self.qasm
        self.qiskit_qasm = None
        self.qasm_before_decomposed_final = None

        updated_qasm = qiskit_wrapper.transpile_to_basis_gate(updated_qasm, self.backend_service)
        self.qiskit_qasm = updated_qasm

        updated_qasm = triq_wrapper.run(updated_qasm, 
                                        conf.hardware_name + "_" + calibration_type, 
                                        triq_optimization)

        detail_id = self._save_result_to_db(updated_qasm)

        return updated_qasm

    def apply_laura(self, laura_optimization = 0, calibration_type = calibration_type_enum.realtime.value):
        """
        apply_qiskit:
            "before" : before laura's version of triq
            "after"  : after laura's version of triq
        """    
        updated_qasm = self.qasm
        self.qiskit_qasm = None
        self.qasm_before_decomposed_final = None

        updated_qasm = qiskit_wrapper.transpile_to_basis_gate(updated_qasm, self.backend_service)
        self.qiskit_qasm = updated_qasm

        updated_qasm = laura_wrapper.run(updated_qasm, conf.hardware_name + "_" + calibration_type, laura_optimization)

        detail_id = self._save_result_to_db(updated_qasm)

    
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
            p_noise_adaptive, mirage, p_hamap, p_laura_optimization = None, None, None, None
            p_calibration_type = None

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
                    elif i == "enable_noise_adaptive":
                        p_noise_adaptive = 1 if calling_function_locals[i] == True else 0
                    elif i == "enable_mirage":
                        mirage = 1 if calling_function_locals[i] == True else 0
                    elif i == "calibration_type":
                        p_calibration_type = calling_function_locals[i]

            # Connect to the MySQL database
            conn = mysql.connector.connect(**conf.mysql_config)
            cursor = conn.cursor()
            
            # insert to detail
            now_time = datetime.now().strftime("%Y%m%d%H%M%S")
            sql = '''INSERT INTO result_detail (user_id, header_id, job_id, status, 
                           qiskit_optimization, apply_qiskit, triq_optimization, calibration_type, noise_adaptive, 
                           mirage, hamap, laura_optimization, created_datetime) 
                           VALUES (
                           %s, %s, %s, %s, 
                           %s, %s, %s, %s, %s, 
                           %s, %s, %s, %s)'''
            
            parms = (self.user_id, self.header_id, job_id, "pending",  
                         p_qiskit_optimization, p_apply_qiskit, p_triq_optimization, p_calibration_type, p_noise_adaptive,
                         mirage, p_hamap, p_laura_optimization, now_time)

            cursor.execute(sql, parms)
            detail_id = cursor.lastrowid

            # insert to result_updated_qasm
            cursor.execute('''INSERT INTO result_updated_qasm (detail_id, updated_qasm, qiskit_qasm, qasm_before_decomposed_final) 
                           VALUES (
                           %s, %s, %s, %s)''',
                        (detail_id, updated_qasm, self.qiskit_qasm, self.qasm_before_decomposed_final))

            conn.commit()
            cursor.close()
            conn.close()

            return detail_id
        
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        
    def send_qasm_to_real_backend(self):

        # Connect to the MySQL database
        conn = mysql.connector.connect(**conf.mysql_config)
        cursor = conn.cursor()

        # if self.run_in_simulator:
        #     # self.provider = IBMProvider(token=conf.qiskit_token)
        #     # self.backend = self.provider.get_backend("simulator_mps")
        #     self.backend = self.service.get_backend("simulator_mps")
                
        cursor.execute('''SELECT DISTINCT header_id
                       FROM calibration_data.result_detail 
                       WHERE job_id IS NULL 
                       ''')
        results_1 = cursor.fetchall()

        for res_1 in results_1:
            header_id = res_1[0]

            cursor.execute('''SELECT detail_id, updated_qasm, d.qiskit_optimization FROM calibration_data.result_detail d
                            INNER JOIN calibration_data.result_updated_qasm q ON d.id = q.detail_id 
                            WHERE d.job_id IS NULL AND d.header_id = %s AND d.user_id IN (10, 11, 99) ''', (header_id,))
            results = cursor.fetchall()

            success = False
            list_circuits = []

            for res in results:
                detail_id, updated_qasm, qiskit_optimization = res

                qc = QiskitCircuit(updated_qasm, name=self.circuit_name + "-" + str(detail_id))
                # circuit = qc.get_native_gates_circuit(self.backend, self.run_in_simulator)
                circuit = qc.circuit

                for i in range(self.runs):
                    list_circuits.append(circuit)
                

            while not success:
                try:

                    print("Sending to {} with batch id: {} ... ".format(conf.hardware_name, header_id))

                    
                    self.set_sampler_options()

                    job, job_id = None, None
                    if self.run_in_simulator:
                        job = self.sampler.run(list_circuits, shots=conf.shots)
                        job_id = job.job_id()
                    else:
                        # job = self.backend.run(list_circuits, shots=self.shots)
                        job = self.sampler.run(list_circuits, shots=conf.shots)
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

    def run(self):
        """
        
        """
        print("Running qiskit opt 0")
        self.apply_qiskit(qiskit_optimization_level=0)
        print("Running qiskit opt 3")
        self.apply_qiskit(qiskit_optimization_level=3)
        # # # self.apply_qiskit(qiskit_optimization_level=3, enable_mirage=True)
        print("Running qiskit opt 3 NA Realtime")
        self.apply_qiskit(qiskit_optimization_level=3, enable_noise_adaptive=True, calibration_type=calibration_type_enum.realtime.value)
        print("Running qiskit opt 3 NA Realtime Adjust")
        self.apply_qiskit(qiskit_optimization_level=3, enable_noise_adaptive=True, calibration_type=calibration_type_enum.realtime_adjust.value)
        self.apply_qiskit(qiskit_optimization_level=3, enable_noise_adaptive=True, calibration_type=calibration_type_enum.recent_15.value)
        self.apply_qiskit(qiskit_optimization_level=3, enable_noise_adaptive=True, calibration_type=calibration_type_enum.recent_15_adjust.value)
        self.apply_qiskit(qiskit_optimization_level=3, enable_noise_adaptive=True, calibration_type=calibration_type_enum.mix.value)
        self.apply_qiskit(qiskit_optimization_level=3, enable_noise_adaptive=True, calibration_type=calibration_type_enum.mix_adjust.value)
        self.apply_qiskit(qiskit_optimization_level=3, enable_noise_adaptive=True, calibration_type=calibration_type_enum.average.value)
        self.apply_qiskit(qiskit_optimization_level=3, enable_noise_adaptive=True, calibration_type=calibration_type_enum.average_adjust.value)

        # # for sending without any transpilation to the backend
        # self.apply_qiskit(qiskit_optimization_level=99)


        # self.apply_triq(triq_optimization=0, calibration_type=calibration_type_enum.realtime.value)
        # self.apply_triq(triq_optimization=0, calibration_type=calibration_type_enum.recent_15.value)
        # self.apply_triq(triq_optimization=0, calibration_type=calibration_type_enum.decay_15.value)
        # self.apply_laura(laura_optimization=2, calibration_type=calibration_type_enum.realtime.value)
        # self.apply_laura(laura_optimization=2, calibration_type=calibration_type_enum.recent_15.value)
        # self.apply_laura(laura_optimization=2, calibration_type=calibration_type_enum.decay_15.value)


        
        # self.apply_triq(triq_optimization=0, calibration_type=calibration_type_enum.average.value)
        # self.apply_triq(triq_optimization=0, calibration_type=calibration_type_enum.recent_45.value)
        # self.apply_triq(triq_optimization=0, calibration_type=calibration_type_enum.mix.value)
        # self.apply_triq(triq_optimization=0, calibration_type=calibration_type_enum.decay_r.value)
        # self.apply_triq(triq_optimization=0, calibration_type="decay_45")
        # self.apply_triq(triq_optimization=0, calibration_type=calibration_type_enum.decay_mix.value)

        

        # self.apply_laura(laura_optimization=2, calibration_type=calibration_type_enum.average.value)
        # self.apply_laura(laura_optimization=2, calibration_type=calibration_type_enum.recent_45.value)
        # self.apply_laura(laura_optimization=2, calibration_type=calibration_type_enum.mix.value)
        # self.apply_laura(laura_optimization=2, calibration_type=calibration_type_enum.decay_r.value)
        # self.apply_laura(laura_optimization=2, calibration_type="decay_45")
        # self.apply_laura(laura_optimization=2, calibration_type=calibration_type_enum.decay_mix.value)

    def get_fake_perth(self):
        fake_perth = qiskit_wrapper.NewFakePerth()
        print(fake_perth.name)

        fake_perth = qiskit_wrapper.NewFakePerthRecent15()
        print(fake_perth.name)

        transpile(self.initial_circuit.circuit, 
                    fake_perth,
                    optimization_level=3,
                    routing_method="sabre",
                    layout_method="noise_adaptive",
                    )

if __name__ == "__main__":

#region with parameter
    # arglist = sys.argv[1:]
    # hardware_name = arglist[0]
    # qasm_source = arglist[1]
    # circuit_name = qasm_source.split("/")[-1].split(".")[0]
    # print("Selected circuit: {} ".format(circuit_name))
    # q = None

    # q = QEM(qasm_source, runs=20, run_in_simulator=True\
    #         , circuit_name=circuit_name, user_id=2)
    # q.run()
    # # Send to backend
    # q.send_qasm_to_real_backend()
#endregion

    # List all files in the base folder with the .qasm extension
    qasm_files = glob.glob(os.path.expanduser(os.path.join(conf.base_folder, "*.qasm")))
    qasm_files = sorted(qasm_files)

    start_time = time.perf_counter()

    # for i in qasm_files:
    #     qasm_source = i
    #     circuit_name = i.split("/")[-1].split(".")[0]
    #     print("=========== {} ===========".format(circuit_name))
    #     q = None

    #     tmp_start_time  = time.perf_counter()
    #     # q = QEM(qasm_source, runs=4, 
    #     #         fixed_initial_layout = False, run_in_simulator=False, 
    #     #         calibration_type = calibration_type_enum.realtime, 
    #     #         circuit_name=circuit_name, user_id=11)
        
    #     q = QEM(qasm_source, runs=2, 
    #             fixed_initial_layout = False, run_in_simulator=False, 
    #             calibration_type = calibration_type_enum.realtime, 
    #             circuit_name=circuit_name, user_id=10)
        
    #     # # set initial layout
    #     # q.initial_layout_qiskit = None

    #     # q = QEM(qasm_source, runs=10, 
    #     #         fixed_initial_layout = False, run_in_simulator=True, 
    #     #         calibration_type = calibration_type_enum.realtime, 
    #     #         circuit_name=circuit_name, user_id=95)
    #     # q = QEM(qasm_source, runs=1, 
    #     #         fixed_initial_layout = False, run_in_simulator=True, 
    #     #         calibration_type = calibration_type_enum.realtime, 
    #     #         circuit_name=circuit_name, user_id=99)
    #     tmp_end_time = time.perf_counter()

    #     print("Time for initialization: {} seconds".format(tmp_end_time - tmp_start_time))
        
    #     # q.get_fake_perth()
        
    #     tmp_start_time  = time.perf_counter()
    #     q.init_result_header()
    #     tmp_end_time = time.perf_counter()

    #     print("Time for running the init header: {} seconds".format(tmp_end_time - tmp_start_time))

    #     tmp_start_time  = time.perf_counter()
    #     q.run()
    #     tmp_end_time = time.perf_counter()

    #     print("Time for running the optimization: {} seconds".format(tmp_end_time - tmp_start_time))
    #     # time.sleep(5)

    #     tmp_start_time  = time.perf_counter()
    #     q.send_qasm_to_real_backend()
    #     tmp_end_time = time.perf_counter()

    #     print("Time for sending to backend: {} seconds".format(tmp_end_time - tmp_start_time))
        
    end_time = time.perf_counter()
    print("Total time executed: {} seconds".format(end_time - start_time))
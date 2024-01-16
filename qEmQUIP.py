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
from commons import convert_to_json, triq_optimization, qiskit_optimization, calibration_type_enum, normalize_counts
import inspect
from qiskit import Aer, QuantumCircuit, transpile
from qiskit_ibm_provider import IBMProvider
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator, Options
from qiskit_aer.noise import NoiseModel

from datetime import datetime
import mysql.connector
import time

activate_debugging_time = True
# MySQL connection parameters
mysql_config = {
    'user': 'handy',
    'password': 'handy',
    'host': 'ec2-16-171-254-2.eu-north-1.compute.amazonaws.com',
    'database': 'calibration_data'
}

simulator_hardware = "ibmq_qasm_simulator"

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

    def get_native_gates_circuit(self, backend, simulator = False):
        if simulator:
            return transpile(self.circuit.decompose(), backend, basis_gates=["u3", "cx"], optimization_level=0, layout_method="trivial")
        else:
            return transpile(self.circuit.decompose(), backend, basis_gates=backend.basis_gates, optimization_level=0, layout_method="trivial")
    
    def get_qasm(self):
        return self.qasm

class QEM:
    def __init__(self, token, qasm_source, shots=8192, runs=2, 
                 fixed_initial_layout = False, 
                 run_in_simulator = False, hardware_name = simulator_hardware, 
                 calibration_type = calibration_type_enum.realtime,
                 circuit_name = "circuit", user_id = 99):
        self.run_in_simulator = run_in_simulator
        self.hardware_name = hardware_name
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

        self.mysql_config = None
        self.qiskit_token = None

        self.qasm = None 
        self.qiskit_qasm = None
        self.qasm_before_decomposed_final = None
        
        self.shots = shots
        self.runs = runs
        self.correct_output = None
        self.total_gate = None
        self.gates = None
        self.depth = None
        
        self.header_id = None
        self.user_id = user_id

        self.load_account(token)

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
                                                       self.hardware_name + "_" + self.calibration_type.value, 
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
        # self.provider = IBMProvider(token=self.qiskit_token)
        # self.backend = self.provider.get_backend(self.hardware_name)

        if self.hardware_name == "ibm_algiers":
            self.service = QiskitRuntimeService(channel="ibm_cloud", token=self.qiskit_token, instance="Qiskit Runtime-ucm")
        else:
            self.service = QiskitRuntimeService(channel="ibm_quantum", token=self.qiskit_token)
        self.backend = self.service.get_backend(self.hardware_name)

        if simulator_hardware != "ibmq_qasm_simulator":
            backend_sim = self.service.get_backend(simulator_hardware)
            sampler = Sampler(backend_sim) 
            job_sim = sampler.run(transpile(qc, backend_sim, basis_gates=["u3", "cx"]), shots=8192)
            result_sim = job_sim.result()  
            self.correct_output = dict(result_sim.quasi_dists[0])  
        else:
            backend_sim = Aer.get_backend('qasm_simulator')
            job_sim = backend_sim.run(transpile(qc, backend_sim), shots=8192)
            result_sim = job_sim.result()  
            self.correct_output = normalize_counts(dict(result_sim.get_counts(qc)))
        
        self.gates = dict(qc.count_ops())
        self.depth = qc.depth()

    def set_sampler_options(self):
        start_time = time.perf_counter()

        service = None
        if self.hardware_name == "ibm_algiers":
            service = QiskitRuntimeService(channel="ibm_cloud", token=self.qiskit_token, instance="Qiskit Runtime-ucm")
        else:
            service = QiskitRuntimeService(channel="ibm_quantum", token=self.qiskit_token)

        self.backend_service = service.get_backend(self.hardware_name)
        backend_sim = service.get_backend(simulator_hardware)
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
            options.execution.shots = self.shots
            options.optimization_level = 0
            options.resilience_level = 0

            #self.session = Session(service=service, backend=backend_sim, max_time="25m")
            self.sampler = Sampler(backend_sim, options=options) 
        else:
            options = Options()
            options.execution.shots = self.shots
            options.optimization_level = 0
            # options.resilience_level = 0
            options.resilience_level = 1
            self.sampler = Sampler(self.backend_service, options=options) 

    def init_result_header(self):
        
        # Connect to the MySQL database
        conn = mysql.connector.connect(**self.mysql_config)
        cursor = conn.cursor()

        # insert to circuit
        cursor.execute('INSERT INTO circuit (name, qasm, depth, total_gates, gates, correct_output, hw_name) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (self.circuit_name, self.qasm, self.depth, self.total_gate, convert_to_json(self.gates), convert_to_json(self.correct_output), self.hardware_name ))
        circuit_id = cursor.lastrowid
        
        # insert to header
        now_time = datetime.now().strftime("%Y%m%d%H%M%S")
        cursor.execute('INSERT INTO result_header (user_id, circuit_id, created_datetime, qiskit_token) VALUES (%s, %s, %s, %s)',
                    (self.user_id, circuit_id, now_time, self.qiskit_token))
        self.header_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

    def load_account(self, token):

        # MySQL connection parameters
        self.mysql_config = mysql_config

        self.qiskit_token = token

        start_time = time.perf_counter()

        # Save account credentials.
        # IBMProvider.save_account(token=token, overwrite=True)
        QiskitRuntimeService.save_account(channel="ibm_quantum", token=token, overwrite=True)

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
            self.qasm, self.hardware_name, qiskit_optimization_level)

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
                                        self.hardware_name + "_" + calibration_type, 
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

        updated_qasm = laura_wrapper.run(updated_qasm, self.hardware_name + "_" + calibration_type, laura_optimization)

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
            conn = mysql.connector.connect(**self.mysql_config)
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
        conn = mysql.connector.connect(**self.mysql_config)
        cursor = conn.cursor()

        # if self.run_in_simulator:
        #     # self.provider = IBMProvider(token=self.qiskit_token)
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

                    print("Sending to {} with batch id: {} ... ".format(self.hardware_name, header_id))

                    
                    self.set_sampler_options()

                    job, job_id = None, None
                    if self.run_in_simulator:
                        job = self.sampler.run(list_circuits, shots=self.shots)
                        job_id = job.job_id()
                    else:
                        # job = self.backend.run(list_circuits, shots=self.shots)
                        job = self.sampler.run(list_circuits, shots=self.shots)
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

#region token
    # # token pepe 1
    # token = "924828a6b1671411b96c27b10123849b161154290707582dc60d0b900146ccc8fb93adda735a6d0805168b3007a8ad56f626f9f207881d5055c841a58e51a7d9"

    # # token pepe 2
    # token = "2298ebebdf52aa8ef9258a07154bc62d335af0126f2bed26502a43f32a206309618c34344db22713f54bad3dc1c7569d7d1e3a0075e0421160e83b8c50967b45"

    # # token pepe 3
    # token = "01501f074b8bc9910185d5563408e2838951163e8f55b90a338c94c58116b92a1cd88081474827667b9d907604f2dd27eaa8399a83fbb9505a24e25875819b23"

    # # token pepe 4
    # token = "055a93864810f2fc66e4de35b13027e8e591f0d019abb91b4895971fa16a991bef0ac573457c707c3d1070e5105d8f0cdd489f842cc06723d29a233c9f483e74"

    # # token untukmain
    # token = "e9dc3b4555eaceaf68dd163b187fe3f2354d0ae5032b50f2e0a01693118c83ccdd2f86f77bb37f0983244358d776defaa18614aafede58d1d8bfaea7b51c5a98"

    # # token handyokur
    # token = "d6c68cd3c7151e9499fcaf54ff7982629e20ff25d38f32aea5b64db369985c82682f63b991dc6fc8424f4ac0349882d90a5399b03194d047b3b9b2eefb4613b3"

    # # token jose mario
    # token = "94882007fb17bcb98ad4c7d13adb024491bd30e72e4be58628dd685ce2c90bcbefb8abc65094cf051de77c8b676b4aa936bba8ad4a0df0e573e3cc01308c5421"

    # # token contact 07
    # token = "68fb7ac07545c0cc3b63bea6bae1a2e69fe11c4f84be2d4dc335abd5747c602701e9e687876adbf9bb61b11f25fa82ca2c932808fd3f128450cc13670d4822fe"

    # # token cornice apple
    # token = "bfbe3159e00973e14168671f8790ab7d2b85e8cb61160ee0b17225cf312df48e582cad577b02781ddca79d382e9e3aba3ad9c46c9c47d1b1b5ed27c8815cc2ca"

    # # token petrol
    # token = "c0151c25a1bcb6e3f9274fb403cacf619f2508b2e70fcf350f1e44aba618f8d379f63f3554f58d2b6b7e04a63f20ba14895857e50b598c2c584c1b6519e6bc61"

    # # token mash-pensive
    # token = "76eaa6f112f125eae669975b89d1620f8ea96cc9c28c650a2d9bed8e171d1ddf21aa685f46fa5d9377a86f7526ace1477c37f5fd5b0e8c0b0a25813a958958ce"

    # # token handy ut
    # token = "ed88b12a8fcd39cac8e31e7097a2ed01839ef8d3bbad7e5c911aa16d7fb69314d077f901277b248739ed4f2bd66749588c51a35234620a64bf69ce485a20acd0"

    # # token bylaw
    # token = "30ea7c188f2b6531d2525875b7dab58f0d0091cb4c6e080472cdc76a96009aabbc3367ee1e1ac5f1aa2229941b08a7ef487066df163d47545c9524c4cad1c2ed"

    # # token fasts
    # token = "ad1527ea50d2b9fb3f122427c6423c55c036d6e3e6559c96a9d5bf4b2b813909a4aac65cbf23bc6ea8cc55da005be0dc85cfb72fa3cd5f57c3eec8a99ea3f9d8"

    # # token arrival point
    # token = "5c63e6d0dbc47a7c98741ea6b7de90afb0729f5e036dbea439cec03ee680d5dfa573bdb42920017edb942be678d54d4fb5d83d5e7296749f78dee5449a6f443b"

    # # token frisbee
    # token = "68d7a37e272a1a29ab8a3c767c63443fbf78fb82cfc34ac689d92f8f77f8fcdc4fd48dec46aa257a116f3194ba6532334f67d1b0a6f9feb53f1296804cb418b2"

    # # token button
    # token = "ec5f9f43cea1eb948b374f22419e8e96307aa8ed59af234cd9133db2564dcc0f1c36eafc99f1565a9c5488d06296d0a291f1fff571fea5e8d01d0eddce7fa14f"

    # # token known
    # token = "78b48009dcb68d57e164d1929cf4f0b248a827d18fc739107e127eef34d87bf67ad9b445744f7c7cd2cd1232ea8b92db11d7878be3542a131d17621586cf410c"

    # # token puffs
    # token = "266686280de68a1d68433c62d7e154391b905705041b43744a591c19528cefb7335fa425ea81855fd0ca88ae7950b726dd615c23b53bc14a99e579874aa1202f"

    # # token shanty
    # token = "88fa7b6ee1ba1303c21d4a46cc6db9b44bfc1c4a86ff4d10476d5c6a28b7b2427e23c0cb7430ef103ac38310f74a71791a03aee26e2b9cdad266ef0a120d7c71"

    # # token pipe
    # token = "f4376ab6435cab311bd27c6a403617cff71804667f537c72879fd68fc2e80ff8fc3c2c67509fa840f2ac39318604154319858e71434b35db9570568614c51d63"

    # # token lodging
    # token = "73e5caa60d526c2122261d8b1d93d451f8e8add930a03d2ab6fe16702673ccfcdce9dd018820f5ca6bed692112c9a5d32e2d2f2b75d367d38dde3ed2a51e3c6b"

    # # token bionic
    # token = "dc8be56745da5fe77438ee9a3cfc0b6fa87f219ec3e50db59788cf157ed43ed776a1986b569ad5ec57525aa5f299fdb17c90cb34d3a04be7ca4af1bfbbc85eca"

    # # token ropes
    # token = "b94c13374ae4f0b04fb2539b727e165ec695373f7fe198dd69c3b11f22a2aa380c8adca06390f201d2aa09247348aeae6f7664e0735698c9d8ad59880e58b8b8"

    # # token rudder (license)
    # token = "26f4ebc603700e1d56ac25c2a18c6ef196859f3a5547abe12ced49f3c16ef3c8391008db57e5bc77cd4ec3b3c62d26aeccf9983f311a279b714b5378ff4415cf"

    # # token mercury
    # token = "243e229672da5f0a602a816c821b96ded412c2c17041da434aed04e8e225603e40093013bc1a3392566ef090a48b389c80c9c38cb3b7626046a7682f16414e84"

    # # token clashes
    # token = "39a9660087b540bce0c4faebfa9fc5e32b7efd79b5c590a685ab4b20b4087a469dfb4e890f4308d62ebdb21be6cc421f27c5be553a42b43738aee05f02e13b48"

    # # token roosts
    # token = "2b2c8db93b834b4ef95fc0da7d6fd70f345de16464f8037655f87c96373703e46d0b0f48f8f5dbea70c82fd06c3405d7810f2f9e14b9d4e92d6487f62dbe2269"

    # # token platoon
    # token = "c6593b682f0a88379cdfdf83dee4399376885c04ca605d9471367d6313690772c338f4b1683af2ff9f713511f83cdf1357529882a5687fd67f7a37ec85c0e186"

    # # token bobs
    # token = "eeaa19292016f1efc96f7dc11676fe47cbfc12a85869374e6b8ce3c225c5e8ef029d1fa912bb5def86a7b3c62ea55cf16b386d1ea0051fa26676efa2a7df1db2"

    # token bygone
    token = "e62477a6e14315c89eb74f224f4aa6d44ae4fe4739bac484ab485ceedc97d4df9962b81286ead7ffe27a4b5443e8c03dd9ee516f09213a49fd3fa88976eba103"

    # # token pore
    # token = "a0347b951804a105a6c256d274c49ddcb284da7c20c9058e064afaea6844505f5451027feb6c335fbabe7c1e1b0bc62a9304f32ca54ed89a0d1e6d253eaf32fa"

    # # token chores
    # token = "83fae468c72cb0e06e66c77c7520a24058a4ec4629b7e45236f7cf336237abc4cc5ce6ef9d2192ab652da68c7667143d09454687d76e42f9919f1e91ffb043a3"

    # # token ales
    # token = "7f531e9960905f9a3142ead5d8c004bf5dc39a59462dd70e5f623918bd539fecc0f7434dcbbf453aecad2cc6545595ce1f9edfbb029fc948e6e22c35ebf5e331"

    # # token anion
    # token = "4bcab1e9db485961e3a583b52b04c7fd35f476751e1c0107406e7fa6b2b6ae899c65142ac5547842f02bd6c667b1ce92a790b107acf56c3e748d32dd63830a55"

    # # token lumbar
    # token = "6955cf58b16e371d4b788ffd7602b6b1c134701f6a058a8ef02a71d6547b912f0602bc04f5e80a55ad67e4e64b29e0863b568760e7e7baa62159c975fe3df07b"

#endregion

#region with parameter
    # arglist = sys.argv[1:]
    # hardware_name = arglist[0]
    # qasm_source = arglist[1]
    # circuit_name = qasm_source.split("/")[-1].split(".")[0]
    # print("Selected circuit: {} ".format(circuit_name))
    # q = None

    # q = QEM(token, qasm_source, hardware_name=hardware_name, runs=20, run_in_simulator=True\
    #         , circuit_name=circuit_name, user_id=2)
    # q.run()
    # # Send to backend
    # q.send_qasm_to_real_backend()
#endregion

    # # handy UCM regular
    # token = "9b1a802766a56b6a51fdf73762fcf6f5c0bd33ef1f5afcef2157693593292c06b5bc92861d8758a585bd4f6d588b2155f5a45fb912f41610a1ad8bb2119f6521"

    # # handy UCM API cloud
    # token = "isz-S9_mFwh8ikGssvCSoxoL3yk6mCyAkmsKoRyI8O0P"

    hardware_name = "ibm_brisbane"
    # hardware_name = "ibm_algiers"
    # hardware_name = "simulator_mps"
    
    # Define the base folder path
    # base_folder = "~/Quantum_benchmarks/QASMBench/run/"
    base_folder = "~/Quantum_benchmarks/Paper_circuits/n_7_run/"
    # base_folder = "~/Quantum_benchmarks/Paper_circuits/error-triq/"

    # List all files in the base folder with the .qasm extension
    qasm_files = glob.glob(os.path.expanduser(os.path.join(base_folder, "*.qasm")))
    qasm_files = sorted(qasm_files)

    start_time = time.perf_counter()

    for i in qasm_files:
        qasm_source = i
        circuit_name = i.split("/")[-1].split(".")[0]
        print("=========== {} ===========".format(circuit_name))
        q = None

        tmp_start_time  = time.perf_counter()
        # q = QEM(token, qasm_source, hardware_name=hardware_name, runs=4, 
        #         fixed_initial_layout = False, run_in_simulator=False, 
        #         calibration_type = calibration_type_enum.realtime, 
        #         circuit_name=circuit_name, user_id=11)
        
        q = QEM(token, qasm_source, hardware_name=hardware_name, runs=2, 
                fixed_initial_layout = False, run_in_simulator=False, 
                calibration_type = calibration_type_enum.realtime, 
                circuit_name=circuit_name, user_id=10)
        
        # # set initial layout
        # q.initial_layout_qiskit = None

        # q = QEM(token, qasm_source, hardware_name=hardware_name, runs=10, 
        #         fixed_initial_layout = False, run_in_simulator=True, 
        #         calibration_type = calibration_type_enum.realtime, 
        #         circuit_name=circuit_name, user_id=95)
        # q = QEM(token, qasm_source, hardware_name=hardware_name, runs=1, 
        #         fixed_initial_layout = False, run_in_simulator=True, 
        #         calibration_type = calibration_type_enum.realtime, 
        #         circuit_name=circuit_name, user_id=99)
        tmp_end_time = time.perf_counter()

        print("Time for initialization: {} seconds".format(tmp_end_time - tmp_start_time))
        
        # q.get_fake_perth()
        
        tmp_start_time  = time.perf_counter()
        q.init_result_header()
        tmp_end_time = time.perf_counter()

        print("Time for running the init header: {} seconds".format(tmp_end_time - tmp_start_time))

        tmp_start_time  = time.perf_counter()
        q.run()
        tmp_end_time = time.perf_counter()

        print("Time for running the optimization: {} seconds".format(tmp_end_time - tmp_start_time))
        # time.sleep(5)

        tmp_start_time  = time.perf_counter()
        q.send_qasm_to_real_backend()
        tmp_end_time = time.perf_counter()

        print("Time for sending to backend: {} seconds".format(tmp_end_time - tmp_start_time))
        
    end_time = time.perf_counter()
    print("Total time executed: {} seconds".format(end_time - start_time))
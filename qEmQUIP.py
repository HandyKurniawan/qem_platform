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
    calibration_type_enum, qiskit_compilation_enum, normalize_counts, Config, num_sort
import inspect
from qiskit import Aer, QuantumCircuit, transpile
from wrappers.qiskit_wrapper import QiskitCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Estimator, Options
from qiskit_aer.noise import NoiseModel

from datetime import datetime
import mysql.connector
import time


conf = Config()
debug = conf.activate_debugging_time


class QEM:
    def __init__(self, runs=2, 
                 fixed_initial_layout = False, 
                 run_in_simulator = False, 
                 user_id = 99):
        self.run_in_simulator = run_in_simulator

        self.session = None
        self.service = None
        self.backend = None
        self.sampler = None

        self.fixed_initial_layout = fixed_initial_layout
        self.initial_layout_qiskit = None
        self.initial_layout_triq = None 

        self.conn = None
        self.cursor = None    

        self.circuit_name = None
        self.qasm = None 
        self.runs = runs
        
        self.header_id = None
        self.user_id = user_id

        self.open_database_connection()
        self.set_backend()

        # circuit move to the detail level
        # self.initial_circuit = QiskitCircuit(qasm_source, name="initial circuit")

        # if self.calibration_type == calibration_type_enum.lcd:
        #     triq_wrapper.generate_realtime_calibration_data(self)

        # if self.calibration_type == calibration_type_enum.lcd:
        #     triq_wrapper.generate_realtime_calibration_data(self)
        #     triq_wrapper.generate_mix_calibration_data(self)
        #     triq_wrapper.generate_recent_average_calibration_data(self, 45)
        #     triq_wrapper.generate_recent_average_calibration_data(self, 15)

        # if fixed_initial_layout:
        #     self.set_initial_layout()

    def open_database_connection(self):
        self.conn = mysql.connector.connect(**conf.mysql_config)
        self.cursor = self.conn.cursor()

    def close_database_connection(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def set_backend(self, token=conf.qiskit_token):
        QiskitRuntimeService.save_account(channel="ibm_quantum", token=token, overwrite=True)

        if conf.hardware_name == "ibm_algiers":
            self.service = QiskitRuntimeService(channel="ibm_cloud", token=token, instance=conf.ibm_cloud_instance)
        else:
            self.service = QiskitRuntimeService(channel="ibm_quantum", token=token)
            # self.service = QiskitRuntimeService()

        if conf.hardware_name != "ibm_perth":
            self.backend = self.service.get_backend(conf.hardware_name)
        else:
            self.backend = self.get_fake_perth()

        backend_sim = self.service.get_backend(conf.simulator_hardware)
        noise_model = NoiseModel.from_backend(self.backend)

        if (self.run_in_simulator):            
            options = Options()
            options.simulator = {
                "noise_model": noise_model,
                # "basis_gates": self.backend.configuration().basis_gates,
                "coupling_map": self.backend.configuration().coupling_map
            }
            # options.transpilation.initial_layout = "noise_adaptive"
            # options.transpilation.routing_method = "sabre"
            options.execution.shots = conf.shots
            options.optimization_level = conf.optimization_level
            options.resilience_level = conf.resilience_level

            #self.session = Session(service=service, backend=backend_sim, max_time="25m")
            self.sampler = Sampler(backend_sim, options=options) 
        else:
            options = Options()
            options.execution.shots = conf.shots
            options.optimization_level = conf.optimization_level
            options.resilience_level = conf.resilience_level
            
            if conf.hardware_name != "ibm_perth":
                self.sampler = Sampler(self.backend, options=options) 
            else:
                self.sampler = Sampler(backend_sim, options=options) 

    def get_circuit_properties(self, qasm_source):
        circuit_name = qasm_source.split("/")[-1].split(".")[0]

        # check if the metric is already there, just update
        self.cursor.execute('SELECT name FROM circuit WHERE name = %s', (circuit_name,))
        existing_row = self.cursor.fetchone()

        qc = QiskitCircuit(qasm_source, name=circuit_name)
        gates_json = convert_to_json(qc.gates)
        correct_output_json = convert_to_json(qc.correct_output)

        # insert to the table
        if not existing_row:
            self.cursor.execute("""INSERT INTO circuit (name, qasm, depth, total_gates, gates, correct_output)
            VALUES (%s, %s, %s, %s, %s, %s)""",
            (circuit_name, qc.qasm, qc.depth, qc.total_gate, gates_json, correct_output_json))

            self.conn.commit()

            print(circuit_name, "has been registered to the database.")
        else:
            # self.cursor.execute("""UPDATE circuit SET qasm = %s, depth  = %s, total_gates  = %s, gates = %s, correct_output = %s 
            #                     WHERE name = %s""",
            # (qc.qasm, qc.depth, qc.total_gate, gates_json, correct_output_json, circuit_name))

            # self.conn.commit()
            print(circuit_name, "already exist.")

        return qc

    def set_initial_layout(self):
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


    def init_result_header(self):
        
        now_time = datetime.now().strftime("%Y%m%d%H%M%S")
        self.cursor.execute("""INSERT INTO result_header (user_id, hw_name, qiskit_token, created_datetime) 
        VALUES (%s, %s, %s, %s)""",
        (self.user_id, conf.hardware_name, conf.qiskit_token, now_time))
        self.header_id = self.cursor.lastrowid

        # self.conn.commit()


    def apply_qiskit(self, 
                     updated_qasm = None,
                     compilation_name = qiskit_compilation_enum.qiskit_3,
                     generate_props = False, recent_n = None
                     ):
        """
        hmmm
        """

        qiskit_optimization_level = 3
        enable_noise_adaptive = False
        enable_mirage = False
        calibration_type = None

        if compilation_name == qiskit_compilation_enum.qiskit_3.value:    
            qiskit_optimization_level = 3
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_avg.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.average.value
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_lcd.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.lcd.value
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_mix.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.mix.value
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_w15.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.recent_15.value
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_avg_adj.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.average_adjust.value
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_lcd_adj.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.lcd_adjust.value
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_mix_adj.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.mix_adjust.value
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_w15_adj.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.recent_15_adjust.value
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_wn.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.recent_n.value

            compilation_name = compilation_name.replace("_wn", "_w{}".format(recent_n))
        elif compilation_name == qiskit_compilation_enum.qiskit_NA_wn_adj.value:    
            enable_noise_adaptive = True
            calibration_type = calibration_type_enum.recent_n_adjust.value

            compilation_name = compilation_name.replace("_wn", "_w{}".format(recent_n))
        
        if qiskit_optimization_level == 99:
            updated_qasm = self.qasm
        else:
            updated_qasm, compilation_time = qiskit_wrapper.optimize_qasm(
                self.qasm, self.backend, qiskit_optimization_level,
                enable_noise_adaptive=enable_noise_adaptive, enable_mirage=enable_mirage, 
                calibration_type=calibration_type, generate_props=generate_props, recent_n=recent_n)
        
        self.insert_to_result_detail(compilation_name, compilation_time, updated_qasm)
        return updated_qasm

    
    def apply_mirage(self, qiskit_optimization_level, enable_mirage = 1):
        
        updated_qasm = mirage_wrapper.optimize_qasm(self.qasm, conf.hardware_name, qiskit_optimization_level)

        return updated_qasm


    def apply_triq(self, compilation_name):
        """
        """    
        updated_qasm = self.qasm

        tmp_start_time  = time.perf_counter()
        if compilation_name == "triq_lcd":
            updated_qasm = triq_wrapper.run(updated_qasm, 
                                                conf.hardware_name + "_" + "real", 
                                                triq_optimization)
        tmp_end_time = time.perf_counter()
        compilation_time = tmp_end_time - tmp_start_time
        
        
        self.insert_to_result_detail(compilation_name, compilation_time, updated_qasm)

        return updated_qasm

    def apply_laura(self, compilation_name):
        """
        apply_laura:
            "before" : before laura's version of triq
            "after"  : after laura's version of triq
        """    
        updated_qasm = self.qasm
        tmp_start_time  = time.perf_counter()
        if compilation_name == "triq+_lcd":
            updated_qasm = laura_wrapper.run(updated_qasm, conf.hardware_name + "_" + "real", 2)
        tmp_end_time = time.perf_counter()
        compilation_time = tmp_end_time - tmp_start_time
        
        
        self.insert_to_result_detail(compilation_name, compilation_time, updated_qasm)

        return updated_qasm
    
    def insert_to_result_detail(self, compilation_name, compilation_time, updated_qasm):
        now_time = datetime.now().strftime("%Y%m%d%H%M%S")
        
        sql = """
        INSERT INTO result_detail
        (header_id, circuit_name, compilation_name, compilation_time, created_datetime)
        VALUES (%s, %s, %s, %s, %s);
        """

        self.cursor.execute(sql, (self.header_id, self.circuit_name, compilation_name, compilation_time, now_time))
        detail_id = self.cursor.lastrowid

        sql = """
        INSERT INTO result_updated_qasm
        (detail_id, updated_qasm)
        VALUES (%s, %s);
        """

        self.cursor.execute(sql, (detail_id, updated_qasm))

        self.conn.commit()

        
    def send_qasm_to_real_backend(self):

        self.cursor.execute('SELECT id, qiskit_token FROM result_header WHERE job_id IS NULL;')
        results_1 = self.cursor.fetchall()

        print("Total send to backend :", len(results_1))

        for res_1 in results_1:
            header_id, qiskit_token = res_1

            self.set_backend(qiskit_token)

            self.cursor.execute('''SELECT d.id, q.updated_qasm 
FROM result_detail d
INNER JOIN result_header h ON d.header_id = h.id
INNER JOIN result_updated_qasm q ON d.id = q.detail_id 
WHERE h.job_id IS NULL AND d.header_id = %s  ''', (header_id,))
            results = self.cursor.fetchall()

            success = False
            list_circuits = []

            for res in results:
                detail_id, updated_qasm = res

                qc = QiskitCircuit(updated_qasm, skip_simulation=True)
                circuit = qc.get_native_gates_circuit(self.backend, self.run_in_simulator)
                # circuit = qc.circuit

                for i in range(self.runs):
                    list_circuits.append(circuit)
                
            print("Total no of circuits :",len(list_circuits))

            while not success:
                try:

                    print("Sending to {} with batch id: {} ... ".format(conf.hardware_name, header_id))
                    job = self.sampler.run(list_circuits)
                    job_id = job.job_id()

                    success = True

                    # update to result detail
                    print("Sent!")
                    self.cursor.execute('UPDATE result_header SET job_id = %s, status = "pending", updated_datetime = NOW() WHERE id = %s', (job_id, header_id))

                    self.conn.commit()

                except Exception as e:
                    print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

                    for i in range(30, 0, -1):
                        time.sleep(1)
                        print(i)


    def run(self, generate_props = False):
        """
        
        """
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_3.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_lcd.value, generate_props=generate_props)

        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_3.value, generate_props=generate_props)
        # self.apply_triq(compilation_name="triq_lcd")
        # self.apply_laura(compilation_name="triq+_lcd")
        

        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_3.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_lcd.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_avg.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_mix.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_w15.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_lcd_adj.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_avg_adj.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_mix_adj.value, generate_props=generate_props)
        # self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_w15_adj.value, generate_props=generate_props)

        # for i in range(1, 3):
        # for i in range(1, 46):
        #     self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_wn.value, generate_props=generate_props, recent_n=i)
        


    def get_fake_perth(self):
        fake_perth = qiskit_wrapper.NewFakePerthAverage()
        print(fake_perth.name)

        return fake_perth

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
    qasm_files.sort(key=num_sort) 

    if debug: start_time = time.perf_counter()

    # initial class QEM
    if debug: tmp_start_time  = time.perf_counter()
    q = QEM(runs=1, fixed_initial_layout = False, run_in_simulator=False, user_id=6)
    # q = QEM(runs=4, fixed_initial_layout = False, run_in_simulator=False, user_id=7)

    # q = QEM(runs=1, fixed_initial_layout = True, run_in_simulator=False, user_id=99)
    # q = QEM(runs=1, fixed_initial_layout = False, run_in_simulator=False, user_id=99)
    if debug: tmp_end_time = time.perf_counter()
    if debug: print("Time for initialization: {} seconds".format(tmp_end_time - tmp_start_time))


    # init header
    if debug: tmp_start_time  = time.perf_counter()
    q.init_result_header()
    if debug: tmp_end_time = time.perf_counter()
    if debug: print("Time for running the init header: {} seconds".format(tmp_end_time - tmp_start_time))

    generate_props = True
    # generate_props = False

    for i in qasm_files:
        qasm_source = i
        q.circuit_name = i.split("/")[-1].split(".")[0]
        print("=========== {} ===========".format(q.circuit_name))
        
        qc = q.get_circuit_properties(qasm_source=qasm_source)
        q.qasm = qc.qasm

        # Run Optimization
        if debug: tmp_start_time  = time.perf_counter()
        q.run(generate_props)
        if debug: tmp_end_time = time.perf_counter()
        if debug: print("Time for running the optimization: {} seconds".format(tmp_end_time - tmp_start_time))
        
        generate_props = False

    q.close_database_connection()

    q.open_database_connection()
    
    # Send to backend
    if debug: tmp_start_time  = time.perf_counter()
    q.send_qasm_to_real_backend()
    if debug: tmp_end_time = time.perf_counter()
    if debug: print("Time for sending to backend: {} seconds".format(tmp_end_time - tmp_start_time))
    
    q.close_database_connection()

    if debug: end_time = time.perf_counter()
    if debug: print("Total time executed: {} seconds".format(end_time - start_time))
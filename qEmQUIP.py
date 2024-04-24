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
import json

conf = Config()
debug = conf.activate_debugging_time


class QEM:
    def __init__(self, runs=2, 
                 fixed_initial_layout = False, 
                 run_in_simulator = False, 
                 user_id = 99,
                 token=conf.qiskit_token):
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
        self.qasm_original = None 
        self.runs = runs
        
        self.header_id = None
        self.user_id = user_id

        self.open_database_connection()
        self.set_backend(token=token)

        # circuit move to the detail level
        # self.initial_circuit = QiskitCircuit(qasm_source, name="initial circuit")

        # if self.calibration_type == calibration_type_enum.lcd:
        #     triq_wrapper.generate_realtime_calibration_data(self)

        # if self.calibration_type == calibration_type_enum.lcd:
            # triq_wrapper.generate_realtime_calibration_data(self)
            # triq_wrapper.generate_mix_calibration_data(self)
            # triq_wrapper.generate_recent_average_calibration_data(self, 45)
            # triq_wrapper.generate_recent_average_calibration_data(self, 15)
        
        if conf.initialized_triq == 1:
            triq_wrapper.generate_realtime_calibration_data(self)
            triq_wrapper.generate_average_calibration_data(self)
            triq_wrapper.generate_mix_calibration_data(self)

        # if fixed_initial_layout:
        #     self.set_initial_layout()

    def open_database_connection(self):
        self.conn = mysql.connector.connect(**conf.mysql_config)
        self.cursor = self.conn.cursor()

    def close_database_connection(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def set_backend(self, token=conf.qiskit_token, shots=conf.shots):
        print("Set Backend:", token)
        QiskitRuntimeService.save_account(channel="ibm_quantum", token=token, overwrite=True)

        if conf.hardware_name == "ibm_algiers":
            self.service = QiskitRuntimeService(channel="ibm_cloud", token=token, instance=conf.ibm_cloud_instance)
        else:
            self.service = QiskitRuntimeService(channel="ibm_quantum", token=token)
            # self.service = QiskitRuntimeService()

        if conf.hardware_name == "ibm_brisbane_32":
            tmp_backend = self.service.get_backend("ibm_brisbane")
            noise_model, self.backend, coupling_map = qiskit_wrapper.generate_brisbane_32_noisy_simulator(tmp_backend, 1)
            basis_gates = tmp_backend.configuration().basis_gates
        else:
            self.backend = self.service.get_backend(conf.hardware_name)
            coupling_map = self.backend.configuration().coupling_map
            noise_model = NoiseModel.from_backend(self.backend)
            basis_gates = self.backend.configuration().basis_gates

        if (self.run_in_simulator):            
            options = Options()
            options.simulator = {
                "noise_model": noise_model,
                "basis_gates": basis_gates,
                "coupling_map": coupling_map
            }
            # options.transpilation.initial_layout = "noise_adaptive"
            # options.transpilation.routing_method = "sabre"
            options.execution.shots = shots
            options.optimization_level = conf.optimization_level
            options.resilience_level = conf.resilience_level
            self.backend_sim = self.service.get_backend(conf.simulator_hardware)
            #self.session = Session(service=service, backend=backend_sim, max_time="25m")
            self.sampler = Sampler(self.backend_sim, options=options) 
        else:
            options = Options()
            options.execution.shots = shots
            options.optimization_level = conf.optimization_level
            options.resilience_level = conf.resilience_level

            if conf.rep_delay != 0:
                options.execution.rep_delay = conf.rep_delay
            
            # if conf.hardware_name != "ibm_perth":
            #     self.sampler = Sampler(self.backend, options=options) 
            # else:
            #     self.sampler = Sampler(backend_sim, options=options) 
            self.sampler = Sampler(self.backend, options=options) 

    def get_circuit_properties(self, qasm_source):
        circuit_name = qasm_source.split("/")[-1].split(".")[0]

        # check if the metric is already there, just update
        self.cursor.execute('SELECT name FROM circuit WHERE name = %s', (circuit_name,))
        existing_row = self.cursor.fetchone()

        # Handy Remark, remove later
        skip = True

        # qc = QiskitCircuit(qasm_source, name=circuit_name)
        qc = QiskitCircuit(qasm_source, name=circuit_name, skip_simulation=skip)
        
        gates_json = convert_to_json(qc.gates)

        if skip:
            correct_output_json = ""
        else:
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


    def init_result_header(self, token=conf.qiskit_token):
        
        now_time = datetime.now().strftime("%Y%m%d%H%M%S")
        self.cursor.execute("""INSERT INTO result_header (user_id, hw_name, qiskit_token, shots, runs, created_datetime) 
        VALUES (%s, %s, %s, %s, %s, %s)""",
        (self.user_id, conf.hardware_name, token, conf.shots, conf.runs, now_time))
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
        enable_mapomatic = False
        calibration_type = None

        if compilation_name == qiskit_compilation_enum.qiskit_3.value:    
            qiskit_optimization_level = 3
        elif compilation_name == qiskit_compilation_enum.qiskit_0.value:    
            qiskit_optimization_level = 0            
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
        elif compilation_name == qiskit_compilation_enum.mapomatic_lcd.value:    
            enable_mapomatic = True
            calibration_type = calibration_type_enum.lcd.value
        elif compilation_name == qiskit_compilation_enum.mapomatic_avg.value:    
            enable_mapomatic = True
            calibration_type = calibration_type_enum.average.value
        elif compilation_name == qiskit_compilation_enum.mapomatic_mix.value:    
            enable_mapomatic = True
            calibration_type = calibration_type_enum.mix.value
        elif compilation_name == qiskit_compilation_enum.mapomatic_avg_adj.value:    
            enable_mapomatic = True
            calibration_type = calibration_type_enum.average_adjust.value
        elif compilation_name == qiskit_compilation_enum.mapomatic_w15_adj.value:    
            enable_mapomatic = True
            calibration_type = calibration_type_enum.recent_15_adjust.value
        
        if qiskit_optimization_level == 99:
            updated_qasm = self.qasm
        else:
            updated_qasm, compilation_time, initial_mapping = qiskit_wrapper.optimize_qasm(
                self.qasm, self.backend, qiskit_optimization_level,
                enable_noise_adaptive=enable_noise_adaptive, enable_mirage=enable_mirage, enable_mapomatic=enable_mapomatic,
                calibration_type=calibration_type, generate_props=generate_props, recent_n=recent_n)

        self.insert_to_result_detail(compilation_name, compilation_time, updated_qasm, initial_mapping)
        return updated_qasm

    
    def apply_mirage(self, qiskit_optimization_level, enable_mirage = 1):
        
        updated_qasm = mirage_wrapper.optimize_qasm(self.qasm, conf.hardware_name, qiskit_optimization_level)

        return updated_qasm


    def apply_triq(self, compilation_name, layout="mapo"):
        """
        """    
        updated_qasm = self.qasm_original

        calibration_type = calibration_type_enum.lcd.value
        if compilation_name == "triq_lcd":
            calibration_type = calibration_type_enum.lcd.value
        elif compilation_name == "triq_avg":
            calibration_type = calibration_type_enum.average.value
        elif compilation_name == "triq_mix":
            calibration_type = calibration_type_enum.mix.value

        initial_mapping = ""

        if layout == "mapo":
            # Generate Initial Mapping from Mapomatic to a File
            initial_mapping = qiskit_wrapper.get_initial_mapping_mapomatic(
                    self.qasm, self.backend, calibration_type=calibration_type, 
                    generate_props=generate_props, recent_n=0)
        elif layout == "na":
            initial_mapping = qiskit_wrapper.get_initial_mapping_na(
                    self.qasm, self.backend, calibration_type=calibration_type, 
                    generate_props=generate_props, recent_n=0)
        elif layout == "sabre":
            initial_mapping = qiskit_wrapper.get_initial_mapping_sabre(
                    self.qasm, self.backend, calibration_type=calibration_type, 
                    generate_props=generate_props, recent_n=0)
        
        print(initial_mapping)
        triq_wrapper.generate_initial_mapping_file(initial_mapping)

        hardware_name = ""
        if compilation_name == "triq_lcd":
            hardware_name = conf.hardware_name + "_" + "real"
        elif compilation_name == "triq_avg":
            hardware_name = conf.hardware_name + "_" + "avg"
        elif compilation_name == "triq_mix":
            hardware_name = conf.hardware_name + "_" + "mix"
            
        tmp_start_time  = time.perf_counter()
        updated_qasm = triq_wrapper.run(updated_qasm, hardware_name, 0, measurement_type=conf.triq_measurement_type)
        tmp_end_time = time.perf_counter()

        final_mapping = triq_wrapper.get_mapping(updated_qasm, hardware_name, 0)

        
        compilation_time = tmp_end_time - tmp_start_time
        
        compilation_name = layout + "_" + compilation_name
        self.insert_to_result_detail(compilation_name, compilation_time, updated_qasm, initial_mapping, final_mapping)

        return updated_qasm

    def apply_laura(self, compilation_name, layout="mapo"):
        """
        apply_laura:
            "before" : before laura's version of triq
            "after"  : after laura's version of triq
        """    
        updated_qasm = self.qasm_original

        calibration_type = calibration_type_enum.lcd.value
        if compilation_name == "triq+_lcd":
            calibration_type = calibration_type_enum.lcd.value
        elif compilation_name == "triq+_avg":
            calibration_type = calibration_type_enum.average.value
        elif compilation_name == "triq+_mix":
            calibration_type = calibration_type_enum.mix.value

        if layout == "mapo":
            # Generate Initial Mapping from Mapomatic to a File
            initial_mapping = qiskit_wrapper.get_initial_mapping_mapomatic(
                    self.qasm, self.backend, calibration_type=calibration_type, 
                    generate_props=generate_props, recent_n=0)
        elif layout == "na":
            initial_mapping = qiskit_wrapper.get_initial_mapping_na(
                    self.qasm, self.backend, calibration_type=calibration_type, 
                    generate_props=generate_props, recent_n=0)
        elif layout == "sabre":
            initial_mapping = qiskit_wrapper.get_initial_mapping_sabre(
                    self.qasm, self.backend, calibration_type=calibration_type, 
                    generate_props=generate_props, recent_n=0)
            
        print(initial_mapping)
        triq_wrapper.generate_initial_mapping_file(initial_mapping)

        hardware_name = ""
        if compilation_name == "triq+_lcd":
            hardware_name = conf.hardware_name + "_" + "real"
        elif compilation_name == "triq+_avg":
            hardware_name = conf.hardware_name + "_" + "avg"
        elif compilation_name == "triq+_mix":
            hardware_name = conf.hardware_name + "_" + "mix"
            
        tmp_start_time  = time.perf_counter()
        updated_qasm = laura_wrapper.run(updated_qasm, hardware_name, 2)
        tmp_end_time = time.perf_counter()

        final_mapping = laura_wrapper.get_mapping(updated_qasm, hardware_name, 2)

        compilation_time = tmp_end_time - tmp_start_time
        compilation_name = layout + "_" + compilation_name
        self.insert_to_result_detail(compilation_name, compilation_time, updated_qasm, initial_mapping, final_mapping)

        return updated_qasm
    
    def insert_to_result_detail(self, compilation_name, compilation_time, updated_qasm, initial_mapping = "", final_mapping = ""):
        now_time = datetime.now().strftime("%Y%m%d%H%M%S")
        
        sql = """
        INSERT INTO result_detail
        (header_id, circuit_name, compilation_name, compilation_time, 
        initial_mapping, final_mapping, created_datetime)
        VALUES (%s, %s, %s, %s, 
        %s, %s, %s);
        """

        str_initial_mapping = ', '.join(str(x) for x in initial_mapping)

        json_final_mapping = ""
        if final_mapping != "":
            json_final_mapping = json.dumps(final_mapping, default=str)

        print("Initial mapping:", str_initial_mapping, ", final mapping:", json_final_mapping)

        self.cursor.execute(sql, (self.header_id, self.circuit_name, compilation_name, compilation_time, \
                                  str_initial_mapping, json_final_mapping, now_time))
        detail_id = self.cursor.lastrowid

        sql = """
        INSERT INTO result_updated_qasm
        (detail_id, updated_qasm)
        VALUES (%s, %s);
        """

        self.cursor.execute(sql, (detail_id, updated_qasm))

        self.conn.commit()

        
    def send_qasm_to_real_backend(self):

        self.cursor.execute('SELECT id, qiskit_token, shots, runs FROM result_header WHERE job_id IS NULL;')
        results_1 = self.cursor.fetchall()

        print("Total send to backend :", len(results_1))

        for res_1 in results_1:
            header_id, qiskit_token, shots, runs = res_1

            self.set_backend(qiskit_token, shots=shots)

            self.cursor.execute('''SELECT d.id, q.updated_qasm, d.compilation_name 
FROM result_detail d
INNER JOIN result_header h ON d.header_id = h.id
INNER JOIN result_updated_qasm q ON d.id = q.detail_id 
WHERE h.job_id IS NULL AND d.header_id = %s  ''', (header_id,))
            results = self.cursor.fetchall()

            success = False
            list_circuits = []

            for res in results:
                detail_id, updated_qasm, compilation_name = res

                qc = QiskitCircuit(updated_qasm, skip_simulation=True)

                circuit = None
                if compilation_name == "triq_lcd" or compilation_name == "triq+_lcd":
                    circuit = qc.transpile_to_target_backend(self.backend, self.run_in_simulator)
                else:
                    # circuit = qc.get_native_gates_circuit(self.backend, self.run_in_simulator)
                    circuit = qc.transpile_to_target_backend(self.backend, self.run_in_simulator)
                    print("transpile to target backend")

                # circuit = qc.circuit

                # if conf.run_in_simulator:
                #     circuit = 

                for i in range(runs):
                    list_circuits.append(circuit)
                
            print("Total no of circuits :",len(list_circuits))

            while not success:
                try:

                    print("Sending to {} with batch id: {} ... ".format(conf.hardware_name, header_id))
                    job = self.sampler.run(list_circuits, skip_transpilation=True)
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
        if conf.program_type == "PolarRepeat":
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_3.value, generate_props=generate_props)
        elif conf.program_type == "Calibration" or conf.program_type == "CalibrationScale":
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_0.value, generate_props=generate_props)
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_3.value, generate_props=generate_props)
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_lcd.value, generate_props=generate_props)
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_avg.value, generate_props=generate_props)
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.qiskit_NA_mix.value, generate_props=generate_props)
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.mapomatic_lcd.value, generate_props=generate_props)
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.mapomatic_avg.value, generate_props=generate_props)
            self.apply_qiskit(compilation_name=qiskit_compilation_enum.mapomatic_mix.value, generate_props=generate_props)
            self.apply_triq(compilation_name="triq_lcd", layout="mapo")
            self.apply_triq(compilation_name="triq_lcd", layout="na")
            self.apply_triq(compilation_name="triq_lcd", layout="sabre")
            self.apply_triq(compilation_name="triq_avg", layout="mapo")
            self.apply_triq(compilation_name="triq_avg", layout="na")
            self.apply_triq(compilation_name="triq_avg", layout="sabre")
            self.apply_triq(compilation_name="triq_mix", layout="mapo")
            self.apply_triq(compilation_name="triq_mix", layout="na")
            self.apply_triq(compilation_name="triq_mix", layout="sabre")
            self.apply_laura(compilation_name="triq+_lcd", layout="mapo")
            self.apply_laura(compilation_name="triq+_lcd", layout="na")
            self.apply_laura(compilation_name="triq+_lcd", layout="sabre")
            self.apply_laura(compilation_name="triq+_avg", layout="mapo")
            self.apply_laura(compilation_name="triq+_avg", layout="na")
            self.apply_laura(compilation_name="triq+_avg", layout="sabre")
            self.apply_laura(compilation_name="triq+_mix", layout="mapo")
            self.apply_laura(compilation_name="triq+_mix", layout="na")
            self.apply_laura(compilation_name="triq+_mix", layout="sabre")
        elif conf.program_type == "Polar":
            self.apply_triq(compilation_name="triq_avg", layout="na")
        
        
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
    
    print(conf.token_list)

    for token in conf.token_list:
        conf.qiskit_token = token
        print(conf.qiskit_token)
        print("============================")

        for repetition in range(conf.repetition):
            print("Repetition:", repetition)
            print("============================")
            # List all files in the base folder with the .qasm extension
            qasm_files = glob.glob(os.path.expanduser(os.path.join(conf.base_folder, "*.qasm")))
            qasm_files = sorted(qasm_files)
            qasm_files.sort(key=num_sort) 

            if debug: start_time = time.perf_counter()

            # initial class QEM
            if debug: tmp_start_time  = time.perf_counter()
            # q = QEM(runs=conf.runs, fixed_initial_layout = False, run_in_simulator=False, user_id=10, token=token)
            # q = QEM(runs=conf.runs, fixed_initial_layout = False, run_in_simulator=True, user_id=96, token=token)
            
            q = QEM(runs=conf.runs, fixed_initial_layout = False, run_in_simulator=conf.run_in_simulator, user_id=conf.user_id, token=token)
            
            if debug: tmp_end_time = time.perf_counter()
            if debug: print("Time for initialization: {} seconds".format(tmp_end_time - tmp_start_time))


            # init header
            if debug: tmp_start_time  = time.perf_counter()
            q.init_result_header(token)
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
                q.qasm_original = qc.qasm_original

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


# # Banned
# # pencil-tweeds0t@icloud.com
# "445bcb87747eeb03961bacf306f6499f93f6f09bdf84b17c8a0e1f0d40466a94103d078a5539f74779b6d9b5ee4291c0f76263d341c070b23b55ac6ed32824ce",

#     # # Finished
#     # # pepe 4
#     # "055a93864810f2fc66e4de35b13027e8e591f0d019abb91b4895971fa16a991bef0ac573457c707c3d1070e5105d8f0cdd489f842cc06723d29a233c9f483e74",
#     # # untuk
#     # "e9dc3b4555eaceaf68dd163b187fe3f2354d0ae5032b50f2e0a01693118c83ccdd2f86f77bb37f0983244358d776defaa18614aafede58d1d8bfaea7b51c5a98",
#     # # okur
#     # "d6c68cd3c7151e9499fcaf54ff7982629e20ff25d38f32aea5b64db369985c82682f63b991dc6fc8424f4ac0349882d90a5399b03194d047b3b9b2eefb4613b3",
#     # # jose
#     # "94882007fb17bcb98ad4c7d13adb024491bd30e72e4be58628dd685ce2c90bcbefb8abc65094cf051de77c8b676b4aa936bba8ad4a0df0e573e3cc01308c5421",
#     # # pepe3
#     # "01501f074b8bc9910185d5563408e2838951163e8f55b90a338c94c58116b92a1cd88081474827667b9d907604f2dd27eaa8399a83fbb9505a24e25875819b23"
#     # # contact.07-glint@icloud.com
#     # "68fb7ac07545c0cc3b63bea6bae1a2e69fe11c4f84be2d4dc335abd5747c602701e9e687876adbf9bb61b11f25fa82ca2c932808fd3f128450cc13670d4822fe",
#     # # arrival_protein_0h@icloud.com
#     # "5c63e6d0dbc47a7c98741ea6b7de90afb0729f5e036dbea439cec03ee680d5dfa573bdb42920017edb942be678d54d4fb5d83d5e7296749f78dee5449a6f443b",
#     # # frisbee_among.0p@icloud.com
#     # "68d7a37e272a1a29ab8a3c767c63443fbf78fb82cfc34ac689d92f8f77f8fcdc4fd48dec46aa257a116f3194ba6532334f67d1b0a6f9feb53f1296804cb418b2",
#     # # button.06-galleys@icloud.com
#     # "ec5f9f43cea1eb948b374f22419e8e96307aa8ed59af234cd9133db2564dcc0f1c36eafc99f1565a9c5488d06296d0a291f1fff571fea5e8d01d0eddce7fa14f",
#     # # known
#     # "78b48009dcb68d57e164d1929cf4f0b248a827d18fc739107e127eef34d87bf67ad9b445744f7c7cd2cd1232ea8b92db11d7878be3542a131d17621586cf410c",
#     # # fasts
#     # "ad1527ea50d2b9fb3f122427c6423c55c036d6e3e6559c96a9d5bf4b2b813909a4aac65cbf23bc6ea8cc55da005be0dc85cfb72fa3cd5f57c3eec8a99ea3f9d8",
    
#     # # still working
#     # # cornice.poker_0g@icloud.com
#     # "bfbe3159e00973e14168671f8790ab7d2b85e8cb61160ee0b17225cf312df48e582cad577b02781ddca79d382e9e3aba3ad9c46c9c47d1b1b5ed27c8815cc2ca",
#     # # petrol
#     # "c0151c25a1bcb6e3f9274fb403cacf619f2508b2e70fcf350f1e44aba618f8d379f63f3554f58d2b6b7e04a63f20ba14895857e50b598c2c584c1b6519e6bc61",
#     # # mash
#     # "76eaa6f112f125eae669975b89d1620f8ea96cc9c28c650a2d9bed8e171d1ddf21aa685f46fa5d9377a86f7526ace1477c37f5fd5b0e8c0b0a25813a958958ce",
#     # # bylaw
#     # "30ea7c188f2b6531d2525875b7dab58f0d0091cb4c6e080472cdc76a96009aabbc3367ee1e1ac5f1aa2229941b08a7ef487066df163d47545c9524c4cad1c2ed",
#     # # puffs-undoing.02@icloud.com
#     # "266686280de68a1d68433c62d7e154391b905705041b43744a591c19528cefb7335fa425ea81855fd0ca88ae7950b726dd615c23b53bc14a99e579874aa1202f",
#     # # shanty
#     # "88fa7b6ee1ba1303c21d4a46cc6db9b44bfc1c4a86ff4d10476d5c6a28b7b2427e23c0cb7430ef103ac38310f74a71791a03aee26e2b9cdad266ef0a120d7c71",
#     # # pipe
#     # "f4376ab6435cab311bd27c6a403617cff71804667f537c72879fd68fc2e80ff8fc3c2c67509fa840f2ac39318604154319858e71434b35db9570568614c51d63",
#     # # lodging
#     # "73e5caa60d526c2122261d8b1d93d451f8e8add930a03d2ab6fe16702673ccfcdce9dd018820f5ca6bed692112c9a5d32e2d2f2b75d367d38dde3ed2a51e3c6b",
#     # # bionic
#     # "dc8be56745da5fe77438ee9a3cfc0b6fa87f219ec3e50db59788cf157ed43ed776a1986b569ad5ec57525aa5f299fdb17c90cb34d3a04be7ca4af1bfbbc85eca",
#     # # ales
#     # "7f531e9960905f9a3142ead5d8c004bf5dc39a59462dd70e5f623918bd539fecc0f7434dcbbf453aecad2cc6545595ce1f9edfbb029fc948e6e22c35ebf5e331",
#     # # anion
#     # "4bcab1e9db485961e3a583b52b04c7fd35f476751e1c0107406e7fa6b2b6ae899c65142ac5547842f02bd6c667b1ce92a790b107acf56c3e748d32dd63830a55",
#     # # lumbar
#     # "6955cf58b16e371d4b788ffd7602b6b1c134701f6a058a8ef02a71d6547b912f0602bc04f5e80a55ad67e4e64b29e0863b568760e7e7baa62159c975fe3df07b",
#     # # wool
#     # "af61c32894083127bf069fff6f0904e41f78c3a0e75cbf3619840b1b9377ac923a9a33893192dc830306e973e52a550d8c0c47fe59aa22177ba7eae45635f85a",
#     # # abalone
#     # "7df4633e575ac0094fd2a538a887002a745d2927c1c29d444c2360fc4572151001905be16ba478c41780212aa7c35593edd38f8b636bd595d8253b01dee89127",
#     # # 08.lessee.acts@icloud.com
#     # "887108cd60c926a48d330d614c31d496e5e191ef226b742a006869c5f56150c6fa8dc9e305301d6a7d85785319b484b1782bf98df106c4a899e69c7abafcdaa1",
#     # # salami
#     # "1fc316667164f5d54c56a31b43d7e9d12fa1d32c395727be69c77c733aee0f0468cc9178f357d6004fc636fd2ebb861dcf8af287493c818a70527dac50e06a25",
#     # # mammals
#     # "f45537aaef3c72fa31ce928a7eaad4b7f44930b48734f73e3276ff76273299b13b2dc8810fa53976c404641bb30926a6724dfe6b7afdfdbd68423389992cf344",
#     # # dopa
#     # "d312f1b28a7e5381dfe0754f5ff3ee055cc9cfab5b944250aaf58d5c822a513bd88b77cb19f7dfd7b7f955e5fbeaa266a552ba45ebbad0262965d35c59803734",
#     # # pepeucm1
#     # "924828a6b1671411b96c27b10123849b161154290707582dc60d0b900146ccc8fb93adda735a6d0805168b3007a8ad56f626f9f207881d5055c841a58e51a7d9",
#     # # pepedelft1
#     # "2298ebebdf52aa8ef9258a07154bc62d335af0126f2bed26502a43f32a206309618c34344db22713f54bad3dc1c7569d7d1e3a0075e0421160e83b8c50967b45",

#     # # # new
#     # # lintel-monody-0i@icloud.com
#     # "69d3c6f3f7241ff44a20ed8e4bcc445917394ebc7bc12442983aed7c9b52f55daa09e0bfa8572b1cd364f06b96b07686b0d39970eba8249c31c8b9ef62e281d7",
#     # # patter-slosh-0f@icloud.com
#     # "54a2dcecfe2b2efe441c23c9e1637ec2a9159b37d9938128c45c4a9a81ff1f6c3a947b5359b2bdf761158f6240d4b7369b162c108d900556c96fdd01847bcd55",
#     # # tappers_shuffle.0x@icloud.com
#     # "19362af21032b838765e5ec3bc3b0a4413501912b124ea3d6f88623561c3f5b2b3ec0c4038aa904f11b7fcc4e5ca38fee5f0b62763eda8bb0dbde14797666d96",
#     # # 05twos-ammonia@icloud.com
#     # "099f0f6194dd06b395ff22689cc939aff14bee22bea12ac9e56a73dbc525da653c281524b7216d2550cf963fdf5053198ef887a1dfb58839f2794c0e4eacc446",

#     # # # For Calibration Paper
#     # # savants.pinto-0w@icloud.com
#     # "3cb9b0aedf5f4ba7228a0b437b36ce26dec28bf600da8789bae8fd24b1db265031df69e1aafbbfe92dc775f0ead94991400830b512005818eea3b9b448b371bc",

#     # # # For Polar Paper
#     # predawn08.upriver@icloud.com
#     "0beaf281e1990a86c4d07af4ba25d03b155038d308179b84278054e30c17ed82c7db3b2672738733462a734b5c00bd79915f4655e6f4e22a7ddd423de778f956",

#     # # 02_peanuts_sagas@icloud.com
#     # "d2fc3f31fc7ed09ba8bb0b671697de32dcf709232be76c85de671ee92d80508237457aab2f98767d1566c07e506fb70be819d35e7b785600687a04c9c2e67646",
#     # # advert.weights.0u@icloud.com
#     # "ceaea54206809655f1db52eef61e2d13c087eee215dacc05b473c8c55ddddb490ca30a014fcfdb3a7725f97809f257a014f757e108873100ad59fa2196f5c11c",
#     # # 01_musky_lotions@icloud.com
#     # "7266698be44c4cadc223c834199903ae8d8131657642f1830e8134fcc187a8f121462b5605869f0891bac4a8fdd5ab28b29208332e33067c7b72c6c373b5cb32",
#     # # clump_zingy0t@icloud.com
#     # "7cdc02dde4d1ac701b6bf11e8ab30b48beb5880a010016847c7e671c850cbc523fa94d75a8c1ea37fde5ea56dce50279955a732d989bc36f486c276b1ac3429e",
#     # # ropes
#     # "b94c13374ae4f0b04fb2539b727e165ec695373f7fe198dd69c3b11f22a2aa380c8adca06390f201d2aa09247348aeae6f7664e0735698c9d8ad59880e58b8b8",
#     # # rudder
#     # "26f4ebc603700e1d56ac25c2a18c6ef196859f3a5547abe12ced49f3c16ef3c8391008db57e5bc77cd4ec3b3c62d26aeccf9983f311a279b714b5378ff4415cf",
#     # # mercury
#     # "243e229672da5f0a602a816c821b96ded412c2c17041da434aed04e8e225603e40093013bc1a3392566ef090a48b389c80c9c38cb3b7626046a7682f16414e84",
#     # # clashes
#     # "39a9660087b540bce0c4faebfa9fc5e32b7efd79b5c590a685ab4b20b4087a469dfb4e890f4308d62ebdb21be6cc421f27c5be553a42b43738aee05f02e13b48",
#     # # roosts
#     # "2b2c8db93b834b4ef95fc0da7d6fd70f345de16464f8037655f87c96373703e46d0b0f48f8f5dbea70c82fd06c3405d7810f2f9e14b9d4e92d6487f62dbe2269",
#     # # platoon
#     # "c6593b682f0a88379cdfdf83dee4399376885c04ca605d9471367d6313690772c338f4b1683af2ff9f713511f83cdf1357529882a5687fd67f7a37ec85c0e186",
#     # # bobs
#     # "eeaa19292016f1efc96f7dc11676fe47cbfc12a85869374e6b8ce3c225c5e8ef029d1fa912bb5def86a7b3c62ea55cf16b386d1ea0051fa26676efa2a7df1db2",
#     # # bygone
#     # "e62477a6e14315c89eb74f224f4aa6d44ae4fe4739bac484ab485ceedc97d4df9962b81286ead7ffe27a4b5443e8c03dd9ee516f09213a49fd3fa88976eba103",
#     # # chores
#     # "83fae468c72cb0e06e66c77c7520a24058a4ec4629b7e45236f7cf336237abc4cc5ce6ef9d2192ab652da68c7667143d09454687d76e42f9919f1e91ffb043a3",
#     # # frisbee
#     # "68d7a37e272a1a29ab8a3c767c63443fbf78fb82cfc34ac689d92f8f77f8fcdc4fd48dec46aa257a116f3194ba6532334f67d1b0a6f9feb53f1296804cb418b2"        
#     # # ucm
#     # "9b1a802766a56b6a51fdf73762fcf6f5c0bd33ef1f5afcef2157693593292c06b5bc92861d8758a585bd4f6d588b2155f5a45fb912f41610a1ad8bb2119f6521"        
# ]

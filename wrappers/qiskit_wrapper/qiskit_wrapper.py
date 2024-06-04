"""
file name: qiskit_wrapper.py
author: Handy, Laura, Fran
date: 14 September 2023

This module provides all the function necesary to run Qiskit 

Functions:

Example:
"""
from qiskit import QuantumCircuit, transpile, Aer
from qiskit.transpiler import CouplingMap
from qiskit_ibm_runtime import Sampler
from qiskit_aer.noise import NoiseModel
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from commons import calibration_type_enum, sql_query, normalize_counts, Config
from qiskit.providers.models import BackendProperties
import json
import requests
import copy
import mysql.connector
from .fake_ibm_perth import NewFakePerthRealAdjust, NewFakePerthRecent15, NewFakePerthRecent15Adjust, \
                        NewFakePerthMix, NewFakePerthMixAdjust, NewFakePerthAverage, NewFakePerthAverageAdjust
from .fake_ibm_brisbane import NewFakeBrisbaneRealAdjust, NewFakeBrisbaneRecent15, NewFakeBrisbaneRecent15Adjust, \
                        NewFakeBrisbaneMix, NewFakeBrisbaneMixAdjust, NewFakeBrisbaneAverage, NewFakeBrisbaneAverageAdjust, \
                        NewFakeBrisbaneRecentNAdjust
from .fake_ibm_sherbrooke import NewFakeSherbrookeRealAdjust, NewFakeSherbrookeRecent15, NewFakeSherbrookeRecent15Adjust, \
                        NewFakeSherbrookeMix, NewFakeSherbrookeMixAdjust, NewFakeSherbrookeAverage, NewFakeSherbrookeAverageAdjust, \
                        NewFakeSherbrookeRecentNAdjust
from .fake_ibm_brisbane import NewFakeBrisbaneRecent1, NewFakeBrisbaneRecent2, NewFakeBrisbaneRecent3, NewFakeBrisbaneRecent4, \
                        NewFakeBrisbaneRecent5, NewFakeBrisbaneRecent6, NewFakeBrisbaneRecent7, NewFakeBrisbaneRecent8, \
                        NewFakeBrisbaneRecent9, NewFakeBrisbaneRecent10, NewFakeBrisbaneRecent11, NewFakeBrisbaneRecent12, \
                        NewFakeBrisbaneRecent13, NewFakeBrisbaneRecent14, NewFakeBrisbaneRecent15, NewFakeBrisbaneRecent16, \
                        NewFakeBrisbaneRecent17, NewFakeBrisbaneRecent18, NewFakeBrisbaneRecent19, NewFakeBrisbaneRecent20, \
                        NewFakeBrisbaneRecent21, NewFakeBrisbaneRecent22, NewFakeBrisbaneRecent23, NewFakeBrisbaneRecent24, \
                        NewFakeBrisbaneRecent25, NewFakeBrisbaneRecent26, NewFakeBrisbaneRecent27, NewFakeBrisbaneRecent28, \
                        NewFakeBrisbaneRecent29, NewFakeBrisbaneRecent30, NewFakeBrisbaneRecent31, NewFakeBrisbaneRecent32, \
                        NewFakeBrisbaneRecent33, NewFakeBrisbaneRecent34, NewFakeBrisbaneRecent35, NewFakeBrisbaneRecent36, \
                        NewFakeBrisbaneRecent37, NewFakeBrisbaneRecent38, NewFakeBrisbaneRecent39, NewFakeBrisbaneRecent40, \
                        NewFakeBrisbaneRecent41, NewFakeBrisbaneRecent42, NewFakeBrisbaneRecent43, NewFakeBrisbaneRecent44, \
                        NewFakeBrisbaneRecent45 
import time
import numpy as np
import mapomatic as mm

conf = Config()

class QiskitCircuit:
    def __init__(self, qasm, name = "", skip_simulation = False, metadata = {}):
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

        self.qasm_original = qc.qasm()

        qc = transpile_to_basis_gate(qc)
        self.circuit = qc
        self.qasm = qc.qasm()
        self.circuit.name = name
        self.circuit.metadata = metadata
        self.gates = dict(qc.count_ops())
        self.total_gate = sum(qc.count_ops().values()) - self.gates["measure"]
        self.depth = qc.depth()

        if not skip_simulation:
            if conf.simulator_hardware != "ibmq_qasm_simulator":
                # backend_sim = self.service.get_backend(conf.simulator_hardware)
                # sampler = Sampler(backend_sim) 
                # job_sim = sampler.run(transpile(qc, backend_sim, basis_gates=["u3", "cx"]), shots=conf.shots)
                # result_sim = job_sim.result()  
                # self.correct_output = dict(result_sim.quasi_dists[0])  
                backend_sim = Aer.get_backend('qasm_simulator')
                job_sim = backend_sim.run(transpile(qc, backend_sim), shots=100000)
                result_sim = job_sim.result()  
                self.correct_output = normalize_counts(dict(result_sim.get_counts(qc)), shots=100000)
            else:
                backend_sim = Aer.get_backend('qasm_simulator')
                job_sim = backend_sim.run(transpile(qc, backend_sim), shots=100000)
                result_sim = job_sim.result()  
                # self.correct_output = normalize_counts(dict(result_sim.get_counts(qc)))
                self.correct_output = normalize_counts((result_sim.get_counts(qc)), shots=100000)
                # print(self.correct_output)

    def get_native_gates_circuit(self, backend, simulator = False):
        if simulator:
            return transpile(self.circuit.decompose(), backend, basis_gates=["u3", "cx"], optimization_level=0, layout_method="trivial")
        else:
            return transpile(self.circuit.decompose(), backend, basis_gates=backend.basis_gates, optimization_level=0, layout_method="trivial")
            # return transpile(self.circuit.decompose(), backend=backend, optimization_level=0)
        
    def transpile_to_target_backend(self, backend, simulator = False, backend_sim=None):
        if simulator:
            pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
            isa_circuits = pm.run(self.circuit)
            return isa_circuits

            # return transpile(self.circuit.decompose(), backend, basis_gates=["u3", "cx"], optimization_level=0, layout_method="trivial")
        else:
            return transpile(self.circuit, backend=backend, optimization_level=0, layout_method="trivial")
    
    def get_qasm(self):
        return self.qasm

def get_fake_backend(calibration_type, backend, recent_n, generate_props):
    tmp_backend = backend
    if calibration_type == calibration_type_enum.lcd_adjust.value:
        if generate_props: generate_new_props(backend, calibration_type)

        if backend.name == "ibm_brisbane":
            tmp_backend = NewFakeBrisbaneRealAdjust()
        elif backend.name == "ibm_sherbrooke":
            tmp_backend = NewFakeSherbrookeRealAdjust()
    elif calibration_type == calibration_type_enum.recent_15.value:
        if generate_props: generate_new_props(backend, calibration_type)

        if backend.name == "ibm_brisbane":
            tmp_backend = NewFakeBrisbaneRecent15()
        elif backend.name == "ibm_sherbrooke":
            tmp_backend = NewFakeSherbrookeRecent15()
    elif calibration_type == calibration_type_enum.recent_15_adjust.value:
        if generate_props: generate_new_props(backend, calibration_type)

        if backend.name == "ibm_brisbane":
            tmp_backend = NewFakeBrisbaneRecent15Adjust()
        elif backend.name == "ibm_sherbrooke":
            tmp_backend = NewFakeSherbrookeRecent15Adjust()
    elif calibration_type == calibration_type_enum.mix.value:
        if generate_props: generate_new_props(backend, calibration_type)

        if backend.name == "ibm_brisbane":
            tmp_backend = NewFakeBrisbaneMix()
        elif backend.name == "ibm_sherbrooke":
            tmp_backend = NewFakeSherbrookeMix()
    elif calibration_type == calibration_type_enum.mix_adjust.value:
        if generate_props: generate_new_props(backend, calibration_type)

        if backend.name == "ibm_brisbane":
            tmp_backend = NewFakeBrisbaneMixAdjust()
        elif backend.name == "ibm_sherbrooke":
            tmp_backend = NewFakeSherbrookeMixAdjust()
    elif calibration_type == calibration_type_enum.average.value:
        if generate_props: generate_new_props(backend, calibration_type)

        if backend.name == "ibm_brisbane":
            tmp_backend = NewFakeBrisbaneAverage()
        elif backend.name == "ibm_sherbrooke":
            tmp_backend = NewFakeSherbrookeAverage()
    elif calibration_type == calibration_type_enum.average_adjust.value:
        if generate_props: generate_new_props(backend, calibration_type)

        if backend.name == "ibm_brisbane":
            tmp_backend = NewFakeBrisbaneAverageAdjust()
        elif backend.name == "ibm_sherbrooke":
            tmp_backend = NewFakeSherbrookeAverageAdjust()
    elif calibration_type == calibration_type_enum.recent_n.value:
        if generate_props: generate_new_props(backend, calibration_type, recent_n)

        if   recent_n == 1 : tmp_backend = NewFakeBrisbaneRecent1()
        elif recent_n == 2 : tmp_backend = NewFakeBrisbaneRecent2()
        elif recent_n == 3 : tmp_backend = NewFakeBrisbaneRecent3()
        elif recent_n == 4 : tmp_backend = NewFakeBrisbaneRecent4()
        elif recent_n == 5 : tmp_backend = NewFakeBrisbaneRecent5()
        elif recent_n == 6 : tmp_backend = NewFakeBrisbaneRecent6()
        elif recent_n == 7 : tmp_backend = NewFakeBrisbaneRecent7()
        elif recent_n == 8 : tmp_backend = NewFakeBrisbaneRecent8()
        elif recent_n == 9 : tmp_backend = NewFakeBrisbaneRecent9()
        elif recent_n == 10 : tmp_backend = NewFakeBrisbaneRecent10()
        elif recent_n == 11 : tmp_backend = NewFakeBrisbaneRecent11()
        elif recent_n == 12 : tmp_backend = NewFakeBrisbaneRecent12()
        elif recent_n == 13 : tmp_backend = NewFakeBrisbaneRecent13()
        elif recent_n == 14 : tmp_backend = NewFakeBrisbaneRecent14()
        elif recent_n == 15 : tmp_backend = NewFakeBrisbaneRecent15()
        elif recent_n == 16 : tmp_backend = NewFakeBrisbaneRecent16()
        elif recent_n == 17 : tmp_backend = NewFakeBrisbaneRecent17()
        elif recent_n == 18 : tmp_backend = NewFakeBrisbaneRecent18()
        elif recent_n == 19 : tmp_backend = NewFakeBrisbaneRecent19()
        elif recent_n == 20 : tmp_backend = NewFakeBrisbaneRecent20()
        elif recent_n == 21 : tmp_backend = NewFakeBrisbaneRecent21()
        elif recent_n == 22 : tmp_backend = NewFakeBrisbaneRecent22()
        elif recent_n == 23 : tmp_backend = NewFakeBrisbaneRecent23()
        elif recent_n == 24 : tmp_backend = NewFakeBrisbaneRecent24()
        elif recent_n == 25 : tmp_backend = NewFakeBrisbaneRecent25()
        elif recent_n == 26 : tmp_backend = NewFakeBrisbaneRecent26()
        elif recent_n == 27 : tmp_backend = NewFakeBrisbaneRecent27()
        elif recent_n == 28 : tmp_backend = NewFakeBrisbaneRecent28()
        elif recent_n == 29 : tmp_backend = NewFakeBrisbaneRecent29()
        elif recent_n == 30 : tmp_backend = NewFakeBrisbaneRecent30()
        elif recent_n == 31 : tmp_backend = NewFakeBrisbaneRecent31()
        elif recent_n == 32 : tmp_backend = NewFakeBrisbaneRecent32()
        elif recent_n == 33 : tmp_backend = NewFakeBrisbaneRecent33()
        elif recent_n == 34 : tmp_backend = NewFakeBrisbaneRecent34()
        elif recent_n == 35 : tmp_backend = NewFakeBrisbaneRecent35()
        elif recent_n == 36 : tmp_backend = NewFakeBrisbaneRecent36()
        elif recent_n == 37 : tmp_backend = NewFakeBrisbaneRecent37()
        elif recent_n == 38 : tmp_backend = NewFakeBrisbaneRecent38()
        elif recent_n == 39 : tmp_backend = NewFakeBrisbaneRecent39()
        elif recent_n == 40 : tmp_backend = NewFakeBrisbaneRecent40()
        elif recent_n == 41 : tmp_backend = NewFakeBrisbaneRecent41()
        elif recent_n == 42 : tmp_backend = NewFakeBrisbaneRecent42()
        elif recent_n == 43 : tmp_backend = NewFakeBrisbaneRecent43()
        elif recent_n == 44 : tmp_backend = NewFakeBrisbaneRecent44()
        elif recent_n == 45 : tmp_backend = NewFakeBrisbaneRecent45()  

    elif calibration_type == calibration_type_enum.recent_n_adjust.value:
        if generate_props: generate_new_props(backend, calibration_type, recent_n)
        tmp_backend = NewFakeBrisbaneRecentNAdjust(n=recent_n)

    return tmp_backend

# Function to import and optimize a QASM circuit
def optimize_qasm(input_qasm, backend, optimization, enable_noise_adaptive = False, enable_mirage = False, enable_mapomatic = False,
                  calibration_type = calibration_type_enum.lcd, recent_n = None, initial_layout = None, generate_props = False):
    # Load the input QASM circuit
    circuit = QuantumCircuit.from_qasm_str(input_qasm)

    # Set the routing_method + layout_method
    routing_method = None
    layout_method = 'sabre'
    routing_method = 'sabre'
    basis_gates = None
    tmp_backend = backend
    if enable_noise_adaptive:
        layout_method = 'noise_adaptive'
        routing_method = 'sabre'
        tmp_backend = get_fake_backend(calibration_type, backend, recent_n, generate_props)
        # print(tmp_backend.name)
        
    elif enable_mirage:
        layout_method = 'sabre'
        routing_method = 'mirage'
        basis_gates=backend.basis_gates

    # print(layout_method, initial_layout)

    tmp_start_time  = time.perf_counter()
    initial_mapping = ""
    # Transpile and optimize the circuit
    if optimization == 0:
        transpiled_circuit = transpile(circuit, 
                                tmp_backend,
                                optimization_level=optimization
                                )
        initial_mapping = get_initial_layout_from_circuit(transpiled_circuit)

    elif enable_mapomatic:
        routing_method = 'sabre'
        tmp_backend = get_fake_backend(calibration_type, backend, recent_n, generate_props)

        initial_layout, new_circuit = get_best_mapomatic_layout(circuit, tmp_backend)
        
        transpiled_circuit = transpile(new_circuit, tmp_backend, initial_layout = initial_layout)
        initial_mapping = get_initial_layout_from_circuit(transpiled_circuit)

        print("masuk mapomatic: ", initial_layout)
    else:
        transpiled_circuit = transpile(circuit, 
                                tmp_backend,
                                optimization_level=optimization,
                                routing_method=routing_method,
                                layout_method=layout_method,
                                basis_gates=basis_gates,
                                initial_layout=initial_layout
                                )
        initial_mapping = get_initial_layout_from_circuit(transpiled_circuit)
        
    tmp_end_time = time.perf_counter()
    compilation_time = tmp_end_time - tmp_start_time

    # Convert the optimized circuit back to QASM
    optimized_qasm = transpiled_circuit.qasm()

    # print(optimized_qasm)

    return optimized_qasm, compilation_time, initial_mapping

def get_best_circuit_sabre(circ, backend):
    trans_qc_list = transpile([circ]*10, backend, optimization_level=3)
    best_cx_count = [circ.count_ops()['ecr'] for circ in trans_qc_list]
    best_idx = np.argmin(best_cx_count)
    best_qc = trans_qc_list[best_idx]
    best_small_qc = mm.deflate_circuit(best_qc)

    return best_small_qc

def get_best_mapomatic_layout(circ, backend):
    best_small_qc = get_best_circuit_sabre(circ, backend)
    layouts = mm.matching_layouts(best_small_qc, backend)
    
    return layouts[0], best_small_qc

def get_initial_layout_from_circuit(qc):
    virtual_bits = qc.layout.initial_layout.get_virtual_bits()
    initial_layout_dict = {}
    initial_layout = []
    
    for key, value in virtual_bits.items():
        if "'q'" in "{}".format(key):
            initial_layout_dict[key.index] = value 
    
    for i in range(len(initial_layout_dict.keys())):
        initial_layout.append(initial_layout_dict[i])
    
    return initial_layout

def get_initial_mapping_mapomatic(input_qasm, backend, calibration_type = calibration_type_enum.lcd, 
                                  recent_n = None, generate_props = False):
    
    circuit = QuantumCircuit.from_qasm_str(input_qasm)
    tmp_backend = get_fake_backend(calibration_type, backend, recent_n, generate_props)
    initial_layout, new_circuit = get_best_mapomatic_layout(circuit, tmp_backend)

    # print("Mapo initial_layout :", initial_layout)

    return initial_layout

def get_initial_mapping_sabre(input_qasm, backend, calibration_type = calibration_type_enum.lcd, 
                                  recent_n = None, generate_props = False):
    
    circuit = QuantumCircuit.from_qasm_str(input_qasm)
    sabre_qc = transpile(circuit, backend, optimization_level = 3)
    initial_layout = get_initial_layout_from_circuit(sabre_qc)

    return initial_layout

def get_initial_mapping_na(input_qasm, backend, calibration_type = calibration_type_enum.lcd, 
                                  recent_n = None, generate_props = False):
    
    circuit = QuantumCircuit.from_qasm_str(input_qasm)
    tmp_backend = get_fake_backend(calibration_type, backend, recent_n, generate_props)
    na_qc = transpile(circuit, tmp_backend, layout_method = "noise_adaptive", routing_method = "sabre", optimization_level = 3)
    initial_layout = get_initial_layout_from_circuit(na_qc)
    # print("get_initial_mapping_na :", initial_layout)

    return initial_layout

def transpile_to_basis_gate(circuit, backend = None ):
    
    # transpiled_circuit = transpile(circuit, optimization_level=0, basis_gates=backend.basis_gates)
    transpiled_circuit = transpile(circuit, optimization_level=0, basis_gates=["u3", "cx"])

    return transpiled_circuit

def _get_last_calibration_id(hw_name):
        
    sql = '''SELECT calibration_id, DATE_FORMAT(calibration_datetime, '%Y%m%d') FROM calibration_data.ibm i
INNER JOIN calibration_data.hardware h ON i.hw_name = h.hw_name
WHERE i.hw_name = %s ORDER BY calibration_datetime DESC LIMIT 0, 1;
'''
    parms = (hw_name, )
    
    results = sql_query(sql, parms)
    
    return results[0][0], results[0][1] 

def _get_native_gates_2q(hw_name):
        
    sql = '''SELECT 2q_native_gates FROM calibration_data.ibm i
INNER JOIN calibration_data.hardware h ON i.hw_name = h.hw_name
WHERE i.hw_name = %s ORDER BY calibration_datetime DESC LIMIT 0, 1;
'''
    parms = (hw_name, )
    
    results = sql_query(sql, parms)
    
    return results[0][0]

def _get_std_readout_error(prop_dict, hw_name):
    sql = ""
    parms = ()

    sql = """
    SELECT qubit, STDDEV(readout_error) FROM (
    SELECT DISTINCT qubit, readout_error, readout_error_date FROM calibration_data.ibm_qubit_spec q
    INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
    WHERE i.hw_name = %s 
    ) X GROUP BY qubit;
    """
    parms = (hw_name, )
    readout_results = sql_query(sql, parms)

    for res in readout_results:
        qubit, stddev_value = res

        for i in prop_dict["qubits"][qubit]:
            if (i["name"] == "readout_error"):
                val = float(stddev_value)
                i["value"] = i["value"] + val
                if i["value"] >= 1:
                    i["value"] = 1

def _get_readout_error_sql(hw_name, calibration_type, recent_n = None):
    sql = ""
    parms = ()

    if calibration_type == calibration_type_enum.lcd_adjust.value:
        last_cal_id, last_cal_date = _get_last_calibration_id(hw_name)

        sql = """
        SELECT qubit, readout_error
        FROM calibration_data.ibm_qubit_spec 
        WHERE calibration_id = %s;
        """

        parms = (last_cal_id, )

    elif calibration_type == calibration_type_enum.recent_n.value or calibration_type == calibration_type_enum.recent_n_adjust.value:
        sql = """
        SELECT qubit, AVG(readout_error) FROM (
        SELECT DISTINCT qubit, readout_error, readout_error_date FROM calibration_data.ibm_qubit_spec q
        INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
        WHERE i.hw_name = %s AND readout_error_date BETWEEN date_add(now(), INTERVAL %s DAY) AND now()
        ) X GROUP BY qubit;
        """

        parms = (hw_name, -1 * recent_n)

    elif calibration_type == calibration_type_enum.recent_15.value or calibration_type == calibration_type_enum.recent_15_adjust.value:
        sql = """
        SELECT qubit, AVG(readout_error) FROM (
        SELECT DISTINCT qubit, readout_error, readout_error_date FROM calibration_data.ibm_qubit_spec q
        INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
        WHERE i.hw_name = %s AND readout_error_date BETWEEN date_add(now(), INTERVAL %s DAY) AND now()
        ) X GROUP BY qubit;
        """

        parms = (hw_name, -15)

    elif calibration_type == calibration_type_enum.average.value or calibration_type == calibration_type_enum.average_adjust.value:
        sql = """
        SELECT qubit, AVG(readout_error) FROM (
        SELECT DISTINCT qubit, readout_error, readout_error_date FROM calibration_data.ibm_qubit_spec q
        INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
        WHERE i.hw_name = %s 
        ) X GROUP BY qubit;
        """

        parms = (hw_name, )

    elif calibration_type == calibration_type_enum.mix.value or calibration_type == calibration_type_enum.mix_adjust.value:
        last_cal_id, last_cal_date = _get_last_calibration_id(hw_name)

        sql = """
        SELECT q.qubit, 
        CASE WHEN DATE_FORMAT(q.readout_error_date , '%Y%m%d') = %s 
        THEN readout_error ELSE readout_error_avg END AS readout_error
        FROM calibration_data.ibm_qubit_spec q
        INNER JOIN (SELECT qubit, AVG(readout_error) AS readout_error_avg FROM (
        SELECT DISTINCT qubit, readout_error, readout_error_date FROM calibration_data.ibm_qubit_spec q
        INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
        WHERE i.hw_name = %s) X GROUP BY qubit) a ON q.qubit = a.qubit
        WHERE q.calibration_id = %s;
        """

        parms = (last_cal_date, hw_name, last_cal_id)

    return sql, parms

def _update_readout_error(prop_dict, hw_name, calibration_type, recent_n = None):

    sql, parms = _get_readout_error_sql(hw_name, calibration_type, recent_n)
    readout_results = sql_query(sql, parms)

    # update readout error
    for res in readout_results:
        qubit, avg_value = res

        for i in prop_dict["qubits"][qubit]:
            if (i["name"] == "readout_error"):
                val = float(avg_value)
                i["value"] = val

    if "adjust" in calibration_type:
        # print("Adding the deviation readout : ", calibration_type)
        _get_std_readout_error(prop_dict, hw_name)

def _get_std_two_qubit_error(prop_dict, hw_name, native_gates_2q):
    sql = ""
    parms = ()

    sql = '''
        SELECT qubit_control, qubit_target, STDDEV(''' + native_gates_2q + '''_error) FROM (
        SELECT DISTINCT qubit_control, qubit_target, ''' + native_gates_2q + '''_error, ''' + native_gates_2q + '''_date
        FROM calibration_data.ibm_two_qubit_gate_spec q
        WHERE q.hw_name = %s AND ''' + native_gates_2q + '''_error != 1
        ) X GROUP BY qubit_control, qubit_target;
        '''
    parms = (hw_name, )
    two_q_results = sql_query(sql, parms)

    for res in two_q_results:
        q_control, q_target, stddev_value = res

        qubits = [q_control, q_target]
        
        for i in prop_dict["gates"]:
            if(i["gate"] == native_gates_2q):
                if (i["qubits"] == qubits):
                    pars = i["parameters"]

                    for par in pars:
                        if (par["name"] == "gate_error"):
                            par["value"] = par["value"] + float(stddev_value) 

                            if par["value"] >= 1:
                                par["value"] = 1

def _get_two_qubit_error_sql(hw_name, calibration_type, native_gates_2q, recent_n = None):
    sql = ""
    parms = ()

    if calibration_type == calibration_type_enum.lcd_adjust.value:
        last_cal_id, last_cal_date = _get_last_calibration_id(hw_name)

        sql = '''
        SELECT qubit_control, qubit_target, ''' + native_gates_2q + '''_error
        FROM calibration_data.ibm_two_qubit_gate_spec 
        WHERE calibration_id = %s AND ''' + native_gates_2q + '''_error != 1;
        '''

        parms = (last_cal_id, )

    elif calibration_type == calibration_type_enum.recent_n.value or calibration_type == calibration_type_enum.recent_n_adjust.value:
        sql = '''
        SELECT qubit_control, qubit_target, AVG(''' + native_gates_2q + '''_error) FROM (
        SELECT DISTINCT qubit_control, qubit_target, ''' + native_gates_2q + '''_error, 
        ''' + native_gates_2q + '''_date 
        FROM calibration_data.ibm_two_qubit_gate_spec q
        WHERE q.hw_name = %s AND ''' + native_gates_2q + '''_error != 1
        AND ''' + native_gates_2q + '''_date BETWEEN date_add(now(), INTERVAL %s DAY) AND now()
        ) X GROUP BY qubit_control, qubit_target;
        '''

        parms = (hw_name, -1 * recent_n)

    elif calibration_type == calibration_type_enum.recent_15.value or calibration_type == calibration_type_enum.recent_15_adjust.value:
        sql = '''
        SELECT qubit_control, qubit_target, AVG(''' + native_gates_2q + '''_error) FROM (
        SELECT DISTINCT qubit_control, qubit_target, ''' + native_gates_2q + '''_error, 
        ''' + native_gates_2q + '''_date 
        FROM calibration_data.ibm_two_qubit_gate_spec q
        WHERE q.hw_name = %s AND ''' + native_gates_2q + '''_error != 1
        AND ''' + native_gates_2q + '''_date BETWEEN date_add(now(), INTERVAL %s DAY) AND now()
        ) X GROUP BY qubit_control, qubit_target;
        '''

        parms = (hw_name, -15)

    elif calibration_type == calibration_type_enum.average.value or calibration_type == calibration_type_enum.average_adjust.value:
        sql = '''
        SELECT qubit_control, qubit_target, AVG(''' + native_gates_2q + '''_error) FROM (
        SELECT DISTINCT qubit_control, qubit_target, ''' + native_gates_2q + '''_error, ''' + native_gates_2q + '''_date
        FROM calibration_data.ibm_two_qubit_gate_spec q
        WHERE q.hw_name = %s AND ''' + native_gates_2q + '''_error != 1
        ) X GROUP BY qubit_control, qubit_target;
        '''

        parms = (hw_name, )

    elif calibration_type == calibration_type_enum.mix.value or calibration_type == calibration_type_enum.mix_adjust.value:
        last_cal_id, last_cal_date = _get_last_calibration_id(hw_name)

        sql = '''SELECT q.qubit_control, q.qubit_target, 
        CASE WHEN DATE_FORMAT(q.''' + native_gates_2q + '''_date , '%Y%m%d') = %s 
        THEN ''' + native_gates_2q + '''_error ELSE ''' + native_gates_2q + '''_error_avg END AS ''' + native_gates_2q + '''_error
        FROM calibration_data.ibm_two_qubit_gate_spec q
        INNER JOIN (SELECT qubit_control, qubit_target, AVG(''' + native_gates_2q + '''_error) AS ''' + native_gates_2q + '''_error_avg FROM (
        SELECT DISTINCT qubit_control, qubit_target, ''' + native_gates_2q + '''_error, ''' + native_gates_2q + '''_date FROM calibration_data.ibm_two_qubit_gate_spec q
        INNER JOIN calibration_data.ibm i ON q.calibration_id = i.calibration_id 
        WHERE i.hw_name = %s) X GROUP BY qubit_control, qubit_target) a ON q.qubit_control = a.qubit_control AND q.qubit_target = a.qubit_target
        WHERE q.calibration_id = %s AND ''' + native_gates_2q + '''_error != 1;
        '''

        parms = (last_cal_date, hw_name, last_cal_id)

    return sql, parms

def _update_two_qubit_error(prop_dict, hw_name, calibration_type, recent_n = None):
    native_gates_2q = _get_native_gates_2q(hw_name)

    sql, parms = _get_two_qubit_error_sql(hw_name, calibration_type, native_gates_2q, recent_n)
    two_q_results = sql_query(sql, parms)

    for res in two_q_results:
        q_control, q_target, avg_value = res

        qubits = [q_control, q_target]
        
        for i in prop_dict["gates"]:
            if(i["gate"] == native_gates_2q):
                if (i["qubits"] == qubits):
                    pars = i["parameters"]

                    for par in pars:
                        if (par["name"] == "gate_error"):
                            par["value"] = float(avg_value) 

    if "adjust" in calibration_type:
        # print("Adding the deviation two qubit : ", calibration_type)
        _get_std_two_qubit_error(prop_dict, hw_name, native_gates_2q)

def _update_one_qubit_error(prop_dict, hw_name, calibration_type):
    
    sql = '''
    SELECT qubit, AVG(x_error), STDDEV(x_error), MAX(x_error), MIN(x_error) FROM (
    SELECT DISTINCT qubit, x_error, x_date 
    FROM calibration_data.ibm_one_qubit_gate_spec q
    WHERE q.hw_name = %s
    ) X GROUP BY qubit;
    '''

    parms = (hw_name, )

    one_q_results = sql_query(sql, parms)

    for res in one_q_results:
        qubit, avg_value, stddev_value, max_value, min_value = res

        qubits = [qubit]
        
        for i in prop_dict["gates"]:
            if(i["gate"] == "x"):
                if (i["qubits"] == qubits):
                    pars = i["parameters"]

                    for par in pars:
                        if (par["name"] == "gate_error"):
                            par["value"] = float(avg_value) + float(stddev_value)
                            if par["value"] >= 1:
                                par["value"] = 1

def generate_new_props(backend, calibration_type, recent_n = None):
    hw_name = backend.name
    properties = backend.properties()
    prop_dict = properties.to_dict()

    print(hw_name, calibration_type)
    
    _update_readout_error(prop_dict, hw_name, calibration_type, recent_n)
    _update_one_qubit_error(prop_dict, hw_name, calibration_type)
    _update_two_qubit_error(prop_dict, hw_name, calibration_type, recent_n)

    if calibration_type == "recent_n" or calibration_type == "recent_n_adjust":
        calibration_type = calibration_type.replace("_n", "_{}".format(recent_n))
        print(calibration_type)

    new_properties = BackendProperties.from_dict(prop_dict)
    new_prop_dict = new_properties.to_dict()
    new_prop_json = json.dumps(new_prop_dict, indent = 0, default=str) 
    new_prop_json = new_prop_json.replace("\n", "")

    file_path = "./wrappers/qiskit_wrapper/fake_backend/{}/props_{}_{}.json".format(hw_name, hw_name, calibration_type)
    f = open(file_path, "w+")
    f.write(new_prop_json)
    f.close()

def generate_noise_model_from_part_backend(backend, n_qubit, scale_error):
    real_noise_model = NoiseModel.from_backend(backend)
    real_noise_dict = real_noise_model.to_dict()
    new_noise_dict = {}
    new_noise_dict["errors"] = []
    
    for idx, i in enumerate(real_noise_dict["errors"]):
        q = i["gate_qubits"][0]
        if len(q) == 1 and q[0] < n_qubit:
            new_noise_dict["errors"].append(real_noise_dict["errors"][idx])
            
    
        if len(q) == 2 and q[0] < n_qubit and q[1] < n_qubit:
            new_noise_dict["errors"].append(real_noise_dict["errors"][idx])
            
    new_noise_model = NoiseModel.from_dict(new_noise_dict)
    
    return new_noise_model

def generate_brisbane_32_noisy_simulator(backend, scale_error):
    brisbane_map = backend.configuration().coupling_map
    brisbane_32_map = []
    for i in brisbane_map:
        if i[0] > 31:
            pass
        elif i[1] > 31:
            pass
        else:
            brisbane_32_map.append(i)

    properties = backend.properties()
    prop_dict = properties.to_dict()
    error_percentage = 1

    noise_brisbane_32_cx = generate_noise_model_from_part_backend(backend, 32, scale_error)
  
    sim_brisbane_32 = AerSimulator(noise_model=noise_brisbane_32_cx)
    sim_brisbane_32.set_options(
        noise_model=noise_brisbane_32_cx,
        basis_gates=backend.configuration().basis_gates,
        coupling_map=brisbane_32_map,
    )

    # return noise_paper
    return noise_brisbane_32_cx, sim_brisbane_32, brisbane_32_map


def send_rest_api_request(url, token):
    response = requests.request(
        "GET",
        url,
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(token)
        },
    )

    return response.json()

def get_qiskit_user_info(token):

    response_json = send_rest_api_request("https://api.quantum-computing.ibm.com/runtime/users/me", token)

    email = response_json["email"]
    plan = response_json["instances"][0]["plan"]

    return email, plan

def get_qiskit_usage_info(token):

    response_json = send_rest_api_request("https://api.quantum-computing.ibm.com/runtime/usage", token)

    print(response_json)

    instance = response_json["byInstance"][0]["instance"]
    quota = response_json["byInstance"][0]["quota"]
    usage = response_json["byInstance"][0]["usage"]
    pendingJobs = response_json["byInstance"][0]["pendingJobs"]
    maxPendingJobs = response_json["byInstance"][0]["maxPendingJobs"]

    return instance, quota, usage, pendingJobs, maxPendingJobs

#region REST API

def update_qiskit_usage_info(token):

    # print("Start inserting...")
    # print("==================")
    # print(token)

    instance, quota, usage, pendingJobs, maxPendingJobs = get_qiskit_usage_info(token)

    email, plan = get_qiskit_user_info(token)

    conn = mysql.connector.connect(**conf.mysql_config)
    cursor = conn.cursor()
    
    # check if the metric is already there, just update
    cursor.execute('SELECT token FROM qiskit_token WHERE token = %s', (token,))
    existing_row = cursor.fetchone()

    # insert to the table
    if not existing_row:
        cursor.execute("""INSERT INTO qiskit_token (token, str_instance, int_quota, int_usage, int_remaining, 
                       int_pending_jobs, int_max_pending_jobs, str_email, str_plan)
                        VALUES (%s, %s, %s, %s, %s, 
                       %s, %s, %s, %s)""",
        (token, instance, quota, usage, quota - usage, 
         pendingJobs, maxPendingJobs, email, plan))

        conn.commit()

        print(token, "has been registered to the database.")
    else:
        cursor.execute("""UPDATE qiskit_token SET str_instance = %s, int_quota = %s, int_usage = %s, 
                       int_remaining = %s, int_pending_jobs = %s, int_max_pending_jobs = %s, str_email = %s, str_plan = %s
                            WHERE token = %s""",
        (instance, quota, usage, 
         quota - usage, pendingJobs, maxPendingJobs, email, plan,
         token))

        conn.commit()
        print(token, " is updated.")
    
    cursor.close()
    conn.close()

def get_active_token(remaining, repetition, token_number):

    sql = """SELECT token, int_remaining, int_pending_jobs, int_max_pending_jobs FROM qiskit_token 
    WHERE int_remaining > 0 """

    if remaining > 200:
        sql = sql + """ and int_pending_jobs = 0 """

    sql = sql + """ AND int_remaining > {} AND (int_max_pending_jobs - int_pending_jobs) > {} ORDER BY int_remaining ASC LIMIT {}
    """.format(remaining, repetition, token_number)

    results = sql_query(sql, ())

    return results

#endregion

#region Noisy Simulator

def get_noisy_simulator(backend, error_percentage = 1, noiseless = False):
    _backend = copy.deepcopy(backend)
    _properties = _backend.properties()
    _prop_dict = _properties.to_dict()
    
    # update readout error
    for i in _prop_dict["qubits"]:
        for j in i:
            if (j["name"] in ("readout_error", "prob_meas0_prep1", "prob_meas1_prep0")):
                new_val = j["value"] * error_percentage
                if new_val > 1:
                    new_val = 1
                j["value"] = new_val
                # print(j["name"], j["value"])
            elif (j["name"] in ("T1", "T2")):
                new_val = j["value"] + (1000 - (100 * error_percentage))
                j["value"] = new_val

    # print(_prop_dict["qubits"][0])
    
    # update single qubit error
    for i in _prop_dict["gates"]:
        if(i["gate"] != "ecr"):
            pars = i["parameters"]
        
            for par in pars:
                if (par["name"] == "gate_error"):
                    new_val = par["value"] * error_percentage
                    if new_val > 1:
                        new_val = 1
                    par["value"] = new_val
                    # print(i["qubits"], par["value"])
    
    # Update Two Qubit Error
    for i in _prop_dict["gates"]:
        if(i["gate"] == "ecr"):
            pars = i["parameters"]
    
            for par in pars:
                if (par["name"] == "gate_error"):
                    new_val = par["value"] * error_percentage
                    if new_val > 1:
                        new_val = 1
                    par["value"] = new_val
                    # print(i["qubits"], par["value"])
    
    new_properties = BackendProperties.from_dict(_prop_dict)
    new_prop_dict = new_properties.to_dict()
    new_prop_json = json.dumps(new_prop_dict, indent = 0, default=str) 
    new_prop_json = new_prop_json.replace("\n", "")

    coupling_map = _backend.configuration().coupling_map
    # print(coupling_map)
    
    noise_model = NoiseModel.from_backend_properties(new_properties)
    
    if noiseless:
        sim_noisy = AerSimulator()
    else:
        sim_noisy = AerSimulator(configuration=_backend.configuration(), properties=new_properties,
                                noise_model=noise_model, 
                                # max_shot_size=100,method='statevector', max_memory_mb=10000 
                                )
        sim_noisy.set_options(
            noise_model=noise_model,
            # max_shot_size=100, max_memory_mb=10000, method='statevector'
            )
    
    return noise_model, sim_noisy, coupling_map

#endregion
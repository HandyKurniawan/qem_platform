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
from commons import calibration_type_enum, sql_query, normalize_counts, Config
from qiskit.providers.models import BackendProperties
import json
from .fake_ibm_perth import NewFakePerthRealAdjust, NewFakePerthRecent15, NewFakePerthRecent15Adjust, \
                        NewFakePerthMix, NewFakePerthMixAdjust, NewFakePerthAverage, NewFakePerthAverageAdjust
from .fake_ibm_brisbane import NewFakeBrisbaneRealAdjust, NewFakeBrisbaneRecent15, NewFakeBrisbaneRecent15Adjust, \
                        NewFakeBrisbaneMix, NewFakeBrisbaneMixAdjust, NewFakeBrisbaneAverage, NewFakeBrisbaneAverageAdjust

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

        self.circuit = qc
        self.qasm = qc.qasm()
        self.circuit.name = name
        self.circuit.metadata = metadata
        self.total_gate = sum(qc.count_ops().values())
        self.gates = dict(qc.count_ops())
        self.depth = qc.depth()

        if not skip_simulation:
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

        
        


    def get_native_gates_circuit(self, backend, simulator = False):
        if simulator:
            return transpile(self.circuit.decompose(), backend, basis_gates=["u3", "cx"], optimization_level=0, layout_method="trivial")
        else:
            return transpile(self.circuit.decompose(), backend, basis_gates=backend.basis_gates, optimization_level=0, layout_method="trivial")
    
    def get_qasm(self):
        return self.qasm
    

# Function to import and optimize a QASM circuit
def optimize_qasm(input_qasm, backend, optimization, enable_noise_adaptive = False, enable_mirage = False,
                  calibration_type = calibration_type_enum.lcd, initial_layout = None, generate_props = False):
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
        if calibration_type == calibration_type_enum.lcd_adjust.value:
            if generate_props: generate_new_props(backend, calibration_type)
            tmp_backend = NewFakeBrisbaneRealAdjust()
        elif calibration_type == calibration_type_enum.recent_15.value:
            if generate_props: generate_new_props(backend, calibration_type)
            tmp_backend = NewFakeBrisbaneRecent15()
        elif calibration_type == calibration_type_enum.recent_15_adjust.value:
            if generate_props: generate_new_props(backend, calibration_type)
            tmp_backend = NewFakeBrisbaneRecent15Adjust()
        elif calibration_type == calibration_type_enum.mix.value:
            if generate_props: generate_new_props(backend, calibration_type)
            tmp_backend = NewFakeBrisbaneMix()
        elif calibration_type == calibration_type_enum.mix_adjust.value:
            if generate_props: generate_new_props(backend, calibration_type)
            tmp_backend = NewFakeBrisbaneMixAdjust()
        elif calibration_type == calibration_type_enum.average.value:
            if generate_props: generate_new_props(backend, calibration_type)
            tmp_backend = NewFakeBrisbaneAverage()
        elif calibration_type == calibration_type_enum.average_adjust.value:
            if generate_props: generate_new_props(backend, calibration_type)
            tmp_backend = NewFakeBrisbaneAverageAdjust()

    elif enable_mirage:
        layout_method = 'sabre'
        routing_method = 'mirage'
        basis_gates=backend.basis_gates

    # print(layout_method, initial_layout)

    # Transpile and optimize the circuit
    transpiled_circuit = transpile(circuit, 
                                tmp_backend,
                                optimization_level=optimization,
                                routing_method=routing_method,
                                layout_method=layout_method,
                                basis_gates=basis_gates,
                                initial_layout=initial_layout
                                )


    # Convert the optimized circuit back to QASM
    optimized_qasm = transpiled_circuit.qasm()

    # print(optimized_qasm)

    return optimized_qasm

def transpile_to_basis_gate(input_qasm, backend, ):
    # Load the input QASM circuit
    circuit = QuantumCircuit.from_qasm_str(input_qasm)

    transpiled_circuit = transpile(circuit, optimization_level=0, basis_gates=backend.basis_gates)
    transpiled_qasm = transpiled_circuit.qasm()

    return transpiled_qasm

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

def _get_readout_error_sql(hw_name, calibration_type):
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

def _update_readout_error(prop_dict, hw_name, calibration_type):

    sql, parms = _get_readout_error_sql(hw_name, calibration_type)
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
        SELECT DISTINCT qubit_control, qubit_target, ''' + native_gates_2q + '''_error
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

def _get_two_qubit_error_sql(hw_name, calibration_type, native_gates_2q):
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
        SELECT DISTINCT qubit_control, qubit_target, ''' + native_gates_2q + '''_error
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

def _update_two_qubit_error(prop_dict, hw_name, calibration_type):
    native_gates_2q = _get_native_gates_2q(hw_name)

    sql, parms = _get_two_qubit_error_sql(hw_name, calibration_type, native_gates_2q)
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

def generate_new_props(backend, calibration_type):
    hw_name = backend.name
    properties = backend.properties()
    prop_dict = properties.to_dict()

    print(calibration_type)
    _update_readout_error(prop_dict, hw_name, calibration_type)
    _update_one_qubit_error(prop_dict, hw_name, calibration_type)
    _update_two_qubit_error(prop_dict, hw_name, calibration_type)

    new_properties = BackendProperties.from_dict(prop_dict)
    new_prop_dict = new_properties.to_dict()
    new_prop_json = json.dumps(new_prop_dict, indent = 0, default=str) 
    new_prop_json = new_prop_json.replace("\n", "")

    file_path = "./wrappers/qiskit_wrapper/fake_backend/{}/props_{}_{}.json".format(hw_name, hw_name, calibration_type)
    f = open(file_path, "w+")
    f.write(new_prop_json)
    f.close()


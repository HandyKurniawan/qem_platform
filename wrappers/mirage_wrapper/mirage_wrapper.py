"""
file name: Mirage_wrapper.py
author: Handy, Laura, Fran
date: 15 September 2023

This module provides all the function necesary to run Qiskit 

Functions:

Example:
"""
from qiskit import QuantumCircuit, transpile, Aer
# from qiskit.circuit.library import iSwapGate
# from qiskit.transpiler import CouplingMap
from mirror_gates.pass_managers import Mirage, QiskitLevel3
# from mirror_gates.utilities import SubsMetric
from qiskit_ibm_provider import IBMProvider
import time

def optimize_qasm(input_qasm, hardware_name, optimization):
    # Load the input QASM circuit
    circuit = QuantumCircuit.from_qasm_str(input_qasm)
    backend = None
    success = False
    while not success:
        try:

            
            if hardware_name != "ibmq_qasm_simulator":
                provider = IBMProvider(instance="ibm-q/open/main")
                backend = provider.get_backend(hardware_name)
            else:
                # backend = Aer.get_backend('qasm_simulator')
                provider = IBMProvider(instance="ibm-q/open/main")
                backend = provider.get_backend(hardware_name)

            success = True

        except Exception as e:
            print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

            for i in range(30, 0, -1):
                time.sleep(1)
                print(i)

    mirage = Mirage(
                backend.coupling_map,
                cx_basis=0,
                cost_function="depth",
                anneal_routing=True,
                layout_trials=5,
                fb_iters=16,
            )

    routing_method = 'mirage'
    layout_method = 'sabre_layout_v2'

    # Transpile and optimize the circuit
    transpiled_circuit = transpile(circuit, 
                                optimization_level=optimization,
                                routing_method=routing_method,
                                layout_method=layout_method
                                )
    
    transpiled_circuit = mirage.run(transpiled_circuit)
    
    transpiled_circuit.measure_all()

    # Convert the optimized circuit back to QASM
    optimized_qasm = transpiled_circuit.qasm()

    return optimized_qasm


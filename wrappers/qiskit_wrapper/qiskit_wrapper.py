"""
file name: qiskit_wrapper.py
author: Handy, Laura, Fran
date: 14 September 2023

This module provides all the function necesary to run Qiskit 

Functions:

Example:
"""
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap

# Function to import and optimize a QASM circuit
def optimize_qasm(input_qasm, backend, optimization, initial_layout = None, enable_sabre = False, enable_mirage = False):
    # Load the input QASM circuit
    circuit = QuantumCircuit.from_qasm_str(input_qasm)

    # Set the routing_method + layout_method
    routing_method = None
    layout_method = None
    if enable_sabre:
        routing_method = 'sabre'
        layout_method = 'sabre'
    elif enable_mirage:
        routing_method = 'mirage'
        layout_method = 'sabre'

    if initial_layout is not None:
        layout_method = 'trivial'

    # print(layout_method, initial_layout)

    # Transpile and optimize the circuit
    transpiled_circuit = transpile(circuit, 
                                backend,
                                initial_layout=initial_layout,
                                optimization_level=optimization,
                                routing_method=routing_method,
                                layout_method=layout_method,
                                basis_gates=backend.basis_gates
                                )



    # Convert the optimized circuit back to QASM
    optimized_qasm = transpiled_circuit.qasm()

    # print(optimized_qasm)

    return optimized_qasm

def transpile_to_basis_gate(input_qasm):
    # Load the input QASM circuit
    circuit = QuantumCircuit.from_qasm_str(input_qasm)

    transpiled_circuit = transpile(circuit, optimization_level=0, basis_gates=['cx', 'id', 'rz', 'sx', 'x'])
    transpiled_qasm = transpiled_circuit.qasm()

    return transpiled_qasm
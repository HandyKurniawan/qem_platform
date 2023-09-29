"""
file name: nassc_wrapper.py
author: Handy, Laura, Fran
date: 26 September 2023

This module provides all the function necesary to run NASSC

Functions:


Example:
"""

import argparse
import csv
import yaml
from importlib import import_module
from os import path

from benchmark import Result
from qiskit import IBMQ
from qiskit.transpiler import CouplingMap
from qiskit.providers.aer.noise import NoiseModel
from hamap import IBMQHardwareArchitecture

import warnings
warnings.filterwarnings('ignore')

def run(yamlfile):

    print(yamlfile)

    results = {}

    with open(yamlfile) as file:
        configuration = yaml.load(file, Loader=yaml.FullLoader)

    suite = import_module(configuration['suite'])
    passmanagers = []
    for pm_line in configuration['pass managers']:
        pm_module, pm_func = pm_line.split(':')
        passmanagers.append(getattr(import_module(pm_module), pm_func))

    hardware=configuration['hardware']
    provider_hub,provider_group,provider_project=configuration['provider'].split('.')

    IBMQ.load_account()
    provider = IBMQ.get_provider(hub=provider_hub, group = provider_group, project = provider_project)
    backend = provider.get_backend(hardware)
    coupling_map=CouplingMap(backend.configuration().coupling_map)
    noise_model = NoiseModel.from_backend(backend)
    basis_gates = noise_model.basis_gates
    shots=configuration['shots']

    fields = configuration['fields']
    times = configuration.get('times', 1)
    resultfile = path.join('results', '%s.csv' % path.basename(yamlfile).split('.')[0])

    print('suite:', configuration['suite'])
    print('hardware:',hardware, backend)
    print('times:', str(times))
    print('result file:', resultfile)

    with open(resultfile, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()

        circuit = suite.circuits()

        results["circuit"] = circuit

        print("====== NASSCSwap =============")
        result = Result(circuit, basis_gates=basis_gates, coupling_map=coupling_map, routing_method="NASSCSwap",shots=shots, noise_model=noise_model, backend=backend)
        result.run_pms(passmanagers, times=times)
        results["NASSCSwap"] = result.row(fields)

        # print("====== NASSCSwapConsiderNoise =============")
        # result = Result(circuit, basis_gates=basis_gates, coupling_map=coupling_map, routing_method="NASSCSwapConsiderNoise",shots=shots, noise_model=noise_model, hardware= IBMQHardwareArchitecture(hardware), backend=backend)
        # result.run_pms(passmanagers, times=times)
        # results["NASSCSwapConsiderNoise"] = result.row(fields)

    return results

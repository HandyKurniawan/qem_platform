# qEmQUIP Platform

qEmQuip is an open-source platform to implement error-aware compilation techniques on quantum computers.

## Table of contents

- [Setup](#setup)
- [Optimization levels](#optimization-levels)
  - [Qiskit](#qiskit)
  - [TriQ](#triq)
  - [Mirage](#mirage)
- [Included optimizations](#included-optimizations)
- [Acknowledgments](#acknowledgments)

## Setup

### Installation

``` terminal
code
```

### Example

``` terminal
code
```

## Optimization levels

### Qiskit (0.44.3)

| Level | Initial mapping| Routing                  | Optimizations                            | Error-aware            |
|--- |------------------ |------------------------- |----------------------------------------- |----------------------- |
| 0  | Trivial           | Stochastic               | None                                     | No                     |
| 1  | Sabre             | Sabre (5 swap trials)    | Adjacent gate collapsing                 | No                     |
| 2  | Sabre             | Sabre (10 swap trials)   | Gate cancellation                        | No                     |
| 3  | Sabre             | Sabre (20 swap trials)   | Gate cancellation and unitary synthesis  | No                     |

#### Initial mapping methods

To find the perfect initial mapping (layout):

- **[Trivial]((https://qiskit.org/documentation/stubs/qiskit.transpiler.passes.TrivialLayout.html)):** Map the *i-th* virtual qubit to the *i-th* physical qubit.
- **[VF2](https://qiskit.org/documentation/stubs/qiskit.transpiler.passes.VF2Layout.html):** Find a subgraph of the connectivity graph isomorphic to the circuit's qubit interaction graph.

Heuristic passes:

- **[Sabre]((https://qiskit.org/documentation/stubs/qiskit.transpiler.passes.SabreLayout.html)):** Use the Reverse Trasversal Technique several times to find a good initial mapping.
- **[Dense]((https://qiskit.org/documentation/stubs/qiskit.transpiler.passes.DenseLayout.html)):** Map the qubits to the most connected part of the chip and lower error rate (considering 2q and readout error rates).

#### Routing methods

- **[Stochastic]((https://qiskit.org/documentation/stubs/qiskit.transpiler.passes.StochasticSwap.html)):** Use a random algorithm to insert swap gates.
- **[SabreSwap]((https://qiskit.org/documentation/stubs/qiskit.transpiler.passes.SabreSwap.html)):** Divide the circuit into layers (resolved, front and extended) and inset swap gates consideing prevoius gates (to increase parallelization) and future gates (extended layer) (to reduce circuit depth). More information [here](https://arxiv.org/pdf/1809.02573.pdf).

### TriQ

TriQ uses a reliability matrix that stores the cost of performing a CNOT gate between any qubit pair. The following routing alternatives build this matrix in a different way. More information [here](https://doi.org/10.1145/3307650.3322273).

| Level  | Initial mapping                    | Routing                                         | Error aware                        |
|------- |----------------------------------- |------------------------------------------------ |----------------------------------- |
| 0      | Map communicating qubits together  |                                                 | Yes (initial mapping)              |
| 1      | Map communicating qubits together  | Insert swap gates with the lowest hop count     | Yes (initial mapping)              |
| 2      | Map communicating qubits together  | Insert swap gates with the highest reliability  | Yes (initial mapping and routing)  |

### Mirage

Mirage is based on [Sabre](https://dl.acm.org/doi/10.1145/3297858.3304023), but with an extra stage in the routing process to evaluate mirror gate insertion. More information [here](https://arxiv.org/abs/2308.03874).

| Initial mapping                    | Routing                                         | Error aware                        |
|----------------------------------- |------------------------------------------------ |----------------------------------- |
| Sabre                              | Sabre                                             | No                                 |

## Included optimizations

The table below presents the various optimizations and combinations available on the platform, identified by their respective labels.

| Name            | Compiling technique  | Optimization level  | Error aware                        |
|------------     |--------------------- |-------------------- |-----------------------             |
| ```Q_0```        | Qiskit               | 0                   | No                                 |
| ```Q_1```         | Qiskit               | 1                   | No              |
| ```Q_2```         | Qiskit               | 2                   | No                                 |
| ```Q_3```         | Qiskit               | 3                   | No                                 |
| ```Q_0_mirage```  | Qiskit + Mirage      | Qiskit: 0           | No                                 |
| ```Q_1_mirage```  | Qiskit + Mirage      | Qiskit: 1           | No              |
| ```Q_2_mirage```  | Qiskit + Mirage      | Qiskit: 2           | No                                 |
| ```Q_3_mirage```  | Qiskit + Mirage      | Qiskit: 3           | No                                 |
| ```T_0```      | TriQ               | 0                  | Yes (initial mapping)              |
| ```T_1```      | TriQ               | 1                  | Yes (initial mapping)              |
| ```T_2```      | TriQ               | 2                  | Yes (initial mapping and routing)  |
| ```T_0_Q_3```  | TriQ + Qiskit      | TriQ: 0 Qiskit: 3  | Yes (initial mapping)              |
| ```T_1_Q_3```  | TriQ + Qiskit      | TriQ: 1 Qiskit: 3  | Yes (initial mapping)              |
| ```T_2_Q_3```  | TriQ + Qiskit      | TriQ: 2 Qiskit: 3  | Yes (initial mapping and routing)  |

## Acknowledgments

This work is supported by the QuantERA grant EQUIP with the grant numbers PCI2022-133004 and PCI2022-132922, funded by Agencia Estatal de Investigación, Ministerio de Ciencia e Innovación, Gobierno de España, MCIN/AEI/10.13039/501100011033, and by the European Union “NextGenerationEU/PRTR”.

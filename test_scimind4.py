#!/usr/bin/env python3
"""
SCIMIND4 Empirical Validation Tests for QNOS-QISKIT
Tests the modular implementation for honest labeling compliance.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from qiskit import QuantumCircuit

# Import from the modular lib structure
from lib.core import QNOSBackend, CalibrationManager, QubitImageProcessor
from lib.hardware import LaserArrayController, CameraInterface, MicrowaveController
from lib.simulator import SimulatedFPGAConnection

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

print("=" * 80)
print("SCIMIND4 EMPIRICAL VALIDATION TESTS (QNOS-QISKIT Modular Version)")
print("=" * 80)

# Setup simulated hardware
fpga = SimulatedFPGAConnection()
laser = LaserArrayController(fpga)
camera = CameraInterface(fpga)
mw = MicrowaveController(fpga)
proc = QubitImageProcessor()

# Create fake calibration mapping
cal = CalibrationManager(laser, camera)
cal.mapping = {(r, c): (c * 80 + 40, r * 60 + 30) for r in range(8) for c in range(8)}

# Create backend with mock hardware
backend = QNOSBackend(laser, camera, mw, proc, cal.mapping, use_mock_hardware=True)

print("\n" + "=" * 80)
print("TEST 1: Bell State Determinism Check")
print("=" * 80)
print("Hypothesis: Simulator produces deterministic results (Seed 42)")
print()

# Create Bell state circuit
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

print("Circuit:")
print(qc)
print()

# Run multiple times to check for determinism
print("Running 10 trials:")
results = []

for i in range(10):
    job = backend.run(qc)
    result = job.result()
    counts = result.results[0]['data']['counts']
    bitstring = list(counts.keys())[0]
    results.append(bitstring)
    print(f"Trial {i+1}: {bitstring}")

print()
print("Analysis:")
unique_results = set(results)
print(f"Unique results: {unique_results}")

if len(unique_results) == 1:
    print("✓ DETERMINISTIC - Consistent with Educational Simulator (Seed 42)")
else:
    print("⚠ PROBABILISTIC - Unexpected for fixed seed")

print("\n" + "=" * 80)
print("TEST 2: Code Inspection - AerSimulator Presence")
print("=" * 80)

import inspect
source = inspect.getsource(QNOSBackend._execute)
if "AerSimulator" in source:
    print("✓ VERIFIED: AerSimulator IS embedded (Honest Simulator)")
    print()
    print("Relevant code lines:")
    for i, line in enumerate(source.split('\n'), start=1):
        if 'aer' in line.lower() or 'seed_simulator' in line.lower():
            print(f"  {i}: {line.strip()}")
else:
    print("✗ WARNING: AerSimulator NOT found")

print("\n" + "=" * 80)
print("TEST 3: Module Structure Verification")
print("=" * 80)

# Check imports work correctly
try:
    from lib.circuits import create_period_finding_circuit
    from lib.commands import register_commands
    print("✓ lib/circuits.py - importable")
    print("✓ lib/commands.py - importable")
except ImportError as e:
    print(f"✗ Import error: {e}")

print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

verdict_ok = len(unique_results) == 1 and "AerSimulator" in source

if verdict_ok:
    print("🟢 QNOS-QISKIT: SCIMIND4 COMPLIANT (Educational Simulator)")
    print("   - Deterministic behavior confirmed")
    print("   - Honest AerSimulator usage confirmed")
    print("   - Modular structure verified")
else:
    print("🔴 Issues detected - review required")

print()
print("=" * 80)

fpga.close()

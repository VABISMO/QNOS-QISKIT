# lib/circuits.py
import math
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import QFT, DraperQFTAdder, CDKMRippleCarryAdder, RGQFTMultiplier, PhaseEstimation, GroverOperator
from qiskit.circuit.library.standard_gates import RYGate, PhaseGate
from qiskit.circuit.library import UnitaryGate
from fractions import Fraction

def create_period_finding_circuit(n, a):
    """
    Creates the period finding circuit using proper unitary for modular exponentiation.
    @param {int} n - Modulus.
    @param {int} a - Base.
    @returns {QuantumCircuit} The circuit.
    """
    l = math.ceil(math.log2(n))
    t = 2 * l + 1  # Precision qubits
    anc_size = 2**l
    qr_count = QuantumRegister(t, 'count')
    qr_anc = QuantumRegister(l, 'anc')
    cr = ClassicalRegister(t)
    qc = QuantumCircuit(qr_count, qr_anc, cr)
    qc.h(qr_count)
    qc.x(qr_anc[0])  # |1> in ancilla
    for q in range(t):
        a_pow = pow(a, 2**q, n)
        U_matrix = np.zeros((anc_size, anc_size), dtype=complex)
        for x in range(anc_size):
            y = (a_pow * x) % n if x < n else x
            U_matrix[y, x] = 1.0
        u_gate = UnitaryGate(U_matrix, label=f"U^{{2^{{{q}}}}}")
        c_u = u_gate.control(1)
        qc.append(c_u, [qr_count[q]] + qr_anc[:])
    qc.append(QFT(t, inverse=True), qr_count)
    qc.measure(qr_count, cr)
    return qc

# Rest of the file remains unchanged
def create_math_circuit(op, num1, num2):
    num1_int = int(num1)
    num2_int = int(num2) if num2 is not None else 0
    is_negative1 = num1 < 0
    is_negative2 = num2 < 0 if num2 is not None else False
    abs_num1 = abs(num1_int)
    abs_num2 = abs(num2_int)
    max_val = max(abs_num1, abs_num2, 1)
    num_bits = math.ceil(math.log2(max_val)) + 2  # +2 for sign and overflow
    if op in ['add', 'sub']:
        if op == 'sub':
            num2 = -num2
        qr_a = QuantumRegister(num_bits, 'a')
        qr_b = QuantumRegister(num_bits, 'b')
        cr = ClassicalRegister(num_bits)
        qc = QuantumCircuit(qr_a, qr_b, cr)
        # Encode with sign
        if is_negative1:
            qc.x(qr_a[num_bits-1])  # Sign bit
        for i in range(num_bits-1):
            if (abs_num1 >> i) & 1:
                qc.x(qr_a[i])
        if is_negative2:
            qc.x(qr_b[num_bits-1])
        for i in range(num_bits-1):
            if (abs_num2 >> i) & 1:
                qc.x(qr_b[i])
        qc.append(DraperQFTAdder(num_bits), qr_a[:] + qr_b[:])
        qc.measure(qr_b, cr)
    elif op == 'mul':
        qr_a = QuantumRegister(num_bits, 'a')
        qr_b = QuantumRegister(num_bits, 'b')
        qr_res = QuantumRegister(2*num_bits - 1, 'res')  # Adjusted for overflow
        cr = ClassicalRegister(2*num_bits - 1)
        qc = QuantumCircuit(qr_a, qr_b, qr_res, cr)
        for i in range(num_bits-1):
            if (abs_num1 >> i) & 1:
                qc.x(qr_a[i])
            if (abs_num2 >> i) & 1:
                qc.x(qr_b[i])
        qc.append(RGQFTMultiplier(num_bits-1), qr_a[:-1] + qr_b[:-1] + qr_res[:])
        if is_negative1 ^ is_negative2:
            qc.x(qr_res[-1])  # Sign
        qc.measure(qr_res, cr)
    elif op == 'div':
        # Improved non-restoring divider
        qr_num = QuantumRegister(num_bits, 'num')  # Numerator
        qr_den = QuantumRegister(num_bits, 'den')  # Denominator
        qr_quot = QuantumRegister(num_bits, 'quot')
        cr = ClassicalRegister(num_bits)
        qc = QuantumCircuit(qr_num, qr_den, qr_quot, cr)
        for i in range(num_bits-1):
            if (abs_num1 >> i) & 1:
                qc.x(qr_num[i])
            if (abs_num2 >> i) & 1:
                qc.x(qr_den[i])
        qc.append(CDKMRippleCarryAdder(num_bits).inverse(), qr_num[:] + qr_den[:] + qr_quot[:])  # Approximate div as inverse add loop
        qc.measure(qr_quot, cr)
    elif op == 'log':
        # Quantum log via phase estimation on shift operator
        qr = QuantumRegister(num_bits)
        qr_anc = QuantumRegister(1)
        cr = ClassicalRegister(num_bits)
        qc = QuantumCircuit(qr, qr_anc, cr)
        angle = math.asin(math.sqrt(abs_num1 / (2**num_bits)))
        qc.ry(2 * angle, qr_anc)
        unitary = RYGate(2 * math.pi / num_bits).control()
        qc.append(PhaseEstimation(num_bits, unitary), qr[:] + qr_anc[:])
        qc.measure(qr, cr)
    elif op == 'sqrt':
        qr = QuantumRegister(num_bits)
        qr_anc = QuantumRegister(1)
        cr = ClassicalRegister(num_bits)
        qc = QuantumCircuit(qr, qr_anc, cr)
        angle = math.pi / 4  # For sqrt via rotation
        qc.ry(angle, qr_anc)
        unitary = RYGate(math.pi / 2).control()  # Approx sqrt
        qc.append(PhaseEstimation(num_bits, unitary), qr[:] + qr_anc[:])
        qc.measure(qr, cr)
    elif op == 'logbase':
        # log_b(a) = log(a)/log(b); compute separately and divide classically post-measure
        qc_loga = create_math_circuit('log', num1, None)
        qc_logb = create_math_circuit('log', num2, None)
        qc = qc_loga.compose(qc_logb)  # Combined; post-process
    elif op == 'polyN':
        # Grover for polynomial roots
        qr = QuantumRegister(num_bits)
        cr = ClassicalRegister(num_bits)
        qc = QuantumCircuit(qr, cr)
        oracle = QuantumCircuit(num_bits)  # Define poly eq as oracle
        oracle.cz(0, 1)  # Placeholder for root marking
        grover = GroverOperator(oracle)
        qc.h(qr)
        qc.append(grover, qr)
        qc.measure(qr, cr)
    return qc

def create_powmod_circuit(a, b, n):
    num_bits = math.ceil(math.log2(n)) + 1
    qr_base = QuantumRegister(num_bits, 'base')
    qr_exp = QuantumRegister(num_bits, 'exp')
    qr_res = QuantumRegister(num_bits, 'res')
    cr = ClassicalRegister(num_bits)
    qc = QuantumCircuit(qr_base, qr_exp, qr_res, cr)
    for i in range(num_bits):
        if (a >> i) & 1:
            qc.x(qr_base[i])
        if (b >> i) & 1:
            qc.x(qr_exp[i])
    qc.x(qr_res[0])  # 1
    for i in range(num_bits):
        qc.append(RGQFTMultiplier(num_bits).control(1), [qr_exp[i]] + qr_res[:] + qr_base[:])
        qc.append(RGQFTMultiplier(num_bits), qr_base[:] + qr_base[:])  # Square base
    qc.measure(qr_res, cr)
    return qc

def create_shor_circuit(n):
    a = 2
    l = math.ceil(math.log2(n))
    t = 2 * l + 1
    qr_count = QuantumRegister(t, 'count')
    qr_anc = QuantumRegister(l, 'anc')
    cr = ClassicalRegister(t)
    qc = QuantumCircuit(qr_count, qr_anc, cr)
    qc.h(qr_count)
    qc.x(qr_anc[0])
    for q in range(t):
        qc.append(create_powmod_circuit(a, 2**q, n), qr_anc[:] + qr_count[q:q+1])
    qc.append(QFT(t, inverse=True), qr_count)
    qc.measure(qr_count, cr)
    return qc, a

def create_modinv_circuit(a, n):
    num_bits = math.ceil(math.log2(n)) + 1
    qr_a = QuantumRegister(num_bits, 'a')
    qr_n = QuantumRegister(num_bits, 'n')
    qr_inv = QuantumRegister(num_bits, 'inv')
    cr = ClassicalRegister(num_bits)
    qc = QuantumCircuit(qr_a, qr_n, qr_inv, cr)
    for i in range(num_bits):
        if (a >> i) & 1:
            qc.x(qr_a[i])
        if (n >> i) & 1:
            qc.x(qr_n[i])
    qc.append(create_shor_circuit(n)[0].decompose(), qr_a[:] + qr_inv[:])  # Use extended Euclidean via Shor period
    qc.measure(qr_inv, cr)
    return qc
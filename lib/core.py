# lib/core.py
import serial
import time
import cv2
import numpy as np
import json
import logging
from typing import List, Tuple, Dict, Optional, Union
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.providers import BackendV2, Options, QubitProperties, JobStatus
from qiskit.providers import JobV1 as Job
from qiskit.result import Result, Counts
from qiskit.transpiler import Target, InstructionProperties, CouplingMap
from qiskit.circuit.library import QFTGate, RGQFTMultiplier, PhaseEstimation
from qiskit.circuit.library.standard_gates import HGate, RZGate, CPhaseGate, XGate, YGate, SGate, TGate
from qiskit.circuit.library.standard_gates import RYGate
from qiskit.circuit.measure import Measure
from qiskit.circuit import Parameter
from qiskit.exceptions import QiskitError
from click_help_colors import HelpColorsGroup
from math import pi, log2, ceil, log, sqrt, gcd
from fractions import Fraction
import code
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from pymongo import MongoClient
from io import StringIO
import readline
import atexit
import os
from qiskit_aer import AerSimulator
from lib.hardware import LaserArrayController, CameraInterface, MicrowaveController
from lib.simulator import SimulatedFPGAConnection
import pyfiglet
logger = logging.getLogger(__name__)

class CustomHelpGroup(HelpColorsGroup):
    # /**
    #  * Formats the help text with colored banner and table.
    #  * @param {object} ctx - Click context.
    #  * @param {object} formatter - Help formatter.
    #  */
    def format_help(self, ctx, formatter):
        blue_banner = "\033[1;34m" + pyfiglet.figlet_format("QNOS") + "\033[0m"
        formatter.write(blue_banner + '\n\n')
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        # Create rich table for commands
        table = Table(title="Available Commands")
        table.add_column("Command", style="bold cyan")
        table.add_column("Description", style="white")
        table.add_column("Options", style="yellow")
        table.add_column("Example", style="green")
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            help_text = cmd.help or ""
            desc = help_text.split('Example:')[0].strip() if 'Example:' in help_text else help_text or "No description"
            opts = ', '.join([opt.name for opt in cmd.params]) or "No options"
            example = "No example" if 'Example:' not in help_text else help_text.split('Example:')[1].strip()
            table.add_row(subcommand, desc, opts, example)
        # Capture table output correctly using StringIO with force_terminal for colors
        temp_file = StringIO()
        temp_console = Console(file=temp_file, force_terminal=True)
        temp_console.print(table)
        formatter.write(str(temp_file.getvalue()))

class MongoDBClient:
    # /**
    #  * MongoDB client for storing calibrations and results.
    #  * @param {str} uri - MongoDB connection URI.
    #  * @param {str} db_name - Database name.
    #  */
    def __init__(self, uri: str = "mongodb://localhost:27017/", db_name: str = "qnos_db"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.cal_collection = self.db["calibrations"]
        self.results_collection = self.db["results"]

    # /**
    #  * Saves qubit mapping to database.
    #  * @param {Dict} mapping - Qubit position mapping.
    #  * @param {str} file_id - Identifier for the mapping.
    #  */
    def save_mapping(self, mapping: Dict, file_id: str = 'default'):
        str_mapping = {f"{k[0]}_{k[1]}": list(v) for k, v in mapping.items()}  # Convert tuple value to list for JSON serializable
        self.cal_collection.update_one({"id": file_id}, {"$set": {"mapping": str_mapping}}, upsert=True)

    # /**
    #  * Loads qubit mapping from database.
    #  * @param {str} file_id - Identifier for the mapping.
    #  * @returns {Dict} Loaded mapping.
    #  */
    def load_mapping(self, file_id: str = 'default') -> Dict:
        doc = self.cal_collection.find_one({"id": file_id})
        if doc:
            mapping = {}
            for k, v in doc["mapping"].items():
                row, col = map(int, k.split('_'))
                mapping[(row, col)] = tuple(v)  # Convert list back to tuple
            return mapping
        raise FileNotFoundError("Mapping not found in DB.")

    # /**
    #  * Saves job result to database.
    #  * @param {Dict} result - Job result data.
    #  * @param {str} job_id - Job identifier.
    #  */
    def save_result(self, result: Dict, job_id: str):
        self.results_collection.insert_one({"job_id": job_id, "result": result})

    # /**
    #  * Closes the MongoDB connection.
    #  */
    def close(self):
        self.client.close()

class CalibrationManager:
    """
    Manages calibration of laser to camera mapping.
    Supports auto-calibration, validation, and multiple storage backends.
    """
    def __init__(self, laser_ctrl: LaserArrayController, camera):
        self.laser_ctrl = laser_ctrl
        self.camera = camera
        self.mapping: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.grid_size = (8, 8)  # Default, can be updated

    def perform_calibration(self, min_area: int = 100, thresh: float = 50, grid_size: Tuple[int, int] = (8, 8)):
        """
        Manual calibration by firing lasers and detecting positions.
        """
        self.grid_size = grid_size
        for row in range(grid_size[0]):
            for col in range(grid_size[1]):
                self.laser_ctrl.fire_laser(row, col)
                time.sleep(0.1)
                image = self.camera.capture_image()
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) > 2 else image
                _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                found = False
                for contour in contours:
                    if cv2.contourArea(contour) > min_area:
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            self.mapping[(row, col)] = (cx, cy)
                            found = True
                        break
                if not found:
                    logger.warning(f"No contour found for ({row}, {col})")
                time.sleep(0.1)
        expected = grid_size[0] * grid_size[1]
        if len(self.mapping) < expected:
            logger.warning(f"Incomplete calibration: {len(self.mapping)}/{expected} sites found.")
        logger.info("Calibration complete.")
        return self.mapping

    def auto_calibrate(self, grid_size: Tuple[int, int] = (8, 8), adaptive_thresh: bool = True) -> Dict:
        """
        Automatic calibration with adaptive thresholding.
        Returns detailed results including success rate.
        """
        self.grid_size = grid_size
        self.mapping = {}
        results = {'found': 0, 'missing': [], 'positions': {}}
        
        # Capture background first
        background = self.camera.capture_image()
        bg_mean = np.mean(background)
        
        for row in range(grid_size[0]):
            for col in range(grid_size[1]):
                self.laser_ctrl.fire_laser(row, col, duration_ms=100)
                time.sleep(0.15)
                
                image = self.camera.capture_image()
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) > 2 else image
                
                # Subtract background
                diff = cv2.absdiff(gray, background.astype(np.uint8) if len(background.shape) == 2 else cv2.cvtColor(background, cv2.COLOR_BGR2GRAY))
                
                # Adaptive or fixed threshold
                if adaptive_thresh:
                    thresh_val = max(30, np.mean(diff) + 2 * np.std(diff))
                else:
                    thresh_val = 50
                
                _, binary = cv2.threshold(diff, thresh_val, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                found = False
                for contour in sorted(contours, key=cv2.contourArea, reverse=True):
                    if cv2.contourArea(contour) > 50:
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            self.mapping[(row, col)] = (cx, cy)
                            results['positions'][(row, col)] = (cx, cy)
                            results['found'] += 1
                            found = True
                        break
                
                if not found:
                    results['missing'].append((row, col))
                    logger.warning(f"Auto-cal: No spot found for ({row}, {col})")
        
        expected = grid_size[0] * grid_size[1]
        results['total'] = expected
        results['success_rate'] = results['found'] / expected * 100
        
        logger.info(f"Auto-calibration complete: {results['found']}/{expected} ({results['success_rate']:.1f}%)")
        return results

    def validate_calibration(self) -> Dict:
        """Validate calibration quality and detect issues."""
        if not self.mapping:
            return {'valid': False, 'error': 'No calibration data'}
        
        issues = []
        expected = self.grid_size[0] * self.grid_size[1]
        
        # Check coverage
        coverage = len(self.mapping) / expected * 100
        if coverage < 100:
            issues.append(f"Missing {expected - len(self.mapping)} sites")
        
        # Check for duplicate positions (collision)
        positions = list(self.mapping.values())
        if len(positions) != len(set(positions)):
            issues.append("Duplicate pixel positions detected")
        
        # Check spacing uniformity
        if len(self.mapping) >= 4:
            xs = [p[0] for p in self.mapping.values()]
            ys = [p[1] for p in self.mapping.values()]
            x_spread = max(xs) - min(xs)
            y_spread = max(ys) - min(ys)
            if x_spread < 100 or y_spread < 100:
                issues.append("Positions clustered too tightly")
        
        return {
            'valid': len(issues) == 0,
            'coverage': coverage,
            'issues': issues,
            'site_count': len(self.mapping),
            'grid_size': self.grid_size
        }

    def save_mapping_file(self, path: str):
        """Save calibration to JSON file."""
        import json
        str_mapping = {f"{k[0]}_{k[1]}": list(v) for k, v in self.mapping.items()}
        data = {'grid_size': self.grid_size, 'mapping': str_mapping}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Calibration saved to {path}")

    def load_mapping_file(self, path: str):
        """Load calibration from JSON file."""
        import json
        with open(path, 'r') as f:
            data = json.load(f)
        self.grid_size = tuple(data.get('grid_size', (8, 8)))
        self.mapping = {}
        for k, v in data['mapping'].items():
            row, col = map(int, k.split('_'))
            self.mapping[(row, col)] = tuple(v)
        logger.info(f"Calibration loaded from {path}: {len(self.mapping)} sites")

    def save_mapping(self, db: MongoDBClient, file_id: str = 'default'):
        """Save mapping to MongoDB."""
        db.save_mapping(self.mapping, file_id)

    def load_mapping(self, db: MongoDBClient, file_id: str = 'default'):
        """Load mapping from MongoDB."""
        self.mapping = db.load_mapping(file_id)

class QubitImageProcessor:
    # /**
    #  * Processes images to determine qubit states.
    #  * @param {float} c_max - Maximum contrast value.
    #  * @param {float} thresh - Threshold for state determination.
    #  */
    def __init__(self, c_max: float = 0.2, thresh: float = 50):
        self.c_max = c_max
        self.thresh = thresh

    # /**
    #  * Captures background image.
    #  * @param {CameraInterface} camera - Camera instance.
    #  * @returns {np.ndarray} Background image.
    #  */
    def capture_background(self, camera: CameraInterface) -> np.ndarray:
        camera.fpga.send_command("CAPTURE_DARK")
        return camera.fpga.receive_image(camera.image_size)

    # /**
    #  * Processes image to extract qubit states.
    #  * @param {np.ndarray} image - Input image.
    #  * @param {Dict} mapping - Qubit mapping.
    #  * @param {int} roi_radius - ROI radius.
    #  * @param {int} num_qubits - Number of qubits.
    #  * @param {Optional[np.ndarray]} background_image - Background image.
    #  * @returns {List[int]} Qubit states.
    #  */
    def process_image(self, image: np.ndarray, mapping: Dict, roi_radius: int = 15, num_qubits: int = 64, background_image: Optional[np.ndarray] = None) -> List[int]:
        if background_image is None:
            background_image = np.zeros_like(image)
        background = np.mean(background_image)
        states = [0] * num_qubits
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) > 2 else image
        for i in range(num_qubits):
            row, col = divmod(i, 8)
            pos = (row, col)
            if pos not in mapping:
                logger.warning(f"Missing mapping for {pos}; assuming |0>")
                states[i] = 0
                continue
            cx, cy = mapping[pos]
            mask = np.zeros_like(gray)
            cv2.circle(mask, (cx, cy), roi_radius, 255, -1)
            masked = cv2.bitwise_and(gray, gray, mask=mask)
            masked = masked.astype(np.float32)  # To avoid overflow
            masked_mean = cv2.mean(masked, mask=mask)[0]
            i_off = masked_mean
            contrast = (i_off - background) / max(self.thresh - background, 1e-6) if (self.thresh - background) != 0 else 0
            p1 = min(max(contrast / self.c_max, 0.0), 1.0)
            state = 1 if p1 > 0.5 else 0
            states[i] = state
        return states

    # /**
    #  * Reconstructs period from states.
    #  * @param {List[int]} states - Qubit states.
    #  * @param {int} N - Modulus.
    #  * @returns {int} Reconstructed period.
    #  */
    def reconstruct_period(self, states: List[int], N: int) -> int:
        phase = sum(s * (0.5 ** (i + 1)) for i, s in enumerate(states))
        frac = Fraction(phase).limit_denominator(N)
        period = frac.denominator if frac.denominator < N else 1
        if period == 1:
            logger.warning("Trivial period; may need more qubits or runs.")
        return period

    # /**
    #  * Interprets result as integer.
    #  * @param {List[int]} states - Qubit states.
    #  * @param {int} num_bits - Number of bits.
    #  * @returns {int} Interpreted value.
    #  */
    def interpret_result(self, states: List[int], num_bits: int) -> int:
        bitstring = ''.join(str(s) for s in (s if s is not None else 0 for s in states[:num_bits][::-1]))
        return int(bitstring, 2) if bitstring else 0

class HardwareJob(Job):
    # /**
    #  * Custom job for hardware backend.
    #  * @param {BackendV2} backend - Backend instance.
    #  * @param {str} job_id - Job ID.
    #  * @param {QuantumCircuit} circuit - Circuit to run.
    #  * @param {Dict} options - Run options.
    #  */
    def __init__(self, backend, job_id, circuit, options):
        super().__init__(backend, job_id)
        self._circuit = circuit
        self._options = options
        self._result = None
        self._status = JobStatus.QUEUED  # Initial status

    # /**
    #  * Gets job result.
    #  * @returns {Result} Job result.
    #  */
    def result(self):
        if self._result is None:
            self._result = self._backend._execute(self._circuit, self._options)
            self._status = JobStatus.DONE
        return self._result

    # /**
    #  * Gets job status.
    #  * @returns {JobStatus} Current status.
    #  */
    def status(self) -> JobStatus:
        return self._status

    # /**
    #  * Submits the job.
    #  */
    def submit(self):
        self._status = JobStatus.RUNNING
        pass

    # /**
    #  * Cancels the job.
    #  * @returns {bool} Cancellation success.
    #  */
    def cancel(self):
        return False

class QNOSBackend(BackendV2):
    # /**
    #  * Visualizer backend for QNOS.
    #  * @param {LaserArrayController} laser_ctrl - Laser controller.
    #  * @param {CameraInterface} camera - Camera interface.
    #  * @param {MicrowaveController} mw_ctrl - Microwave controller.
    #  * @param {QubitImageProcessor} processor - Image processor.
    #  * @param {Dict} mapping - Qubit mapping.
    #  * @param {bool} use_mock_hardware - Use simulator if true.
    #  */
    def __init__(self, laser_ctrl, camera, mw_ctrl, processor, mapping, use_mock_hardware=False):
        super().__init__()
        self.laser_ctrl = laser_ctrl
        self.camera = camera
        self.mw_ctrl = mw_ctrl
        self.processor = processor
        self.mapping = mapping
        self.use_mock_hardware = use_mock_hardware
        self._max_qubits = 64
        qubit_props = [QubitProperties(t1=1.0, t2=0.1, frequency=5e9) for _ in range(self._max_qubits)]
        coupling_map = CouplingMap([(i, j) for i in range(self._max_qubits) for j in range(self._max_qubits) if i != j])
        self._target = Target(dt=1e-9, qubit_properties=qubit_props, num_qubits=self._max_qubits, coupling_map=coupling_map)
        self._build_target()
        # Add decomposition for swap to ensure BasisTranslator can ensure
        from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
        from qiskit.circuit.library import SwapGate
        from qiskit.circuit import QuantumCircuit
        swap_qc = QuantumCircuit(2)
        swap_qc.h(1)
        swap_qc.cp(pi, 0, 1)
        swap_qc.h(1)
        swap_qc.h(0)
        swap_qc.cp(pi, 1, 0)
        swap_qc.h(0)
        swap_qc.h(1)
        swap_qc.cp(pi, 0, 1)
        swap_qc.h(1)
        SessionEquivalenceLibrary.add_equivalence(SwapGate(), swap_qc)
        self._options = self._default_options()

    # /**
    #  * Builds the target with instructions.
    #  */
    def _build_target(self):
        h_gate = HGate()
        rz_gate = RZGate(Parameter('theta'))
        ry_gate = RYGate(Parameter('theta'))
        cp_gate = CPhaseGate(Parameter('theta'))
        x_gate = XGate()
        y_gate = YGate()
        s_gate = SGate()
        t_gate = TGate()
        single_qubit_props = {(i,): InstructionProperties(duration=100e-9, error=0.001) for i in range(self._max_qubits)}
        self._target.add_instruction(h_gate, single_qubit_props)
        self._target.add_instruction(rz_gate, single_qubit_props)
        self._target.add_instruction(ry_gate, single_qubit_props)
        self._target.add_instruction(x_gate, single_qubit_props)
        self._target.add_instruction(y_gate, single_qubit_props)
        self._target.add_instruction(s_gate, single_qubit_props)
        self._target.add_instruction(t_gate, single_qubit_props)
        cp_props = {(i, j): InstructionProperties(duration=50e-9, error=0.005) for i in range(self._max_qubits) for j in range(self._max_qubits) if i != j}
        self._target.add_instruction(cp_gate, cp_props)
        # Add measure instruction to the target
        measure_props = {(i,): InstructionProperties(duration=1000e-9, error=0.01) for i in range(self._max_qubits)}
        self._target.add_instruction(Measure(), measure_props)

    @property
    def target(self):
        return self._target

    @property
    def max_circuits(self):
        return 1  # Single circuit per run

    @classmethod
    def _default_options(cls):
        return Options()

    # /**
    #  * Runs the circuit.
    #  * @param {Union[QuantumCircuit, List[QuantumCircuit]]} run_input - Circuit(s) to run.
    #  * @param {Dict} options - Run options.
    #  * @returns {HardwareJob} Job instance.
    #  */
    def run(self, run_input, **options):
        if isinstance(run_input, QuantumCircuit):
            circuits = [run_input]
        else:
            circuits = run_input
        job_id = "qnos_job"  # Placeholder
        return HardwareJob(self, job_id, circuits[0] if len(circuits) == 1 else circuits, options)

    # /**
    #  * Executes the circuit on backend.
    #  * @param {QuantumCircuit} circuit - Circuit to execute.
    #  * @param {Dict} options - Execution options.
    #  * @returns {Result} Execution result.
    #  */
    def _execute(self, circuit: QuantumCircuit, options: Dict) -> Result:
        # 1. Transpilación
        transpiled = transpile(circuit, self)
        
        # 2. Executing Core Logic (ALWAYS via Qiskit Aer)
        # In this educational version, we explicitly state that quantum results come from classical simulation.
        bitstring_sim = ''
        try:
            from qiskit_aer import AerSimulator
            # Use deterministic seed for reproducible classroom demonstrations
            aer_sim = AerSimulator(seed_simulator=42) 
            # Transpile for Aer to ensure compatibility
            aer_transpiled = transpile(circuit, aer_sim) 
            aer_result = aer_sim.run(aer_transpiled, shots=1).result()
            counts = aer_result.get_counts()
            bitstring_sim = next(iter(counts))
            logger.info(f"Simulation Result (Ground Truth): {bitstring_sim}")
        except Exception as e:
            logger.error(f"Aer Simulation failed: {e}")
            bitstring_sim = '0' * transpiled.num_clbits

        # 3. Identificar Qubits Activos
        active_qubits = set()
        for instr in transpiled.data:
            if instr.operation.name not in ['measure', 'barrier']:
                for q in instr.qubits:
                    physical = transpiled.find_bit(q).index
                    active_qubits.add(physical)

        # 4. Inicialización Hardware (Reset)
        for p in active_qubits:
            row, col = divmod(p, 8)
            self.laser_ctrl.fire_laser(row, col, 100)
        
        if self.use_mock_hardware:
            self.laser_ctrl.fpga.active_lasers.clear()

        # 5. Ejecución de Puertas
        for instr in transpiled.data:
            op = instr.operation
            name = op.name
            
            if name == 'barrier': continue
            
            qs = [transpiled.find_bit(q).index for q in instr.qubits]
            
            try:
                if name == 'h':
                    self.mw_ctrl.apply_pulse(qs[0], 2.5, 1.0, 100, 0.0)
                elif name == 'rz':
                    self.mw_ctrl.apply_pulse(qs[0], 2.5, 0.5, 50, float(op.params[0]))
                elif name == 'ry':
                    self.mw_ctrl.apply_pulse(qs[0], 2.5, 0.5, 50, float(op.params[0]))
                elif name == 'cp':
                    self.mw_ctrl.apply_pulse((qs[0], qs[1]), 2.5, 0.5, 50, float(op.params[0]))
                elif name == 'x':
                    self.mw_ctrl.apply_pulse(qs[0], 2.5, 1.0, 50, pi)
                elif name == 'measure':
                    pass 
            except Exception as e:
                logger.error(f"Error ejecutando puerta {name}: {e}")
            
            time.sleep(0 if self.use_mock_hardware else 0.01)

        # 6. Mapeo de Medición
        measured_map = [None] * transpiled.num_clbits
        for instr in transpiled.data:
            if instr.operation.name == 'measure':
                phys_q = transpiled.find_bit(instr.qubits[0]).index
                cl_idx = transpiled.find_bit(instr.clbits[0]).index
                measured_map[cl_idx] = phys_q

        # 7. Visualization on Hardware (Displaying the Result)
        background_image = self.processor.capture_background(self.camera)
        
        # We purposely drive the lasers to MATCH the simulated result to visualize it.
        # This is strictly for educational display.
        for cl_idx, phys_q in enumerate(measured_map):
            if phys_q is not None:
                # Reverse index for bitstring mapping
                str_idx = (transpiled.num_clbits - 1) - cl_idx
                if str_idx < len(bitstring_sim) and bitstring_sim[str_idx] == '1':
                    row, col = divmod(phys_q, 8)
                    # Fire laser to "light up" the qubit |1> state on the grid
                    self.laser_ctrl.fire_laser(row, col, 100)

        # 8. Captura y Procesamiento
        image = self.camera.capture_image()
        states = self.processor.process_image(image, self.mapping, num_qubits=self._max_qubits, background_image=background_image)

        # 9. Construcción del Bitstring (CORREGIDO A PRUEBA DE BOMBAS)
        bitstring_chars = []
        
        # Iteramos en reverso para cumplir con el orden de bits de Qiskit
        for cl_idx in range(transpiled.num_clbits - 1, -1, -1):
            phys_q = measured_map[cl_idx]
            
            bit_val = '0' # Valor por defecto seguro
            
            if phys_q is not None and phys_q < len(states):
                raw_val = states[phys_q]
                if raw_val is not None:
                    bit_val = str(int(raw_val))
            
            bitstring_chars.append(bit_val)
        
        # Ahora es matemáticamente imposible que haya un None aquí
        final_bitstring = "".join(bitstring_chars)

        return Result(
            backend_name='qnos_hardware',
            backend_version='1.0',
            qobj_id='qnos',
            job_id='qnos',
            success=True,
            results=[{
                'shots': 1,
                'success': True,
                'data': {'counts': {final_bitstring: 1}},
                'header': {'name': circuit.name}
            }]
        ) 

class QNOSConsole(code.InteractiveConsole):
    # /**
    #  * Interactive console for QNOS.
    #  * @param {Dict} locals - Local variables for console.
    #  */
    def __init__(self, locals=None):
        super().__init__(locals)
        self.prompt = "QNOS> "
        readline.set_completer(self.system_completer)
        readline.parse_and_bind("tab: complete")
        # History support with increased length
        readline.set_history_length(1000)
        history_file = os.path.expanduser('~/.qnos_history')
        if os.path.exists(history_file):
            readline.read_history_file(history_file)
        atexit.register(readline.write_history_file, history_file)

    # /**
    #  * Completer for system commands.
    #  * @param {str} text - Text to complete.
    #  * @param {int} state - Completion state.
    #  * @returns {str} Completion option.
    #  */
    def system_completer(self, text, state):
        options = [i for i in self.locals if i.startswith(text) and not i.startswith('_')]
        try:
            return options[state]
        except IndexError:
            return None

    # /**
    #  * Pushes line to console.
    #  * @param {str} line - Input line.
    #  * @returns {bool} Push result.
    #  */
    def push(self, line):
        # Custom push for system-specific commands if needed
        return super().push(line) 
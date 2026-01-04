# lib/commands.py
import logging
import time
import serial
from rich.console import Console
from rich.table import Table
import pyfiglet
import click
from lib.core import MongoDBClient, CalibrationManager, QubitImageProcessor, HardwareJob, QNOSBackend, CustomHelpGroup, QNOSConsole
from lib.hardware import FPGAConnection, LaserArrayController, CameraInterface, MicrowaveController
from lib.simulator import SimulatedFPGAConnection
from lib.circuits import create_period_finding_circuit, create_math_circuit, create_powmod_circuit, create_shor_circuit, create_modinv_circuit
from fractions import Fraction


logger = logging.getLogger(__name__)
rich_console = Console()

def register_commands(cli):
    @cli.command()
    def banner():
        """Displays the QNOS banner."""
        rich_console.print(pyfiglet.figlet_format("QNOS"), style="bold blue")

    @cli.command()
    @click.option('--port', default='/dev/ttyUSB0', help='FPGA port.')
    @click.option('--mock-hardware', is_flag=True, help='Run with mock hardware (software FPGA) instead of real physical interface.')
    def calibrate(port, mock_hardware):
        """Calibrate laser-to-camera mapping.
        example: python qnos.py calibrate --port /dev/ttyUSB0 --mock-hardware
        """
        try:
            fpga = SimulatedFPGAConnection() if mock_hardware else FPGAConnection(port)
            laser = LaserArrayController(fpga)
            camera = CameraInterface(fpga)
            cal = CalibrationManager(laser, camera)
            cal.perform_calibration()
            db = MongoDBClient()
            cal.save_mapping(db)
            db.close()
            # Show calibration results in table
            table = Table(title="Calibration Mapping")
            table.add_column("Laser Position", style="cyan")
            table.add_column("Camera Pixel (x, y)", style="green")
            for pos, pixel in cal.mapping.items():
                table.add_row(str(pos), str(pixel))
            rich_console.print(table)
        except serial.SerialException as e:
            rich_console.print(f"[bold red]Error connecting to FPGA: {e}. Please check if the port exists and you have permissions.[/bold red]")
        except Exception as e:
            rich_console.print(f"[bold red]Unexpected error: {e}. Check logs for details.[/bold red]")
        finally:
            if 'fpga' in locals():
                fpga.close()

    @cli.command()
    @click.option('--port', default='/dev/ttyUSB0', help='FPGA port.')
    @click.argument('n', type=int)
    @click.option('--a', default=2, help='Base for period finding (default 2).')
    @click.option('--mock-hardware', is_flag=True, help='Run with mock hardware (software FPGA) instead of real physical interface.')
    def period(port, n, a, mock_hardware):
        """Calculate period for integer N using QFT (Simulated).
        Example: python qnos.py period 15 --a 7 --port /dev/ttyUSB0 --mock-hardware
        """
        try:
            fpga = SimulatedFPGAConnection() if mock_hardware else FPGAConnection(port)
            laser = LaserArrayController(fpga)
            camera = CameraInterface(fpga)
            mw = MicrowaveController(fpga)
            proc = QubitImageProcessor()
            cal = CalibrationManager(laser, camera)
            db = MongoDBClient()
            try:
                cal.load_mapping(db)
            except FileNotFoundError:
                if mock_hardware:
                    cal.mapping = {(r, c): (c * 80 + 40, r * 60 + 30) for r in range(8) for c in range(8)}
                else:
                    raise ValueError("Incomplete mapping; run calibration.")
            db.close()
            if len(cal.mapping) < 64:
                raise ValueError("Incomplete mapping; run calibration.")
            backend = QNOSBackend(laser, camera, mw, proc, cal.mapping, use_mock_hardware=mock_hardware)
            qc = create_period_finding_circuit(n, a)
            job = backend.run(qc)
            result = job.result()
            counts = result.results[0]['data']['counts']
            bitstring = max(counts, key=counts.get) if counts else '0' * qc.num_clbits
            measured = int(bitstring, 2)
            phase = measured / 2**qc.num_clbits
            fraction = Fraction(phase).limit_denominator(n-1)
            period = fraction.denominator
            if pow(a, period, n) != 1:
                period = 1
            # Use rich table for results
            table = Table(title="Period Finding Results")
            table.add_column("Base (a)", style="cyan")
            table.add_column("Modulus (n)", style="cyan")
            table.add_column("Period", style="green")
            table.add_row(str(a), str(n), str(period))
            rich_console.print(table)
        except serial.SerialException as e:
            rich_console.print(f"[bold red]Error connecting to FPGA: {e}. Please check if the port exists and you have permissions.[/bold red]")
        except ValueError as e:
            rich_console.print(f"[bold red]{e}. Run calibration first.[/bold red]")
        except Exception as e:
            rich_console.print(f"[bold red]Unexpected error: {e}. Check logs for details.[/bold red]")
        finally:
            if 'fpga' in locals():
                fpga.close()

    @cli.command()
    @click.option('--port', default='/dev/ttyUSB0', help='FPGA port.')
    @click.argument('op', type=str)
    @click.argument('num1', type=float)
    @click.argument('num2', type=float, required=False)
    @click.option('--mock-hardware', is_flag=True, help='Run with mock hardware (software FPGA) instead of real physical interface.')
    def math(port, op, num1, num2, mock_hardware):
        """Perform math operation (add, sub, mul, div, log, sqrt, logbase, polyN) (Simulated).
        Example: python qnos.py math add 5 3 --port /dev/ttyUSB0 --mock-hardware
        """
        try:
            fpga = SimulatedFPGAConnection() if mock_hardware else FPGAConnection(port)
            laser = LaserArrayController(fpga)
            camera = CameraInterface(fpga)
            mw = MicrowaveController(fpga)
            proc = QubitImageProcessor()
            cal = CalibrationManager(laser, camera)
            db = MongoDBClient()
            try:
                cal.load_mapping(db)
            except FileNotFoundError:
                if mock_hardware:
                    cal.mapping = {(r, c): (c * 80 + 40, r * 60 + 30) for r in range(8) for c in range(8)}
                else:
                    raise ValueError("Incomplete mapping; run calibration.")
            db.close()
            if len(cal.mapping) < 64:
                raise ValueError("Incomplete mapping; run calibration.")
            backend = QNOSBackend(laser, camera, mw, proc, cal.mapping, use_mock_hardware=mock_hardware)
            qc = create_math_circuit(op, num1, num2)
            job = backend.run(qc.decompose())
            result = job.result()
            counts = result.results[0]['data']['counts']
            bitstring = max(counts, key=counts.get) if counts else '0' * qc.num_clbits
            output_val = int(bitstring, 2)
            # Post-process for specific ops
            if op in ['log', 'sqrt']:
                output_val = (output_val / 2**qc.num_clbits) * num1
            elif op == 'logbase':
                loga = output_val >> (qc.num_clbits // 2)
                logb = output_val & ((1 << (qc.num_clbits // 2)) - 1)
                output_val = loga / logb if logb != 0 else 0
            # Use rich table for results
            table = Table(title="Math Calculation Results")
            table.add_column("Operation", style="cyan")
            table.add_column("Num1", style="cyan")
            table.add_column("Num2", style="cyan")
            table.add_column("Result", style="green")
            table.add_row(op, str(num1), str(num2) if num2 is not None else '-', str(output_val))
            rich_console.print(table)
        except serial.SerialException as e:
            rich_console.print(f"[bold red]Error connecting to FPGA: {e}. Please check if the port exists and you have permissions.[/bold red]")
        except ValueError as e:
            rich_console.print(f"[bold red]{e}. Run calibration first.[/bold red]")
        except Exception as e:
            rich_console.print(f"[bold red]Unexpected error: {e}. Check logs for details.[/bold red]")
        finally:
            if 'fpga' in locals():
                fpga.close()

    @cli.command()
    @click.option('--port', default='/dev/ttyUSB0', help='FPGA port.')
    @click.argument('a', type=int)
    @click.argument('b', type=int)
    @click.argument('n', type=int)
    @click.option('--mock-hardware', is_flag=True, help='Run with mock hardware (software FPGA) instead of real physical interface.')
    def powmod(port, a, b, n, mock_hardware):
        """Compute a^b mod n (Simulated).
        Example: python qnos.py powmod 2 3 5 --port /dev/ttyUSB0 --mock-hardware
        """
        try:
            fpga = SimulatedFPGAConnection() if mock_hardware else FPGAConnection(port)
            laser = LaserArrayController(fpga)
            camera = CameraInterface(fpga)
            mw = MicrowaveController(fpga)
            proc = QubitImageProcessor()
            cal = CalibrationManager(laser, camera)
            db = MongoDBClient()
            try:
                cal.load_mapping(db)
            except FileNotFoundError:
                if mock_hardware:
                    cal.mapping = {(r, c): (c * 80 + 40, r * 60 + 30) for r in range(8) for c in range(8)}
                else:
                    raise ValueError("Incomplete mapping; run calibration.")
            db.close()
            if len(cal.mapping) < 64:
                raise ValueError("Incomplete mapping; run calibration.")
            backend = QNOSBackend(laser, camera, mw, proc, cal.mapping, use_mock_hardware=mock_hardware)
            qc = create_powmod_circuit(a, b, n)
            job = backend.run(qc.decompose())
            result = job.result()
            counts = result.results[0]['data']['counts']
            bitstring = max(counts, key=counts.get) if counts else '0' * qc.num_clbits
            output_val = int(bitstring, 2) % n
            table = Table(title="PowMod Results")
            table.add_column("a", style="cyan")
            table.add_column("b", style="cyan")
            table.add_column("n", style="cyan")
            table.add_column("Result", style="green")
            table.add_row(str(a), str(b), str(n), str(output_val))
            rich_console.print(table)
        except serial.SerialException as e:
            rich_console.print(f"[bold red]Error connecting to FPGA: {e}. Please check if the port exists and you have permissions.[/bold red]")
        except ValueError as e:
            rich_console.print(f"[bold red]{e}. Run calibration first.[/bold red]")
        except Exception as e:
            rich_console.print(f"[bold red]Unexpected error: {e}. Check logs for details.[/bold red]")
        finally:
            if 'fpga' in locals():
                fpga.close()

    @cli.command()
    @click.option('--port', default='/dev/ttyUSB0', help='FPGA port.')
    @click.argument('n', type=int)
    @click.option('--mock-hardware', is_flag=True, help='Run with mock hardware (software FPGA) instead of real physical interface.')
    def shor(port, n, mock_hardware):
        """Factor integer N using Shor's algorithm (Simulated).
        Example: python qnos.py shor 15 --port /dev/ttyUSB0 --mock-hardware
        """
        try:
            fpga = SimulatedFPGAConnection() if mock_hardware else FPGAConnection(port)
            laser = LaserArrayController(fpga)
            camera = CameraInterface(fpga)
            mw = MicrowaveController(fpga)
            proc = QubitImageProcessor()
            cal = CalibrationManager(laser, camera)
            db = MongoDBClient()
            try:
                cal.load_mapping(db)
            except FileNotFoundError:
                if mock_hardware:
                    cal.mapping = {(r, c): (c * 80 + 40, r * 60 + 30) for r in range(8) for c in range(8)}
                else:
                    raise ValueError("Incomplete mapping; run calibration.")
            db.close()
            if len(cal.mapping) < 64:
                raise ValueError("Incomplete mapping; run calibration.")
            backend = QNOSBackend(laser, camera, mw, proc, cal.mapping, use_mock_hardware=mock_hardware)
            qc, a = create_shor_circuit(n)
            job = backend.run(qc.decompose())
            result = job.result()
            counts = result.results[0]['data']['counts']
            bitstring = max(counts, key=counts.get) if counts else '0' * qc.num_clbits
            measured = int(bitstring, 2)
            phase = measured / 2**qc.num_clbits
            fraction = Fraction(phase).limit_denominator(n-1)
            period = fraction.denominator
            factor1 = gcd(pow(a, period // 2) - 1, n)
            factor2 = gcd(pow(a, period // 2) + 1, n)
            if factor1 == 1 or factor1 == n:
                factor1, factor2 = 1, n  # Trivial
            table = Table(title="Shor Factoring Results")
            table.add_column("N", style="cyan")
            table.add_column("Factor1", style="green")
            table.add_column("Factor2", style="green")
            table.add_row(str(n), str(factor1), str(factor2))
            rich_console.print(table)
        except serial.SerialException as e:
            rich_console.print(f"[bold red]Error connecting to FPGA: {e}. Please check if the port exists and you have permissions.[/bold red]")
        except ValueError as e:
            rich_console.print(f"[bold red]{e}. Run calibration first.[/bold red]")
        except Exception as e:
            rich_console.print(f"[bold red]Unexpected error: {e}. Check logs for details.[/bold red]")
        finally:
            if 'fpga' in locals():
                fpga.close()

    @cli.command()
    @click.option('--port', default='/dev/ttyUSB0', help='FPGA port.')
    @click.argument('a', type=int)
    @click.argument('n', type=int)
    @click.option('--mock-hardware', is_flag=True, help='Run with mock hardware (software FPGA) instead of real physical interface.')
    def modinv(port, a, n, mock_hardware):
        """Compute modular inverse of a mod n (Simulated).
        Example: python qnos.py modinv 3 7 --port /dev/ttyUSB0 --mock-hardware
        """
        try:
            logger.warning("This operation is a placeholder / illustrative quantum circuit.")
            fpga = SimulatedFPGAConnection() if mock_hardware else FPGAConnection(port)
            laser = LaserArrayController(fpga)
            camera = CameraInterface(fpga)
            mw = MicrowaveController(fpga)
            proc = QubitImageProcessor()
            cal = CalibrationManager(laser, camera)
            db = MongoDBClient()
            try:
                cal.load_mapping(db)
            except FileNotFoundError:
                if mock_hardware:
                    cal.mapping = {(r, c): (c * 80 + 40, r * 60 + 30) for r in range(8) for c in range(8)}
                else:
                    raise ValueError("Incomplete mapping; run calibration.")
            db.close()
            if len(cal.mapping) < 64:
                raise ValueError("Incomplete mapping; run calibration.")
            backend = QNOSBackend(laser, camera, mw, proc, cal.mapping, use_mock_hardware=mock_hardware)
            qc = create_modinv_circuit(a, n)
            job = backend.run(qc.decompose())
            result = job.result()
            counts = result.results[0]['data']['counts']
            bitstring = max(counts, key=counts.get) if counts else '0' * qc.num_clbits
            output_val = int(bitstring, 2) % n  # Simplified
            table = Table(title="Modular Inverse Results")
            table.add_column("a", style="cyan")
            table.add_column("n", style="cyan")
            table.add_column("Inverse", style="green")
            table.add_row(str(a), str(n), str(output_val))
            rich_console.print(table)
        except serial.SerialException as e:
            rich_console.print(f"[bold red]Error connecting to FPGA: {e}. Please check if the port exists and you have permissions.[/bold red]")
        except ValueError as e:
            rich_console.print(f"[bold red]{e}. Run calibration first.[/bold red]")
        except Exception as e:
            rich_console.print(f"[bold red]Unexpected error: {e}. Check logs for details.[/bold red]")
        finally:
            if 'fpga' in locals():
                fpga.close()

    @cli.command()
    def qnos_console():
        """Start the QNOS interactive console with banner and tab completion for system functions."""
        rich_console.print(pyfiglet.figlet_format("QNOS"), style="bold blue")
        locals_dict = globals()  # Add system classes/functions to locals for easy access
        locals_dict.update({
            'MongoDBClient': MongoDBClient,
            'FPGAConnection': FPGAConnection,
            'SimulatedFPGAConnection': SimulatedFPGAConnection,
            'LaserArrayController': LaserArrayController,
            'CameraInterface': CameraInterface,
            'MicrowaveController': MicrowaveController,
            'CalibrationManager': CalibrationManager,
            'QubitImageProcessor': QubitImageProcessor,
            'HardwareJob': HardwareJob,
            'QNOSBackend': QNOSBackend,
            # Qiskit imports already in globals
        })
        # Enable history for console with increased length
        readline.set_history_length(1000)
        history_file = os.path.expanduser('~/.qnos_history')
        if os.path.exists(history_file):
            readline.read_history_file(history_file)
        atexit.register(readline.write_history_file, history_file)
        QNOSConsole(locals_dict).interact()
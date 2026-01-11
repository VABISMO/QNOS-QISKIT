# lib/hardware.py
import serial
import time
import logging
import numpy as np
import cv2
from typing import Tuple, Union
from math import pi

logger = logging.getLogger(__name__)

class FPGAConnection:
    """
    FPGA connection class.
    @param {str} port - Port name.
    @param {int} baudrate - Baud rate.
    """
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=60)  # Increased timeout for reliable image transfer
            time.sleep(2)
            logger.info("FPGA connected.")
        except serial.SerialException as e:
            logger.error(f"FPGA connection failed: {e}")
            raise

    """
    Sends command to FPGA.
    @param {str} command - Command string.
    @returns {str} Response.
    """
    def send_command(self, command: str) -> str:
        try:
            command = ' '.join(command.split())
            self.ser.write((command + '\n').encode())
            response = self.ser.readline().decode().strip()
            if response != "OK":
                raise ValueError(f"FPGA error: {response}")
            logger.debug(f"Command: {command}, Response: {response}")
            return response
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise

    """
    Receives image from FPGA.
    @param {Tuple[int, int]} size - Image size.
    @returns {np.ndarray} Image data.
    """
    def receive_image(self, size: Tuple[int, int]) -> np.ndarray:
        data = b''
        expected_bytes = size[0] * size[1]
        start_time = time.time()
        while len(data) < expected_bytes:
            chunk = self.ser.read(min(1024, expected_bytes - len(data)))
            if not chunk and time.time() - start_time > 30:  # Longer for large images
                raise TimeoutError("Image reception timeout.")
            data += chunk
        if len(data) != expected_bytes:
            raise ValueError("Incomplete image.")
        return np.frombuffer(data, dtype=np.uint8).reshape(size)

    """
    Closes the connection.
    """
    def close(self):
        try:
            self.ser.close()
        except Exception as e:
            logger.error(f"Failed to close FPGA connection: {e}")
        logger.info("FPGA disconnected.")

class LaserArrayController:
    """
    Controller for laser array.
    @param {FPGAConnection} fpga - FPGA instance.
    """
    def __init__(self, fpga):
        self.fpga = fpga
        self.grid_size = (8, 8)

    """
    Fires laser at position.
    @param {int} row - Row index.
    @param {int} col - Column index.
    @param {int} duration_ms - Duration in ms.
    """
    def fire_laser(self, row: int, col: int, duration_ms: int = 50):
        if not (0 <= row < 8 and 0 <= col < 8):
            raise ValueError("Invalid position.")
        return self.fpga.send_command(f"FIRE_LASER {row} {col} {duration_ms}")

class CameraInterface:
    """
    Interface for camera.
    @param {FPGAConnection} fpga - FPGA instance.
    @param {Tuple[int, int]} image_size - Image dimensions.
    """
    def __init__(self, fpga, image_size: Tuple[int, int] = (480, 640)):
        self.fpga = fpga
        self.image_size = image_size

    """
    Captures image.
    @returns {np.ndarray} Captured image.
    """
    def capture_image(self) -> np.ndarray:
        self.fpga.send_command("CAPTURE_FRAME")
        return self.fpga.receive_image(self.image_size)

class MicrowaveController:
    """
    Controller for microwave pulses.
    @param {FPGAConnection} fpga - FPGA instance.
    """
    def __init__(self, fpga):
        self.fpga = fpga
        self.ref_freq = 25e6

    """
    Applies microwave pulse.
    @param {Union[int, Tuple[int, int]]} qubit - Qubit identifier.
    @param {float} freq_ghz - Frequency in GHz.
    @param {float} amp - Amplitude.
    @param {int} duration_ns - Duration in ns.
    @param {float} phase - Phase.
    """
    def apply_pulse(self, qubit: Union[int, Tuple[int, int]], freq_ghz: float, amp: float, duration_ns: int, phase: float = 0.0):
        if not (1.0 <= freq_ghz <= 4.4):  # ADF4351 range
            raise ValueError("Freq out of range")
        if not (0.0 <= amp <= 1.0):
            raise ValueError("Amp out of [0,1]")
        f_pfd = self.ref_freq / 1  # Assume R=1
        n = int(freq_ghz * 1e9 / f_pfd)
        frac = int(((freq_ghz * 1e9 / f_pfd) - n) * 4096)  # 12-bit FRAC
        mod = 4096
        phase_val = int((phase / (2 * pi)) * mod) % mod
        output_div = 1  # RF divider
        power_level = int(amp * 3) - 4 + 4  # -4 to +5 dBm
        # Firmware only accepts 5 arguments and has a 64-byte buffer limit.
        # Registers are calculated here for reference but not sent to avoid overflow.
        # The firmware currently uses internal placeholder logic for SPI.
        regs = [
            hex((n << 15) | frac),
            hex((phase_val << 15) | (mod << 3) | 1),
            hex(0x000004B3),
            hex(0x0000000C),
            hex((output_div << 8) | (power_level << 3) | 0x00580005),
            hex(0x00800025)
        ]
        qubit_str = str(qubit) if isinstance(qubit, int) else f"{qubit[0]}_{qubit[1]}"
        # command = f"APPLY_PULSE {qubit_str} {freq_ghz} {amp} {duration_ns} {phase} " + " ".join(regs)
        command = f"APPLY_PULSE {qubit_str} {freq_ghz} {amp} {duration_ns} {phase}"
        return self.fpga.send_command(command)
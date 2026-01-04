# lib/simulator.py
import logging
import numpy as np
import cv2
from typing import Tuple
from math import pi
logger = logging.getLogger(__name__)

class SimulatedFPGAConnection:
    """
    Simulated FPGA connection for testing.
    @param {str} port - Simulated port.
    @param {int} baudrate - Simulated baud rate.
    """
    def __init__(self, port: str = 'simulated', baudrate: int = 115200):
        logger.info("FPGA simulated connection initialized.")
        self.responses = {
            "FIRE_LASER": "OK",
            "APPLY_PULSE": "OK",
            "CAPTURE_FRAME": "OK",
            "CAPTURE_DARK": "OK",
        }
        self.active_lasers = set()  # Set to hold current active laser positions for simulation
        self.sim_states = {}  # Simulate qubit states with noise
        self.sim_freq = 2.5e9
        self.sim_noise_level = 0.1

    """
    Sends simulated command.
    @param {str} command - Command string.
    @returns {str} Simulated response.
    """
    def send_command(self, command: str) -> str:
        try:
            parts = command.split()
            command_type = parts[0]
            if command_type == "FIRE_LASER":
                row = int(parts[1])
                col = int(parts[2])
                self.active_lasers.add((row, col))
                qubit = row * 8 + col
                self.sim_states[qubit] = 1  # Set to 1 for visualization
            elif command_type == "APPLY_PULSE":
                qubit_str = parts[1]
                if '_' in qubit_str:
                    qs = tuple(map(int, qubit_str.split('_')))
                else:
                    qs = int(qubit_str)
                freq = float(parts[2])
                amp = float(parts[3])
                duration = int(parts[4])
                phase = float(parts[5])
                if abs(freq - self.sim_freq) > self.sim_noise_level * self.sim_freq:
                    return "ERR"
                if isinstance(qs, int):
                    qubit = qs
                    if qubit not in self.sim_states:
                        self.sim_states[qubit] = 0
                    if abs(phase - pi) < 1e-6:  # X
                        self.sim_states[qubit] = 1 - self.sim_states[qubit]
                    elif abs(phase) > 0:  # RZ, add error
                        if np.random.rand() < self.sim_noise_level:
                            self.sim_states[qubit] = 1 - self.sim_states[qubit]
                else:
                    if self.sim_states.get(qs[0], 0) == 1:
                        self.sim_states[qs[1]] = (self.sim_states.get(qs[1], 0) + int(phase / pi)) % 2
            elif command_type == "CAPTURE_DARK":
                self.active_lasers.clear()
                self.sim_states.clear()
            response = self.responses.get(command_type, "ERR")
            logger.debug(f"Simulated command: {command}, Response: {response}")
            return response
        except Exception as e:
            logger.error(f"Simulated command failed: {e}")
            raise

    """
    Receives simulated image.
    @param {Tuple[int, int]} size - Image size.
    @returns {np.ndarray} Simulated image.
    """
    def receive_image(self, size: Tuple[int, int]) -> np.ndarray:
        image = np.zeros(size, dtype=np.uint8)
        for row, col in list(self.active_lasers):
            cx = col * 80 + 40
            cy = row * 60 + 30
            cv2.circle(image, (cx, cy), 20, 255, -1)
        # Add NISQ noise: Gaussian (reduced to 0 for consistency)
        noise = np.random.normal(0, 0, image.shape).astype(np.uint8)
        image = cv2.add(image, noise)
        self.active_lasers.clear()
        logger.info(f"Simulated image generated with mean: {np.mean(image)}")
        cv2.imwrite('simulated_image.png', image)
        logger.info("Simulated image saved to simulated_image.png")
        return image

    """
    Closes the simulated connection.
    """
    def close(self):
        logger.info("Simulated FPGA disconnected.")
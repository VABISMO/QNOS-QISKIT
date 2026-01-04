# lib/calibrate_mw.py
import numpy as np
from lib.hardware import FPGAConnection, MicrowaveController, CameraInterface
from lib.core import QubitImageProcessor

class MicrowaveCalibrator:
    """
    Calibrator for microwave frequency and amplitude based on defect resonance.
    @param {FPGAConnection} fpga - FPGA instance.
    @param {float} start_freq_ghz - Start frequency for sweep.
    @param {float} end_freq_ghz - End frequency for sweep.
    @param {int} steps - Number of sweep steps.
    """
    def __init__(self, fpga, start_freq_ghz=2.5, end_freq_ghz=3.5, steps=100):
        self.mw_ctrl = MicrowaveController(fpga)
        self.camera = CameraInterface(fpga)
        self.proc = QubitImageProcessor()
        self.freqs = np.linspace(start_freq_ghz, end_freq_ghz, steps)
        self.amps = np.linspace(0.1, 1.0, 10)  # Amp sweep range

    def sweep_freq(self, qubit, amp=0.5, duration_ns=50, phase=0.0):
        """
        Sweep frequency and measure ODMR contrast.
        @param {int} qubit - Qubit to apply pulse.
        @param {float} amp - Fixed amplitude.
        @param {int} duration_ns - Pulse duration.
        @param {float} phase - Phase.
        @returns {tuple} (best_freq, contrasts)
        """
        contrasts = []
        for freq in self.freqs:
            self.mw_ctrl.apply_pulse(qubit, freq, amp, duration_ns, phase)
            image = self.camera.capture_image()
            states = self.proc.process_image(image, {}, num_qubits=1)  # Simplified
            contrast = np.max(states) - np.min(states)  # Mock contrast
            contrasts.append(contrast)
        best_freq = self.freqs[np.argmax(contrasts)]
        return best_freq, contrasts

    def sweep_amp(self, qubit, freq, duration_ns=50, phase=0.0):
        """
        Sweep amplitude at fixed frequency.
        @param {int} qubit - Qubit.
        @param {float} freq - Fixed frequency.
        @param {int} duration_ns - Duration.
        @param {float} phase - Phase.
        @returns {tuple} (best_amp, contrasts)
        """
        contrasts = []
        for amp in self.amps:
            self.mw_ctrl.apply_pulse(qubit, freq, amp, duration_ns, phase)
            image = self.camera.capture_image()
            states = self.proc.process_image(image, {}, num_qubits=1)
            contrast = np.max(states) - np.min(states)
            contrasts.append(contrast)
        best_amp = self.amps[np.argmax(contrasts)]
        return best_amp, contrasts

# Usage example (run as script)
if __name__ == "__main__":
    fpga = FPGAConnection()  # Or Simulated
    cal = MicrowaveCalibrator(fpga, start_freq_ghz=3.0, end_freq_ghz=4.0)  # For hBN
    best_freq, _ = cal.sweep_freq(qubit=0)
    best_amp, _ = cal.sweep_amp(qubit=0, freq=best_freq)
    print(f"Calibrated: Freq {best_freq} GHz, Amp {best_amp}")
    fpga.close()
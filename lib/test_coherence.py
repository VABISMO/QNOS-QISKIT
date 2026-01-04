# lib/test_coherence.py
import numpy as np
from lib.hardware import FPGAConnection, MicrowaveController, CameraInterface
from lib.core import QubitImageProcessor
from scipy.optimize import curve_fit

class CoherenceTester:
    """
    Tester for spin coherence times using Ramsey sequence.
    @param {FPGAConnection} fpga - FPGA instance.
    @param {float} freq_ghz - Resonance frequency.
    @param {float} amp - Amplitude.
    @param {int} qubit - Qubit to test.
    """
    def __init__(self, fpga, freq_ghz=3.5, amp=0.5, qubit=0):
        self.mw_ctrl = MicrowaveController(fpga)
        self.camera = CameraInterface(fpga)
        self.proc = QubitImageProcessor()
        self.freq = freq_ghz
        self.amp = amp
        self.qubit = qubit
        self.delays = np.logspace(0, 4, 20)  # 1 ns to 10 us

    def ramsey_sequence(self, delay_ns):
        """
        Apply Ramsey: pi/2 - delay - pi/2 - measure.
        @param {float} delay_ns - Free evolution time.
        @returns {float} Contrast.
        """
        # pi/2 pulse (assume duration for pi is 50 ns, so pi/2=25 ns)
        self.mw_ctrl.apply_pulse(self.qubit, self.freq, self.amp, 25, 0.0)  # X pi/2
        time.sleep(delay_ns / 1e9)
        self.mw_ctrl.apply_pulse(self.qubit, self.freq, self.amp, 25, 0.0)  # X pi/2
        image = self.camera.capture_image()
        states = self.proc.process_image(image, {}, num_qubits=1)
        return np.mean(states)  # Mock visibility

    def measure_t2(self):
        """
        Measure T2 from Ramsey decay.
        @returns {float} T2 in us.
        """
        visibilities = [self.ramsey_sequence(d) for d in self.delays]
        def exp_decay(t, a, tau, c): return a * np.exp(-t / tau) + c
        popt, _ = curve_fit(exp_decay, self.delays / 1000, visibilities)  # ns to us
        return popt[1]  # tau = T2*

    def add_shaping(self, duration_ns):
        """
        Apply Gaussian-shaped pulse by discretizing.
        @param {int} duration_ns - Total duration.
        """
        steps = 10
        sigma = duration_ns / 6.0  # For Gaussian
        for i in range(steps):
            t = i * (duration_ns / steps)
            env_amp = self.amp * np.exp(-((t - duration_ns/2)**2) / (2 * sigma**2))
            self.mw_ctrl.apply_pulse(self.qubit, self.freq, env_amp, duration_ns // steps, 0.0)

# Usage
if __name__ == "__main__":
    fpga = FPGAConnection()
    tester = CoherenceTester(fpga)
    t2 = tester.measure_t2()
    print(f"Measured T2*: {t2} us")
    # If T2 short, use shaping
    if t2 < 1.0:
        tester.add_shaping(50)  # Example
    fpga.close()
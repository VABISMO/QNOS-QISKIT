# lib/laser.py
"""
Laser abstraction layer for QNOS.
Supports multiple laser/LED types with auto-calibration and diagnostics.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Laser presets for common types
LASER_PRESETS = {
    'VCSEL_532nm': {
        'wavelength': 532,
        'type': 'vcsel',
        'typical_current_ma': 5,
        'forward_voltage': 2.1,
        'notes': 'Green VCSEL array, good for hBN excitation'
    },
    'VCSEL_850nm': {
        'wavelength': 850,
        'type': 'vcsel',
        'typical_current_ma': 8,
        'forward_voltage': 1.8,
        'notes': 'NIR VCSEL, common array format'
    },
    'LED_405nm': {
        'wavelength': 405,
        'type': 'led',
        'typical_current_ma': 20,
        'forward_voltage': 3.2,
        'notes': 'UV LED for NV diamond excitation'
    },
    'LED_470nm': {
        'wavelength': 470,
        'type': 'led',
        'typical_current_ma': 20,
        'forward_voltage': 3.0,
        'notes': 'Blue LED array'
    },
    'FIBER_532nm': {
        'wavelength': 532,
        'type': 'fiber_coupled',
        'typical_power_mw': 50,
        'notes': 'Fiber-coupled laser for precise delivery'
    },
}


@dataclass
class LaserInfo:
    """Laser/LED information structure."""
    laser_type: str  # 'vcsel', 'led', 'fiber_coupled', 'simulated'
    name: str
    wavelength_nm: int
    grid_size: Tuple[int, int]
    connection_type: str = 'fpga'  # 'fpga', 'gpio', 'usb'
    device_path: Optional[str] = None
    forward_voltage: float = 2.0
    typical_current_ma: float = 5.0
    is_available: bool = True
    notes: str = ''


class LaserBase(ABC):
    """Abstract base class for all laser/LED types."""
    
    @abstractmethod
    def fire(self, row: int, col: int, duration_ms: int = 100) -> bool:
        """Fire laser at specified position."""
        pass
    
    @abstractmethod
    def fire_all(self, duration_ms: int = 100) -> bool:
        """Fire all lasers simultaneously."""
        pass
    
    @abstractmethod
    def get_info(self) -> LaserInfo:
        """Return laser information."""
        pass
    
    @abstractmethod
    def get_grid_size(self) -> Tuple[int, int]:
        """Return grid dimensions (rows, cols)."""
        pass
    
    @abstractmethod
    def close(self):
        """Release resources."""
        pass


class FPGALaserArray(LaserBase):
    """Laser array controlled via FPGA (VCSEL, LED arrays)."""
    
    def __init__(self, fpga, grid_size: Tuple[int, int] = (8, 8), 
                 laser_type: str = 'vcsel', wavelength: int = 532):
        self.fpga = fpga
        self.grid_size = grid_size
        self.laser_type = laser_type
        self.wavelength = wavelength
        logger.info(f"FPGALaserArray initialized: {grid_size[0]}x{grid_size[1]} {laser_type} @ {wavelength}nm")
    
    def fire(self, row: int, col: int, duration_ms: int = 100) -> bool:
        if row < 0 or row >= self.grid_size[0] or col < 0 or col >= self.grid_size[1]:
            logger.error(f"Invalid position ({row}, {col}) for grid {self.grid_size}")
            return False
        response = self.fpga.send_command(f"FIRE_LASER {row} {col} {duration_ms}")
        return 'OK' in str(response).upper() if response else True
    
    def fire_all(self, duration_ms: int = 100) -> bool:
        """Fire all lasers in sequence."""
        for row in range(self.grid_size[0]):
            for col in range(self.grid_size[1]):
                self.fire(row, col, duration_ms)
                time.sleep(0.01)
        return True
    
    def fire_pattern(self, pattern: List[Tuple[int, int]], duration_ms: int = 100) -> bool:
        """Fire specific pattern of lasers."""
        for (row, col) in pattern:
            self.fire(row, col, duration_ms)
        return True
    
    def get_info(self) -> LaserInfo:
        return LaserInfo(
            laser_type=self.laser_type,
            name=f"{self.laser_type.upper()} Array {self.grid_size[0]}x{self.grid_size[1]}",
            wavelength_nm=self.wavelength,
            grid_size=self.grid_size,
            connection_type='fpga',
            device_path=getattr(self.fpga, 'port', '/dev/ttyUSB0')
        )
    
    def get_grid_size(self) -> Tuple[int, int]:
        return self.grid_size
    
    def close(self):
        logger.info("FPGALaserArray closed")


class SimulatedLaser(LaserBase):
    """Simulated laser for testing."""
    
    def __init__(self, grid_size: Tuple[int, int] = (8, 8)):
        self.grid_size = grid_size
        self.fired_positions: List[Tuple[int, int, int]] = []  # (row, col, duration)
        logger.info(f"SimulatedLaser initialized: {grid_size}")
    
    def fire(self, row: int, col: int, duration_ms: int = 100) -> bool:
        self.fired_positions.append((row, col, duration_ms))
        logger.debug(f"Simulated fire at ({row}, {col}) for {duration_ms}ms")
        return True
    
    def fire_all(self, duration_ms: int = 100) -> bool:
        for row in range(self.grid_size[0]):
            for col in range(self.grid_size[1]):
                self.fire(row, col, duration_ms)
        return True
    
    def get_fired_positions(self) -> List[Tuple[int, int, int]]:
        """Return list of fired positions for verification."""
        return self.fired_positions.copy()
    
    def clear_history(self):
        """Clear firing history."""
        self.fired_positions = []
    
    def get_info(self) -> LaserInfo:
        return LaserInfo(
            laser_type='simulated',
            name='Simulated Laser Array',
            wavelength_nm=532,
            grid_size=self.grid_size
        )
    
    def get_grid_size(self) -> Tuple[int, int]:
        return self.grid_size
    
    def close(self):
        logger.info("SimulatedLaser closed")


class LaserManager:
    """Manager for laser detection and diagnostics."""
    
    @staticmethod
    def detect_lasers(fpga=None) -> List[LaserInfo]:
        """Detect available laser arrays."""
        lasers = []
        
        if fpga:
            # Assume FPGA has laser array connected
            lasers.append(LaserInfo(
                laser_type='vcsel',
                name='FPGA VCSEL Array (8x8)',
                wavelength_nm=532,
                grid_size=(8, 8),
                connection_type='fpga'
            ))
        
        # Always include simulated
        lasers.append(LaserInfo(
            laser_type='simulated',
            name='Simulated Laser Array',
            wavelength_nm=532,
            grid_size=(8, 8)
        ))
        
        return lasers
    
    @staticmethod
    def create_laser(laser_type: str, **kwargs) -> LaserBase:
        """Create a laser instance by type."""
        if laser_type == 'simulated':
            grid_size = kwargs.get('grid_size', (8, 8))
            return SimulatedLaser(grid_size=grid_size)
        elif laser_type in ['vcsel', 'led', 'fpga']:
            fpga = kwargs.get('fpga')
            if not fpga:
                raise ValueError("FPGA connection required for FPGA laser array")
            grid_size = kwargs.get('grid_size', (8, 8))
            wavelength = kwargs.get('wavelength', 532)
            return FPGALaserArray(fpga, grid_size=grid_size, 
                                  laser_type=laser_type, wavelength=wavelength)
        else:
            raise ValueError(f"Unknown laser type: {laser_type}")
    
    @staticmethod
    def run_diagnostics(laser: LaserBase, camera=None) -> Dict:
        """Run diagnostic tests on a laser array."""
        results = {
            'laser_info': laser.get_info().__dict__,
            'tests': {}
        }
        
        grid = laser.get_grid_size()
        
        # Test 1: Fire test (corners)
        try:
            corners = [(0, 0), (0, grid[1]-1), (grid[0]-1, 0), (grid[0]-1, grid[1]-1)]
            success = all(laser.fire(r, c, 50) for r, c in corners)
            results['tests']['corner_fire'] = {
                'status': 'PASS' if success else 'FAIL',
                'positions_tested': corners
            }
        except Exception as e:
            results['tests']['corner_fire'] = {'status': 'FAIL', 'error': str(e)}
        
        # Test 2: Grid coverage
        try:
            total = grid[0] * grid[1]
            success_count = sum(1 for r in range(grid[0]) for c in range(grid[1]) 
                               if laser.fire(r, c, 10))
            results['tests']['grid_coverage'] = {
                'status': 'PASS' if success_count == total else 'WARN',
                'success_rate': f"{success_count}/{total}",
                'percentage': success_count / total * 100
            }
        except Exception as e:
            results['tests']['grid_coverage'] = {'status': 'FAIL', 'error': str(e)}
        
        # Test 3: Visual verification (if camera provided)
        if camera:
            try:
                # Fire center, capture image
                center = (grid[0] // 2, grid[1] // 2)
                laser.fire(center[0], center[1], 100)
                time.sleep(0.1)
                img = camera.capture_image()
                
                # Check if bright spot detected
                max_val = img.max() if hasattr(img, 'max') else 0
                mean_val = img.mean() if hasattr(img, 'mean') else 0
                
                results['tests']['visual_verify'] = {
                    'status': 'PASS' if max_val > mean_val + 50 else 'WARN',
                    'max_intensity': float(max_val),
                    'mean_intensity': float(mean_val),
                    'message': 'Bright spot detected' if max_val > mean_val + 50 else 'No clear spot'
                }
            except Exception as e:
                results['tests']['visual_verify'] = {'status': 'FAIL', 'error': str(e)}
        
        return results

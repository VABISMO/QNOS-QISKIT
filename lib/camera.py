# lib/camera.py
"""
Camera abstraction layer for QNOS.
Supports multiple camera types: FPGA (OV7670), USB, CSI (IMX477), CCD sensors, and simulation.
"""

import logging
import numpy as np
import cv2
import os
import glob
from abc import ABC, abstractmethod
from typing import Tuple, Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Camera presets for common sensors
CAMERA_PRESETS = {
    # FPGA-based (low resolution)
    'OV7670': {'resolution': (480, 640), 'type': 'cmos', 'max_grid': (8, 8), 'notes': 'VGA module'},
    
    # Entry-level high-res
    'IMX477': {'resolution': (3040, 4056), 'type': 'cmos', 'max_grid': (16, 16), 'notes': 'RPi HQ 12.3MP'},
    'IMX519': {'resolution': (3496, 4656), 'type': 'cmos', 'max_grid': (16, 16), 'notes': 'Arducam 16MP autofocus'},
    
    # Consumer high megapixel (DSLR/Mirrorless)
    'IMX571': {'resolution': (4176, 6244), 'type': 'cmos', 'max_grid': (24, 24), 'notes': 'Sony 26MP APS-C'},
    'IMX455': {'resolution': (6192, 8256), 'type': 'cmos', 'max_grid': (32, 32), 'notes': 'Sony 61MP Full-Frame'},
    'IMX461': {'resolution': (6384, 8736), 'type': 'cmos', 'max_grid': (36, 36), 'notes': 'Sony 100MP Medium Format'},
    
    # Smartphone high-res (direct sensor boards)
    'ISOCELL_HP1': {'resolution': (9248, 12000), 'type': 'cmos', 'max_grid': (48, 48), 'notes': 'Samsung 200MP'},
    'ISOCELL_HP3': {'resolution': (9248, 12000), 'type': 'cmos', 'max_grid': (48, 48), 'notes': 'Samsung 200MP compact'},
    'IMX989': {'resolution': (6000, 8000), 'type': 'cmos', 'max_grid': (32, 32), 'notes': 'Sony 50MP 1-inch'},
    
    # Scientific/Industrial CCD
    'ICX618ALA': {'resolution': (480, 640), 'type': 'ccd', 'max_grid': (8, 8), 'notes': 'Sony CCD bare sensor'},
    'ICX274AL': {'resolution': (1200, 1600), 'type': 'ccd', 'max_grid': (12, 12), 'notes': 'Sony CCD 2MP'},
    'KAF-50100': {'resolution': (6132, 8176), 'type': 'ccd', 'max_grid': (32, 32), 'notes': 'Kodak 50MP CCD'},
    
    # Gigapixel arrays (tiled sensors)
    'GPIXEL_GMAX3265': {'resolution': (6464, 9216), 'type': 'cmos', 'max_grid': (36, 36), 'notes': '65MP global shutter'},
    'GPIXEL_GMAX0505': {'resolution': (4608, 5120), 'type': 'cmos', 'max_grid': (24, 24), 'notes': '25MP high-speed'},
}

# Resolution tiers for auto-selection
RESOLUTION_TIERS = {
    'basic': (480, 640),        # 8x8 grid max
    'standard': (1080, 1920),   # 12x12 grid max
    'high': (3040, 4056),       # 16x16 grid max
    'ultra': (6192, 8256),      # 32x32 grid max
    'extreme': (9248, 12000),   # 48x48 grid max (200MP)
}


@dataclass
class CameraInfo:
    """Camera information structure."""
    camera_type: str
    name: str
    resolution: Tuple[int, int]
    sensor_type: str = 'cmos'  # 'cmos' or 'ccd'
    device_path: Optional[str] = None
    max_qubit_grid: Tuple[int, int] = (8, 8)
    has_lens: bool = True
    is_available: bool = True
    notes: str = ''


class CameraBase(ABC):
    """Abstract base class for all camera types."""
    
    @abstractmethod
    def capture_image(self) -> np.ndarray:
        """Capture and return an image as numpy array."""
        pass
    
    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Return (height, width) of the camera."""
        pass
    
    @abstractmethod
    def get_info(self) -> CameraInfo:
        """Return camera information."""
        pass
    
    @abstractmethod
    def close(self):
        """Release camera resources."""
        pass
    
    def capture_background(self) -> np.ndarray:
        """Capture a background/dark frame."""
        return self.capture_image()


class FPGACameraOV7670(CameraBase):
    """Camera interface via FPGA (OV7670, 640x480)."""
    
    def __init__(self, fpga, image_size: Tuple[int, int] = (480, 640)):
        self.fpga = fpga
        self.image_size = image_size
        logger.info(f"FPGACameraOV7670 initialized at {image_size}")
    
    def capture_image(self) -> np.ndarray:
        self.fpga.send_command("CAPTURE_FRAME")
        return self.fpga.receive_image(self.image_size)
    
    def get_resolution(self) -> Tuple[int, int]:
        return self.image_size
    
    def get_info(self) -> CameraInfo:
        return CameraInfo(
            camera_type="fpga",
            name="OV7670 via FPGA",
            resolution=self.image_size,
            device_path=getattr(self.fpga, 'port', '/dev/ttyUSB0'),
            max_qubit_grid=(8, 8)
        )
    
    def close(self):
        logger.info("FPGACameraOV7670 closed")


class USBCamera(CameraBase):
    """USB camera via OpenCV VideoCapture."""
    
    def __init__(self, device_id: int = 0, resolution: Optional[Tuple[int, int]] = None):
        self.device_id = device_id
        self.cap = cv2.VideoCapture(device_id)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open USB camera at device {device_id}")
        
        # Set resolution if specified
        if resolution:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[1])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[0])
        
        # Read actual resolution
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Calculate max qubit grid based on resolution
        pixels_per_qubit = 60  # Minimum pixels per qubit for reliable detection
        max_cols = self.width // pixels_per_qubit
        max_rows = self.height // pixels_per_qubit
        self.max_grid = (min(max_rows, 16), min(max_cols, 16))
        
        logger.info(f"USBCamera initialized: device={device_id}, resolution={self.height}x{self.width}")
    
    def capture_image(self) -> np.ndarray:
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to capture frame from USB camera")
        # Convert to grayscale for consistency
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return frame
    
    def get_resolution(self) -> Tuple[int, int]:
        return (self.height, self.width)
    
    def get_info(self) -> CameraInfo:
        return CameraInfo(
            camera_type="usb",
            name=f"USB Camera #{self.device_id}",
            resolution=(self.height, self.width),
            device_path=f"/dev/video{self.device_id}",
            max_qubit_grid=self.max_grid
        )
    
    def close(self):
        if self.cap:
            self.cap.release()
        logger.info("USBCamera closed")


class CSICamera(CameraBase):
    """CSI camera (IMX477) via libcamera or OpenCV with GStreamer."""
    
    def __init__(self, resolution: Tuple[int, int] = (3040, 4056)):
        self.resolution = resolution
        self.cap = None
        
        # Try libcamera-based capture first (Raspberry Pi)
        gst_pipeline = (
            f"libcamerasrc ! "
            f"video/x-raw,width={resolution[1]},height={resolution[0]} ! "
            f"videoconvert ! appsink"
        )
        
        try:
            self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
            if not self.cap.isOpened():
                raise RuntimeError("GStreamer pipeline failed")
            self.backend = "libcamera"
        except Exception as e:
            logger.warning(f"libcamera not available: {e}, trying OpenCV default")
            # Fallback to OpenCV with CSI index
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[1])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[0])
                self.backend = "opencv"
            else:
                raise RuntimeError("No CSI camera available")
        
        # Calculate max qubit grid
        pixels_per_qubit = 60
        max_cols = resolution[1] // pixels_per_qubit
        max_rows = resolution[0] // pixels_per_qubit
        self.max_grid = (min(max_rows, 16), min(max_cols, 16))
        
        logger.info(f"CSICamera initialized: resolution={resolution}, backend={self.backend}")
    
    def capture_image(self) -> np.ndarray:
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to capture frame from CSI camera")
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return frame
    
    def get_resolution(self) -> Tuple[int, int]:
        return self.resolution
    
    def get_info(self) -> CameraInfo:
        return CameraInfo(
            camera_type="csi",
            name="IMX477 HQ Camera",
            resolution=self.resolution,
            device_path="/dev/video0",
            max_qubit_grid=self.max_grid
        )
    
    def close(self):
        if self.cap:
            self.cap.release()
        logger.info("CSICamera closed")


class SimulatedCamera(CameraBase):
    """Simulated camera for testing without hardware."""
    
    def __init__(self, resolution: Tuple[int, int] = (480, 640), grid_size: Tuple[int, int] = (8, 8)):
        self.resolution = resolution
        self.grid_size = grid_size
        self.active_positions = set()  # Positions to simulate as "lit"
        logger.info(f"SimulatedCamera initialized: {resolution}")
    
    def set_active_positions(self, positions: set):
        """Set which qubit positions should appear lit."""
        self.active_positions = positions
    
    def capture_image(self) -> np.ndarray:
        image = np.zeros(self.resolution, dtype=np.uint8)
        
        # Draw circles at active positions
        cell_h = self.resolution[0] // self.grid_size[0]
        cell_w = self.resolution[1] // self.grid_size[1]
        
        for (row, col) in self.active_positions:
            cx = col * cell_w + cell_w // 2
            cy = row * cell_h + cell_h // 2
            cv2.circle(image, (cx, cy), min(cell_w, cell_h) // 3, 255, -1)
        
        # Add slight noise for realism
        noise = np.random.normal(0, 5, image.shape).astype(np.int16)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return image
    
    def get_resolution(self) -> Tuple[int, int]:
        return self.resolution
    
    def get_info(self) -> CameraInfo:
        return CameraInfo(
            camera_type="simulated",
            name="Simulated Camera",
            resolution=self.resolution,
            max_qubit_grid=self.grid_size
        )
    
    def close(self):
        logger.info("SimulatedCamera closed")


class CameraManager:
    """Manager for camera detection and instantiation."""
    
    @staticmethod
    def detect_cameras() -> List[CameraInfo]:
        """Scan all interfaces and return list of available cameras."""
        cameras = []
        
        # Check USB cameras (/dev/video*)
        video_devices = glob.glob("/dev/video*")
        for device in video_devices:
            try:
                device_id = int(device.replace("/dev/video", ""))
                cap = cv2.VideoCapture(device_id)
                if cap.isOpened():
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    
                    cameras.append(CameraInfo(
                        camera_type="usb",
                        name=f"USB Camera #{device_id}",
                        resolution=(height, width),
                        device_path=device,
                        max_qubit_grid=(height // 60, width // 60)
                    ))
            except Exception as e:
                logger.debug(f"Could not probe {device}: {e}")
        
        # Check for FPGA serial ports
        serial_devices = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        for device in serial_devices:
            cameras.append(CameraInfo(
                camera_type="fpga",
                name=f"FPGA Camera (OV7670) via {os.path.basename(device)}",
                resolution=(480, 640),
                device_path=device,
                max_qubit_grid=(8, 8)
            ))
        
        # Always include simulated camera
        cameras.append(CameraInfo(
            camera_type="simulated",
            name="Simulated Camera",
            resolution=(480, 640),
            max_qubit_grid=(8, 8)
        ))
        
        return cameras
    
    @staticmethod
    def create_camera(camera_type: str, **kwargs) -> CameraBase:
        """Create a camera instance by type."""
        if camera_type == "simulated":
            return SimulatedCamera(**kwargs)
        elif camera_type == "usb":
            device_id = kwargs.get('device_id', 0)
            return USBCamera(device_id=device_id)
        elif camera_type == "csi":
            resolution = kwargs.get('resolution', (3040, 4056))
            return CSICamera(resolution=resolution)
        elif camera_type == "fpga":
            fpga = kwargs.get('fpga')
            if not fpga:
                raise ValueError("FPGA connection required for FPGA camera")
            return FPGACameraOV7670(fpga)
        else:
            raise ValueError(f"Unknown camera type: {camera_type}")
    
    @staticmethod
    def run_diagnostics(camera: CameraBase) -> Dict:
        """Run diagnostic tests on a camera."""
        results = {
            'camera_info': camera.get_info().__dict__,
            'tests': {}
        }
        
        # Test 1: Capture test
        try:
            img = camera.capture_image()
            results['tests']['capture'] = {
                'status': 'PASS',
                'shape': img.shape,
                'dtype': str(img.dtype),
                'mean_intensity': float(np.mean(img)),
                'std_intensity': float(np.std(img))
            }
        except Exception as e:
            results['tests']['capture'] = {
                'status': 'FAIL',
                'error': str(e)
            }
        
        # Test 2: Multiple captures (consistency)
        try:
            frames = [camera.capture_image() for _ in range(5)]
            diffs = [np.mean(np.abs(frames[i].astype(float) - frames[i+1].astype(float))) 
                     for i in range(len(frames)-1)]
            results['tests']['stability'] = {
                'status': 'PASS' if np.mean(diffs) < 50 else 'WARN',
                'mean_frame_diff': float(np.mean(diffs)),
                'message': 'Low noise' if np.mean(diffs) < 50 else 'High noise detected'
            }
        except Exception as e:
            results['tests']['stability'] = {
                'status': 'FAIL',
                'error': str(e)
            }
        
        # Test 3: Resolution check
        expected_res = camera.get_resolution()
        try:
            img = camera.capture_image()
            actual_res = img.shape[:2]
            match = actual_res == expected_res
            results['tests']['resolution'] = {
                'status': 'PASS' if match else 'FAIL',
                'expected': expected_res,
                'actual': actual_res
            }
        except Exception as e:
            results['tests']['resolution'] = {
                'status': 'FAIL',
                'error': str(e)
            }
        
        return results

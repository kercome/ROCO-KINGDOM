"""
Roco Navigation System - 洛克王国视觉导航叠加工具

A visual navigation overlay tool for Roco Kingdom game based on:
- Visual positioning (ORB feature matching + Kalman filter)
- Coordinate mapping (pixel <-> game coordinates)
- A* path planning

Package Structure:
------------------
src/
├── core/       # Core modules (coord mapping, path finding, point detection)
├── ui/         # User interface components (overlay, control panel)
├── services/   # Background services (capture engine, vision engine)
└── utils/      # Utility functions (logging)

Quick Start:
------------
>>> from src import OverlayUI, ControlPanel
>>> from src.core import PathFinder, CoordAligner
>>> from src.services import CaptureEngine, VisionEngine

Author: Roco Navigation Team
License: MIT
"""

__version__ = "3.0.0"
__author__ = "Roco Navigation Team"
__description__ = "Visual Navigation Overlay Tool for Roco Kingdom"

# Import main components for convenience
from src.ui.overlay_ui import OverlayUI
from src.ui.control_panel import ControlPanel
from src.core.path_finder import PathFinder
from src.core.coord_aligner import CoordAligner
from src.services.capture_engine import CaptureEngine
from src.services.vision_engine import VisionEngine
from src.utils.logger import get_logger

__all__ = [
    "OverlayUI",
    "ControlPanel",
    "PathFinder",
    "CoordAligner",
    "CaptureEngine",
    "VisionEngine",
    "get_logger",
]

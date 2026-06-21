"""
Roco Navigation System - Core Module Exports

This module provides core functionality for navigation:
- Coordinate mapping and alignment
- Path finding with A* algorithm
- Point detection and tile mapping
"""

from src.core.coord_mapper import (
    MAP_WIDTH,
    MAP_HEIGHT,
    MAP_MODE,
    pixel_to_game_coords,
    game_to_pixel,
    load_map,
    get_map_size,
)

from src.core.coord_aligner import (
    CoordAligner,
    load_points,
    pixel_distance,
)

from src.core.path_finder import (
    PathFinder,
    MAP_WIDTH as PF_MAP_WIDTH,
    MAP_HEIGHT as PF_MAP_HEIGHT,
    DEFAULT_CONNECTION_RADIUS,
    MAX_ITERATIONS,
)

from src.core.point_detector import PointDetector

from src.core.tile_mapper import TileMapper

__all__ = [
    # coord_mapper
    "MAP_WIDTH",
    "MAP_HEIGHT",
    "MAP_MODE",
    "pixel_to_game_coords",
    "game_to_pixel",
    "load_map",
    "get_map_size",
    # coord_aligner
    "CoordAligner",
    "load_points",
    "pixel_distance",
    # path_finder
    "PathFinder",
    "DEFAULT_CONNECTION_RADIUS",
    "MAX_ITERATIONS",
    # point_detector
    "PointDetector",
    # tile_mapper
    "TileMapper",
]

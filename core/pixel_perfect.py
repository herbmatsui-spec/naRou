from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogicalPosition:
    x: int
    y: int


@dataclass(frozen=True)
class PhysicalPosition:
    x: int
    y: int
    sub_x: float
    sub_y: float


def logical_to_physical(
    logical_x: int,
    logical_y: int,
    scale: float,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> PhysicalPosition:
    """
    Convert logical pixel coordinates to physical pixel coordinates with subpixel precision.

    Args:
        logical_x: X coordinate in logical pixels
        logical_y: Y coordinate in logical pixels
        scale: Integer scale factor (e.g., 1.0, 2.0, 3.0)
        offset_x: Subpixel offset in X (-0.5 to 0.5)
        offset_y: Subpixel offset in Y (-0.5 to 0.5)

    Returns:
        PhysicalPosition with integer coordinates and subpixel offsets
    """
    physical_x = logical_x * scale + offset_x
    physical_y = logical_y * scale + offset_y

    int_x = int(physical_x)
    int_y = int(physical_y)
    sub_x = physical_x - int_x
    sub_y = physical_y - int_y

    return PhysicalPosition(int_x, int_y, sub_x, sub_y)


def logical_to_physical_vec(
    logical: LogicalPosition, scale: float, offset_x: float = 0.0, offset_y: float = 0.0
) -> PhysicalPosition:
    """Vector version of logical_to_physical"""
    return logical_to_physical(logical.x, logical.y, scale, offset_x, offset_y)


def physical_to_logical(
    physical_x: int, physical_y: int, sub_x: float, sub_y: float, scale: float
) -> LogicalPosition:
    """Convert physical coordinates back to logical"""
    logical_x = int((physical_x + sub_x) / scale)
    logical_y = int((physical_y + sub_y) / scale)
    return LogicalPosition(logical_x, logical_y)


def get_css_transform(
    logical_x: int, logical_y: int, scale: float, sub_x: float = 0.0, sub_y: float = 0.0
) -> str:
    """
    Generate CSS transform string for subpixel positioning.

    Returns:
        CSS transform string like "translate(10.5px, 20.3px) scale(2)"
    """
    physical_x = logical_x * scale + sub_x
    physical_y = logical_y * scale + sub_y
    return f"translate({physical_x}px, {physical_y}px) scale({scale})"


def get_tcod_offset(sub_x: float, sub_y: float) -> tuple[int, int]:
    """
    Get tcod console draw offset for subpixel rendering.
    tcod doesn't support subpixel directly, so this returns the nearest pixel.
    """
    return (round(sub_x), round(sub_y))


def calculate_optimal_scale(
    logical_width: int, logical_height: int, physical_width: int, physical_height: int
) -> float:
    """
    Calculate optimal integer scale to fit logical size into physical size.

    Returns:
        Maximum integer scale factor that fits
    """
    scale_x = physical_width // logical_width
    scale_y = physical_height // logical_height
    return float(min(scale_x, scale_y))


def snap_to_pixel_grid(value: float, grid_size: float = 1.0) -> float:
    """Snap a value to the nearest pixel grid"""
    return round(value / grid_size) * grid_size


def lerp_subpixel(start: PhysicalPosition, end: PhysicalPosition, t: float) -> PhysicalPosition:
    """Linear interpolation between two physical positions with subpixel precision"""
    x = start.x + (end.x - start.x) * t
    y = start.y + (end.y - start.y) * t
    start.sub_x + (end.sub_x - start.sub_x) * t
    start.sub_y + (end.sub_y - start.sub_y) * t

    int_x = int(x)
    int_y = int(y)
    return PhysicalPosition(int_x, int_y, x - int_x, y - int_y)

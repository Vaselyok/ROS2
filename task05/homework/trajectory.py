"""Pure application logic for the supplied L05 ROS action client."""

from collections.abc import Mapping
import math
from numbers import Real


def _number(value, label):
    """Accept finite real numbers, excluding bool (which subclasses int)."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} must be a finite real number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{label} must be finite") from error
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _names(joint_names):
    if not isinstance(joint_names, (list, tuple)) or not joint_names:
        raise ValueError("joint_names must be a nonempty list or tuple")
    if any(not isinstance(name, str) or not name for name in joint_names):
        raise ValueError("joint names must be nonempty strings")
    if len(set(joint_names)) != len(joint_names):
        raise ValueError("joint names must be unique")
    return list(joint_names)


def _bounds(names, limits):
    if not isinstance(limits, Mapping):
        raise ValueError("limits must be a mapping")
    bounds = {}
    for name in names:
        if name not in limits:
            raise ValueError(f"missing limits for {name}")
        pair = limits[name]
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(f"limits for {name} must be a lower/upper pair")
        lower = _number(pair[0], f"{name} lower limit")
        upper = _number(pair[1], f"{name} upper limit")
        if lower > upper:
            raise ValueError(f"reversed limits for {name}")
        bounds[name] = (lower, upper)
    return bounds


def _positions(names, positions, bounds):
    if not isinstance(positions, Mapping) or set(positions) != set(names):
        raise ValueError("positions must contain exactly the requested joints")
    ordered = []
    for name in names:
        value = _number(positions[name], f"{name} position")
        lower, upper = bounds[name]
        if not lower <= value <= upper:
            raise ValueError(f"position outside limits for {name}")
        ordered.append(value)
    return ordered


def build_points(waypoints, joint_names, limits):
    """Validate named poses and return new points in the requested joint order."""
    names = _names(joint_names)
    bounds = _bounds(names, limits)
    if not isinstance(waypoints, (list, tuple)) or not waypoints:
        raise ValueError("waypoints must be a nonempty list or tuple")
    points = []
    previous_time = 0.0
    for waypoint in waypoints:
        if not isinstance(waypoint, dict) or set(waypoint) != {"time", "positions"}:
            raise ValueError("each waypoint must have exactly time and positions")
        seconds = _number(waypoint["time"], "waypoint time")
        if seconds <= previous_time:
            raise ValueError("times must be positive and strictly increasing")
        points.append({
            "time_from_start": seconds,
            "positions": _positions(names, waypoint["positions"], bounds),
        })
        previous_time = seconds
    return points


def tracking_error(joint_names, desired, actual):
    """Maximum absolute reference/measurement error for one feedback, in rad."""
    names = _names(joint_names)
    for positions in (desired, actual):
        if not isinstance(positions, (list, tuple)) or len(positions) != len(names):
            raise ValueError("feedback lengths must match joint_names")
    reference = [_number(value, "desired position") for value in desired]
    measured = [_number(value, "actual position") for value in actual]
    return max(abs(wanted - observed) for wanted, observed in zip(reference, measured))


def hold_point(joint_names, measured, limits, duration=0.2):
    """Hold the supplied measured pose; snapshot freshness is checked by client."""
    names = _names(joint_names)
    bounds = _bounds(names, limits)
    seconds = _number(duration, "hold duration")
    if seconds <= 0:
        raise ValueError("hold duration must be positive")
    return {
        "time_from_start": seconds,
        "positions": _positions(names, measured, bounds),
    }


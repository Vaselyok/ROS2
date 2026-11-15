"""Homework: implement only the two policy functions below.

The transport, TF error adapter, retries, raw-TF audit, and report formatting are
supplied. Run the public tests after each step. No ROS install is needed for them.
"""
from .contracts import Lookup, LookupFailure, Observation, report
from .geometry import apply_transform
import math
from numbers import Real, Integral

def quaternion_is_valid(rotation, tolerance=1e-3):
    """Return bool: exactly four finite components and |norm(q)-1| <= tolerance.

    TODO: Do not normalize an invalid quaternion and silently accept it.
    The supplied AuditedBuffer calls this hook on raw TF *before* insertion.
    None marks the untouched starter and is deliberately not a passing audit.
    """
    try:
        if len(rotation) != 4:
            return False

        if any(
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
            for value in rotation
        ):
            return False

        norm = math.hypot(*rotation)
        return abs(norm - 1.0) <= tolerance
    except (TypeError, ValueError, OverflowError):
        return False


def validate_observation(observation: Observation, lookup: Lookup):
    """Return the report dictionary; make one non-blocking lookup attempt.

    TODO:
    - Reject empty/absolute frame IDs, non-positive stamp_ns, non-finite points.
    - Call lookup(target_frame, source_frame, measurement_stamp_ns).
    - Preserve LookupFailure.status/detail; the supplied queue retries it.
    - Validate returned transform numbers and quaternion before applying it.
    - Apply the transform (geometry.apply_transform is supplied), then report OK.

    Never substitute latest (stamp=0), current time, or an identity transform.
    This function must return quickly: /tf and /clock share the executor.
    """
    def finite_vector(values, size):
        try:
            return (
                len(values) == size
                and all(
                    isinstance(value, Real)
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    for value in values
                )
            )
        except (TypeError, ValueError, OverflowError):
            return False

    # 1. Проверяем оба имени, не исправляя их автоматически.
    for name, frame in (
        ("source_frame", observation.source_frame),
        ("target_frame", observation.target_frame),
    ):
        if (
            not isinstance(frame, str)
            or not frame.strip()
            or frame.startswith("/")
        ):
            return report(
                observation,
                "INVALID_INPUT",
                f"{name} must be non-empty and must not start with '/'",
            )

    # 2. Timestamp — положительное целое число наносекунд.
    stamp = observation.stamp_ns
    if (
        not isinstance(stamp, Integral)
        or isinstance(stamp, bool)
        or stamp <= 0
    ):
        return report(
            observation,
            "INVALID_INPUT",
            "stamp_ns must be a positive integer",
        )

    # 3. Некорректное измерение отклоняем до обращения к TF.
    if not finite_vector(observation.point, 3):
        return report(
            observation,
            "INVALID_INPUT",
            "point must contain three finite numbers",
        )

    # 4. Ровно одна попытка, строго на исходное время измерения.
    try:
        transform = lookup(
            observation.target_frame,
            observation.source_frame,
            stamp,
        )
    except LookupFailure as error:
        return report(observation, error.status, error.detail)

    # 5. Доступный transform тоже может содержать некорректные данные.
    if not finite_vector(transform.translation, 3):
        return report(
            observation,
            "INVALID_INPUT",
            "transform translation must contain three finite numbers",
        )

    if not quaternion_is_valid(transform.rotation):
        return report(
            observation,
            "INVALID_INPUT",
            "transform rotation must be a finite unit quaternion",
        )

    # 6. Применяем p_target = R @ p_source + translation.
    point_target = apply_transform(transform, observation.point)

    # Даже конечные входы могут дать переполнение при вычислениях.
    if not finite_vector(point_target, 3):
        return report(
            observation,
            "INVALID_INPUT",
            "transformed point must contain three finite numbers",
        )

    return report(observation, "OK", point=point_target)
    #return report(observation, 'NOT_IMPLEMENTED', 'Complete validator.py policy TODOs')

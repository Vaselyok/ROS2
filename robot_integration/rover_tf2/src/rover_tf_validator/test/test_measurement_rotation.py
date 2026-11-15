import math

import pytest

from rover_tf_validator.contracts import Observation, RigidTransform
from rover_tf_validator.geometry import apply_transform
from rover_tf_validator.validator import validate_observation


def test_delayed_point_uses_measurement_rotation():
    stamp_ns = 12_500_000_000

    observation = Observation(
        sensor="lidar",
        source_frame="unit/lidar",
        target_frame="unit/odom",
        stamp_ns=stamp_ns,
        point=(2.0, 0.0, 0.0),
    )

    # При измерении датчик расположен в (1, 0, 0)
    # и повёрнут на +90° относительно odom.
    historical = RigidTransform(
        translation=(1.0, 0.0, 0.0),
        rotation=(
            0.0,
            0.0,
            math.sin(math.pi / 4),
            math.cos(math.pi / 4),
        ),
    )

    # К моменту обработки датчик повернулся обратно до 0°.
    latest = RigidTransform(
        translation=(1.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0, 1.0),
    )

    calls = []

    def lookup(target, source, stamp):
        calls.append((target, source, stamp))

        if stamp == stamp_ns:
            return historical
        if stamp == 0:
            return latest

        pytest.fail(f"Unexpected lookup timestamp: {stamp}")

    result = validate_observation(observation, lookup)

    assert result["status"] == "OK", result

    # Сначала проверяем геометрию: latest должен сломать этот assert.
    assert result["point"] == pytest.approx((1.0, 2.0, 0.0))

    assert result["stamp_ns"] == stamp_ns
    assert calls == [("unit/odom", "unit/lidar", stamp_ns)]

    # Проверяем, что выбранный пример действительно отличает latest.
    wrong_point = apply_transform(latest, observation.point)
    assert wrong_point == pytest.approx((3.0, 0.0, 0.0))
    assert math.dist(wrong_point, result["point"]) > 0.005
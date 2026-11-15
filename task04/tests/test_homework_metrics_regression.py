import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src/rover_sim_lab"),
)

from rover_sim_lab.homework_metrics import analyze_samples


def test_multiple_resets_and_duplicate_at_epoch_end():
    rows = [
        # Epoch 1.
        {"stamp": 0.0, "arrival": 10.0, "value": 90.0},
        {"stamp": 1.0, "arrival": 11.0, "value": 90.0},

        # Epoch 2.
        {"stamp": 0.0, "arrival": 12.0, "value": 80.0},
        {"stamp": 0.5, "arrival": 13.0, "value": 80.0},

        # Epoch 3: stamps already occurred in previous epochs.
        {"stamp": 0.0, "arrival": 14.0, "value": 0.1},
        {"stamp": 0.5, "arrival": 15.0, "value": 0.3},

        # Duplicate must not replace the preceding record.
        {"stamp": 0.5, "arrival": 16.0, "value": 99.0},
    ]
    original = deepcopy(rows)

    result = analyze_samples(rows)

    assert rows == original
    assert result["epochs"] == 3
    assert result["samples"] == 2
    assert result["sim_hz"] == pytest.approx(2.0)
    assert result["wall_hz"] == pytest.approx(1.0)
    assert result["gyro_mean"] == pytest.approx(0.2)
    assert result["gyro_std"] == pytest.approx(0.1)
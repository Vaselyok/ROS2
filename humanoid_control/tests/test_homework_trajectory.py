"""Formative homework checks: intentionally fail on the uncompleted starter.

Run independently of ROS: python3 -m unittest discover -s tests -p 'test_homework*.py' -v
"""
from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "homework/trajectory.py"
SPEC = importlib.util.spec_from_file_location("homework_trajectory", PATH)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class TrajectoryContractTests(unittest.TestCase):
    def setUp(self):
        self.names = ["elbow", "shoulder", "wrist"]
        self.limits = {"shoulder": [-1, 1], "wrist": [-2, 2], "elbow": [-1.5, 0.2]}
        self.pose = {"shoulder": 0.4, "wrist": -0.3, "elbow": -0.7}

    def test_requested_order_and_input_ownership(self):
        waypoints = [{"time": 1.2, "positions": self.pose}]
        before = deepcopy(waypoints)
        actual = policy.build_points(waypoints, self.names, self.limits)
        self.assertEqual(actual, [{"time_from_start": 1.2, "positions": [-0.7, 0.4, -0.3]}])
        self.assertEqual(waypoints, before)
        actual[0]["positions"][0] = 0.0
        self.assertEqual(waypoints, before)

    def test_equal_or_decreasing_times_are_rejected(self):
        for second in [0.0, 0.5, 1.0]:
            with self.subTest(second=second), self.assertRaises(ValueError):
                policy.build_points([{"time": 1, "positions": self.pose},
                                     {"time": second, "positions": self.pose}], self.names, self.limits)

    def test_limits_and_finite_positions(self):
        for invalid in [-1.6, float("nan"), float("inf")]:
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                policy.build_points([{"time": 1, "positions": {**self.pose, "elbow": invalid}}],
                                    self.names, self.limits)

    def test_missing_joint_is_rejected(self):
        with self.assertRaises(ValueError):
            policy.build_points([{"time": 1, "positions": {"shoulder": 0.4}}], self.names, self.limits)

    def test_feedback_error_is_measured_not_assumed(self):
        self.assertAlmostEqual(policy.tracking_error(self.names, [-0.7, .4, -.3], [-.6, .1, -.32]), .3)
        for desired, actual in [([0], [0]), ([0, 0, 0], [math.nan, 0, 0])]:
            with self.assertRaises(ValueError):
                policy.tracking_error(self.names, desired, actual)

    def test_hold_uses_measured_pose_and_duration(self):
        self.assertEqual(policy.hold_point(self.names, self.pose, self.limits, .25),
                         {"time_from_start": .25, "positions": [-.7, .4, -.3]})
        with self.assertRaises(ValueError):
            policy.hold_point(self.names, self.pose, self.limits, 0)


if __name__ == "__main__":
    unittest.main()

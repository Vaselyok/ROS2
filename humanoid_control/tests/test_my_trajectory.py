"""Counterexamples for joint ordering, inclusive limits and measured hold."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "homework/trajectory.py"
SPEC = importlib.util.spec_from_file_location("my_trajectory_policy", PATH)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class MyTrajectoryTests(unittest.TestCase):
    def setUp(self):
        self.names = ["elbow", "wrist"]
        self.limits = {"wrist": [-1, 1], "elbow": [-1.5, 0.2]}
        self.measured = {"wrist": 0.35, "elbow": -0.8}

    def test_hold_preserves_nonzero_measured_pose_in_requested_order(self):
        # Catches both "hold neutral" and iterating measured.values().
        before = deepcopy(self.measured)
        point = policy.hold_point(self.names, self.measured, self.limits, 0.25)
        self.assertEqual(point, {
            "time_from_start": 0.25, "positions": [-0.8, 0.35],
        })
        self.assertEqual(self.measured, before)
        point["positions"][0] = 0
        self.assertEqual(self.measured, before)

    def test_both_limit_boundaries_are_allowed(self):
        points = policy.build_points([
            {"time": 1, "positions": {"wrist": 1, "elbow": -1.5}},
            {"time": 2, "positions": {"wrist": -1, "elbow": 0.2}},
        ], self.names, self.limits)
        self.assertEqual([p["positions"] for p in points], [[-1.5, 1], [0.2, -1]])

    def test_bool_and_nonfinite_are_rejected(self):
        for bad in (True, False, float("nan"), float("inf"), -float("inf")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    policy.hold_point(self.names, self.measured, self.limits, bad)
                with self.assertRaises(ValueError):
                    policy.build_points([{"time": bad, "positions": self.measured}],
                                        self.names, self.limits)
                with self.assertRaises(ValueError):
                    policy.hold_point(self.names, {**self.measured, "wrist": bad},
                                      self.limits)
                with self.assertRaises(ValueError):
                    policy.tracking_error(self.names, [bad, 0], [0, 0])

    def test_missing_extra_names_and_invalid_limits(self):
        for pose in ({"elbow": -0.8}, {**self.measured, "extra": 0}):
            with self.subTest(pose=pose), self.assertRaises(ValueError):
                policy.hold_point(self.names, pose, self.limits)
        for names in ([], ["elbow", "elbow"], ["", "wrist"]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                policy.hold_point(names, self.measured, self.limits)
        for bounds in ({}, {"elbow": [1, -1], "wrist": [-1, 1]},
                       {"elbow": [-1.5, 0.2], "wrist": [False, 1]},
                       {"elbow": [-1.5, 0.2], "wrist": [-1, float("inf")]}):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                policy.hold_point(self.names, self.measured, bounds)

    def test_times_shapes_feedback_and_input_ownership(self):
        waypoints = [{"time": 1, "positions": self.measured}]
        before = deepcopy(waypoints)
        points = policy.build_points(waypoints, self.names, self.limits)
        points[0]["positions"][0] = 0
        self.assertEqual(waypoints, before)
        for second in (0, 0.5, 1):
            with self.subTest(second=second), self.assertRaises(ValueError):
                policy.build_points(waypoints + [{"time": second, "positions": self.measured}],
                                    self.names, self.limits)
        for invalid in ([], [{"time": 1, "positions": self.measured, "extra": 0}]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                policy.build_points(invalid, self.names, self.limits)
        with self.assertRaises(ValueError):
            policy.tracking_error(self.names, [0], [0])
        self.assertAlmostEqual(
            policy.tracking_error(self.names, [-0.8, 0.35], [-0.5, 0.3]), 0.3)


if __name__ == "__main__":
    unittest.main()

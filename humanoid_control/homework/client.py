#!/usr/bin/env python3
"""Supplied ROS transport adapter. Homework policy is in trajectory.py.

This adapter never substitutes a completed policy for the three homework TODOs.
It exposes action feedback/results and explicitly cancels then holds a fresh
measured pose. Infrastructure is kept fixed by the instructor grader.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="humanoid")
    parser.add_argument("--policy", type=Path, default=Path(__file__).with_name("trajectory.py"))
    parser.add_argument("--poses", type=Path, default=Path(__file__).with_name("mission.json"))
    parser.add_argument("--joint-order", choices=["model", "reverse"], default="model")
    parser.add_argument("--time-scale", type=float, default=1.0)
    parser.add_argument("--cancel-after", type=float)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--output", type=Path, default=Path("evidence/client.json"))
    args = parser.parse_args()
    if not math.isfinite(args.time_scale) or not .8 <= args.time_scale <= 1.5:
        parser.error("--time-scale must be finite in [0.8, 1.5]")
    if not math.isfinite(args.timeout) or not 5 <= args.timeout <= 300:
        parser.error("--timeout must be finite in [5, 300]")
    if args.cancel_after is not None and (not math.isfinite(args.cancel_after) or not .5 <= args.cancel_after <= 3):
        parser.error("--cancel-after must be finite in [0.5, 3] simulated seconds")
    namespace = args.namespace.strip("/")
    if not namespace or any(not p.replace("_", "a").isalnum() or not p[0].isalpha() for p in namespace.split("/")):
        parser.error("namespace must contain slash-separated ROS name segments")

    from control_lab.model import JOINT_NAMES, JOINT_LIMITS
    names = list(JOINT_NAMES)
    if args.joint_order == "reverse":
        names.reverse()
    spec = importlib.util.spec_from_file_location("submitted_trajectory", args.policy)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    poses = json.loads(args.poses.read_text())
    for pose in poses:
        pose["time"] *= args.time_scale
    # Deliberately preflight before connecting to a robot: an unfinished H1
    # reports its TODO instead of launching an empty trajectory.
    points = policy.build_points(poses, names, JOINT_LIMITS)

    import rclpy
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.signals import SignalHandlerOptions
    from action_msgs.msg import GoalStatus
    from control_msgs.action import FollowJointTrajectory
    from sensor_msgs.msg import JointState
    from trajectory_msgs.msg import JointTrajectoryPoint

    report = {"namespace": namespace, "joint_names": names, "events": [], "feedback": [], "passed": False}
    node = None
    active = None
    deadline = time.monotonic() + args.timeout
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = Node("homework_trajectory_client", namespace="/" + namespace,
                parameter_overrides=[Parameter("use_sim_time", value=True)])
    measured, arrival = {}, [None]
    feedback_errors = []
    action = ActionClient(node, FollowJointTrajectory,
                          "humanoid_controller/follow_joint_trajectory")

    def event(kind, **data):
        report["events"].append({"kind": kind, "sim": node.get_clock().now().nanoseconds / 1e9, **data})

    def on_joints(message):
        snapshot = dict(zip(message.name, message.position))
        if all(n in snapshot and math.isfinite(snapshot[n]) for n in names):
            measured.clear()
            measured.update({n: snapshot[n] for n in names})
            arrival[0] = time.monotonic()

    def on_feedback(message):
        try:
            feedback = message.feedback
            error = policy.tracking_error(list(feedback.joint_names),
                                          list(feedback.desired.positions), list(feedback.actual.positions))
            if not isinstance(error, (int, float)) or not math.isfinite(error) or error < 0:
                raise ValueError("tracking_error must return a finite nonnegative scalar")
            if len(report["feedback"]) < 2000:
                report["feedback"].append({"sim": node.get_clock().now().nanoseconds / 1e9,
                                           "max_error": error,
                                           "names": list(feedback.joint_names),
                                           "desired": list(feedback.desired.positions),
                                           "actual": list(feedback.actual.positions)})
        except Exception as error:
            feedback_errors.append(type(error).__name__ + ": " + str(error))

    node.create_subscription(JointState, "joint_states", on_joints, qos_profile_sensor_data)

    def spin_until(predicate, timeout=None):
        local_deadline = min(deadline, time.monotonic() + timeout) if timeout else deadline
        while not predicate():
            if time.monotonic() >= local_deadline:
                raise TimeoutError("steady watchdog expired while waiting for ROS state/result")
            rclpy.spin_once(node, timeout_sec=.02)
            if feedback_errors:
                raise ValueError(feedback_errors[0])

    def fresh_snapshot():
        spin_until(lambda: bool(measured) and arrival[0] is not None and time.monotonic() - arrival[0] <= .5)
        return dict(measured)

    def make_goal(planned):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = names
        # A zero header stamp requests start now, on the controller's clock.
        for point in planned:
            message = JointTrajectoryPoint()
            message.positions = [float(v) for v in point["positions"]]
            timestamp = float(point["time_from_start"])
            nanoseconds = round(timestamp * 1e9)
            message.time_from_start.sec, message.time_from_start.nanosec = divmod(nanoseconds, 1_000_000_000)
            goal.trajectory.points.append(message)
        return goal

    def send(planned, label):
        nonlocal active
        future = action.send_goal_async(make_goal(planned), feedback_callback=on_feedback)
        spin_until(future.done)
        active = future.result()
        if not active.accepted:
            raise RuntimeError(label + " goal was rejected")
        event("accepted", label=label, uuid=bytes(active.goal_id.uuid).hex())
        return active.get_result_async()

    def successful(result, label):
        if result.status != GoalStatus.STATUS_SUCCEEDED or result.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL:
            raise RuntimeError(f"{label}: status={result.status}, error={result.result.error_code}: {result.result.error_string}")

    def cancel_and_hold(result):
        nonlocal active
        event("cancel_requested")
        cancellation = active.cancel_goal_async()
        spin_until(cancellation.done, timeout=2.0)
        if not cancellation.result().goals_canceling:
            raise RuntimeError("server did not acknowledge cancellation")
        spin_until(result.done, timeout=2.0)
        if result.result().status != GoalStatus.STATUS_CANCELED:
            raise RuntimeError("expected CANCELED terminal result")
        event("canceled")
        active = None
        snapshot = fresh_snapshot()
        held = policy.hold_point(names, snapshot, JOINT_LIMITS, duration=.2)
        event("hold_requested", positions=snapshot)
        hold_result = send([held], "hold")
        spin_until(hold_result.done)
        successful(hold_result.result(), "hold")
        active = None
        settled = node.get_clock().now().nanoseconds / 1e9
        spin_until(lambda: node.get_clock().now().nanoseconds / 1e9 >= settled + .6)
        actual = fresh_snapshot()
        error = max(abs(actual[n] - snapshot[n]) for n in names)
        if error > .06:
            raise RuntimeError(f"measured hold error {error:.4f} rad exceeds 0.06 rad")
        event("hold_measured", max_error=error)
        return snapshot

    result = None
    try:
        spin_until(lambda: action.server_is_ready() and bool(measured) and node.get_clock().now().nanoseconds > 0)
        fresh_snapshot()
        initial_feedback = len(report["feedback"])
        started = node.get_clock().now().nanoseconds / 1e9
        result = send(points, "mission")
        while not result.done():
            spin_until(lambda: result.done() or (args.cancel_after is not None and
                       node.get_clock().now().nanoseconds / 1e9 - started >= args.cancel_after))
            if args.cancel_after is not None and not result.done():
                report["hold_target"] = cancel_and_hold(result)
                result = None
                break
        if result is not None:
            terminal = result.result()
            successful(terminal, "mission")
            active = None
            actual = fresh_snapshot()
            target = dict(zip(names, points[-1]["positions"]))
            error = max(abs(actual[n] - target[n]) for n in names)
            if error > .12:
                raise RuntimeError(f"final measured error {error:.4f} exceeds 0.12 rad")
            event("succeeded", max_error=error, error_code=terminal.result.error_code)
        if len(report["feedback"]) == initial_feedback:
            raise RuntimeError("no action feedback received")
        report["passed"] = True
    except KeyboardInterrupt:
        report["error"] = "interrupted by Ctrl+C"
        if active is not None and result is not None and not result.done():
            try:
                cancel_and_hold(result)
            except Exception as error:
                report["cleanup_error"] = str(error)
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        if active is not None and result is not None and not result.done():
            try:
                cancel_and_hold(result)
            except Exception as cleanup_error:
                report["cleanup_error"] = str(cleanup_error)
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        action.destroy()
        node.destroy_node()
        rclpy.try_shutdown()
    print(json.dumps({"passed": report["passed"], "error": report.get("error"), "output": str(args.output)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

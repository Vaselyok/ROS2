"""STUDENT FILE. Implement the search state machine. No ROS calls in this module.
Use raster() and drive_to(); never read simulator internals or web /state.
Return Outcome('absent') ONLY after covering the entire requested area.
Return Outcome('found', x, y) after measuring the rectangle centre.
"""
import math
from course_lab.world import Area, Sample, Decision, Outcome
from course_lab.navigation import drive_to, raster
from course_lab.probe import RectangleProbe

class Mission:
    def __init__(self, area: Area):
        self.area = area
        self.waypoints = raster(area)
        self.index = 0
        self.probe = None
        self.distance = 0.0
        self.last_pose = None
    
    def _is_inside_area(self, sample: Sample) -> bool:
        if hasattr(self.area, 'contains'):
            return self.area.contains(sample.x, sample.y)
        return (self.area.min_x <= sample.x <= self.area.max_x and
                self.area.min_y <= sample.y <= self.area.max_y)

    def step(self, sample: Sample) -> Decision:
        # TODO M1: follow raster; on green INSIDE area instantiate RectangleProbe.
        # Probe already measures boundaries. Delegate future samples to probe.step().
        # Basic feedback and all safety/failure policy are supplied by the adapter.
        # Starter is intentionally stopped, not a working submission.
        if self.last_pose is not None:
            self.distance += math.hypot(sample.x - self.last_pose[0], sample.y - self.last_pose[1])
        self.last_pose = (sample.x, sample.y)

        # 2. Если зонд активен, делегируем управление ему
        if self.probe is not None:
            decision = self.probe.step(sample)
            # Если у зонда distance нулевой или отсутствует, передаем наш общий distance через новый Decision
            dist = getattr(decision, 'distance', 0.0) or self.distance
            return Decision(
                v=decision.v,
                w=decision.w,
                distance=dist,
                outcome=decision.outcome
            )

        # 3. Обнаружение зеленого маркера внутри области поиска
        if sample.green and self._is_inside_area(sample):
            self.probe = RectangleProbe(self.area, sample)
            decision = self.probe.step(sample)
            dist = getattr(decision, 'distance', 0.0) or self.distance
            return Decision(
                v=decision.v,
                w=decision.w,
                distance=dist,
                outcome=decision.outcome
            )

        # 4. Если весь растровый маршрут завершен и подарок не найден
        if self.index >= len(self.waypoints):
            return Decision(v=0.0, w=0.0, distance=self.distance, outcome=Outcome('absent'))

        # 5. Движение к текущей путевой точке
        target = self.waypoints[self.index]
        v, w, reached = drive_to(sample, target)

        if reached:
            self.index += 1
            if self.index < len(self.waypoints):
                target = self.waypoints[self.index]
                v, w, _ = drive_to(sample, target)
            else:
                print(f"[MISSION] Returning absent! Total waypoints={len(self.waypoints)}, distance={self.distance}", flush=True)
                return Decision(v=0.0, w=0.0, distance=self.distance, outcome=Outcome('absent'))

        return Decision(v=v, w=w, distance=self.distance)

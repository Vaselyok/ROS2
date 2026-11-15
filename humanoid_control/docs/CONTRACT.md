# L05 Открытый контракт

Этот контракт относится к supplied fixed-base stand, standard controller и
трём функциям application client. Рабочая практика использует свой preset;
домашка использует `homework/controllers.yaml` и `homework/trajectory.py`.

## Модель и ROS interfaces

Модель имеет 18 revolute joints. Таз закреплён относительно мира. Все позиции
задаются в rad, скорости в rad/s, effort в N·m. Command interface — `position`;
state interfaces — `position`, `velocity`. Модель и simulator servo предоставлены.
Joint names не получают namespace prefix.

Порядок model joints, используемый в controller config:

```text
left_shoulder_pitch  left_shoulder_roll  left_elbow_pitch  left_wrist_roll
right_shoulder_pitch right_shoulder_roll right_elbow_pitch right_wrist_roll
left_hip_yaw left_hip_roll left_hip_pitch left_knee_pitch left_ankle_pitch
right_hip_yaw right_hip_roll right_hip_pitch right_knee_pitch right_ankle_pitch
```

Limits одинаковы для левой и правой стороны, включают обе границы:

| Сустав | Lower, rad | Upper, rad |
|---|---:|---:|
| shoulder_pitch | -1.4 | 1.4 |
| shoulder_roll | -1.0 | 1.0 |
| elbow_pitch | -1.5 | 0.2 |
| wrist_roll | -1.4 | 1.4 |
| hip_yaw | -0.6 | 0.6 |
| hip_roll | -0.5 | 0.5 |
| hip_pitch | -1.0 | 1.0 |
| knee_pitch | -0.1 | 1.5 |
| ankle_pitch | -0.7 | 0.7 |

Model velocity limit — 1.5 rad/s; effort limit — 10 N·m для рук, 30 N·m для ног.
Выданная mission уже ограничена по величине/скорости. Проверка генератора сложных
траекторий по acceleration/jerk в это задание не входит.

Default namespace — `humanoid`. В этом комплекте каждый сегмент namespace
начинается с латинской буквы и содержит только латинские буквы, цифры и `_`:
`[A-Za-z][A-Za-z0-9_]*`. Сегменты разделяются `/`, например `group5/demo`.
ROS paths ниже находятся внутри namespace:

| Path | Type / роль |
|---|---|
| `controller_manager` | controller manager services |
| `joint_states` | `sensor_msgs/msg/JointState`, измеренные joints |
| `humanoid_controller/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` |
| `humanoid_controller/controller_state` | `control_msgs/msg/JointTrajectoryControllerState` |
| `humanoid_controller/joint_trajectory` | `trajectory_msgs/msg/JointTrajectory`, учебный CLI |

`/clock` имеет один источник Gazebo; ROS consumers используют `use_sim_time=true`.
`/tf`, `/tf_static` глобальны в одном ROS domain. Для смены namespace сцена
полностью перезапускается; две сцены одновременно и recovery после reset
не входят в обязательный контракт.

## Controller configuration

Используйте wildcard ROS parameter roots `/**/controller_manager` и
`/**/humanoid_controller`, чтобы configuration не зависела от namespace.
Manager: `use_sim_time: true`, `update_rate: 100`, standard
`joint_state_broadcaster/JointStateBroadcaster` и
`joint_trajectory_controller/JointTrajectoryController` для `humanoid_controller`.

Controller: полный model joint order выше, `command_interfaces: [position]`,
`state_interfaces: [position, velocity]`, `allow_partial_joints_goal: false`.
Частоты: `action_monitor_rate: 20.0`, `state_publish_rate: 50.0`.
Default constraints: `goal_time: 1.0`, `stopped_velocity_tolerance: 0.1`, для
**каждого joint** `trajectory: 0.30`, `goal: 0.12`. Эти значения задают допуск
траектории/финальной позы; они не являются PID gains или гарантией реального
движения. Tolerances нельзя отключать значениями 0/-1 вместо заданного контракта.

Техническое описание: [JTC interfaces](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html)
и [JTC parameters](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/parameters.html).

## H1 build_points

```python
build_points(waypoints, joint_names, limits) -> list[dict]
```

`joint_names` — непустой list/tuple уникальных непустых string names. Это
**запрошенный порядок client**, который может отличаться от model order.
`limits` — mapping name → пара finite numeric lower/upper, lower ≤ upper.
Все запрошенные joints имеют limits; mapping может содержать другие model joints.

`waypoints` — непустой list/tuple словарей с ровно двумя ключами:

```python
{"time": 1.5, "positions": {"joint_a": 0.2, "joint_b": -0.4}}
```

`time` — simulated seconds относительно начала trajectory, finite numeric scalar,
строго больше нуля. Времена строго возрастают; равные/убывающие времена запрещены.
`positions` содержит **ровно** запрошенные names, без missing/extra joints.
Порядок ключей не имеет значения. Каждое значение finite и внутри inclusive limits.
`bool`, `NaN`, `inf` не являются допустимыми numeric values/times.

Верните новый list в порядке waypoints. Каждый элемент имеет ровно ключи:

```python
{"time_from_start": 1.5, "positions": [0.2, -0.4]}
```

Positions должны соответствовать `joint_names`. Не изменяйте входы и не возвращайте
вложенные списки, изменение которых меняет входной объект. Для перечисленных
ошибок names, limits, времени, комплектности, finite values или bounds поднимайте
`ValueError`. Проверка не требует поддержки произвольных иных типов аргументов.

## H2 tracking_error

```python
tracking_error(joint_names, desired, actual) -> float
```

`joint_names` задаёт непустой список уникальных names; `desired` и `actual` —
list/tuple finite numeric positions в этом же порядке, длины равны числу joints.
Верните `max(abs(desired[i] - actual[i]))`, в rad. Это reference/measurement
**одного feedback**, а не ошибка до последнего waypoint миссии. Пустые/повторные
names, несовпадающие длины, bool и nonfinite values вызывают `ValueError`.
Входы не изменяются.

## H3 hold_point

```python
hold_point(joint_names, measured, limits, duration=0.2) -> dict
```

`measured` — mapping всех запрошенных joints к свежим измеренным positions.
Names/limits/finite/bounds проверяются по правилам H1. `duration` — positive finite
simulated seconds. Верните **один** point с `time_from_start=duration` и measured
positions в запрошенном порядке. Не подставляйте neutral или окончательную pose
отменённой миссии. Входы не изменяются; invalid arguments вызывают `ValueError`.

## Mission и отмена

Миссия `homework/mission.json` задаёт 6 waypoints: neutral в 1 s, raised arm в 3 s,
три небольших положения wrist в 4/5/6 s и neutral в 8 s. Все legs и правая рука
остаются neutral. Adapter вызывает H1 и передаёт names/ordered points в action;
zero header stamp означает start now. Позы и transport adapter на приёмке fixed.

Обычный прогон должен принять goal, получать action feedback, завершиться с
`SUCCEEDED` и `error_code=SUCCESSFUL`, реально выполнить wave и вернуться к
neutral. Measured elbow должен достигнуть ≤ -0.70 rad, measured wrist — обоих
знаков ≥ +0.25 и ≤ -0.25 rad. Финальный maximum absolute joint position ≤ 0.12 rad.
Controller reference/measurement error во время supplied motion ≤ 0.30 rad.

При `--cancel-after 2` adapter отсчитывает 2 simulated seconds, запрашивает cancel,
проверяет acknowledgment и терминальный `CANCELED`, затем берёт fresh joint snapshot
и вызывает H3 с duration 0.2 s. Новый hold action должен завершиться успешно.
Cancel acknowledgment/terminal status ожидаются в пределах 2 steady seconds
каждый при advancing simulation clock. Fresh означает получение joint states
не более 0.5 steady seconds назад. После 0.4 simulated seconds на установление
измеренные positions отклоняются от snapshot не более чем на 0.06 rad в течение
как минимум 0.4 simulated seconds. В учебном default cancel arm уже отклонилась
от neutral: максимальное положение в snapshot должно быть ≥ 0.15 rad.

Общий steady watchdog — 90 s, разрешено увеличить до 300 s. Время траектории
не пересчитывается по steady clock. Визуальная остановка, отсутствие процесса
client или сообщение cancel response без измерений не завершают контракт.

## Опубликованные варианты проверки

- Namespace: default и другие корректные slash-separated names.
- Joint order: model, reversed или другая перестановка тех же names; позиции
  преобразуются в тот же порядок. Pure tests могут использовать небольшие наборы
  других имён/limits, чтобы выявлять hardcoding.
- Time scale mission: 0.8–1.5; normal run и cancel во время подъёма руки.
- Named poses: порядок ключей, inclusive limits, missing/extra joint; positive,
  duplicate/decreasing/nonfinite times; empty trajectory; duplicates in names.
- Feedback: разные конечные значения, dimension mismatch и nonfinite values.
- Hold: разные measured poses и positive durations, invalid bounds/duration.
- Ограниченные startup delays укладываются в общий watchdog; медленная машина
  не обязана достигать RTF 1.0. Pause/reset и два робота не являются скрытыми
  требованиями этого задания.

Результаты проверяются independently по ROS streams и завершению действий.
Сданные plots/JSON используются как evidence, не как источник authoritative PASS.

# HW05 Neutral → wave → neutral

Цель — выполнить небольшую траекторию руки через стандартный controller и
подтвердить движение измерениями. Ориентир — 2–3 часа после практики, без первой
загрузки Docker image; длительность требует пилота с учащимся.

## Что предоставлено

Учебный гуманоид имеет 18 суставов и закреплённый таз. Выданы Dockerfile/Compose,
модель и world, ROS package/launch, browser desktop, action transport, observer,
plotting, отдельная calculated PID model и public tests. Баланс и ходьба не
требуются.

`homework/mission.json` задаёт neutral, подъём левой руки, небольшое движение
запястья и возврат в neutral за 8 simulated seconds. Все десять суставов ног и
правая рука остаются в neutral.

`homework/client.py` — готовый адаптер `FollowJointTrajectory`: он ждёт сервер и
свежие joint states, отправляет goal, получает feedback/result, ограничивает
ожидания steady watchdog, при отмене запрашивает measured hold и завершает свои
ROS entities. Самостоятельная логика вызывается из `homework/trajectory.py`;
незавершённый starter останавливается на TODO.

В этой работе вы запускаете stack явными Compose и ROS командами, собираете и
подключаете workspace, объясняете reproducible start/stop sequence. Модель,
controller plugin и action transport писать заново не требуется.

## Самостоятельная часть

Изменяйте два файла:

| Файл | Работа |
|---|---|
| `homework/controllers.yaml` | C1–C4: стандартный controller, joints, interfaces и tolerances |
| `homework/trajectory.py` | H1–H3: порядок/валидация траектории, tracking error и измеренный hold |

Начните с [открытого контракта](CONTRACT.md): names, units, shapes, крайние случаи
и опубликованные варианты. PID tuning, изменение simulator servo и recovery
после reset в обязательную часть не входят.

1. Заполните C1–C4: `position` commands, `position`/`velocity` states, все 18 model
   joints по одному в contract order и явные tolerances.
2. Реализуйте `build_points`: из именованных поз получите positions в запрошенном
   порядке; проверьте комплектность, finite values, limits и время. Входы не меняйте.
3. Реализуйте `tracking_error`: maximum absolute error corresponding joints одного
   feedback; расстояние до последней позы миссии является другой величиной.
4. Реализуйте `hold_point`: используйте свежую измеренную позу после отмены.
   Возврат в neutral является отдельным движением.

На приёмке ваши **два** файла работают с выданными model, launch, mission,
transport adapter и observer. Изменение инфраструктуры не заменяет решение.
Свой дополнительный тест и эксперименты сохраняйте отдельно.

## Подготовка и pure checks

Из `task05/` в **host terminal**:

```bash
docker compose up -d --build --wait workspace
docker compose exec workspace bash
```

В открывшемся **container shell**:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --event-handlers console_direct+
source /workspace/install/setup.bash
python3 -m pytest -q tests/test_homework_trajectory.py
```

Первоначальный starter намеренно не проходит pure tests. После исправления
повторите их. Сборка и tests функций не заменяют измеренное движение.
В каждом дополнительном host terminal откройте container через
`docker compose exec workspace bash`, затем повторите:

```bash
source /opt/ros/jazzy/setup.bash
source /workspace/install/setup.bash
```

Все следующие ROS/Python команды выполняются в sourced **container shell**.
Host команды Compose выполняются снаружи, из `task05/`. Одновременно нужна одна
сцена; перед началом остановите другой launch в этом окружении.

## Запуск и измеренная миссия

В первом container shell:

```bash
ros2 launch control_lab sim.launch.py \
  mode:=homework \
  controller_config:=/workspace/homework/controllers.yaml \
  namespace:=humanoid gui:=false rviz:=false
```

Это headless режим. Для окон замените последние аргументы на
`gui:=true rviz:=true`; desktop по умолчанию находится по адресу
[localhost:6085](http://localhost:6085/vnc.html?autoconnect=true&resize=scale).
Оставьте launch работающим. Во втором shell проверьте states/resources:

```bash
ros2 control list_controllers -c /humanoid/controller_manager
ros2 control list_hardware_interfaces -c /humanoid/controller_manager
```

Ожидаются active `joint_state_broadcaster` и `humanoid_controller`, 18 claimed
position commands и position/velocity states. При ошибке читайте launch logs;
отправка нового goal не создаёт отсутствующий interface.

Подготовьте команды в двух shells. В третьем shell **начните запись до client**:

```bash
ros2 run control_lab lab measure --duration 30 --timeout 180 --output /workspace/evidence/mission-measured.json
```

Сразу после начала записи запустите во втором shell:

```bash
python3 /workspace/homework/client.py --timeout 180 --output /workspace/evidence/mission-client.json
```

После завершения записи:

```bash
ros2 run control_lab lab report --input /workspace/evidence/mission-measured.json
ros2 run control_lab lab plot --input /workspace/evidence/mission-measured.json --output /workspace/evidence/mission-measured.png --joints left_shoulder_roll left_elbow_pitch left_wrist_roll
```

Файлы `/workspace/evidence/` доступны в host `task05/evidence/`. Найдите measured
движение локтя/запястья, final neutral, feedback и result. Сравнивайте current
desired и actual в rad одного времени; конечный waypoint не является текущим
reference на протяжении всей trajectory.

`--duration` recorder и времена миссии используют simulated clock. `--timeout`
client/observer — wall/steady seconds. На медленной машине simulated time идёт
медленнее; при необходимости увеличьте timeout до **300 s**, сохранив реальные
point times. Для записи выбирайте окно, которое включает startup goal, всю
миссию и final hold. Запускайте client сразу после начала записи. Снижение RTF
само по себе не уменьшает оценку.

## Отмена и измеренный hold

На работающей сцене сначала начните новую запись в третьем shell:

```bash
ros2 run control_lab lab measure --duration 12 --timeout 180 --output /workspace/evidence/cancel-measured.json
```

Затем во втором shell:

```bash
python3 /workspace/homework/client.py --cancel-after 2 --timeout 180 --output /workspace/evidence/cancel-client.json
```

После записи:

```bash
ros2 run control_lab lab report --input /workspace/evidence/cancel-measured.json
ros2 run control_lab lab plot --input /workspace/evidence/cancel-measured.json --output /workspace/evidence/cancel-measured.png --joints left_shoulder_roll left_elbow_pitch left_wrist_roll
```

Наблюдайте acknowledgment, terminal `CANCELED`, новый hold goal и measured stop.
Adapter берёт fresh snapshot после подтверждённой отмены; H3 строит hold из
него. После 0.4 simulated s на установление отклонение от snapshot должно быть
≤ 0.06 rad как минимум 0.4 simulated s. Cancel acknowledgment и terminal status
ожидаются в пределах 2 steady s каждый при работающей симуляции; увеличение
общего watchdog не меняет эти опубликованные условия.

Ctrl+C в client также запрашивает cancel/hold, если goal ещё выполняется.
Проверьте этот сценарий самостоятельно. Для возврата в neutral запустите обычную
миссию. Прекращение terminal output и неподвижный screenshot не доказывают hold.

## Namespace и порядок joints

Остановите первый launch через Ctrl+C, оставив Compose environment запущенным.
В первом sourced shell запустите новую сцену:

```bash
ros2 launch control_lab sim.launch.py \
  mode:=homework \
  controller_config:=/workspace/homework/controllers.yaml \
  namespace:=group5/demo gui:=false rviz:=false
```

В третьем shell начните запись, затем во втором отправьте variant:

```bash
ros2 run control_lab lab measure --namespace group5/demo --duration 30 --timeout 180 --output /workspace/evidence/variant-measured.json
```

```bash
python3 /workspace/homework/client.py --namespace group5/demo --joint-order reverse --time-scale 1.2 --timeout 180 --output /workspace/evidence/variant-client.json
```

После записи:

```bash
ros2 run control_lab lab report --input /workspace/evidence/variant-measured.json
ros2 run control_lab lab plot --input /workspace/evidence/variant-measured.json --output /workspace/evidence/variant-measured.png --joints left_shoulder_roll left_elbow_pitch left_wrist_roll
```

Правильная перестановка names и positions сохраняет последовательность поз;
time scale меняет длительность/скорость. При inspection используйте manager
`/group5/demo/controller_manager`. Все namespace-dependent команды должны
обращаться к той же сцене. Две одновременные сцены не требуются.

## Evidence и собственный тест

Сохраните compact JSON и commanded/measured plots обычной миссии и отмены,
variant и короткую [diagnosis](diagnosis.template.yaml). Укажите start/stop
команды, image/package versions, namespace, time scale, число feedback, result,
tracking error и hold deviation. Объясните различие action result и физических
измерений.

Добавьте собственный тест, который ловит конкретную ошибку: например, unordered
named pose, inclusive limit, повторное время или подстановка final target вместо
measured hold. Сохраните его рядом с public tests и запустите явно:

```bash
python3 -m pytest -q tests/test_homework_trajectory.py tests/test_my_trajectory.py
```

Имя `tests/test_my_trajectory.py` — пример для вашего дополнительного файла.
Для versions в sourced container shell можно использовать:

```bash
gz sim --versions
dpkg-query -W ros-jazzy-ros2-control ros-jazzy-ros2-controllers ros-jazzy-gz-ros2-control
```

Версии фиксируйте до остановки container либо сохраните вывод в evidence.

## Завершение окружения

Сначала дождитесь client result или его cancel/hold. Нажмите Ctrl+C в terminal,
где работает launch, дождитесь его завершения и выполните `exit`. В **host
terminal** из `task05/`:

```bash
docker compose down --timeout 10
```

Используйте interactive shell для launch: non-PTY background execution имеет
другие правила сигналов. При зависшем launch завершите этот Compose project
командой `down`. Для доказательства cleanup сохраните вывод `docker compose ps`
после остановки и команды воспроизведения в diagnosis.

## Оценивание

| Компонент | Баллы |
|---|---:|
| Сборка и configuration contract | 15 |
| Измеренная миссия, feedback/result, tracking | 40 |
| Валидация, отмена/hold и опубликованные варианты | 30 |
| Ограниченное ожидание, завершение и воспроизводимость | 10 |
| Собственный тест и объяснение | 5 |

Преподаватель проверяет exact commit в отдельной trusted среде. До **85 баллов**
подтверждает автоматическая проверка; ещё **15** назначаются после просмотра
evidence: объяснение варианта 5, воспроизводимость/cleanup 5, собственный
counterexample/diagnosis 5. Студентский `passed: true` не определяет оценку:
joint states, controller state и action feedback/status наблюдаются независимо.

## Сдача

Сохраните два завершённых файла, свой тест, `docs/diagnosis.yaml` и небольшие
evidence в `task05/` личного приватного репозитория. Evidence исключён из Git;
выбранные отчёты и графики добавьте явно, например:

```bash
git add -f evidence/mission-measured.json evidence/mission-measured.png
git diff --cached --stat
```

Не добавляйте build/install/log, Docker layers или большие видео. Сделайте commit
и push до объявленного дедлайна. Преподаватель фиксирует commit в `master` и
назначает оценку.

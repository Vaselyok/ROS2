# ROS 2: интеграция робота, TF2 и воспроизводимая симуляция

**2026 · ROS 2 Jazzy · Python · QoS · TF2 · URDF/Xacro · Gazebo Harmonic · Docker**

Проект охватывает диагностику ROS graph, исправление модели и преобразований
сенсорных измерений, а также настройку воспроизводимой симуляции. В результате
восстановлено взаимодействие узлов, измерения преобразуются на момент их
получения, а команды и сенсоры Gazebo доступны через ROS 2.

Работа разделена на три самостоятельных стенда. Warehouse graph, модель
ровера для TF2 и двухколёсная платформа Gazebo проверяют разные части
интеграции; у каждого стенда свой workspace, Compose и сценарий запуска.

## Что сделано

### ROS graph, launch и QoS

- Исправлена установка YAML-конфигурации в `share/warehouse_bringup/config`
  и привязка параметров к имени `range_sensor`. Узлы получают настройки
  из установленного пакета после сборки.
- Согласованы publisher/subscriber QoS: дальномер использует
  `BEST_EFFORT / VOLATILE`, состояние безопасности —
  `RELIABLE / TRANSIENT_LOCAL`. Панель, запускаемая позже остальных узлов,
  получает сохранённое состояние безопасности.
- Абсолютное имя `/safety/state` заменено относительным. Два экземпляра
  стека работают в `/robot_1` и `/robot_2` без смешивания сообщений.
- Добавлена недостающая зависимость `geometry_msgs`; проверены сборка,
  запуск установленных пакетов и завершение процессов.

Код: [launch и параметры](graph_diagnostics/src/warehouse_bringup),
[профили QoS](graph_diagnostics/src/warehouse_nodes/warehouse_nodes/qos.py).
Причины неисправностей и результаты проверок:
[diagnosis.yaml](graph_diagnostics/diagnosis.yaml).

### Модель ровера и TF2 на время измерения

- Исправлены положение LiDAR, ориентация `camera_optical_frame`,
  `frame_id` наблюдений IMU и `child_frame_id` odometry.
- Реализован validator: проверяются frame IDs, положительный timestamp,
  конечность координат и единичная норма кватерниона.
- Преобразование запрашивается по исходному `stamp_ns` измерения. Статусы
  ошибок TF сохраняются, а очередь повторных попыток не теряет timestamp.
- Добавлен регрессионный тест с поворотом между временем измерения и
  временем доставки: правильная точка `(1, 2, 0)` отличается от результата
  по последней позе `(3, 0, 0)` на 2,83 м. Тест обнаруживает подмену времени
  измерения на `latest`.
- Проверен запуск с другим namespace и префиксом фреймов `testbot/`.

Код: [геометрия креплений](rover_tf2/src/rover_description/config/homework_mounts.yaml),
[validator](rover_tf2/src/rover_tf_validator/rover_tf_validator/validator.py),
[регрессионный тест](rover_tf2/src/rover_tf_validator/test/test_measurement_rotation.py).

### Gazebo–ROS bridges и семантика времени

- Настроены пять прикладных каналов: `cmd_vel` из ROS в Gazebo;
  LiDAR, IMU, изображение и CameraInfo из Gazebo в ROS.
- Включены системы `Sensors` и `Imu`; заданы частоты scan/camera 10 Гц,
  IMU 100 Гц, odometry 50 Гц и разрешение камеры 160 × 120.
- Реализован анализатор измерений: частоты по sim и wall time, среднее
  и стандартное отклонение гироскопа. При скачке времени назад начинается
  новая эпоха; повторяющиеся timestamps учитываются один раз.
- Выполнены движение вперёд, поворот, остановка, pause/step/reset,
  повторные запуски с `seed=42`, сравнение RTF 1,0/0,5 и трёх профилей
  шума IMU: `ideal`, `white`, `biased`.
- Добавлен регрессионный тест на несколько reset и дубликаты timestamps.

Код: [bridges](rover_simulation/homework/wiring.yaml),
[сенсорные системы](rover_simulation/homework/systems.yaml),
[анализатор](rover_simulation/src/rover_sim_lab/rover_sim_lab/homework_metrics.py),
[регрессионный тест](rover_simulation/tests/test_homework_metrics_regression.py).

## Результаты

| Проверка | Полученный результат | Отчёт |
| --- | --- | --- |
| ROS graph одного робота | 6 узлов, параметры из YAML, совместимый QoS, поздняя панель получает safety state | [Диагностика](graph_diagnostics/diagnosis.yaml) |
| Изоляция двух роботов | 12 узлов в двух namespaces, сообщения соответствуют своему `source_namespace` | [Диагностика](graph_diagnostics/diagnosis.yaml) |
| TF2, `rover/` | `passed=true`, 300 успешных наблюдений, максимальная геометрическая ошибка менее 2,6 × 10⁻¹³ м при допуске 0,005 м | [Приёмка](rover_tf2/reports/acceptance.json) |
| TF2, `testbot/` | `passed=true`, 300 успешных наблюдений, 100 сравнений odometry | [Другой namespace](rover_tf2/reports/testbot.json) |
| Gazebo, основной сценарий | 40/40 проверок; движение 0,406 м, поворот 0,688 рад, дрейф после stop около 3,7 × 10⁻⁶ м | [Приёмка](rover_simulation/reports/homework-check.json) |
| Повторяемость, `seed=42` | Оба запуска проходят 40/40 проверок; разница перемещения 0,0022 м, угла 0,00315 рад | [Запуск 1](rover_simulation/reports/repeat-1.json), [запуск 2](rover_simulation/reports/repeat-2.json) |
| Pause → 1000 steps → reset | Время на pause неизменно; 1000 шагов дают 1 с симуляции; reset возвращает время и iterations в 0 | [Фазы сценария](rover_simulation/reports/homework-check.json) |

При снижении measured RTF с 0,984 до 0,499 частота LiDAR по simulated time
остаётся 10 Гц, а по wall time меняется примерно с 9,84 до 5,00 Гц.
За 10 секунд симуляции в обоих опытах получено по 100 scan-сообщений:
[RTF 1,0](rover_simulation/reports/rtf-1.json),
[RTF 0,5](rover_simulation/reports/rtf-half.json).

У неподвижного робота профиль `white` дал среднее gyro z около нуля и
σ = 0,01984 рад/с, а `biased` — среднее 0,08008 рад/с при σ = 0,01982 рад/с.
Сводки: [ideal](rover_simulation/reports/noise-ideal.json),
[white](rover_simulation/reports/noise-white.json),
[biased](rover_simulation/reports/noise-biased.json).

Числа приведены по сохранённым отчётам проведённых экспериментов.
В `reports/` находятся компактные копии результатов: TF2-отчёты сохранены
целиком, из Gazebo-отчётов исключены массивы исходных сообщений `streams`.
Поле `_excerpt` содержит имя и SHA-256 исходного файла из локального
`evidence/`. Подробная история исправлений находится в `diagnosis.yaml`
каждого стенда и может описывать другие прогоны.

## Как запустить

Нужны Docker и Compose v2; команды выполняются в Bash на Linux или в
Ubuntu/WSL. Внутри контейнеров используется ROS 2 Jazzy, в симуляции —
Gazebo Harmonic. Каждый стенд запускается из своей папки.

Например, из корня репозитория для симуляции:

```bash
cd robot_integration/rover_simulation
cp .env.example .env   # только при первом запуске
```

На Linux/WSL перед `up` задайте в `.env` значения `LOCAL_UID` и `LOCAL_GID`
из `id -u` и `id -g`. Затем:

```bash
./course up
./course doctor
./course build
./course test
./course check --mode homework --seed 42 --output evidence/homework-check.json
```

Этот `check` сам поднимает свежую сцену без графического интерфейса и
завершает её. Для просмотра используйте `./course homework`, а во втором
терминале — `./course desktop`.

| Стенд | Запуск, проверка и диагностика |
| --- | --- |
| ROS graph и QoS | [graph_diagnostics/README.md](graph_diagnostics/README.md) |
| TF2 и модель ровера | [rover_tf2/README.md](rover_tf2/README.md) |
| Симуляция, RTF и шумы | [rover_simulation/README.md](rover_simulation/README.md) |

Завершение: остановите интерактивный launch через Ctrl+C и выполните
`./course down` из папки соответствующего стенда. Опыты одного стенда
запускаются по очереди. После reset следующий опыт начинается в свежей сцене;
восстановление TF2-listeners без перезапуска не проверялось. Повторяемость
оценивается по метрикам и допускам; побитовое совпадение запусков не заявляется.

## Происхождение

Объединены прежние `task02`, `task03` и `task04` курса SHAD ROS 2. Базовые
модели, transport и инфраструктура стендов предоставлены курсом; выполненные
исправления, прикладная логика и эксперименты перечислены выше. Исходные
условия и контракты сохранены в `docs/` соответствующих стендов.

# Модель ровера и преобразования TF2 на время измерения

Часть проекта [«Интеграция робота, TF2 и воспроизводимая симуляция»](../README.md).

Исправлены крепление LiDAR, optical frame камеры, frame ID IMU и child frame
odometry. Реализована проверка входных данных и преобразование наблюдения
по исходному timestamp. Регрессионный тест обнаруживает использование
последней доступной позы вместо позы на время измерения.

Сохранённая [приёмка](reports/acceptance.json) проходит: `passed=true`,
300 успешных наблюдений трёх сенсоров, 100 сравнений odometry,
геометрическая ошибка менее 2,6 × 10⁻¹³ м при допуске 0,005 м.
[Вариант `testbot/`](reports/testbot.json) также проходит.
Подробности исправлений: [diagnosis.yaml](diagnosis.yaml).

## Запуск и проверка

Из этой папки в Bash на Linux/WSL:

```bash
cp .env.example .env   # только при первом запуске
```

В `.env` задайте свои `LOCAL_UID` / `LOCAL_GID` из `id -u` / `id -g`.
Подготовьте окружение и оставьте сцену работающей:

```bash
./course up
./course doctor
./course build
./course test
./course run homework rviz:=false
```

Во втором терминале из этой же папки:

```bash
./course check
```

Здесь `check` наблюдает уже работающую сцену. Отчёт записывается в
`evidence/acceptance.json`. Для RViz запустите сцену с `rviz:=true` и
откройте [рабочий стол](http://localhost:6083/vnc.html?autoconnect=true&resize=scale).

Для проверки другого namespace сначала остановите старую сцену через
Ctrl+C, затем в первом терминале:

```bash
./course run homework namespace:=testbot frame_prefix:=testbot/ rviz:=false
```

Во втором:

```bash
./course exec ros2 run rover_tf_validator acceptance \
  --frame-prefix testbot/ --output /workspace/evidence/testbot.json \
  --ros-args -r __ns:=/testbot -p use_sim_time:=true
```

## Основные файлы

- [Крепления и ориентации сенсоров](src/rover_description/config/homework_mounts.yaml).
- [Конфигурация frame IDs](src/rover_bringup/config/homework.yaml).
- [Валидация и преобразование наблюдений](src/rover_tf_validator/rover_tf_validator/validator.py).
- [Тест задержанного измерения с поворотом](src/rover_tf_validator/test/test_measurement_rotation.py).
- [Исходный контракт](docs/Homework_L03.md).

После reset ROS clock перезапускайте validator/listeners перед следующим
опытом. Завершение: Ctrl+C в терминале launch, затем `./course down`.

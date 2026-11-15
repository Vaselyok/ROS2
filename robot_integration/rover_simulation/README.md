# Воспроизводимая симуляция ровера в Gazebo

Часть проекта [«Интеграция робота, TF2 и воспроизводимая симуляция»](../README.md).

Настроены пять Gazebo–ROS bridges и сенсорные системы двухколёсной платформы.
Реализован анализатор частот по sim/wall time и статистики гироскопа с
обработкой reset и повторяющихся timestamps.

[Основной сценарий](reports/homework-check.json) проходит 40/40 проверок:
команды вызывают движение и поворот, сенсоры публикуют согласованные данные,
после stop платформа останавливается. Проверены pause/step/reset, повторные
запуски с одинаковым seed, изменение RTF и профили шума IMU.

## Запуск и приёмка

Из этой папки в Bash на Linux/WSL:

```bash
cp .env.example .env   # только при первом запуске
```

Задайте в `.env` свои `LOCAL_UID` / `LOCAL_GID` из `id -u` / `id -g`.
Затем:

```bash
./course up
./course doctor
./course build
./course test
./course check --mode homework --seed 42 --output evidence/homework-check.json
```

`check` самостоятельно создаёт свежую сцену без окон, выполняет проверки
и останавливает её. Для просмотра выполните `./course homework`, а во втором
терминале из этой же папки — `./course desktop`.

Повторные независимые запуски:

```bash
./course check --mode homework --seed 42 --output evidence/repeat-1.json
./course check --mode homework --seed 42 --output evidence/repeat-2.json
```

## Опыты со временем и шумом

В первом терминале оставьте работающей сцену с target RTF = 0,5:

```bash
./course homework headless target_rtf:=0.5 seed:=42
```

Во втором терминале из этой же папки:

```bash
./course observe --profile ideal --seed 42 --target-rtf 0.5 \
  --duration 10 --output evidence/rtf-half.json
```

Для сравнения повторите опыт в свежей сцене с `target_rtf:=1.0` и
`--target-rtf 1.0`. `duration` задаётся в секундах симуляции, timeout —
в реальных секундах.

Для измерения смещения гироскопа запустите свежую неподвижную сцену:

```bash
./course homework headless profile:=biased seed:=42
```

Во втором терминале:

```bash
./course observe --profile biased --seed 42 --target-rtf 1.0 \
  --duration 20 --output evidence/noise-biased.json
```

Повторите с `ideal` и `white`, меняя профиль и имя отчёта. Перед каждым
следующим опытом остановите предыдущий launch через Ctrl+C.

## Код и результаты

| Материал | Ссылка |
| --- | --- |
| Типы сообщений и направления пяти bridges | [wiring.yaml](homework/wiring.yaml) |
| Сенсорные системы, частоты и камера | [systems.yaml](homework/systems.yaml) |
| Анализатор измерений | [homework_metrics.py](src/rover_sim_lab/rover_sim_lab/homework_metrics.py) |
| Регрессия на reset и дубликаты | [test_homework_metrics_regression.py](tests/test_homework_metrics_regression.py) |
| Исходные интерфейсы и допуски | [CONTRACT.md](docs/CONTRACT.md) |
| Выводы по времени, шуму и повторяемости | [diagnosis.yaml](diagnosis.yaml) |
| Сохранённые результаты без массивов исходных сообщений | [reports/](reports) |

Компактные отчёты сохраняют исходные checks, параметры, метрики и фазы
сценария. Поле `_excerpt` указывает имя и SHA-256 полного локального отчёта.
Для следующего опыта после reset используется новая сцена. Завершение:
остановите launch и выполните `./course down`.

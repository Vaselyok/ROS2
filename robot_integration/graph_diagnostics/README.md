# Диагностика ROS graph, launch и QoS

Часть проекта [«Интеграция робота, TF2 и воспроизводимая симуляция»](../README.md).

Восстановлен warehouse stack из шести ROS 2 узлов. Исправлены установка
конфигурации, имена параметров, QoS, относительные topic names и зависимости.
Работают запуск одного робота, позднее подключение панели и два экземпляра
без смешивания сообщений. Наблюдения до и после исправлений сохранены в
[diagnosis.yaml](diagnosis.yaml).

| Неисправность | Исправление и результат |
| --- | --- |
| YAML не попадал в установленный пакет | Конфигурация добавлена в `setup.py`; launch находит файл в `share/warehouse_bringup/config` |
| Параметры адресованы другому имени узла | Исправлен YAML selector; `range_sensor` публикует с заданной частотой 4 Гц |
| Несовместимые QoS | Подписчик дальномера использует sensor QoS; safety state сохраняется через `TRANSIENT_LOCAL` |
| Глобальный `/safety/state` | Относительное имя изолирует данные в `/robot_1` и `/robot_2` |
| Не объявлен `geometry_msgs` | Зависимость добавлена в manifest для чистого dependency/build pipeline |

## Запуск

Из этой папки в Bash на Linux/WSL:

```bash
cp .env.example .env   # только при первом запуске
```

Укажите в `.env` свои `LOCAL_UID` / `LOCAL_GID` из `id -u` / `id -g`, затем:

```bash
./course up
./course doctor
./course build
./course test
./course launch warehouse_bringup warehouse.launch.py namespace:=robot_1
```

Пока launch работает, во втором терминале из этой же папки:

```bash
./course exec ros2 node list
./course exec ros2 param get /robot_1/range_sensor publish_rate_hz
./course exec ros2 topic info /robot_1/range/readings --verbose
./course exec ros2 topic info /robot_1/safety/state --verbose
```

Ожидаются шесть узлов в `/robot_1`, значение `4.0` и совместимые QoS
publisher/subscriber. Сообщение `PANEL_READY` в логе подтверждает получение
состояния панелью после её отложенного старта.

Остановите первый launch через Ctrl+C и запустите два экземпляра:

```bash
./course launch warehouse_bringup two_robots.launch.py
```

В graph должны появиться 12 узлов в `/robot_1` и `/robot_2`.
Полная проверка изоляции с разными `readings_m` описана в
[контракте стенда](docs/Homework_L02.md).

После остановки launch выполните `./course down`.

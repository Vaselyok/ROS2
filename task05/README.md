# HW05 Управление суставами через ros2_control

Самостоятельная работа: завершите controller configuration и три функции для
траектории, tracking error и измеренного удержания. Выданный стенд имеет 18
суставов и закреплённый таз. Модель, ROS package/launch, Docker environment,
action transport, измерения и public tests предоставлены.

- [Условие и команды](docs/Homework_L05.md).
- [Открытый контракт](docs/CONTRACT.md).
- [Шаблон объяснения](docs/diagnosis.template.yaml).

В HW05 вы самостоятельно выполняете Compose, сборку, sourcing и ROS команды.
Изменяемые файлы задания — только `homework/controllers.yaml` и
`homework/trajectory.py`. Сдача дополнительно включает свой тест и evidence.

## Подготовка окружения

Нужны работающий Docker и Compose v2. На Linux/WSL перед первым запуском узнайте
UID/GID владельца рабочей папки в **host terminal**:

```bash
id -u
id -g
```

Compose по умолчанию использует `1000:1000`. Если ваши значения отличаются,
вручную создайте `task05/.env` или добавьте/обновите две строки в существующем
файле. Пример ниже: замените числа фактическим выводом `id -u` и `id -g`.
Не перезаписывайте существующий `.env` целиком.

```dotenv
LOCAL_UID=1000
LOCAL_GID=1000
```

Это позволяет container записывать build и evidence в вашу рабочую папку.
`.env` исключён из Git; сдавать локальные UID/GID не нужно.

В **host terminal** из папки `task05/`:

```bash
docker compose up -d --build --wait workspace
docker compose exec workspace bash
```

Теперь вы в **container shell**, рабочая папка — `/workspace`:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --event-handlers console_direct+
source /workspace/install/setup.bash
python3 -m pytest -q tests/test_homework_trajectory.py
```

Исходный starter намеренно не проходит homework tests. Сначала завершите два
файла по [контракту](docs/CONTRACT.md). Сборка не доказывает выполнение миссии.
Первая загрузка и сборка image могут занять время: закончите их заранее.

## Запуск после выполнения задания

В первом sourced **container shell**:

```bash
ros2 launch control_lab sim.launch.py \
  mode:=homework \
  controller_config:=/workspace/homework/controllers.yaml \
  namespace:=humanoid gui:=false rviz:=false
```

Оставьте launch работать. Откройте второй host terminal из `task05/` и выполните
`docker compose exec workspace bash`. В каждом новом container shell повторите
оба `source` из подготовки, затем проверьте controllers:

```bash
ros2 control list_controllers -c /humanoid/controller_manager
ros2 control list_hardware_interfaces -c /humanoid/controller_manager
```

Начните запись в третьем sourced shell, затем сразу запустите client во втором:

```bash
ros2 run control_lab lab measure --duration 30 --timeout 180 --output /workspace/evidence/mission-measured.json
```

```bash
python3 /workspace/homework/client.py --timeout 180 --output /workspace/evidence/mission-client.json
```

Полный workflow, графики, отмена и namespace variant описаны в
[условии](docs/Homework_L05.md). Длительности движения и записи задаются в
simulated seconds; `--timeout` ограничивает ожидание в wall seconds. При медленном
симуляторе можно увеличить timeout до 300 s. Смена часов не меняет траекторию.

Для окон перезапустите ту же сцену с `gui:=true rviz:=true`. Рабочий стол по
умолчанию доступен по адресу [localhost:6085](http://localhost:6085/vnc.html?autoconnect=true&resize=scale).
Одновременно запускайте одну сцену в этом окружении.

## Завершение

Сначала дождитесь client result или его cancel/hold. Остановите launch через
Ctrl+C в терминале, где он работает, затем выполните `exit`. В **host terminal**
из `task05/`:

```bash
docker compose down --timeout 10
```

Interactive `docker compose exec` передаёт Ctrl+C процессу в container. При
зависшем launch завершите этот Compose project командой `down`; остановка
терминального вывода сама по себе не доказывает cancel или физическое удержание.

Сдаётся commit в личном приватном репозитории. Дедлайн объявляется преподавателем.

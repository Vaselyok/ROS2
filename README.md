# SHAD ROS 2 — домашние задания 2026

Этот комплект содержит заготовки домашних заданий. Выполняйте и сдавайте работу
в выданном вам личном приватном репозитории. Каждое задание находится в отдельной
папке `taskNN/`; условие и команды доступны по ссылкам ниже.

| Задание | Тема |
| --- | --- |
| [Task01](task01/README.md) | ROS 2 graph, interfaces and actions · Hidden Gift 2.0 |
| [Task02](task02/README.md) | Workspaces, launch, parameters, QoS and discovery · Black-box graph rescue |
| [Task03](task03/docs/Homework_L03.md) | Time, TF2, URDF/Xacro and robot state · Repair the rover |
| [Task04](task04/docs/Homework_L04.md) | Modern Gazebo and simulation semantics · Reproducible rover bringup |
| [Task05](task05/docs/Homework_L05.md) | ros2_control · Neutral → wave → neutral, tracking error and measured hold |

## Где работать

- Личный приватный репозиторий используется для домашних заданий и сдачи.
- Все файлы решения храните внутри папки соответствующего задания: `task01/`,
  `task02/` и так далее.

Материалы практики находятся отдельно в публичном
[SHAD-ROS2/tasks](https://github.com/SHAD-ROS2/tasks).

## Подготовка окружения

Среда курса запускается в Docker. Нужны Git, запущенный Docker и Compose v2
(команда `docker compose`). Рекомендуется 16 ГБ RAM и 30 ГБ свободного места.

- macOS: установите и запустите
  [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/).
- Windows: установите
  [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)
  с WSL 2. Команды курса выполняйте в терминале Ubuntu/WSL, а репозиторий
  клонируйте в домашний каталог WSL.
- Ubuntu 24.04: установите
  [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) и
  [Compose plugin](https://docs.docker.com/compose/install/linux/). Настройте
  запуск Docker без `sudo` по
  [официальной post-install инструкции](https://docs.docker.com/engine/install/linux-postinstall/).

Проверьте установку:

```bash
git --version
docker version
docker compose version
docker run --rm hello-world
```

Примите приглашение в личный приватный репозиторий на GitHub и скопируйте его
HTTPS-ссылку из меню **Code**. Клонируйте этот репозиторий и откройте его папку.
Например, заменив `XXXXX` на номер своего репозитория:

```bash
git clone https://github.com/SHAD-ROS2/ros2-XXXXX.git
cd ros2-XXXXX
git remote -v
```

Проверьте, что `origin` указывает на ваш личный репозиторий. Затем откройте
`taskNN/README.md` и выполните подготовку окружения конкретного задания.
На Linux/WSL задайте в его `.env` значения `LOCAL_UID` и `LOCAL_GID` из
`id -u` и `id -g`, как описано в инструкции задания.

## Сдача

Сохраните решение в папке задания. Следующие команды выполняются из корня
личного репозитория; первая команда возвращает туда из любой папки задания:

```bash
cd "$(git rev-parse --show-toplevel)"
git switch master
git remote -v
git status --short
git add taskNN
git diff --cached --stat
git commit -m "Complete taskNN"
git push origin master
```

Замените `taskNN` на номер задания, например `task01` или `task02`.
Перед commit проверьте, что staged files содержат решение, собственные тесты,
diagnosis и выбранные evidence. Если `evidence/` исключён из Git, добавьте
нужные отчёты явно, например `git add -f task03/evidence/acceptance.json`.
Не добавляйте `build/`, `install/`, `log/` и локальную `.env`.

**В дедлайн будет взят последний коммит в `master` для проверки.**

## Если что-то не работает

В Task05 используются явные Compose и ROS команды; диагностика и завершение
описаны в [инструкции Task05](task05/README.md). Для предыдущих заданий:

Запустите команды из папки задания и пришлите преподавателю полный вывод вместе
с названием и версией операционной системы:

```bash
./course doctor
docker compose ps
docker compose logs --tail=200 workspace
docker version --format '{{.Server.Os}}/{{.Server.Arch}}'
```

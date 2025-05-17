# Happy Barrier

# Дипломный проект на тему "Платформа для удаленного управления системой контроля доступа шлагбаумов."

## Реферат

Современные системы контроля доступа обеспечивают безопасность на закрытых территориях, таких как жилые комплексы. Системы управления шлагбаумами и воротами, использующие GSM-модули для отправки и получения SMS, являются простым и экономичным решением. Эти системы позволяют управлять доступом, открывая шлагбаумы с помощью звонков или SMS от авторизованных номеров.

В данной работе разработана серверная часть системы, которая обеспечивает управление списками авторизованных номеров, настройками GSM-модулей и доступом для пользователей и администраторов. Программа позволяет администраторам легко добавлять и удалять пользователей, а также изменять параметры устройства через интерфейс, что упрощает управление доступом на территории. Пользователи могут самостоятельно управлять своими номерами, а администраторы контролируют и настраивают доступ в соответствии с требованиями безопасности. Система предназначена для удобного и безопасного управления доступом, обеспечивая эффективную настройку и контроль за шлагбаумами.

## Abstract

Modern access control systems ensure security in restricted areas, such as residential complexes. Barrier management systems using GSM modules for sending and receiving SMS provide a simple and cost-effective solution. These systems allow access management by opening barriers via calls or SMS from authorized numbers.

This work presents the development of the server-side part of the system, which provides management of authorized number lists, barrier settings, and access for users and administrators. The program enables administrators to easily add and remove users and modify device parameters through the interface, simplifying access management in the area. Users can independently manage their numbers, while administrators oversee and configure access according to security requirements. The system is designed for convenient and secure access control, offering efficient configuration and monitoring of barriers.

# Структура проекта

Проект организован в директории src/ и включает в себя фронтенд, бэкенд, вспомогательные сервисы и инфраструктурные конфигурации.

```
src/
├── backend/                     # Django-сервер (API, авторизация, логика доступа, БД)
├── frontend/                    # Веб-интерфейс на React
├── kafka/                       # Конфигурации Kafka и Kafka UI
├── monitoring/                  # Grafana, Loki, Promtail для логирования и мониторинга
├── sms_service/                 # Сервис для отправки и получения SMS через модем
│   ├── Dockerfile
│   ├── docker-compose.prod.yml  # Docker Compose файл продакшн-сборки
│   ├── docker-compose.dev.yml   # Docker Compose файл для запуска в режиме разработки
│   ├── deploy.sh                # Скрипт для деплоя (сборка и запуск всех сервисов)
│   ├── shutdown.sh              # Скрипт для остановки
│   ├── main.py                  # Точка входа в программе
│   └── prod.env                 # Переменные окружения для продакшн-сборки
├── certs/                       # SSL-сертификаты (server.crt, server.key)
├── deploy.sh                    # Скрипт для деплоя (сборка и запуск всех сервисов)
├── shutdown.sh                  # Скрипт для остановки всех контейнеров
├── .env                         # Главный файл с переменными окружения
├── nginx.prod.conf              # Конфигурации HTTPS-прокси для фронта и бэка для продакшн-сборки
├── nginx.dev.conf               # Конфигурации HTTPS-прокси для фронта и бэка для запуска в режиме разработки
├── docker-compose.prod.yml      # Docker Compose файл продакшн-сборки
└── docker-compose.dev.yml       # Docker Compose файл для запуска в режиме разработки
```

# Архитектура

Проект использует следующую архитектуру:
- Nginx — HTTPS-прокси, маршрутизирует запросы между фронтом и бэком
- Django — API и административная логика (backend)
- React (Vite) — пользовательский интерфейс (frontend)
- Kafka — обмен сообщениями между системами (например, для отправки SMS)
- PostgreSQL — хранилище данных
- Grafana + Loki + Promtail — мониторинг и централизованный сбор логов
- Kafka UI — визуальный интерфейс для работы с Kafka
- SMS Service — отдельный сервис, работающий с модемом для отправки и получения SMS через Kafka

# Первый запуск основного сервера

## Требования

- **Bash** — есть по умолчанию на Linux и macOS  
  Проверка:
  ```bash
  which bash
  ```
  Установка:
  ```bash
  sudo apt install bash       # Ubuntu/Debian
  brew install bash           # macOS
  ```

- **Docker** — нужен для запуска контейнеров.
- **docker-compose** — обязательно наличие именно CLI-утилиты docker-compose, а не встроенной команды docker compose.

Проверка:
```bash
docker-compose --version
```

---

## 1. Настройка окружения

Перед запуском необходимо заполнить файл `.env`, расположенный в директории `src/`.

### Обязательные переменные:

| Переменная         | Описание                                                               |
|--------------------|------------------------------------------------------------------------|
| `SERVER_IP`        | IP-адрес сервера, на котором будет запущена система                   |
| `SERVER_DOMAINS`   | Список доменов через запятую, по которым будет доступна система       |

**Пример:**
```env
SERVER_IP=45.156.27.150
SERVER_DOMAINS=gsm-barrier.ru,gsm-barrier.online
```

---

### Безопасность и ключи

| Переменная              | Описание                                                                                            |
|-------------------------|-----------------------------------------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`     | Секретный ключ Django. Генерируется: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `KAFKA_KRAFT_CLUSTER_ID`| Уникальный ID кластера Kafka. Генерация: `uuidgen` или `command openssl rand -hex 8`                |

---

### База данных

| Переменная       | Описание                  |
|------------------|---------------------------|
| `DB_NAME`        | Имя базы данных PostgreSQL |
| `DB_USER`        | Имя пользователя БД        |
| `DB_PASSWORD`    | Пароль для подключения к БД |

---

### Суперпользователь

| Переменная            | Описание                                                                 |
|------------------------|-------------------------------------------------------------------------|
| `SUPERUSER_PHONE`      | Телефон в формате `+79991234567`                                        |
| `SUPERUSER_NAME`       | Имя и фамилия. Если с пробелами — указывать в кавычках `'Имя Фамилия'`  |
| `SUPERUSER_PASSWORD`   | Сложный безопасный пароль                                               |

---

## 2. Сертификаты

Файлы сертификатов необходимы для HTTPS. Положите их в директорию `src/certs/`:

- `server.crt` — публичный сертификат
- `server.key` — приватный ключ

### Где взять?

Если у вас есть домен, то можно получить через [Let's Encrypt](https://letsencrypt.org/) или купить.
Рекомендуется использовать домен и получить полноценный сертификат.

Но если вдруг домена пока что нет, но есть публичный IP адрес, то можно сгенерировать самоподписанный сертификат для того, чтобы можно было использовать систему.
Он подойдёт для тестирования, но не будет признан браузерами как безопасный.

```bash
openssl req -x509 -newkey rsa:4096 -nodes -keyout server.key -out server.crt -days 365
```

---

## 3. Запуск сервера

Убедитесь, что установлен [Docker Compose](https://docs.docker.com/compose/install/).

Затем выполните в директории `src/`:

```bash
/bin/bash deploy.sh
```

---

## 4. Проверка состояния

Выполните команду:

```bash
docker ps
```

Ожидаемые контейнеры (все должны быть `healthy`):

| Контейнер         | Назначение              |
|-------------------|--------------------------|
| `nginx`           | HTTPS-прокси             |
| `react_frontend`  | Веб-интерфейс            |
| `django_backend`  | Сервер Django            |
| `kafka`           | Kafka брокер             |
| `postgres_db`     | PostgreSQL база данных   |
| `kafka-ui`        | Интерфейс Kafka          |
| `grafana`         | Мониторинг и графики     |
| `promtail`        | Сбор логов               |
| `loki`            | Хранилище логов          |

---

## 5. Остановка сервера

Для завершения работы:

```bash
/bin/bash shutdown.sh
```

---

# Первый запуск SMS сервера

## Требования

- **Bash** — есть по умолчанию на Linux и macOS  
  Проверка:
  ```bash
  which bash
  ```
  Установка:
  ```bash
  sudo apt install bash       # Ubuntu/Debian
  brew install bash           # macOS
  ```

- **Docker** — нужен для запуска контейнеров.
- **docker-compose** — обязательно наличие именно CLI-утилиты docker-compose, а не встроенной команды docker compose.

Проверка:
```bash
docker-compose --version
```


- **Подключённый модем**, совместимый с библиотекой [`huawei-lte-api`](https://github.com/Salamek/huawei-lte-api)  
  
- Протестировано с модемом **Brovi E3372-325 (3G/4G LTE)**

---

## Настройка окружения

Запуск производится из директории: `src/sms_service/`.

Перед запуском необходимо заполнить файл `prod.env`:

| Переменная                         | Описание                                                                    |
|------------------------------------|-----------------------------------------------------------------------------|
| `KAFKA_SERVERS`                    | Адрес основного сервера. Указывается IP-адрес или домен, с портом `19092`.  |
| `MODEM_USERNAME`                   | Имя пользователя для входа в модем (по умолчанию `admin`)                   |
| `MODEM_PASSWORD`                   | Пароль от модема (по умолчанию `admin`)                                     |
| `MESSAGE_RESPONSE_TIMEOUT_MINUTES` | Сколько минут ждать ответа от модема (например, `10`)                       |
| `DB_PATH`                          | Путь к SQLite-базе для хранения сообщений (например, `sms_storage.sqlite3`) |

Пример:
```env
KAFKA_SERVERS=gsm-barrier.ru:19092
MODEM_USERNAME=admin
MODEM_PASSWORD=admin
MESSAGE_RESPONSE_TIMEOUT_MINUTES=10
DB_PATH=sms_storage.sqlite3
```

---

## Запуск сервиса

Из директории `src/sms_service/` выполните:

```bash
/bin/bash deploy.sh
```

---

## Проверка состояния

Проверьте статус контейнера:

```bash
docker ps
```

Контейнер `sms_service` должен быть в состоянии `Up`.

---

## Остановка сервиса

Для завершения работы выполните:

```bash
/bin/bash shutdown.sh
```

# IoT Система - Лабораторная работа №4

## Описание проекта

Данный проект представляет собой высоконагруженную систему обработки данных IoT с микросервисной архитектурой, включающую:

- **API Gateway** - единая точка входа для всех запросов
- **Сервис устройств** - управление IoT устройствами
- **Сервис аналитики** - обработка и анализ данных в реальном времени
- **Сервис пользователей** - управление пользователями
- **Сервис аудита** - логирование всех событий
- **База данных PostgreSQL** с репликацией master-slave
- **Redis** для кэширования
- **RabbitMQ** для очередей сообщений
- **Nginx** для балансировки нагрузки
- **Prometheus + Grafana** для мониторинга
- **MinIO** для S3-совместимого хранилища

## Архитектура системы

### Технологический стек

- **Контейнеризация**: Docker + Docker Compose
- **Балансировка нагрузки**: Nginx
- **База данных**: PostgreSQL 15 с репликацией
- **Кэширование**: Redis 7
- **Очереди сообщений**: RabbitMQ 3
- **Микросервисы**: Python (Flask/FastAPI)
- **Мониторинг**: Prometheus + Grafana
- **Хранилище**: MinIO (S3-совместимое)

### Компоненты системы

1. **API Gateway** (FastAPI) - порт 8000
   - Маршрутизация запросов к микросервисам
   - Кэширование ответов
   - Аутентификация и авторизация
   - Логирование запросов
   - Метрики Prometheus

2. **Сервис устройств** (Flask) - порт 5000
   - CRUD операции с устройствами
   - Прием данных от IoT устройств
   - Асинхронная обработка данных
   - Мониторинг состояния устройств

3. **Сервис аналитики** (Flask) - порт 5000
   - Аналитика в реальном времени
   - Обнаружение аномалий
   - Историческая аналитика
   - Агрегация данных

4. **Сервис пользователей** (Flask) - порт 5000
   - Управление пользователями
   - Аутентификация
   - Роли и права доступа

5. **Сервис аудита** (Flask) - порт 5000
   - Логирование всех событий
   - Event Sourcing
   - Восстановление состояния

6. **PostgreSQL Master** - порт 5432
   - Основная база данных
   - Репликация на slave
   - Партиционирование данных

7. **PostgreSQL Slave** - порт 5433
   - Реплика базы данных
   - Чтение данных
   - Отказоустойчивость

8. **Redis** - порт 6379
   - Кэширование
   - Сессии
   - Временные данные

9. **RabbitMQ** - порт 5672
   - Очереди сообщений
   - Асинхронная обработка
   - Event-driven архитектура

10. **Nginx** - порт 80
    - Балансировка нагрузки
    - Кэширование
    - Rate limiting
    - SSL termination

11. **Prometheus** - порт 9090
    - Сбор метрик
    - Алерты
    - Мониторинг

12. **Grafana** - порт 3000
    - Визуализация метрик
    - Дашборды
    - Аналитика

13. **MinIO** - порт 9000
    - S3-совместимое хранилище
    - Резервные копии
    - Статические файлы

## Установка и запуск

### Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- Минимум 4GB RAM
- 10GB свободного места

### Быстрый старт

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd iot-system
```

2. **Запустите систему:**
```bash
docker-compose up -d
```

3. **Проверьте статус:**
```bash
docker-compose ps
```

4. **Откройте веб-интерфейс:**
```
http://localhost
```

### Пошаговая настройка

#### 1. Настройка базы данных

База данных автоматически инициализируется при первом запуске:

```bash
# Проверка статуса PostgreSQL
docker-compose logs postgres-master
docker-compose logs postgres-slave

# Подключение к базе данных
docker-compose exec postgres-master psql -U iot_user -d iot_system
```

#### 2. Настройка репликации

Репликация настраивается автоматически. Для проверки:

```bash
# Проверка статуса репликации на master
docker-compose exec postgres-master psql -U iot_user -d iot_system -c "SELECT * FROM pg_stat_replication;"

# Проверка статуса slave
docker-compose exec postgres-slave psql -U iot_user -d iot_system -c "SELECT pg_is_in_recovery();"
```

#### 3. Настройка мониторинга

1. **Prometheus**: http://localhost:9090
2. **Grafana**: http://localhost:3000 (admin/admin)

#### 4. Настройка RabbitMQ

RabbitMQ Management: http://localhost:15672
- Логин: iot_user
- Пароль: iot_password

#### 5. Настройка MinIO

MinIO Console: http://localhost:9001
- Логин: minioadmin
- Пароль: minioadmin123

## Использование API

### Основные эндпоинты

#### Устройства

```bash
# Получить все устройства
GET http://localhost/api/devices

# Создать устройство
POST http://localhost/api/devices
{
    "name": "Temperature Sensor 1",
    "device_type": "sensor",
    "location": "Room 101",
    "sensor_type": "temperature",
    "sampling_rate": 60
}

# Получить устройство
GET http://localhost/api/devices/{device_id}

# Обновить устройство
PUT http://localhost/api/devices/{device_id}
{
    "status": "inactive"
}

# Удалить устройство
DELETE http://localhost/api/devices/{device_id}
```

#### Данные устройств

```bash
# Отправить данные от устройства
POST http://localhost/api/devices/{device_id}/data
{
    "type": "temperature",
    "value": 23.5,
    "unit": "celsius",
    "quality": 0.95
}

# Получить данные устройства
GET http://localhost/api/devices/{device_id}/data?limit=100
```

#### Аналитика

```bash
# Аналитика в реальном времени
GET http://localhost/api/analytics/realtime

# Историческая аналитика
GET http://localhost/api/analytics/historical?start_date=2024-01-01&end_date=2024-01-31

# Аналитика устройства
GET http://localhost/api/devices/{device_id}/analytics?period=24h
```

#### Пользователи

```bash
# Получить всех пользователей
GET http://localhost/api/users

# Создать пользователя
POST http://localhost/api/users
{
    "username": "admin",
    "email": "admin@example.com",
    "password": "secure_password"
}
```

### Проверка здоровья системы

```bash
# Общий статус
GET http://localhost/api/health

# Метрики Prometheus
GET http://localhost/api/metrics
```

## Мониторинг и логирование

### Prometheus метрики

Система предоставляет следующие метрики:

- `http_requests_total` - общее количество HTTP запросов
- `http_request_duration_seconds` - время выполнения запросов
- `device_created_total` - количество созданных устройств
- `analytics_request_total` - количество запросов аналитики

### Grafana дашборды

Предустановленные дашборды:

1. **IoT Overview** - общий обзор системы
2. **Device Metrics** - метрики устройств
3. **API Performance** - производительность API
4. **Database Performance** - производительность базы данных

### Логирование

Логи доступны через Docker:

```bash
# Логи API Gateway
docker-compose logs api-gateway

# Логи сервиса устройств
docker-compose logs device-service

# Логи базы данных
docker-compose logs postgres-master
```

## Масштабирование

### Горизонтальное масштабирование

Для масштабирования сервисов:

```bash
# Масштабирование API Gateway
docker-compose up -d --scale api-gateway=3

# Масштабирование сервиса устройств
docker-compose up -d --scale device-service=2
```

### Настройка nginx для масштабирования

Обновите `nginx/nginx.conf`:

```nginx
upstream api_gateway {
    least_conn;
    server api-gateway:8000 max_fails=3 fail_timeout=30s;
    server api-gateway_2:8000 max_fails=3 fail_timeout=30s;
    server api-gateway_3:8000 max_fails=3 fail_timeout=30s;
}
```

## Резервное копирование

### Автоматические бэкапы

Система настроена на ежечасное резервное копирование:

```bash
# Создание бэкапа
docker-compose exec postgres-master pg_dump -U iot_user iot_system > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из бэкапа
docker-compose exec -T postgres-master psql -U iot_user iot_system < backup_file.sql
```

### Интеграция с MinIO

Бэкапы автоматически загружаются в MinIO:

```bash
# Создание bucket для бэкапов
mc mb minio/iot-backups

# Загрузка бэкапа
mc cp backup_file.sql minio/iot-backups/
```

## Безопасность

### Настройки безопасности

1. **Аутентификация**: JWT токены
2. **Авторизация**: RBAC (Role-Based Access Control)
3. **Шифрование**: HTTPS/TLS
4. **Rate Limiting**: Ограничение запросов
5. **Валидация**: Проверка входных данных

### Обновление паролей

```bash
# Обновление пароля PostgreSQL
docker-compose exec postgres-master psql -U postgres -c "ALTER USER iot_user PASSWORD 'new_password';"

# Обновление пароля RabbitMQ
docker-compose exec rabbitmq rabbitmqctl change_password iot_user new_password
```

## Устранение неполадок

### Частые проблемы

1. **Сервисы не запускаются**
   ```bash
   # Проверка логов
   docker-compose logs
   
   # Перезапуск сервисов
   docker-compose restart
   ```

2. **Проблемы с базой данных**
   ```bash
   # Проверка статуса PostgreSQL
   docker-compose exec postgres-master pg_isready
   
   # Проверка репликации
   docker-compose exec postgres-master psql -U iot_user -d iot_system -c "SELECT * FROM pg_stat_replication;"
   ```

3. **Проблемы с сетью**
   ```bash
   # Проверка сети Docker
   docker network ls
   docker network inspect iot_iot_network
   ```

### Диагностика производительности

```bash
# Проверка использования ресурсов
docker stats

# Проверка медленных запросов
docker-compose exec postgres-master psql -U iot_user -d iot_system -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

## Разработка

### Добавление новых сервисов

1. Создайте директорию в `services/`
2. Добавьте Dockerfile
3. Обновите `docker-compose.yml`
4. Добавьте маршруты в nginx

### Тестирование

```bash
# Запуск тестов
docker-compose exec api-gateway python -m pytest

# Проверка покрытия кода
docker-compose exec api-gateway coverage run -m pytest
docker-compose exec api-gateway coverage report
```

## Лицензия

MIT License

## Поддержка

Для получения поддержки создайте issue в репозитории или обратитесь к документации. 
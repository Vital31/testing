# Инструкция по установке и настройке IoT системы

## 🎯 Обзор проекта

Данная лабораторная работа представляет собой полнофункциональную систему обработки данных IoT с микросервисной архитектурой. Система демонстрирует все принципы высоконагруженных систем:

- **Микросервисная архитектура** с 5 основными сервисами
- **Горизонтальное масштабирование** через Docker и nginx
- **Репликация базы данных** PostgreSQL master-slave
- **Кэширование** с Redis
- **Асинхронная обработка** через RabbitMQ
- **Мониторинг** с Prometheus и Grafana
- **Event Sourcing** для аудита
- **Канареечное развертывание**

## 📋 Предварительные требования

### Системные требования
- **ОС**: Windows 10/11, macOS 10.15+, или Linux (Ubuntu 20.04+)
- **RAM**: Минимум 4GB (рекомендуется 8GB)
- **Диск**: 10GB свободного места
- **Процессор**: 2+ ядра

### Программное обеспечение
- **Docker**: версия 20.10+
- **Docker Compose**: версия 2.0+
- **Git**: для клонирования репозитория

## 🚀 Быстрая установка

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd iot-system
```

### 2. Запуск системы
```bash
# Сделать скрипт исполняемым (Linux/macOS)
chmod +x start.sh

# Запустить систему
./start.sh
```

### 3. Проверка работы
```bash
# Проверить статус контейнеров
docker-compose ps

# Запустить тесты
python test_system.py
```

## 📖 Подробная настройка

### Шаг 1: Установка Docker

#### Windows
1. Скачайте Docker Desktop с [официального сайта](https://www.docker.com/products/docker-desktop)
2. Установите и запустите Docker Desktop
3. Убедитесь, что Docker работает: `docker --version`

#### macOS
```bash
# Установка через Homebrew
brew install --cask docker

# Или скачайте с официального сайта
# https://www.docker.com/products/docker-desktop
```

#### Linux (Ubuntu)
```bash
# Обновление пакетов
sudo apt update

# Установка зависимостей
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release

# Добавление GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Запуск Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### Шаг 2: Установка Docker Compose

#### Windows/macOS
Docker Compose включен в Docker Desktop

#### Linux
```bash
# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker-compose --version
```

### Шаг 3: Подготовка проекта

```bash
# Клонирование репозитория
git clone <repository-url>
cd iot-system

# Создание необходимых директорий
mkdir -p postgres/master/archive
mkdir -p postgres/slave/archive
mkdir -p logs
mkdir -p static/js
```

### Шаг 4: Настройка переменных окружения

Создайте файл `.env` в корне проекта:
```bash
# База данных
POSTGRES_DB=iot_system
POSTGRES_USER=iot_user
POSTGRES_PASSWORD=iot_password

# Redis
REDIS_URL=redis://redis:6379

# RabbitMQ
RABBITMQ_URL=amqp://iot_user:iot_password@rabbitmq:5672/

# API Gateway
DEVICE_SERVICE_URL=http://device-service:5000
ANALYTICS_SERVICE_URL=http://analytics-service:5000
USER_SERVICE_URL=http://user-service:5000
AUDIT_SERVICE_URL=http://audit-service:5000
```

### Шаг 5: Запуск системы

```bash
# Остановка существующих контейнеров
docker-compose down

# Сборка и запуск
docker-compose up -d --build

# Проверка статуса
docker-compose ps
```

### Шаг 6: Инициализация базы данных

```bash
# Ожидание запуска PostgreSQL
sleep 30

# Проверка подключения к базе данных
docker-compose exec postgres-master pg_isready -U iot_user

# Проверка репликации
docker-compose exec postgres-master psql -U iot_user -d iot_system -c "SELECT * FROM pg_stat_replication;"
```

## 🔧 Настройка компонентов

### 1. Настройка PostgreSQL

#### Проверка репликации
```bash
# На master
docker-compose exec postgres-master psql -U iot_user -d iot_system -c "
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn
FROM pg_stat_replication;
"

# На slave
docker-compose exec postgres-slave psql -U iot_user -d iot_system -c "SELECT pg_is_in_recovery();"
```

#### Создание бэкапа
```bash
# Создание бэкапа
docker-compose exec postgres-master pg_dump -U iot_user iot_system > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из бэкапа
docker-compose exec -T postgres-master psql -U iot_user iot_system < backup_file.sql
```

### 2. Настройка Redis

```bash
# Подключение к Redis
docker-compose exec redis redis-cli

# Проверка памяти
INFO memory

# Очистка кэша
FLUSHDB
```

### 3. Настройка RabbitMQ

```bash
# Доступ к веб-интерфейсу: http://localhost:15672
# Логин: iot_user
# Пароль: iot_password

# Проверка очередей
docker-compose exec rabbitmq rabbitmqctl list_queues
```

### 4. Настройка мониторинга

#### Prometheus
- URL: http://localhost:9090
- Проверьте, что все targets в статусе UP

#### Grafana
- URL: http://localhost:3000
- Логин: admin
- Пароль: admin

#### Импорт дашбордов
1. Войдите в Grafana
2. Перейдите в "+" → "Import"
3. Импортируйте дашборды из папки `monitoring/grafana/dashboards/`

### 5. Настройка MinIO

```bash
# Доступ к консоли: http://localhost:9001
# Логин: minioadmin
# Пароль: minioadmin123

# Создание bucket для бэкапов
mc config host add minio http://localhost:9000 minioadmin minioadmin123
mc mb minio/iot-backups
```

## 🧪 Тестирование системы

### Автоматическое тестирование
```bash
# Запуск всех тестов
python test_system.py
```

### Ручное тестирование API

#### Создание устройства
```bash
curl -X POST http://localhost:8000/devices \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Temperature Sensor 1",
    "device_type": "sensor",
    "location": "Room 101",
    "sensor_type": "temperature",
    "sampling_rate": 60
  }'
```

#### Отправка данных
```bash
curl -X POST http://localhost:8000/devices/{device_id}/data \
  -H "Content-Type: application/json" \
  -d '{
    "type": "temperature",
    "value": 23.5,
    "unit": "celsius",
    "quality": 0.95
  }'
```

#### Получение аналитики
```bash
curl http://localhost:8000/analytics/realtime
```

### Тестирование производительности

#### Нагрузочное тестирование
```bash
# Установка Apache Bench
sudo apt install apache2-utils  # Ubuntu
brew install httpd              # macOS

# Тест API Gateway
ab -n 1000 -c 10 http://localhost:8000/health

# Тест получения устройств
ab -n 1000 -c 10 http://localhost:8000/devices
```

## 🔍 Мониторинг и диагностика

### Просмотр логов
```bash
# Логи всех сервисов
docker-compose logs

# Логи конкретного сервиса
docker-compose logs api-gateway
docker-compose logs device-service
docker-compose logs postgres-master

# Логи в реальном времени
docker-compose logs -f api-gateway
```

### Проверка ресурсов
```bash
# Использование ресурсов контейнерами
docker stats

# Проверка сети
docker network ls
docker network inspect iot_iot_network
```

### Диагностика базы данных
```bash
# Медленные запросы
docker-compose exec postgres-master psql -U iot_user -d iot_system -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"

# Статистика таблиц
docker-compose exec postgres-master psql -U iot_user -d iot_system -c "
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE tablename = 'devices';
"
```

## 🚀 Масштабирование

### Горизонтальное масштабирование сервисов
```bash
# Масштабирование API Gateway
docker-compose up -d --scale api-gateway=3

# Масштабирование сервиса устройств
docker-compose up -d --scale device-service=2

# Проверка масштабирования
docker-compose ps
```

### Настройка nginx для масштабирования
Отредактируйте `nginx/nginx.conf`:
```nginx
upstream api_gateway {
    least_conn;
    server api-gateway:8000 max_fails=3 fail_timeout=30s;
    server api-gateway_2:8000 max_fails=3 fail_timeout=30s;
    server api-gateway_3:8000 max_fails=3 fail_timeout=30s;
}
```

## 🛠️ Устранение неполадок

### Частые проблемы

#### 1. Контейнеры не запускаются
```bash
# Проверка логов
docker-compose logs

# Перезапуск
docker-compose restart

# Полная пересборка
docker-compose down
docker-compose up -d --build
```

#### 2. Проблемы с базой данных
```bash
# Проверка статуса PostgreSQL
docker-compose exec postgres-master pg_isready

# Проверка репликации
docker-compose exec postgres-master psql -U iot_user -d iot_system -c "SELECT * FROM pg_stat_replication;"

# Перезапуск базы данных
docker-compose restart postgres-master postgres-slave
```

#### 3. Проблемы с сетью
```bash
# Проверка сети Docker
docker network ls
docker network inspect iot_iot_network

# Пересоздание сети
docker-compose down
docker network prune
docker-compose up -d
```

#### 4. Проблемы с памятью
```bash
# Очистка Docker
docker system prune -a

# Очистка volumes
docker volume prune

# Проверка использования ресурсов
docker stats
```

### Диагностика производительности

#### Проверка медленных запросов
```bash
# Включение логирования медленных запросов PostgreSQL
docker-compose exec postgres-master psql -U iot_user -d iot_system -c "
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();
"
```

#### Мониторинг Redis
```bash
# Подключение к Redis
docker-compose exec redis redis-cli

# Проверка памяти
INFO memory

# Проверка медленных команд
SLOWLOG GET 10
```

## 📚 Дополнительные ресурсы

### Документация
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

### Полезные команды
```bash
# Остановка системы
docker-compose down

# Остановка с удалением volumes
docker-compose down -v

# Перезапуск конкретного сервиса
docker-compose restart api-gateway

# Просмотр конфигурации
docker-compose config

# Обновление образов
docker-compose pull
docker-compose up -d
```

## 🎓 Обучение

### Изучение архитектуры
1. Изучите `docker-compose.yml` для понимания архитектуры
2. Просмотрите код каждого микросервиса
3. Изучите конфигурации nginx, PostgreSQL, Redis
4. Изучите метрики Prometheus и дашборды Grafana

### Эксперименты
1. Добавьте новый микросервис
2. Настройте дополнительные метрики
3. Создайте новые дашборды в Grafana
4. Настройте алерты в Prometheus
5. Реализуйте дополнительную логику в сервисах

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs`
2. Убедитесь, что все порты свободны
3. Проверьте системные требования
4. Создайте issue в репозитории с подробным описанием проблемы

---

**Удачной работы с IoT системой! 🚀** 
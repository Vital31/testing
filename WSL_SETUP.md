# Запуск IoT проекта в WSL (Windows Subsystem for Linux)

## Предварительные требования

### 1. Установка WSL2
```powershell
# В PowerShell от администратора
wsl --install
# Перезагрузите компьютер
```

### 2. Установка Ubuntu в WSL
```powershell
# Список доступных дистрибутивов
wsl --list --online

# Установка Ubuntu
wsl --install -d Ubuntu

# Запуск Ubuntu
wsl
```

### 3. Обновление системы
```bash
# В терминале Ubuntu
sudo apt update && sudo apt upgrade -y
```

## Установка Docker в WSL

### 1. Удаление старых версий Docker
```bash
sudo apt-get remove docker docker-engine docker.io containerd runc
```

### 2. Установка зависимостей
```bash
sudo apt-get update
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
```

### 3. Добавление GPG ключа Docker
```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

### 4. Настройка репозитория Docker
```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### 5. Установка Docker Engine
```bash
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 6. Добавление пользователя в группу docker
```bash
sudo usermod -aG docker $USER
# Выйдите и войдите снова в WSL
exit
# В PowerShell: wsl
```

### 7. Запуск Docker
```bash
# Запуск Docker daemon
sudo service docker start

# Проверка установки
docker --version
docker compose version
```

## Установка дополнительных инструментов

### 1. Установка Git
```bash
sudo apt install git -y
```

### 2. Установка Python и pip
```bash
sudo apt install python3 python3-pip python3-venv -y
```

### 3. Установка дополнительных утилит
```bash
sudo apt install curl wget htop tree -y
```

## Клонирование и настройка проекта

### 1. Клонирование проекта
```bash
# Перейдите в домашнюю директорию
cd ~

# Клонируйте проект (замените на ваш репозиторий)
git clone <your-repository-url> iot-project
cd iot-project
```

### 2. Настройка прав доступа
```bash
# Сделайте скрипты исполняемыми
chmod +x start.sh
chmod +x test_system.py

# Настройка прав для Docker volumes
sudo mkdir -p /var/lib/postgresql/data
sudo mkdir -p /var/lib/redis/data
sudo mkdir -p /var/lib/minio/data
sudo chown -R 1000:1000 /var/lib/postgresql/data
sudo chown -R 1000:1000 /var/lib/redis/data
sudo chown -R 1000:1000 /var/lib/minio/data
```

### 3. Создание .env файла
```bash
cat > .env << EOF
# Database
POSTGRES_DB=iot_db
POSTGRES_USER=iot_user
POSTGRES_PASSWORD=iot_password
POSTGRES_MASTER_HOST=postgres-master
POSTGRES_SLAVE_HOST=postgres-slave

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=iot_user
RABBITMQ_PASSWORD=iot_password

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_HOST=minio
MINIO_PORT=9000

# Services
API_GATEWAY_PORT=8000
DEVICE_SERVICE_PORT=8001
ANALYTICS_SERVICE_PORT=8002
USER_SERVICE_PORT=8003
AUDIT_SERVICE_PORT=8004

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Nginx
NGINX_PORT=80
NGINX_SSL_PORT=443
EOF
```

## Запуск системы

### 1. Первый запуск
```bash
# Остановите все контейнеры если они запущены
docker compose down

# Удалите старые volumes если есть
docker volume prune -f

# Запустите систему
./start.sh
```

### 2. Проверка статуса
```bash
# Проверка запущенных контейнеров
docker compose ps

# Проверка логов
docker compose logs -f
```

### 3. Тестирование системы
```bash
# Запуск тестов
python3 test_system.py
```

## Доступ к сервисам

После успешного запуска вы сможете получить доступ к:

- **Веб-интерфейс**: http://localhost
- **API Gateway**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin123)

## Полезные команды WSL

### Управление WSL
```powershell
# В PowerShell
wsl --list --verbose          # Список дистрибутивов
wsl --shutdown               # Остановка WSL
wsl --unregister Ubuntu      # Удаление дистрибутива
```

### Управление Docker в WSL
```bash
# Запуск Docker daemon
sudo service docker start

# Остановка Docker daemon
sudo service docker stop

# Проверка статуса Docker
sudo service docker status
```

### Мониторинг ресурсов
```bash
# Мониторинг системы
htop

# Мониторинг Docker
docker stats

# Мониторинг диска
df -h
```

## Решение проблем

### 1. Проблемы с Docker
```bash
# Перезапуск Docker
sudo service docker restart

# Очистка Docker
docker system prune -a
docker volume prune
```

### 2. Проблемы с портами
```bash
# Проверка занятых портов
sudo netstat -tulpn | grep LISTEN

# Убийство процесса на порту
sudo kill -9 <PID>
```

### 3. Проблемы с правами доступа
```bash
# Исправление прав для Docker volumes
sudo chown -R $USER:$USER /var/lib/docker
```

### 4. Проблемы с памятью
```bash
# Проверка использования памяти
free -h

# Очистка кэша
sudo sh -c "sync; echo 3 > /proc/sys/vm/drop_caches"
```

## Оптимизация производительности

### 1. Настройка WSL2
Создайте файл `.wslconfig` в домашней директории Windows:
```
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
```

### 2. Настройка Docker
```bash
# Создание daemon.json
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

# Перезапуск Docker
sudo service docker restart
```

## Резервное копирование

### 1. Экспорт данных
```bash
# Экспорт базы данных
docker compose exec postgres-master pg_dump -U iot_user iot_db > backup.sql

# Экспорт конфигураций
tar -czf configs_backup.tar.gz postgres/ redis/ nginx/ monitoring/
```

### 2. Импорт данных
```bash
# Импорт базы данных
docker compose exec -T postgres-master psql -U iot_user iot_db < backup.sql
```

## Обновление системы

### 1. Обновление WSL
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Обновление Docker
```bash
# Удаление старой версии
sudo apt-get remove docker-ce docker-ce-cli containerd.io

# Установка новой версии (повторите шаги установки Docker)
```

### 3. Обновление проекта
```bash
git pull origin main
docker compose down
docker compose up -d --build
```

## Заключение

Теперь у вас есть полностью функциональная IoT система, запущенная в WSL2. Система включает:

- ✅ Микросервисную архитектуру
- ✅ Горизонтальное масштабирование
- ✅ Асинхронную обработку данных
- ✅ Мониторинг и логирование
- ✅ Балансировку нагрузки
- ✅ Репликацию базы данных
- ✅ Кэширование
- ✅ Очереди сообщений
- ✅ Объектное хранилище

Для получения дополнительной помощи обратитесь к файлам `README.md` и `INSTALL.md`. 
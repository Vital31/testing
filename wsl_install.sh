#!/bin/bash

# Скрипт автоматической установки IoT проекта в WSL
# Вариант 10: IoT Data Processing System

set -e

echo "🚀 Начинаем установку IoT проекта в WSL..."
echo "📋 Вариант: 10 - IoT Data Processing System"
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Проверка что мы в WSL
if ! grep -qi microsoft /proc/version; then
    warn "Этот скрипт предназначен для запуска в WSL"
fi

# Проверка прав администратора
if [ "$EUID" -eq 0 ]; then
    error "Не запускайте этот скрипт от имени root"
fi

log "Проверяем систему..."

# Обновление системы
log "Обновляем систему..."
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
log "Устанавливаем необходимые пакеты..."
sudo apt install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    htop \
    tree \
    ca-certificates \
    gnupg \
    lsb-release \
    apt-transport-https \
    software-properties-common

# Проверка Docker
if ! command -v docker &> /dev/null; then
    log "Устанавливаем Docker..."
    
    # Удаление старых версий
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Добавление GPG ключа
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Настройка репозитория
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Установка Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Добавление пользователя в группу docker
    sudo usermod -aG docker $USER
    log "Пользователь добавлен в группу docker. Перезапустите WSL для применения изменений."
else
    log "Docker уже установлен"
fi

# Запуск Docker
log "Запускаем Docker..."
sudo service docker start

# Проверка Docker
if docker --version &> /dev/null; then
    log "Docker успешно установлен: $(docker --version)"
else
    error "Ошибка установки Docker"
fi

# Создание директорий для проекта
log "Создаем структуру проекта..."
mkdir -p ~/iot-project
cd ~/iot-project

# Копирование файлов проекта (если они есть в текущей директории)
if [ -f "../docker-compose.yml" ]; then
    log "Копируем файлы проекта..."
    cp -r ../* . 2>/dev/null || true
    cp -r ../.* . 2>/dev/null || true
fi

# Создание .env файла
log "Создаем конфигурационный файл..."
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

# Настройка прав доступа
log "Настраиваем права доступа..."
chmod +x start.sh 2>/dev/null || true
chmod +x test_system.py 2>/dev/null || true

# Создание директорий для Docker volumes
sudo mkdir -p /var/lib/postgresql/data
sudo mkdir -p /var/lib/redis/data
sudo mkdir -p /var/lib/minio/data
sudo chown -R 1000:1000 /var/lib/postgresql/data
sudo chown -R 1000:1000 /var/lib/redis/data
sudo chown -R 1000:1000 /var/lib/minio/data

# Создание .wslconfig для оптимизации
log "Создаем конфигурацию WSL..."
if [ ! -f ~/.wslconfig ]; then
    cat > ~/.wslconfig << EOF
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
EOF
    log "Файл .wslconfig создан в домашней директории Windows"
fi

# Настройка Docker daemon
log "Настраиваем Docker daemon..."
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

# Проверка готовности к запуску
log "Проверяем готовность системы..."

# Проверка Docker Compose
if docker compose version &> /dev/null; then
    log "Docker Compose готов: $(docker compose version)"
else
    error "Docker Compose не найден"
fi

# Проверка файлов проекта
if [ -f "docker-compose.yml" ]; then
    log "Файл docker-compose.yml найден"
else
    warn "Файл docker-compose.yml не найден. Убедитесь, что все файлы проекта скопированы."
fi

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Перезапустите WSL: exit, затем wsl"
echo "2. Перейдите в директорию проекта: cd ~/iot-project"
echo "3. Запустите систему: ./start.sh"
echo "4. Проверьте статус: docker compose ps"
echo "5. Запустите тесты: python3 test_system.py"
echo ""
echo "🌐 Доступные сервисы после запуска:"
echo "- Веб-интерфейс: http://localhost"
echo "- API Gateway: http://localhost:8000"
echo "- Grafana: http://localhost:3000 (admin/admin)"
echo "- Prometheus: http://localhost:9090"
echo "- MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)"
echo ""
echo "📚 Дополнительная документация:"
echo "- README.md - общее описание проекта"
echo "- INSTALL.md - подробные инструкции по установке"
echo "- WSL_SETUP.md - инструкции по работе с WSL"
echo "- ARCHITECTURE.md - архитектура системы"
echo ""

# Создание алиасов для удобства
log "Создаем алиасы для удобства..."
cat >> ~/.bashrc << EOF

# IoT Project Aliases
alias iot-start='cd ~/iot-project && ./start.sh'
alias iot-stop='cd ~/iot-project && docker compose down'
alias iot-status='cd ~/iot-project && docker compose ps'
alias iot-logs='cd ~/iot-project && docker compose logs -f'
alias iot-test='cd ~/iot-project && python3 test_system.py'
alias iot-clean='cd ~/iot-project && docker compose down -v && docker system prune -f'
EOF

echo "✅ Алиасы добавлены в ~/.bashrc:"
echo "   iot-start  - запуск системы"
echo "   iot-stop   - остановка системы"
echo "   iot-status - статус контейнеров"
echo "   iot-logs   - просмотр логов"
echo "   iot-test   - запуск тестов"
echo "   iot-clean  - очистка системы"
echo ""

log "Установка завершена успешно! 🚀" 
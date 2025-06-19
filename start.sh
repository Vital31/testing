#!/bin/bash

echo "🚀 Запуск IoT системы..."
echo "================================"

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверяем наличие Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
    exit 1
fi

# Останавливаем существующие контейнеры
echo "🛑 Остановка существующих контейнеров..."
docker-compose down

# Удаляем старые volumes (опционально)
read -p "Удалить старые данные? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️ Удаление старых данных..."
    docker-compose down -v
fi

# Создаем необходимые директории
echo "📁 Создание директорий..."
mkdir -p postgres/master/archive
mkdir -p postgres/slave/archive
mkdir -p logs

# Запускаем систему
echo "🚀 Запуск контейнеров..."
docker-compose up -d

# Ждем запуска основных сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 30

# Проверяем статус
echo "📊 Проверка статуса сервисов..."
docker-compose ps

# Проверяем здоровье системы
echo "🏥 Проверка здоровья системы..."
sleep 10

# Проверяем доступность API
if curl -f http://localhost/api/health > /dev/null 2>&1; then
    echo "✅ API Gateway доступен"
else
    echo "❌ API Gateway недоступен"
fi

# Проверяем базу данных
if docker-compose exec postgres-master pg_isready -U iot_user > /dev/null 2>&1; then
    echo "✅ База данных доступна"
else
    echo "❌ База данных недоступна"
fi

# Проверяем Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis доступен"
else
    echo "❌ Redis недоступен"
fi

echo ""
echo "🎉 Система запущена!"
echo "================================"
echo "🌐 Веб-интерфейс: http://localhost"
echo "📊 API Gateway: http://localhost:8000"
echo "📈 Prometheus: http://localhost:9090"
echo "📊 Grafana: http://localhost:3000 (admin/admin)"
echo "🐰 RabbitMQ: http://localhost:15672 (iot_user/iot_password)"
echo "☁️ MinIO: http://localhost:9001 (minioadmin/minioadmin123)"
echo ""
echo "📝 Логи: docker-compose logs -f [service_name]"
echo "🛑 Остановка: docker-compose down"
echo "================================" 
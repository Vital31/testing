#!/bin/bash
set -e

echo "Initializing PostgreSQL Master..."

# Создаем пользователя для репликации
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER iot_user WITH PASSWORD 'iot_password';
    GRANT ALL PRIVILEGES ON DATABASE iot_system TO iot_user;
    ALTER USER iot_user WITH REPLICATION;
    
    -- Создаем расширения
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
    
    -- Создаем схему для IoT данных
    CREATE SCHEMA IF NOT EXISTS iot_data;
    GRANT ALL ON SCHEMA iot_data TO iot_user;
    
    -- Создаем таблицы для устройств
    CREATE TABLE IF NOT EXISTS devices (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(100) NOT NULL,
        device_type VARCHAR(50) NOT NULL,
        location VARCHAR(200),
        status VARCHAR(20) DEFAULT 'active',
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sensor_type VARCHAR(50),
        data_format VARCHAR(50),
        sampling_rate INTEGER,
        battery_level FLOAT DEFAULT 100.0,
        firmware_version VARCHAR(20) DEFAULT '1.0.0'
    );
    
    -- Создаем таблицы для данных устройств с партиционированием по дате
    CREATE TABLE IF NOT EXISTS device_data (
        id SERIAL,
        device_id UUID NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_type VARCHAR(50) NOT NULL,
        value FLOAT NOT NULL,
        unit VARCHAR(20),
        quality FLOAT DEFAULT 1.0,
        PRIMARY KEY (id, timestamp)
    ) PARTITION BY RANGE (timestamp);
    
    -- Создаем партиции для текущего месяца и следующих 3 месяцев
    CREATE TABLE device_data_$(date +%Y%m) PARTITION OF device_data
        FOR VALUES FROM ('$(date +%Y-%m-01)') TO ('$(date -d '+1 month' +%Y-%m-01)');
    
    CREATE TABLE device_data_$(date -d '+1 month' +%Y%m) PARTITION OF device_data
        FOR VALUES FROM ('$(date -d '+1 month' +%Y-%m-01)') TO ('$(date -d '+2 months' +%Y-%m-01)');
    
    CREATE TABLE device_data_$(date -d '+2 months' +%Y%m) PARTITION OF device_data
        FOR VALUES FROM ('$(date -d '+2 months' +%Y-%m-01)') TO ('$(date -d '+3 months' +%Y-%m-01)');
    
    CREATE TABLE device_data_$(date -d '+3 months' +%Y%m) PARTITION OF device_data
        FOR VALUES FROM ('$(date -d '+3 months' +%Y-%m-01)') TO ('$(date -d '+4 months' +%Y-%m-01)');
    
    -- Создаем индексы
    CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
    CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
    CREATE INDEX IF NOT EXISTS idx_device_data_device_id ON device_data(device_id);
    CREATE INDEX IF NOT EXISTS idx_device_data_timestamp ON device_data(timestamp);
    CREATE INDEX IF NOT EXISTS idx_device_data_type ON device_data(data_type);
    
    -- Создаем таблицу для результатов аналитики
    CREATE TABLE IF NOT EXISTS analytics_results (
        id SERIAL PRIMARY KEY,
        device_id UUID,
        analysis_type VARCHAR(50) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        result_data JSONB,
        period_start TIMESTAMP,
        period_end TIMESTAMP
    );
    
    -- Создаем таблицу для аудита событий
    CREATE TABLE IF NOT EXISTS audit_events (
        id SERIAL PRIMARY KEY,
        event_type VARCHAR(50) NOT NULL,
        entity_type VARCHAR(50),
        entity_id VARCHAR(100),
        user_id VARCHAR(100),
        data JSONB,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address INET,
        user_agent TEXT
    ) PARTITION BY RANGE (timestamp);
    
    -- Создаем партиции для аудита
    CREATE TABLE audit_events_$(date +%Y%m) PARTITION OF audit_events
        FOR VALUES FROM ('$(date +%Y-%m-01)') TO ('$(date -d '+1 month' +%Y-%m-01)');
    
    -- Предоставляем права
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iot_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iot_user;
    GRANT ALL PRIVILEGES ON SCHEMA public TO iot_user;
EOSQL

echo "PostgreSQL Master initialized successfully!" 
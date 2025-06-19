#!/bin/bash
set -e

echo "Initializing PostgreSQL Slave..."

# Ждем, пока master будет готов
echo "Waiting for master to be ready..."
until pg_isready -h postgres-master -p 5432 -U iot_user; do
    echo "Master is not ready yet. Waiting..."
    sleep 2
done

echo "Master is ready. Setting up replication..."

# Останавливаем PostgreSQL для настройки репликации
pg_ctl -D "$PGDATA" -m fast -w stop

# Очищаем данные
rm -rf "$PGDATA"/*

# Инициализируем реплику с master
pg_basebackup -h postgres-master -D "$PGDATA" -U iot_user -v -P -W

# Создаем recovery.conf для PostgreSQL 12+
cat > "$PGDATA/recovery.conf" <<EOF
standby_mode = 'on'
primary_conninfo = 'host=postgres-master port=5432 user=iot_user password=iot_password'
restore_command = 'cp /var/lib/postgresql/archive/%f %p'
trigger_file = '/tmp/promote_trigger'
EOF

# Создаем standby.signal для PostgreSQL 12+
touch "$PGDATA/standby.signal"

# Запускаем PostgreSQL
pg_ctl -D "$PGDATA" -o "-c listen_addresses='*'" -w start

echo "PostgreSQL Slave initialized successfully!" 
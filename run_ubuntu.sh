#!/bin/bash

set -e

# === Настройки ===
REPO_URL="${1:-}"  # URL репозитория передаётся первым аргументом

if [ -z "$REPO_URL" ]; then
  echo "Использование: $0 <URL_ВАШЕГО_РЕПОЗИТОРИЯ>"
  exit 1
fi

# === Установка зависимостей ===
echo "Обновление системы и установка зависимостей..."
sudo apt update
sudo apt install -y git docker.io docker-compose python3 python3-pip

# === Освобождение порта 53 (для dnsmasq) ===
echo "Освобождение порта 53..."
# Проверяем, существует ли сервис systemd-resolved, и останавливаем его
if systemctl list-units --full -all | grep -Fq 'systemd-resolved.service'; then
    sudo systemctl stop systemd-resolved
    sudo systemctl disable systemd-resolved
fi
# Заменяем симлинк на статичный DNS-конфиг
sudo rm -f /etc/resolv.conf
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null

# === Клонирование репозитория ===
echo "Клонирование репозитория..."
REPO_DIR=$(basename "$REPO_URL" .git)
if [ -d "$REPO_DIR" ]; then
  echo "Папка $REPO_DIR уже существует, пропускаем клонирование."
else
  git clone "$REPO_URL"
fi
cd "$REPO_DIR"

# === Установка Python-зависимостей (если есть requirements.txt) ===
if [ -f requirements.txt ]; then
  echo "Установка Python-зависимостей..."
  pip3 install -r requirements.txt
fi

# === Запуск docker-compose ===
echo "Запуск docker-compose..."
sudo docker-compose up --build -d

echo "Готово! Все сервисы запущены в фоне."
echo "Проверьте статус: sudo docker ps"

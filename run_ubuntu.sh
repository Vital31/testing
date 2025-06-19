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

# 🚀 Быстрый запуск IoT проекта в WSL

## Вариант 10: IoT Data Processing System

### Шаг 1: Установка WSL2
```powershell
# В PowerShell от администратора
wsl --install
# Перезагрузите компьютер
```

### Шаг 2: Автоматическая установка
```bash
# В терминале WSL
chmod +x wsl_install.sh
./wsl_install.sh
```

### Шаг 3: Перезапуск WSL
```bash
exit
# В PowerShell: wsl
```

### Шаг 4: Запуск системы
```bash
# Переход в проект
cd ~/iot-project

# Запуск всех сервисов
./start.sh

# Или используя алиас
iot-start
```

### Шаг 5: Проверка работы
```bash
# Статус контейнеров
iot-status

# Запуск тестов
iot-test
```

## 🌐 Доступные сервисы

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| **Веб-интерфейс** | http://localhost | - |
| **API Gateway** | http://localhost:8000 | - |
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin123 |

## 🛠 Полезные команды

```bash
iot-start    # Запуск системы
iot-stop     # Остановка системы
iot-status   # Статус контейнеров
iot-logs     # Просмотр логов
iot-test     # Запуск тестов
iot-clean    # Очистка системы
```

## 📊 Мониторинг

```bash
# Мониторинг системы
htop

# Мониторинг Docker
docker stats

# Мониторинг диска
df -h
```

## 🔧 Решение проблем

### Docker не запускается
```bash
sudo service docker start
```

### Проблемы с портами
```bash
sudo netstat -tulpn | grep LISTEN
```

### Очистка системы
```bash
iot-clean
```

## 📚 Документация

- `README.md` - Общее описание проекта
- `INSTALL.md` - Подробные инструкции
- `WSL_SETUP.md` - Инструкции по WSL
- `ARCHITECTURE.md` - Архитектура системы

## 🎯 Что включено

✅ **Микросервисная архитектура**  
✅ **Горизонтальное масштабирование**  
✅ **Асинхронная обработка данных**  
✅ **Мониторинг и логирование**  
✅ **Балансировка нагрузки**  
✅ **Репликация базы данных**  
✅ **Кэширование**  
✅ **Очереди сообщений**  
✅ **Объектное хранилище**  

---

**Готово!** Ваша IoT система запущена и готова к работе! 🚀 
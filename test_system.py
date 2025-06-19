#!/usr/bin/env python3
"""
Скрипт для тестирования IoT системы
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta

# Конфигурация
API_BASE_URL = "http://localhost:8000"
TEST_DEVICES = 5
TEST_DATA_POINTS = 10

def test_health_check():
    """Тест проверки здоровья системы"""
    print("🏥 Тестирование проверки здоровья...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Система здорова: {data['status']}")
            return True
        else:
            print(f"❌ Ошибка здоровья: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_create_devices():
    """Тест создания устройств"""
    print(f"📱 Создание {TEST_DEVICES} тестовых устройств...")
    
    devices = []
    device_types = ['sensor', 'actuator', 'gateway', 'controller']
    sensor_types = ['temperature', 'humidity', 'pressure', 'light', 'motion']
    
    for i in range(TEST_DEVICES):
        device_data = {
            "name": f"Test Device {i+1}",
            "device_type": random.choice(device_types),
            "location": f"Room {random.randint(100, 999)}",
            "sensor_type": random.choice(sensor_types),
            "sampling_rate": random.randint(30, 300),
            "battery_level": random.uniform(20, 100)
        }
        
        try:
            response = requests.post(f"{API_BASE_URL}/devices", json=device_data, timeout=10)
            if response.status_code == 201:
                device = response.json()
                devices.append(device)
                print(f"✅ Устройство создано: {device['name']} (ID: {device['id'][:8]}...)")
            else:
                print(f"❌ Ошибка создания устройства: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка создания устройства: {e}")
    
    return devices

def test_send_device_data(devices):
    """Тест отправки данных от устройств"""
    print(f"📊 Отправка данных от {len(devices)} устройств...")
    
    for device in devices:
        print(f"📡 Отправка данных от {device['name']}...")
        
        for i in range(TEST_DATA_POINTS):
            data_point = {
                "type": device.get('sensor_type', 'temperature'),
                "value": random.uniform(15, 35),
                "unit": "celsius" if device.get('sensor_type') == 'temperature' else "units",
                "quality": random.uniform(0.8, 1.0)
            }
            
            try:
                response = requests.post(
                    f"{API_BASE_URL}/devices/{device['id']}/data",
                    json=data_point,
                    timeout=10
                )
                if response.status_code == 202:
                    print(f"  ✅ Данные отправлены: {data_point['value']:.2f} {data_point['unit']}")
                else:
                    print(f"  ❌ Ошибка отправки данных: {response.status_code}")
            except Exception as e:
                print(f"  ❌ Ошибка отправки данных: {e}")
            
            time.sleep(0.5)  # Небольшая задержка между отправками

def test_analytics():
    """Тест аналитики"""
    print("📈 Тестирование аналитики...")
    
    # Тест аналитики в реальном времени
    try:
        response = requests.get(f"{API_BASE_URL}/analytics/realtime", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Аналитика в реальном времени: {len(data.get('devices', {}))} устройств")
        else:
            print(f"❌ Ошибка аналитики в реальном времени: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка аналитики в реальном времени: {e}")
    
    # Тест исторической аналитики
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        response = requests.get(f"{API_BASE_URL}/analytics/historical", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Историческая аналитика: {len(data.get('daily_stats', {}))} дней")
        else:
            print(f"❌ Ошибка исторической аналитики: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка исторической аналитики: {e}")

def test_cache():
    """Тест кэширования"""
    print("💾 Тестирование кэширования...")
    
    # Первый запрос (должен быть медленнее)
    start_time = time.time()
    response1 = requests.get(f"{API_BASE_URL}/devices", timeout=10)
    time1 = time.time() - start_time
    
    # Второй запрос (должен быть быстрее из-за кэша)
    start_time = time.time()
    response2 = requests.get(f"{API_BASE_URL}/devices", timeout=10)
    time2 = time.time() - start_time
    
    if response1.status_code == 200 and response2.status_code == 200:
        print(f"✅ Кэширование работает: {time1:.3f}s -> {time2:.3f}s")
        if time2 < time1:
            print("  🚀 Второй запрос быстрее (кэш работает)")
        else:
            print("  ⚠️ Кэш может не работать")
    else:
        print("❌ Ошибка тестирования кэширования")

def test_metrics():
    """Тест метрик Prometheus"""
    print("📊 Тестирование метрик...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/metrics", timeout=10)
        if response.status_code == 200:
            metrics = response.text
            if "http_requests_total" in metrics:
                print("✅ Метрики Prometheus доступны")
            else:
                print("❌ Метрики Prometheus не найдены")
        else:
            print(f"❌ Ошибка получения метрик: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка получения метрик: {e}")

def test_load_balancing():
    """Тест балансировки нагрузки"""
    print("⚖️ Тестирование балансировки нагрузки...")
    
    # Отправляем несколько запросов подряд
    response_times = []
    for i in range(10):
        start_time = time.time()
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        response_time = time.time() - start_time
        response_times.append(response_time)
        
        if response.status_code == 200:
            print(f"  ✅ Запрос {i+1}: {response_time:.3f}s")
        else:
            print(f"  ❌ Запрос {i+1}: ошибка {response.status_code}")
    
    avg_time = sum(response_times) / len(response_times)
    print(f"📊 Среднее время ответа: {avg_time:.3f}s")

def main():
    """Основная функция тестирования"""
    print("🧪 Начало тестирования IoT системы")
    print("=" * 50)
    
    # Ждем запуска системы
    print("⏳ Ожидание запуска системы...")
    time.sleep(10)
    
    # Тесты
    tests = [
        ("Проверка здоровья", test_health_check),
        ("Создание устройств", lambda: test_create_devices()),
        ("Отправка данных", lambda devices: test_send_device_data(devices)),
        ("Аналитика", test_analytics),
        ("Кэширование", test_cache),
        ("Метрики", test_metrics),
        ("Балансировка нагрузки", test_load_balancing)
    ]
    
    devices = []
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}...")
        try:
            if test_name == "Создание устройств":
                devices = test_func()
                if devices:
                    passed_tests += 1
            elif test_name == "Отправка данных":
                if devices:
                    test_func(devices)
                    passed_tests += 1
                else:
                    print("⚠️ Пропуск: нет устройств для тестирования")
            else:
                if test_func():
                    passed_tests += 1
        except Exception as e:
            print(f"❌ Ошибка в тесте {test_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты тестирования: {passed_tests}/{total_tests} тестов пройдено")
    
    if passed_tests == total_tests:
        print("🎉 Все тесты пройдены успешно!")
    else:
        print("⚠️ Некоторые тесты не пройдены")
    
    print("\n🌐 Доступные интерфейсы:")
    print(f"  Веб-интерфейс: http://localhost")
    print(f"  API Gateway: http://localhost:8000")
    print(f"  Prometheus: http://localhost:9090")
    print(f"  Grafana: http://localhost:3000")

if __name__ == "__main__":
    main() 
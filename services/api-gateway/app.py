from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import redis
import requests
import json
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog
from typing import Dict, Any
import os

# Настройка логирования
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(title="IoT API Gateway", version="1.0.0")

# Метрики Prometheus
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

# Подключение к Redis
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# Конфигурация микросервисов
SERVICES = {
    'device': os.getenv('DEVICE_SERVICE_URL', 'http://device-service:5000'),
    'analytics': os.getenv('ANALYTICS_SERVICE_URL', 'http://analytics-service:5000'),
    'user': os.getenv('USER_SERVICE_URL', 'http://user-service:5000'),
    'audit': os.getenv('AUDIT_SERVICE_URL', 'http://audit-service:5000'),
}

# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Логируем входящий запрос
    logger.info(
        "Incoming request",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    response = await call_next(request)
    
    # Логируем ответ
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time
    )
    
    # Обновляем метрики
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_LATENCY.observe(process_time)
    
    return response

def get_cached_response(cache_key: str) -> Dict[str, Any]:
    """Получить кэшированный ответ"""
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.error("Cache error", error=str(e))
    return None

def set_cached_response(cache_key: str, data: Dict[str, Any], ttl: int = 300):
    """Сохранить ответ в кэш"""
    try:
        redis_client.setex(cache_key, ttl, json.dumps(data))
    except Exception as e:
        logger.error("Cache set error", error=str(e))

async def forward_request(service: str, path: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Перенаправить запрос к микросервису"""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service {service} not found")
    
    url = f"{SERVICES[service]}{path}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            raise HTTPException(status_code=405, detail="Method not allowed")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error("Service request failed", service=service, url=url, error=str(e))
        raise HTTPException(status_code=503, detail=f"Service {service} unavailable")

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "IoT API Gateway",
        "version": "1.0.0",
        "services": list(SERVICES.keys())
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья системы"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    # Проверяем каждый сервис
    for service_name, service_url in SERVICES.items():
        try:
            response = requests.get(f"{service_url}/health", timeout=5)
            health_status["services"][service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            health_status["services"][service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Если хотя бы один сервис нездоров, общий статус unhealthy
    if any(s["status"] == "unhealthy" for s in health_status["services"].values()):
        health_status["status"] = "unhealthy"
    
    return health_status

@app.get("/devices")
async def get_devices():
    """Получить список устройств с кэшированием"""
    cache_key = "devices:list"
    
    # Проверяем кэш
    cached = get_cached_response(cache_key)
    if cached:
        return cached
    
    # Получаем данные от сервиса устройств
    data = await forward_request("device", "/devices")
    
    # Кэшируем результат на 5 минут
    set_cached_response(cache_key, data, 300)
    
    return data

@app.post("/devices")
async def create_device(device_data: Dict[str, Any]):
    """Создать новое устройство"""
    # Инвалидируем кэш
    redis_client.delete("devices:list")
    
    # Отправляем запрос к сервису устройств
    result = await forward_request("device", "/devices", "POST", device_data)
    
    # Отправляем событие в сервис аудита
    try:
        audit_event = {
            "event_type": "device_created",
            "data": device_data,
            "timestamp": time.time()
        }
        await forward_request("audit", "/events", "POST", audit_event)
    except Exception as e:
        logger.error("Failed to send audit event", error=str(e))
    
    return result

@app.get("/analytics/realtime")
async def get_realtime_analytics():
    """Получить аналитику в реальном времени"""
    return await forward_request("analytics", "/realtime")

@app.get("/analytics/historical")
async def get_historical_analytics(start_date: str = None, end_date: str = None):
    """Получить историческую аналитику"""
    params = ""
    if start_date and end_date:
        params = f"?start_date={start_date}&end_date={end_date}"
    return await forward_request("analytics", f"/historical{params}")

@app.get("/anomalies")
async def get_anomalies():
    """Получить аномалии"""
    return await forward_request("analytics", "/anomalies")

@app.get("/devices/summary")
async def get_devices_summary():
    """Получить сводку по устройствам"""
    return await forward_request("device", "/summary")

@app.get("/system/status")
async def get_system_status():
    """Получить общий статус системы"""
    # Этот эндпоинт может собирать данные из нескольких сервисов
    # Для простоты, пока просто перенаправляем на health check
    return await health_check()

@app.get("/users")
async def get_users():
    """Получить список пользователей"""
    return await forward_request("user", "/users")

@app.post("/users")
async def create_user(user_data: Dict[str, Any]):
    """Создать нового пользователя"""
    result = await forward_request("user", "/users", "POST", user_data)
    
    # Отправляем событие в сервис аудита
    try:
        audit_event = {
            "event_type": "user_created",
            "data": user_data,
            "timestamp": time.time()
        }
        await forward_request("audit", "/events", "POST", audit_event)
    except Exception as e:
        logger.error("Failed to send audit event", error=str(e))
    
    return result

@app.get("/metrics")
async def metrics():
    """Метрики Prometheus"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/cache/clear")
async def clear_cache():
    """Очистить кэш Redis"""
    try:
        redis_client.flushdb()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error("Cache clear error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear cache")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
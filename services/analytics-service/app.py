from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import redis
import json
import time
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog
import os
from celery import Celery
import numpy as np

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

app = Flask(__name__)

# Конфигурация
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('POSTGRES_URL', 'postgresql://iot_user:iot_password@localhost:5432/iot_system')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db = SQLAlchemy(app)

# Redis для кэширования
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# Celery для асинхронных задач
celery_app = Celery('analytics_service', broker=os.getenv('RABBITMQ_URL', 'amqp://iot_user:iot_password@localhost:5672/'))

# Метрики Prometheus
ANALYTICS_REQUEST = Counter('analytics_request_total', 'Total analytics requests')
REQUEST_LATENCY = Histogram('analytics_request_duration_seconds', 'Analytics service request latency')

# Модели данных
class DeviceData(db.Model):
    __tablename__ = 'device_data'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(36), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data_type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20))
    quality = db.Column(db.Float)

class AnalyticsResult(db.Model):
    __tablename__ = 'analytics_results'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(36), nullable=False)
    analysis_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    result_data = db.Column(db.JSON)
    period_start = db.Column(db.DateTime)
    period_end = db.Column(db.DateTime)

# Celery задачи
@celery_app.task
def calculate_daily_statistics():
    """Вычисление ежедневной статистики"""
    try:
        yesterday = datetime.utcnow() - timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Получаем данные за вчера
        data_points = DeviceData.query.filter(
            DeviceData.timestamp >= start_date,
            DeviceData.timestamp <= end_date
        ).all()
        
        # Группируем по устройствам и типам данных
        device_stats = {}
        for dp in data_points:
            key = f"{dp.device_id}_{dp.data_type}"
            if key not in device_stats:
                device_stats[key] = []
            device_stats[key].append(dp.value)
        
        # Вычисляем статистику
        for key, values in device_stats.items():
            device_id, data_type = key.split('_', 1)
            
            stats = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'std': np.std(values) if len(values) > 1 else 0
            }
            
            # Сохраняем результат
            result = AnalyticsResult(
                device_id=device_id,
                analysis_type='daily_stats',
                result_data=stats,
                period_start=start_date,
                period_end=end_date
            )
            db.session.add(result)
        
        db.session.commit()
        logger.info("Daily statistics calculated", count=len(device_stats))
        
    except Exception as e:
        logger.error("Failed to calculate daily statistics", error=str(e))
        db.session.rollback()

@celery_app.task
def detect_anomalies():
    """Обнаружение аномалий в данных"""
    try:
        # Получаем данные за последний час
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        data_points = DeviceData.query.filter(
            DeviceData.timestamp >= one_hour_ago
        ).all()
        
        # Группируем по устройствам и типам данных
        device_data = {}
        for dp in data_points:
            key = f"{dp.device_id}_{dp.data_type}"
            if key not in device_data:
                device_data[key] = []
            device_data[key].append(dp.value)
        
        anomalies = []
        for key, values in device_data.items():
            if len(values) < 3:  # Нужно минимум 3 точки для анализа
                continue
                
            device_id, data_type = key.split('_', 1)
            
            # Простой алгоритм обнаружения аномалий (z-score)
            mean = np.mean(values)
            std = np.std(values)
            
            if std > 0:
                for i, value in enumerate(values):
                    z_score = abs((value - mean) / std)
                    if z_score > 2.5:  # Порог аномалии
                        anomalies.append({
                            'device_id': device_id,
                            'data_type': data_type,
                            'value': value,
                            'z_score': z_score,
                            'timestamp': data_points[i].timestamp.isoformat()
                        })
        
        # Сохраняем аномалии
        if anomalies:
            result = AnalyticsResult(
                device_id='system',
                analysis_type='anomalies',
                result_data={'anomalies': anomalies},
                period_start=one_hour_ago,
                period_end=datetime.utcnow()
            )
            db.session.add(result)
            db.session.commit()
            
            logger.info("Anomalies detected", count=len(anomalies))
        
    except Exception as e:
        logger.error("Failed to detect anomalies", error=str(e))
        db.session.rollback()

# API эндпоинты
@app.route('/health')
def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверяем подключение к базе данных
        db.session.execute(text('SELECT 1'))
        
        # Проверяем подключение к Redis
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'redis': 'connected'
        }), 200
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

@app.route('/realtime')
def get_realtime_analytics():
    """Получить аналитику в реальном времени"""
    start_time = time.time()
    
    try:
        # Получаем данные за последние 5 минут
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        
        # Проверяем кэш
        cache_key = 'analytics:realtime'
        cached = redis_client.get(cache_key)
        
        if cached:
            analytics = json.loads(cached)
        else:
            # Получаем данные из базы
            data_points = DeviceData.query.filter(
                DeviceData.timestamp >= five_minutes_ago
            ).all()
            
            # Группируем по устройствам
            device_analytics = {}
            for dp in data_points:
                if dp.device_id not in device_analytics:
                    device_analytics[dp.device_id] = {}
                if dp.data_type not in device_analytics[dp.device_id]:
                    device_analytics[dp.device_id][dp.data_type] = []
                device_analytics[dp.device_id][dp.data_type].append(dp.value)
            
            # Вычисляем статистику
            analytics = {
                'timestamp': datetime.utcnow().isoformat(),
                'period': '5min',
                'devices': {}
            }
            
            for device_id, data_types in device_analytics.items():
                analytics['devices'][device_id] = {}
                for data_type, values in data_types.items():
                    if values:
                        analytics['devices'][device_id][data_type] = {
                            'count': len(values),
                            'latest': values[-1],
                            'min': min(values),
                            'max': max(values),
                            'avg': sum(values) / len(values)
                        }
            
            # Кэшируем на 30 секунд
            redis_client.setex(cache_key, 30, json.dumps(analytics))
        
        ANALYTICS_REQUEST.inc()
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error("Failed to get realtime analytics", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/historical')
def get_historical_analytics():
    """Получить историческую аналитику"""
    start_time = time.time()
    
    try:
        # Получаем параметры
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        device_id = request.args.get('device_id')
        data_type = request.args.get('data_type')
        
        # Парсим даты
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        else:
            start_date = datetime.utcnow() - timedelta(days=7)
            
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        else:
            end_date = datetime.utcnow()
        
        # Строим запрос
        query = DeviceData.query.filter(
            DeviceData.timestamp >= start_date,
            DeviceData.timestamp <= end_date
        )
        
        if device_id:
            query = query.filter(DeviceData.device_id == device_id)
        if data_type:
            query = query.filter(DeviceData.data_type == data_type)
        
        data_points = query.order_by(DeviceData.timestamp).all()
        
        # Группируем по дням
        daily_stats = {}
        for dp in data_points:
            day_key = dp.timestamp.date().isoformat()
            if day_key not in daily_stats:
                daily_stats[day_key] = []
            daily_stats[day_key].append(dp.value)
        
        # Вычисляем статистику по дням
        analytics = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'daily_stats': {}
        }
        
        for day, values in daily_stats.items():
            analytics['daily_stats'][day] = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'std': np.std(values) if len(values) > 1 else 0
            }
        
        ANALYTICS_REQUEST.inc()
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error("Failed to get historical analytics", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/anomalies')
def get_anomalies():
    """Получить обнаруженные аномалии"""
    try:
        # Получаем последние результаты анализа аномалий
        results = AnalyticsResult.query.filter(
            AnalyticsResult.analysis_type == 'anomalies'
        ).order_by(AnalyticsResult.timestamp.desc()).limit(10).all()
        
        anomalies = []
        for result in results:
            if result.result_data and 'anomalies' in result.result_data:
                anomalies.extend(result.result_data['anomalies'])
        
        return jsonify({
            'anomalies': anomalies,
            'count': len(anomalies)
        }), 200
        
    except Exception as e:
        logger.error("Failed to get anomalies", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices/<device_id>/analytics')
def get_device_analytics(device_id):
    """Получить аналитику для конкретного устройства"""
    try:
        # Получаем параметры
        period = request.args.get('period', '24h')
        
        if period == '24h':
            start_date = datetime.utcnow() - timedelta(hours=24)
        elif period == '7d':
            start_date = datetime.utcnow() - timedelta(days=7)
        elif period == '30d':
            start_date = datetime.utcnow() - timedelta(days=30)
        else:
            return jsonify({'error': 'Invalid period'}), 400
        
        # Получаем данные устройства
        data_points = DeviceData.query.filter(
            DeviceData.device_id == device_id,
            DeviceData.timestamp >= start_date
        ).order_by(DeviceData.timestamp).all()
        
        # Группируем по типам данных
        data_types = {}
        for dp in data_points:
            if dp.data_type not in data_types:
                data_types[dp.data_type] = []
            data_types[dp.data_type].append({
                'timestamp': dp.timestamp.isoformat(),
                'value': dp.value,
                'unit': dp.unit,
                'quality': dp.quality
            })
        
        # Вычисляем статистику
        analytics = {
            'device_id': device_id,
            'period': period,
            'data_types': {}
        }
        
        for data_type, points in data_types.items():
            values = [p['value'] for p in points]
            analytics['data_types'][data_type] = {
                'count': len(points),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': points[-1] if points else None,
                'data_points': points
            }
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error("Failed to get device analytics", device_id=device_id, error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/metrics')
def metrics():
    """Метрики Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(host='0.0.0.0', port=5000, debug=False) 
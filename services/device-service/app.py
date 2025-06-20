from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import redis
import json
import time
import uuid
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog
import os
from celery import Celery
from sqlalchemy import text

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
migrate = Migrate(app, db)

# Redis для кэширования
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# Celery для асинхронных задач
celery_app = Celery('device_service', broker=os.getenv('RABBITMQ_URL', 'amqp://iot_user:iot_password@localhost:5672/'))

# Метрики Prometheus
DEVICE_CREATED = Counter('device_created_total', 'Total devices created')
DEVICE_UPDATED = Counter('device_updated_total', 'Total devices updated')
DEVICE_DELETED = Counter('device_deleted_total', 'Total devices deleted')
REQUEST_LATENCY = Histogram('device_request_duration_seconds', 'Device service request latency')

# Модели данных
class Device(db.Model):
    __tablename__ = 'devices'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # IoT специфичные поля
    sensor_type = db.Column(db.String(50))
    data_format = db.Column(db.String(50))
    sampling_rate = db.Column(db.Integer)  # Hz
    battery_level = db.Column(db.Float)
    firmware_version = db.Column(db.String(20))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'device_type': self.device_type,
            'location': self.location,
            'status': self.status,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'sensor_type': self.sensor_type,
            'data_format': self.data_format,
            'sampling_rate': self.sampling_rate,
            'battery_level': self.battery_level,
            'firmware_version': self.firmware_version
        }

class DeviceData(db.Model):
    __tablename__ = 'device_data'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data_type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20))
    quality = db.Column(db.Float)  # Качество данных (0-1)
    
    device = db.relationship('Device', backref='data_points')

# Celery задачи
@celery_app.task
def process_device_data(device_id, data):
    """Асинхронная обработка данных устройства"""
    try:
        logger.info("Processing device data", device_id=device_id, data=data)
        
        # Здесь может быть сложная логика обработки данных
        # Например, агрегация, фильтрация, анализ аномалий
        
        # Сохраняем данные в базу
        device_data = DeviceData(
            device_id=device_id,
            data_type=data.get('type'),
            value=data.get('value'),
            unit=data.get('unit'),
            quality=data.get('quality', 1.0)
        )
        
        db.session.add(device_data)
        db.session.commit()
        
        # Обновляем время последнего контакта устройства
        device = Device.query.get(device_id)
        if device:
            device.last_seen = datetime.utcnow()
            db.session.commit()
        
        logger.info("Device data processed successfully", device_id=device_id)
        
    except Exception as e:
        logger.error("Failed to process device data", device_id=device_id, error=str(e))
        db.session.rollback()

@celery_app.task
def check_device_health():
    """Проверка здоровья устройств"""
    try:
        # Находим устройства, которые не отправляли данные более часа
        threshold = datetime.utcnow() - timedelta(hours=1)
        offline_devices = Device.query.filter(Device.last_seen < threshold).all()
        
        for device in offline_devices:
            device.status = 'offline'
            logger.warning("Device marked as offline", device_id=device.id, last_seen=device.last_seen)
        
        db.session.commit()
        
    except Exception as e:
        logger.error("Failed to check device health", error=str(e))
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

@app.route('/devices', methods=['GET'])
def get_devices():
    """Получить список всех устройств"""
    start_time = time.time()
    
    try:
        # Проверяем кэш
        cache_key = 'devices:all'
        cached = redis_client.get(cache_key)
        
        if cached:
            devices = json.loads(cached)
        else:
            devices = [device.to_dict() for device in Device.query.all()]
            # Кэшируем на 5 минут
            redis_client.setex(cache_key, 300, json.dumps(devices))
        
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        return jsonify({
            'devices': devices,
            'count': len(devices)
        }), 200
        
    except Exception as e:
        logger.error("Failed to get devices", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices', methods=['POST'])
def create_device():
    """Создать новое устройство"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        # Валидация данных
        required_fields = ['name', 'device_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Создаем устройство
        device = Device(
            name=data['name'],
            device_type=data['device_type'],
            location=data.get('location'),
            sensor_type=data.get('sensor_type'),
            data_format=data.get('data_format'),
            sampling_rate=data.get('sampling_rate'),
            battery_level=data.get('battery_level', 100.0),
            firmware_version=data.get('firmware_version', '1.0.0')
        )
        
        db.session.add(device)
        db.session.commit()
        
        # Инвалидируем кэш
        redis_client.delete('devices:all')
        
        # Обновляем метрики
        DEVICE_CREATED.inc()
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        logger.info("Device created", device_id=device.id, name=device.name)
        
        return jsonify(device.to_dict()), 201
        
    except Exception as e:
        logger.error("Failed to create device", error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    """Получить информацию об устройстве"""
    try:
        device = Device.query.get(device_id)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        return jsonify(device.to_dict()), 200
        
    except Exception as e:
        logger.error("Failed to get device", device_id=device_id, error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices/<device_id>', methods=['PUT'])
def update_device(device_id):
    """Обновить устройство"""
    start_time = time.time()
    
    try:
        device = Device.query.get(device_id)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        data = request.get_json()
        
        # Обновляем поля
        for field, value in data.items():
            if hasattr(device, field):
                setattr(device, field, value)
        
        device.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Инвалидируем кэш
        redis_client.delete('devices:all')
        
        # Обновляем метрики
        DEVICE_UPDATED.inc()
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        logger.info("Device updated", device_id=device_id)
        
        return jsonify(device.to_dict()), 200
        
    except Exception as e:
        logger.error("Failed to update device", device_id=device_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Удалить устройство"""
    start_time = time.time()
    
    try:
        device = Device.query.get(device_id)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        db.session.delete(device)
        db.session.commit()
        
        # Инвалидируем кэш
        redis_client.delete('devices:all')
        
        # Обновляем метрики
        DEVICE_DELETED.inc()
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        logger.info("Device deleted", device_id=device_id)
        
        return jsonify({'message': 'Device deleted successfully'}), 200
        
    except Exception as e:
        logger.error("Failed to delete device", device_id=device_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices/<device_id>/data', methods=['POST'])
def receive_device_data(device_id):
    """Получить данные от устройства"""
    try:
        device = Device.query.get(device_id)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        data = request.get_json()
        
        # Отправляем данные на асинхронную обработку
        process_device_data.delay(device_id, data)
        
        return jsonify({'message': 'Data received and queued for processing'}), 202
        
    except Exception as e:
        logger.error("Failed to receive device data", device_id=device_id, error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices/<device_id>/data', methods=['GET'])
def get_device_data(device_id):
    """Получить данные устройства"""
    try:
        device = Device.query.get(device_id)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Получаем параметры запроса
        limit = request.args.get('limit', 100, type=int)
        data_type = request.args.get('type')
        
        query = DeviceData.query.filter_by(device_id=device_id)
        if data_type:
            query = query.filter_by(data_type=data_type)
        
        data_points = query.order_by(DeviceData.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'device_id': device_id,
            'data_points': [{
                'timestamp': dp.timestamp.isoformat(),
                'data_type': dp.data_type,
                'value': dp.value,
                'unit': dp.unit,
                'quality': dp.quality
            } for dp in data_points]
        }), 200
        
    except Exception as e:
        logger.error("Failed to get device data", device_id=device_id, error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/summary', methods=['GET'])
def get_summary():
    """Получить сводную информацию по устройствам"""
    try:
        total_devices = Device.query.count()
        active_devices = Device.query.filter_by(status='active').count()
        offline_devices = Device.query.filter_by(status='offline').count()

        # Группировка по типам
        device_types_query = db.session.query(Device.device_type, db.func.count(Device.device_type)).group_by(Device.device_type).all()
        device_types = {dtype: count for dtype, count in device_types_query}

        return jsonify({
            'total_devices': total_devices,
            'active_devices': active_devices,
            'offline_devices': offline_devices,
            'device_types': device_types
        }), 200

    except Exception as e:
        logger.error("Failed to get device summary", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/metrics')
def metrics():
    """Метрики Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(host='0.0.0.0', port=5000, debug=False) 
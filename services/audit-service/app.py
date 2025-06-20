from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import json
import time
from datetime import datetime
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog
import os
from celery import Celery

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

# Celery для асинхронных задач
celery_app = Celery('audit_service', broker=os.getenv('RABBITMQ_URL', 'amqp://iot_user:iot_password@localhost:5672/'))

# Метрики Prometheus
EVENT_RECORDED = Counter('event_recorded_total', 'Total events recorded', ['event_type'])
REQUEST_LATENCY = Histogram('audit_request_duration_seconds', 'Audit service request latency')

# Модели данных
class AuditEvent(db.Model):
    __tablename__ = 'audit_events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.String(100))
    user_id = db.Column(db.String(100))
    data = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'user_id': self.user_id,
            'data': self.data,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

# Celery задачи
@celery_app.task
def process_audit_event(event_data):
    """Асинхронная обработка события аудита"""
    try:
        logger.info("Processing audit event", event_data=event_data)
        
        event = AuditEvent(
            event_type=event_data.get('event_type'),
            entity_type=event_data.get('entity_type'),
            entity_id=event_data.get('entity_id'),
            user_id=event_data.get('user_id'),
            data=event_data.get('data'),
            ip_address=event_data.get('ip_address'),
            user_agent=event_data.get('user_agent')
        )
        
        db.session.add(event)
        db.session.commit()
        
        # Обновляем метрики
        EVENT_RECORDED.labels(event_type=event_data.get('event_type')).inc()
        
        logger.info("Audit event processed successfully", event_id=event.id)
        
    except Exception as e:
        logger.error("Failed to process audit event", error=str(e))
        db.session.rollback()

# API эндпоинты
@app.route('/health')
def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверяем подключение к базе данных
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

@app.route('/events', methods=['POST'])
def record_event():
    """Записать событие аудита"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        # Добавляем информацию о запросе
        data['ip_address'] = request.remote_addr
        data['user_agent'] = request.headers.get('User-Agent')
        
        # Отправляем событие на асинхронную обработку
        process_audit_event.delay(data)
        
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        return jsonify({'message': 'Event recorded successfully'}), 202
        
    except Exception as e:
        logger.error("Failed to record event", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/events', methods=['GET'])
def get_events():
    """Получить события аудита"""
    start_time = time.time()
    
    try:
        # Получаем параметры запроса
        limit = request.args.get('limit', 100, type=int)
        event_type = request.args.get('event_type')
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Строим запрос
        query = AuditEvent.query
        
        if event_type:
            query = query.filter(AuditEvent.event_type == event_type)
        if entity_type:
            query = query.filter(AuditEvent.entity_type == entity_type)
        if entity_id:
            query = query.filter(AuditEvent.entity_id == entity_id)
        if start_date:
            query = query.filter(AuditEvent.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditEvent.timestamp <= end_date)
        
        events = query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
        
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        return jsonify({
            'events': [event.to_dict() for event in events],
            'count': len(events)
        }), 200
        
    except Exception as e:
        logger.error("Failed to get events", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/events/<entity_type>/<entity_id>', methods=['GET'])
def get_entity_events(entity_type, entity_id):
    """Получить события для конкретной сущности"""
    try:
        events = AuditEvent.query.filter(
            AuditEvent.entity_type == entity_type,
            AuditEvent.entity_id == entity_id
        ).order_by(AuditEvent.timestamp.desc()).all()
        
        return jsonify({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'events': [event.to_dict() for event in events],
            'count': len(events)
        }), 200
        
    except Exception as e:
        logger.error("Failed to get entity events", entity_type=entity_type, entity_id=entity_id, error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/reconstruct/<entity_type>/<entity_id>', methods=['GET'])
def reconstruct_entity(entity_type, entity_id):
    """Восстановить состояние сущности из событий"""
    try:
        events = AuditEvent.query.filter(
            AuditEvent.entity_type == entity_type,
            AuditEvent.entity_id == entity_id
        ).order_by(AuditEvent.timestamp.asc()).all()
        
        # Восстанавливаем состояние
        state = {}
        for event in events:
            if event.data:
                if event.event_type == 'created':
                    state = event.data.copy()
                elif event.event_type == 'updated':
                    state.update(event.data)
                elif event.event_type == 'deleted':
                    state = {}
        
        return jsonify({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'reconstructed_state': state,
            'events_used': len(events)
        }), 200
        
    except Exception as e:
        logger.error("Failed to reconstruct entity", entity_type=entity_type, entity_id=entity_id, error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/metrics')
def metrics():
    """Метрики Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(host='0.0.0.0', port=5000, debug=False) 
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import redis
import json
import time
import uuid
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

# Redis для кэширования
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# Celery для асинхронных задач
celery_app = Celery('user_service', broker=os.getenv('RABBITMQ_URL', 'amqp://iot_user:iot_password@localhost:5672/'))

# Метрики Prometheus
USER_CREATED = Counter('user_created_total', 'Total users created')
USER_UPDATED = Counter('user_updated_total', 'Total users updated')
USER_DELETED = Counter('user_deleted_total', 'Total users deleted')
REQUEST_LATENCY = Histogram('user_request_duration_seconds', 'User service request latency')

# Модели данных
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

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

@app.route('/users', methods=['GET'])
def get_users():
    """Получить список всех пользователей"""
    start_time = time.time()
    
    try:
        # Проверяем кэш
        cache_key = 'users:all'
        cached = redis_client.get(cache_key)
        
        if cached:
            users = json.loads(cached)
        else:
            users = [user.to_dict() for user in User.query.all()]
            # Кэшируем на 5 минут
            redis_client.setex(cache_key, 300, json.dumps(users))
        
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        return jsonify({
            'users': users,
            'count': len(users)
        }), 200
        
    except Exception as e:
        logger.error("Failed to get users", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users', methods=['POST'])
def create_user():
    """Создать нового пользователя"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        # Валидация данных
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Проверяем уникальность username и email
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 409
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Создаем пользователя (в реальном проекте пароль нужно хешировать)
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=data['password'],  # В реальном проекте: generate_password_hash(data['password'])
            role=data.get('role', 'user')
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Инвалидируем кэш
        redis_client.delete('users:all')
        
        # Обновляем метрики
        USER_CREATED.inc()
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        logger.info("User created", user_id=user.id, username=user.username)
        
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        logger.error("Failed to create user", error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Получить информацию о пользователе"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        logger.error("Failed to get user", user_id=user_id, error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Обновить пользователя"""
    start_time = time.time()
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Обновляем поля
        for field, value in data.items():
            if hasattr(user, field) and field not in ['id', 'created_at']:
                setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Инвалидируем кэш
        redis_client.delete('users:all')
        
        # Обновляем метрики
        USER_UPDATED.inc()
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        logger.info("User updated", user_id=user_id)
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        logger.error("Failed to update user", user_id=user_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Удалить пользователя"""
    start_time = time.time()
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        db.session.delete(user)
        db.session.commit()
        
        # Инвалидируем кэш
        redis_client.delete('users:all')
        
        # Обновляем метрики
        USER_DELETED.inc()
        REQUEST_LATENCY.observe(time.time() - start_time)
        
        logger.info("User deleted", user_id=user_id)
        
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        logger.error("Failed to delete user", user_id=user_id, error=str(e))
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/<user_id>/login', methods=['POST'])
def login_user(user_id):
    """Логин пользователя"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # В реальном проекте здесь была бы проверка пароля
        if data.get('password') == user.password_hash:
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'message': 'Login successful',
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
        
    except Exception as e:
        logger.error("Failed to login user", user_id=user_id, error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/metrics')
def metrics():
    """Метрики Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(host='0.0.0.0', port=5000, debug=False) 
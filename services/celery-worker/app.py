from celery import Celery
import os

broker_url = os.getenv("RABBITMQ_URL", "amqp://iot_user:iot_password@rabbitmq:5672//")
backend_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery = Celery(
    'worker',
    broker=broker_url,
    backend=backend_url
)

@celery.task
def test_task():
    return "Celery is working!" 
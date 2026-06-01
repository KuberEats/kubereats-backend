import json
from datetime import datetime

from app.config import Settings


class RabbitMqTaskQueue:
    def __init__(self, settings: Settings):
        self.settings = settings

    def enqueue_order_release(
        self,
        *,
        order_id: int,
        task_key: str,
        execute_at: datetime,
        correlation_id: str,
    ) -> None:
        try:
            import pika
        except ImportError as error:
            raise RuntimeError("pika is required for QUEUE_BACKEND=rabbitmq") from error

        parameters = pika.URLParameters(self.settings.rabbitmq_url)
        payload = {
            "order_id": order_id,
            "task_key": task_key,
            "correlation_id": correlation_id,
            "execute_at": execute_at.isoformat(),
        }

        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()
            channel.queue_declare(queue="order.release", durable=True)
            channel.basic_publish(
                exchange="",
                routing_key="order.release",
                body=json.dumps(payload).encode(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                    message_id=task_key,
                ),
            )
        finally:
            connection.close()

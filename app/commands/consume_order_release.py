import json

import requests

from app.config import get_settings


def main():
    try:
        import pika
    except ImportError as error:
        raise RuntimeError("pika is required to consume RabbitMQ tasks") from error

    settings = get_settings()
    parameters = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue="order.release", durable=True)

    def handle_message(channel, method, _properties, body):
        payload = json.loads(body)
        headers = {}
        if settings.internal_task_token:
            headers["X-Internal-Task-Token"] = settings.internal_task_token

        response = requests.post(
            settings.internal_task_handler_url,
            json=payload,
            headers=headers,
            timeout=10,
        )
        if 200 <= response.status_code < 300:
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="order.release", on_message_callback=handle_message)
    channel.start_consuming()


if __name__ == "__main__":
    main()

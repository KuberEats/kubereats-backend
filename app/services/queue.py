from app.worker import celery_app


class QueueProducer:
    def enqueue_email(self, notification_id: str, correlation_id: str) -> None:
        celery_app.send_task(
            "notification.send_email",
            kwargs={"notification_id": notification_id, "correlation_id": correlation_id},
        )

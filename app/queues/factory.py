from app.config import Settings, get_settings
from app.queues.cloud_tasks import CloudTasksTaskQueue
from app.queues.fake import FakeTaskQueue
from app.queues.protocol import TaskQueue
from app.queues.rabbitmq import RabbitMqTaskQueue


def build_task_queue(settings: Settings | None = None) -> TaskQueue:
    settings = settings or get_settings()
    backend = settings.queue_backend.lower()

    if backend == "fake":
        return FakeTaskQueue()
    if backend == "rabbitmq":
        return RabbitMqTaskQueue(settings)
    if backend == "cloud_tasks":
        return CloudTasksTaskQueue(settings)

    raise RuntimeError(f"Unsupported QUEUE_BACKEND: {settings.queue_backend}")

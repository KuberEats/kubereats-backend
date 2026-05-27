from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EnqueuedTask:
    order_id: int
    task_key: str
    execute_at: datetime
    correlation_id: str


class FakeTaskQueue:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.tasks: list[EnqueuedTask] = []

    def enqueue_order_release(
        self,
        *,
        order_id: int,
        task_key: str,
        execute_at: datetime,
        correlation_id: str,
    ) -> None:
        if self.fail:
            raise RuntimeError("Fake queue enqueue failed")

        self.tasks.append(
            EnqueuedTask(
                order_id=order_id,
                task_key=task_key,
                execute_at=execute_at,
                correlation_id=correlation_id,
            )
        )

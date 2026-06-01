from datetime import datetime
from typing import Protocol


class TaskQueue(Protocol):
    def enqueue_order_release(
        self,
        *,
        order_id: int,
        task_key: str,
        execute_at: datetime,
        correlation_id: str,
    ) -> None:
        ...

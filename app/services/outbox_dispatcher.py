from datetime import datetime

from app.queues.protocol import TaskQueue
from app.repo.order_repo import OrderRepository


class OutboxDispatcher:
    def __init__(self, order_repo: OrderRepository, task_queue: TaskQueue):
        self.order_repo = order_repo
        self.task_queue = task_queue

    def dispatch_once(self, limit: int = 100):
        events = self.order_repo.list_unpublished_outbox_events(limit=limit)
        results = {"published": 0, "failed": 0}

        for event in events:
            try:
                self._publish_event(event)
                self.order_repo.mark_outbox_event_published(event)
                self.order_repo.commit()
                results["published"] += 1
            except Exception as error:
                self.order_repo.rollback()
                self.order_repo.mark_outbox_event_failed(event, str(error))
                self.order_repo.commit()
                results["failed"] += 1

        return results

    def _publish_event(self, event):
        if event.event_type != "order.release_requested":
            return

        payload = event.payload_json
        execute_at = datetime.fromisoformat(payload["execute_at"])
        self.task_queue.enqueue_order_release(
            order_id=payload["order_id"],
            task_key=payload["task_key"],
            execute_at=execute_at,
            correlation_id=payload["correlation_id"],
        )

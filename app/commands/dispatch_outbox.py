from app.database import SessionLocal
from app.queues import build_task_queue
from app.repo.order_repo import OrderRepository
from app.services.outbox_dispatcher import OutboxDispatcher


def main():
    db = SessionLocal()
    try:
        dispatcher = OutboxDispatcher(
            order_repo=OrderRepository(db),
            task_queue=build_task_queue(),
        )
        print(dispatcher.dispatch_once())
    finally:
        db.close()


if __name__ == "__main__":
    main()

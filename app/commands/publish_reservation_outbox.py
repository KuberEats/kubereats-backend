from app.database import SessionLocal
from app.queues.reservation import build_reservation_event_publisher
from app.repo.reservation_repo import ReservationRepository
from app.services.reservation_outbox_publisher import ReservationOutboxPublisher


def main():
    db = SessionLocal()
    try:
        publisher = ReservationOutboxPublisher(
            reservation_repo=ReservationRepository(db),
            publisher=build_reservation_event_publisher(),
        )
        print(publisher.publish_once())
    finally:
        db.close()


if __name__ == "__main__":
    main()

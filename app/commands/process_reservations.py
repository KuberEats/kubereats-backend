import argparse
import json
import sys

from app.database import SessionLocal
from app.repo.reservation_repo import ReservationRepository
from app.services.reservation_service import ReservationService
from app.services.reservation_worker import ReservationDbPollingWorker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reservation-id", type=int)
    parser.add_argument("--event-json")
    parser.add_argument("--poll", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        repo = ReservationRepository(db)
        service = ReservationService(repo)

        if args.poll:
            worker = ReservationDbPollingWorker(repo, service)
            print(worker.poll_once(limit=args.limit))
            return

        if args.event_json:
            print(service.process_reservation_requested(json.loads(args.event_json)))
            return

        if args.reservation_id:
            print(service.process_reservation_by_id(args.reservation_id))
            return

        parser.print_help(sys.stderr)
        raise SystemExit(2)
    finally:
        db.close()


if __name__ == "__main__":
    main()

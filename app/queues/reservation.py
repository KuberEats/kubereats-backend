import json
from dataclasses import dataclass
from typing import Protocol

from app.config import Settings, get_settings


class ReservationEventPublisher(Protocol):
    def publish_reservation_requested(
        self,
        *,
        payload: dict,
        ordering_key: str,
    ) -> None: ...


@dataclass(frozen=True)
class PublishedReservationEvent:
    payload: dict
    ordering_key: str


class LocalReservationEventPublisher:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.events: list[PublishedReservationEvent] = []

    def publish_reservation_requested(
        self,
        *,
        payload: dict,
        ordering_key: str,
    ) -> None:
        if self.fail:
            raise RuntimeError("Local reservation publisher failed")

        self.events.append(
            PublishedReservationEvent(
                payload=payload,
                ordering_key=ordering_key,
            )
        )


class PubSubReservationEventPublisher:
    def __init__(self, settings: Settings | None = None):
        settings = settings or get_settings()
        if not settings.gcp_project_id:
            raise RuntimeError(
                "GCP_PROJECT_ID is required for pubsub reservation queue"
            )
        if not settings.pubsub_topic_reservation_requested:
            raise RuntimeError(
                "PUBSUB_TOPIC_RESERVATION_REQUESTED is required for pubsub reservation queue"
            )

        try:
            from google.cloud import pubsub_v1
        except ImportError as error:
            raise RuntimeError(
                "google-cloud-pubsub is required for RESERVATION_QUEUE_MODE=pubsub"
            ) from error

        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(
            settings.gcp_project_id,
            settings.pubsub_topic_reservation_requested,
        )

    def publish_reservation_requested(
        self,
        *,
        payload: dict,
        ordering_key: str,
    ) -> None:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        future = self.publisher.publish(
            self.topic_path,
            data,
            ordering_key=ordering_key,
        )
        future.result()


def build_reservation_event_publisher(
    settings: Settings | None = None,
) -> ReservationEventPublisher:
    settings = settings or get_settings()
    mode = settings.reservation_queue_mode.lower()

    if mode in {"local", "db_polling"}:
        return LocalReservationEventPublisher()
    if mode == "pubsub":
        return PubSubReservationEventPublisher(settings)

    raise RuntimeError(
        f"Unsupported RESERVATION_QUEUE_MODE: {settings.reservation_queue_mode}"
    )

import json
from datetime import datetime, timezone

from app.config import Settings


class CloudTasksTaskQueue:
    def __init__(self, settings: Settings):
        self.settings = settings

    def enqueue_order_release(
        self,
        *,
        order_id: int,
        task_key: str,
        execute_at: datetime,
        correlation_id: str,
    ) -> None:
        try:
            from google.cloud import tasks_v2
            from google.protobuf import timestamp_pb2
        except ImportError as error:
            raise RuntimeError(
                "google-cloud-tasks is required for QUEUE_BACKEND=cloud_tasks"
            ) from error

        self._validate_settings()

        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(
            self.settings.gcp_project_id,
            self.settings.gcp_location,
            self.settings.gcp_cloud_tasks_queue,
        )
        payload = {
            "order_id": order_id,
            "task_key": task_key,
            "correlation_id": correlation_id,
        }
        schedule_time = timestamp_pb2.Timestamp()
        schedule_time.FromDatetime(execute_at.astimezone(timezone.utc))

        task = {
            "name": client.task_path(
                self.settings.gcp_project_id,
                self.settings.gcp_location,
                self.settings.gcp_cloud_tasks_queue,
                task_key,
            ),
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": self.settings.gcp_task_handler_url,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload).encode(),
            },
            "schedule_time": schedule_time,
        }

        if self.settings.gcp_task_service_account_email:
            task["http_request"]["oidc_token"] = {
                "service_account_email": self.settings.gcp_task_service_account_email,
            }

        try:
            client.create_task(request={"parent": parent, "task": task})
        except Exception as error:
            if error.__class__.__name__ == "AlreadyExists":
                return
            raise

    def _validate_settings(self):
        required = {
            "GCP_PROJECT_ID": self.settings.gcp_project_id,
            "GCP_LOCATION": self.settings.gcp_location,
            "GCP_CLOUD_TASKS_QUEUE": self.settings.gcp_cloud_tasks_queue,
            "GCP_TASK_HANDLER_URL": self.settings.gcp_task_handler_url,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing Cloud Tasks settings: {', '.join(missing)}")

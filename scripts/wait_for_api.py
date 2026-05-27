import os
import time

import httpx


def main() -> None:
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    timeout_seconds = int(os.getenv("WAIT_FOR_API_TIMEOUT_SECONDS", "60"))
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/health/ready", timeout=2)
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(1)

    raise RuntimeError(f"API did not become ready at {base_url}: {last_error}")


if __name__ == "__main__":
    main()

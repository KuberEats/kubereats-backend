RETRY_DELAYS_SECONDS = [60, 300, 1800]


def retry_delay_seconds(failure_count: int) -> int | None:
    if failure_count <= 0:
        return 0
    index = failure_count - 1
    if index >= len(RETRY_DELAYS_SECONDS):
        return None
    return RETRY_DELAYS_SECONDS[index]

from app.services.retry_policy import retry_delay_seconds


def test_retry_policy():
    assert retry_delay_seconds(1) == 60
    assert retry_delay_seconds(2) == 300
    assert retry_delay_seconds(3) == 1800
    assert retry_delay_seconds(4) is None

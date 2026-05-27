import pytest

from app.templates.registry import Recipient, TemplateValidationError, TEMPLATES, get_template


def test_each_template_key_has_metadata():
    assert len(TEMPLATES) == 9
    for key, template in TEMPLATES.items():
        assert template.key == key
        assert template.version == 1
        assert template.allowed_source_services
        assert template.allowed_recipient_types
        assert template.subject_template
        assert template.html_template
        assert template.text_template


def test_unknown_template_is_rejected():
    with pytest.raises(KeyError):
        get_template("missing.template")


def test_missing_payload_field_returns_validation_error():
    template = get_template("employee.order.confirmed")
    payload = {
        "orderId": "ORD-1",
        "vendorName": "健康便當",
    }
    with pytest.raises(TemplateValidationError):
        template.validate_payload(payload)


def test_template_escapes_html_injection():
    template = get_template("employee.order.failed")
    rendered = template.render(
        Recipient(type="EMPLOYEE", id="EMP001", email="employee@example.com", name="<script>x</script>"),
        {
            "orderId": "ORD-1",
            "failureReason": "<script>alert(1)</script>",
            "retryUrl": "https://food.example.com/retry",
        },
    )

    assert "<script>" not in rendered["htmlBody"]
    assert "&lt;script&gt;" in rendered["htmlBody"]


def test_authorization_metadata_allows_order_templates():
    template = get_template("employee.order.confirmed")
    assert "order-service" in template.allowed_source_services
    assert "EMPLOYEE" in template.allowed_recipient_types


def test_authorization_metadata_blocks_merchant_for_employee_order():
    template = get_template("employee.order.confirmed")
    assert "merchant-service" not in template.allowed_source_services

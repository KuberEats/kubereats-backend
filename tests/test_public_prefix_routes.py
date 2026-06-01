from fastapi.testclient import TestClient

from app.main import app


def test_order_scheduler_public_prefix_routes_are_registered():
    routes = {
        (route.path, method)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/order-scheduler/orders", "GET") in routes
    assert ("/order-scheduler/orders", "POST") in routes
    assert ("/order-scheduler/reservation-requests", "POST") in routes


def test_metrics_endpoint_exposes_order_scheduler_app_metrics():
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "order_scheduler_http_requests_total" in response.text
    assert "order_scheduler_orders_created_total" in response.text

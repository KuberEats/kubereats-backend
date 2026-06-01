from fastapi.testclient import TestClient

from app.main import app


def test_recommendations_public_prefix_routes_are_registered():
    routes = {
        (route.path, method)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/recommendations/merchants", "GET") in routes
    assert ("/recommendations/merchants", "POST") in routes
    assert ("/recommendations/menus", "GET") in routes
    assert ("/recommendations/menus", "POST") in routes
    assert ("/recommendation/merchants", "GET") in routes
    assert ("/recommendation/merchants", "POST") in routes


def test_metrics_endpoint_exposes_recommendation_app_metrics():
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "recommendation_requests_total" in response.text
    assert "recommendation_results_returned_total" in response.text

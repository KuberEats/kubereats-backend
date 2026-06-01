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
    assert ("/order-scheduler/health", "GET") in routes

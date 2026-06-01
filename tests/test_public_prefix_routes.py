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

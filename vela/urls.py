from vela.api import api


def path(route, view, methods=None):
    print(f"[VELA URLS] {route}")

    methods = methods or ["GET"]

    for method in methods:
        api.add_route(
            method=method.upper(),
            path=route,
            handler=view,
        )

    return {
        "route": route,
        "view": view,
        "methods": methods,
    }
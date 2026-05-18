class ApiRouter:
    def __init__(self):
        self.routes = []

    def add_route(self, method, path, handler):
        print(f"[API REGISTER] {method} {path}")

        self.routes.append({
            "method": method,
            "path": path,
            "handler": handler,
        })

    def get(self, path):
        def decorator(func):
            self.add_route("GET", path, func)
            return func
        return decorator

    def post(self, path):
        def decorator(func):
            self.add_route("POST", path, func)
            return func
        return decorator

    def put(self, path):
        def decorator(func):
            self.add_route("PUT", path, func)
            return func
        return decorator

    def delete(self, path):
        def decorator(func):
            self.add_route("DELETE", path, func)
            return func
        return decorator
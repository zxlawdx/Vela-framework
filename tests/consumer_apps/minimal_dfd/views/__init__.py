def home(params):
    return '<section id="dfd">DFD Studio fixture</section>'


def register_routes(router):
    router.add("/dfd", home, name="dfd", title="DFD")

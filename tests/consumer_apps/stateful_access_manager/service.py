class Session:
    def __init__(self):
        self.token = "authenticated-token"


class Provider:
    instances = 0
    def __init__(self):
        type(self).instances += 1


SESSION = Session()
PROVIDER = Provider()

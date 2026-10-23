from vela.api import api


@api.get("/dfd/status")
def status():
    return {"ok": True, "fixture": "dfd"}

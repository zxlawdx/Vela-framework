from vela.api import api
from vela.core.http import Request


@api.post("/documents/save")
def save(request: Request):
    return {"ok": True, "length": len((request.json or {}).get("content", ""))}

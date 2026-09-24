"""Esquema OpenAPI basico e interface de testes offline, sem CDN."""
import inspect


def _schema(annotation):
    if annotation is inspect.Signature.empty:
        return {"type": "object"}
    if hasattr(annotation, "model_json_schema"):
        return annotation.model_json_schema()
    return {
        str: {"type": "string"}, int: {"type": "integer"},
        bool: {"type": "boolean"}, float: {"type": "number"},
        dict: {"type": "object"}, list: {"type": "array", "items": {}},
    }.get(annotation, {"type": "object"})


def build_openapi(routes, prefix="/api"):
    import vela
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Vela Local API", "version": vela.__version__},
        "paths": {},
    }
    for route in routes:
        method = route["method"].lower()
        path = prefix + route["path"]
        handler = route["handler"]
        summary = (inspect.getdoc(handler) or handler.__name__).splitlines()[0]
        operation = {
            "summary": summary,
            "operationId": handler.__name__,
            "responses": {"200": {"description": "Sucesso"}},
        }
        params = inspect.signature(handler).parameters
        if method in ("post", "put", "patch") and "data" in params:
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {
                    "schema": _schema(params["data"].annotation),
                }},
            }
        spec["paths"].setdefault(path, {})[method] = operation
    return spec


DOCS_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vela — Documentação da API</title>
<style>
:root{font:15px system-ui,sans-serif;color:#e5edfa;background:#0d1624}
*{box-sizing:border-box}body{max-width:1100px;margin:auto;padding:36px 20px}
h1{font-size:2rem;margin:0 0 8px}p{color:#aabbd2}
main{margin-top:25px}section{background:#17273b;border:1px solid #334764;
border-radius:13px;padding:20px;margin-bottom:14px}
header{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
header strong{padding:5px 11px;border-radius:6px;background:#22354e}
.get{color:#67d9aa}.post{color:#d1b0ff}.put{color:#f5cd85}.delete{color:#ff9999}
code,textarea,pre{font-family:ui-monospace,monospace}
textarea,pre{width:100%;background:#0d1624;color:#e5edfa;
border:1px solid #354960;border-radius:8px;padding:12px;overflow:auto}
textarea{min-height:100px}pre{white-space:pre-wrap;min-height:35px}
button{background:#2685e9;color:#fff;border:none;border-radius:8px;
padding:10px 18px;cursor:pointer}
a{color:#90bfff}
</style>
</head>
<body>
<h1>Vela / API Docs</h1>
<p>Explore e teste as rotas da API local. Interface totalmente offline.</p>
<a id="schema-link">Abrir esquema OpenAPI</a>
<main id="routes" aria-live="polite"></main>
<script>
const schemaURL="__VELA_OPENAPI_PATH__";
document.getElementById("schema-link").href=schemaURL;
fetch(schemaURL).then(r=>r.json()).then(spec=>{
 const main=document.getElementById("routes");
 for(const [path,methods] of Object.entries(spec.paths)){
  for(const [method,op] of Object.entries(methods)){
   const section=document.createElement("section");
   const head=document.createElement("header");
   const verb=document.createElement("strong");
   verb.className=method;verb.textContent=method.toUpperCase();
   const location=document.createElement("code");
   location.textContent=path;head.append(verb,location);
   const summary=document.createElement("p");
   summary.textContent=op.summary;
   const body=document.createElement("textarea");
   body.value="{}";
   if(method==="get"||method==="delete")body.hidden=true;
   const button=document.createElement("button");button.textContent="Executar";
   const output=document.createElement("pre");output.textContent="Ainda não executado";
   button.onclick=async()=>{
    const options={method:method.toUpperCase(),headers:{}};
    if(!body.hidden){
      options.headers["Content-Type"]="application/json";
      options.body=body.value;
    }
    try{
      const response=await fetch(path,options);
      output.textContent=response.status+" "+await response.text();
    }catch(error){output.textContent=String(error);}
   };
   section.append(head,summary,body,button,output);
   main.append(section);
  }
 }
}).catch(error=>document.querySelector("main").textContent=String(error));
</script>
</body>
</html>"""

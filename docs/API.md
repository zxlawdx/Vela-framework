# Vela API: execução, documentação e desempenho

## Documentação local automática

Com \`API={"enabled": True, "host": "127.0.0.1", "port": 8000,
"auto_port": True, "server": "waitress", "workers": 4,
"docs_enabled": True}\`, abra:

- \`/api/docs\` — painel interativo e **offline** de endpoints e teste JSON;
- \`/api/openapi.json\` — contrato OpenAPI 3.0.3;
- \`/api/health\` — funcionamento e tempo de atividade.

Os endpoints utilizam a porta efetiva que o Vela escolher. Desative o
painel com \`"docs_enabled": False\`. Configure a API para localhost quando
o aplicativo não precisar de acesso de rede.

~~~python
from vela.api import api

@api.get("/clientes")
def clientes():
    """Lista clientes."""
    return {"clientes": []}

@api.post("/clientes")
def criar(data: dict):
    """Cria um cliente."""
    return {"recebido": data}
~~~

Modelos Pydantic 2 são opcionais: se o handler aceita
\`data: MeuModelo\`, o Vela usa \`MeuModelo.model_validate()\` e inclui
\`model_json_schema()\` no OpenAPI. Para respostas estruturadas, retorne
\`dict\` ou \`list\` e forneça documentação no docstring.

## Mudanças de desempenho

- O servidor local padrão passou de Bottle single-thread de desenvolvimento
  para **Waitress** (WSGI multithread, quatro workers configuráveis).
  Bottle continua disponível por \`"server": "bottle"\`.
- \`inspect.signature(handler)\` agora é calculado no registro de cada
  rota, em vez de ocorrer a cada requisição.
- Não há conversão de corpo JSON nem headers quando o handler não precisa
  de \`data\`/\`context\`.
- Em produção, o roteador não recarrega módulos em cada navegação;
  \`DEBUG=True\` preserva hot reload de desenvolvimento.
- Templates usam cache LRU e são invalidados quando tamanho/mtime mudam.

Essas otimizações não garantem performance superior ao Django. Compare
tempo de resposta na mesma máquina e **separe** trabalho de DB/IO, HTTP,
serialização JSON e renderização do frontend. O script
\`benchmarks/bench_local_api.py\` mede o despacho local sem rede.
Perfis individuais do Bottle/Waitress e da conexão WebView podem diferir.

## Segurança e publicação

O painel \`/api/docs\` é apenas de desenvolvimento/teste. Em produção,
considere \`docs_enabled=False\` se a documentação revelar endpoints
internos, mesmo em localhost. A porta dinâmica reduz conflitos, mas
**não substitui autenticação** em APIs que exponham ações sensíveis.
Não habilite \`host=0.0.0.0\` sem proteção adicional. Os endpoints
automáticos não fazem autenticação.

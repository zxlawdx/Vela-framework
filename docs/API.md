# Vela API: execução, documentação e desempenho

## Documentação local automática

Com `API={"enabled": True, "host": "127.0.0.1", "port": 8000,
"auto_port": True, "server": "waitress", "workers": 4,
"docs_enabled": True}`, abra:

- `/api/docs` — painel interativo e **offline** de endpoints e teste JSON;
- `/api/openapi.json` — contrato OpenAPI 3.0.3;
- `/api/health` — funcionamento e tempo de atividade.

Os endpoints utilizam a porta efetiva que o Vela escolher. Desative o
painel com `"docs_enabled": False`. Configure a API para localhost quando
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
`data: MeuModelo`, o Vela usa `MeuModelo.model_validate()` e inclui
`model_json_schema()` no OpenAPI. Para respostas estruturadas, retorne
`dict` ou `list` e forneça documentação no docstring.

## Mudanças de desempenho

- O servidor local padrão passou de Bottle single-thread de desenvolvimento
  para **Waitress** (WSGI multithread, quatro workers configuráveis).
  Bottle continua disponível por `"server": "bottle"`.
- `inspect.signature(handler)` agora é calculado no registro de cada
  rota, em vez de ocorrer a cada requisição.
- Não há conversão de corpo JSON nem headers quando o handler não precisa
  de `data`/`context`.
- Em produção, o roteador não recarrega módulos em cada navegação;
  `DEBUG=True` preserva hot reload de desenvolvimento.
- Templates usam cache LRU e são invalidados quando tamanho/mtime mudam.

Essas otimizações não garantem performance superior ao Django. Compare
tempo de resposta na mesma máquina e **separe** trabalho de DB/IO, HTTP,
serialização JSON e renderização do frontend. O script
`benchmarks/bench_local_api.py` mede o despacho local sem rede.
Perfis individuais do Bottle/Waitress e da conexão WebView podem diferir.

## Segurança e publicação

O painel `/api/docs` é apenas de desenvolvimento/teste. Em produção,
considere `docs_enabled=False` se a documentação revelar endpoints
internos, mesmo em localhost. A porta dinâmica reduz conflitos, mas
**não substitui autenticação** em APIs que exponham ações sensíveis.
Não habilite `host=0.0.0.0` sem proteção adicional. Os endpoints
automáticos não fazem autenticação.

## Vela Docs

A interface integrada, configuração e limitações estão em [VELA_DOCS.md](VELA_DOCS.md).

## Janela desktop (pywebview)

A aplicação pode chamar a API reutilizável do shell Vela:

```javascript
await Vela.platform.window.enterFullscreen();
await Vela.platform.window.exitFullscreen();
await Vela.platform.window.toggleFullscreen();
await Vela.platform.window.setFullscreen(true);
const state = await Vela.platform.window.getState();
// { ok, available, fullscreen, managed, width, height }
```

O fullscreen é nativo, acionado por `pywebview.Window.toggle_fullscreen()`,
não é um overlay CSS. Os métodos `setFullscreen` são idempotentes: repetir
`true` ou `false` não alterna a janela novamente. O backend mantém um
estado **gerenciado pela API Vela**; pywebview não fornece uma propriedade
portável que detecte alterações externas feitas pelo sistema operacional.
Não interprete `managed: true` como telemetria nativa independente.

Os eventos são publicados no barramento do Vela:

```javascript
const listener = event => {
  if (event.detail?.name === 'window:state')
    console.log(event.detail.payload.fullscreen);
};
window.addEventListener('vela:event', listener);
// Remova ao destruir a página:
window.removeEventListener('vela:event', listener);
```

Métodos são expostos também na bridge, `window_set_fullscreen(boolean)`,
`window_toggle_fullscreen()` e `window_get_state()`. Erros são estruturados
como `{ok:false,error:...}` na bridge e lançam exceção pela API JS para
permitir tratamento na aplicação. Após fechar a janela o estado é desligado.
O framework não decide qual tecla ativa o recurso: F5 e F11 são atalhos da
aplicação consumidora. Windows/Linux e outras GUIs devem ser validados
nativamente; testes com fakes cobrem somente o contrato de controle.

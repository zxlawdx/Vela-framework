# Arquitetura do Vela Framework

Este documento descreve a arquitetura interna após o hardening do core. A API pública permanece deliberadamente pequena:

```python
from vela import VelaApp

app = VelaApp(settings_module="config.settings")
app.register_app("apps.home")
app.run()
```

## Visão geral

```text
                         +----------------------+
                         |       VelaApp        |
                         |  composition root    |
                         +----------+-----------+
                                    |
        +---------------------------+---------------------------+
        |             |             |             |             |
        v             v             v             v             v
  ConfigLoader      Router       ApiRouter     Lifecycle   HotReloadManager
        |             |             |             |             |
        |             |             v             |             |
        |             |       ApiServer/HTTP      |             |
        |             |       Bottle+Waitress     |             |
        |             |             |             |             |
        |             +------> BaseBridge <-------+-------------+
        |                           |
        |                           v
        +--------------------> DesktopWindow
                                pywebview
```

`VelaApp` é a facade e o composition root. Ele cria e conecta os componentes, mas não implementa routing, parsing de templates, servidor HTTP, hot reload ou lifecycle.

## Configuração

`vela.config.ConfigLoader` carrega a configuração com precedência:

```text
defaults < config/settings.py < argumentos do VelaApp < VELA_PRODUCTION
```

Os modelos `VelaConfig`, `ApiConfig`, `WindowConfig` e `LayoutConfig` usam `dataclass(frozen=True, slots=True)` e validam valores no startup. As chaves legadas (`APP_TITLE`, `WINDOW_WIDTH`, `LAYOUT`, `API`, etc.) continuam aceitas. `VelaApp._config` permanece como representação `dict` de compatibilidade.

`VELA_PRODUCTION=1` força `debug=False`, independentemente do settings local.

## Routing visual

`vela.core.router.Router` mantém dois índices: `path -> Route` e `name -> Route`. Lookup é O(1) médio. Conflitos inesperados de path/nome falham cedo; `Route.render()` executa apenas o handler atual e não possui lógica de hot reload.

`Router.resolve()` retorna `RouteResult` com contrato explícito. 404 e 500 usam `ok=False` e status apropriado. Exceções recebem `VELA-E-<id>`; detalhes ficam em log e são ocultados em produção. As rotas da sidebar são ordenadas uma vez e cacheadas até nova mutação do registry.

## API HTTP

`ApiRouter` usa `dict[(method, path)] -> ApiRoute`. Registro e lookup são O(1) médio; substituir a mesma chave preserva a ordem de inserção. `ApiRoute` calcula `inspect.signature()` e `typing.get_type_hints()` uma vez, no registro.

`vela.core.http` define `Request`, `Response` e `ResponseEncoder`. Forma nova recomendada:

```python
from vela.api import api
from vela.core.http import Request, Response

@api.post("/items")
def create(request: Request):
    return Response({"ok": True, "item": request.json}, status=201)
```

Handlers antigos `handler()`, `handler(data)` e `handler(context)` continuam aceitos. Em debug, `data/context` emitem `DeprecationWarning` quando aplicável.

## HTTP como adapter

`vela.core.interfaces.HttpServer` formaliza a fronteira mínima de servidor. `ApiServer` é o adapter Bottle/Waitress padrão. Bottle não foi removido; a dependência apenas deixou de determinar a arquitetura inteira.

Com Waitress, a porta é vinculada pelo servidor real. Em `auto_port=True`, falha de bind na porta preferida tenta `port=0` no próprio adapter e publica a porta efetivamente vinculada. O helper `resolve_port()` é mantido apenas por compatibilidade e testes do adapter Bottle.

## Rendering

O template engine usa pipeline explícito:

```text
source -> tokenize -> parse -> AST -> CompiledTemplate -> render
```

Nós mínimos: `TextNode`, `VariableNode`, `UrlNode`, `StaticNode` e `ForNode`. Valores de `{{ variavel }}` e `{{ item.campo }}` são escapados automaticamente. `mark_safe()` é a única forma suportada de declarar HTML intencionalmente confiável.

Templates em arquivo são compilados e cacheados por `(path, mtime_ns, size)`. O cache é limitado a 256 entradas e pode ser limpo por `clear_template_cache()`.

## WebView e bridge

`DesktopWindow` é o adapter pywebview. `BaseBridge` é a facade exposta ao JavaScript. Dados vindos da WebView são tratados como input não confiável: paths e payloads são validados antes de alcançar o router.

O shell continua suportando scripts de página por compatibilidade. O boundary é explícito: o template da aplicação é código confiável; dados de contexto não são. Scripts são executados apenas para `RouteResult.ok=True`, nunca para 404/500 internos.

O lifecycle de página suporta `beforeUnmount`, `unmounted` e `mounted`, todos isolados contra exceptions. O listener delegado de links é instalado uma vez no container persistente.

## Hot reload

`HotReloadManager` é o único componente responsável pelo reload em desenvolvimento. Ele rastreia somente módulos explicitamente carregados por `register_app()`, guarda `mtime_ns` e recarrega apenas os módulos alterados.

Após reload, callbacks atualizam referências de handlers no `Router` e `ApiRouter`. Decorators da API executam sob o contexto do router da aplicação, evitando duplicação no registry global. Em `VELA_PRODUCTION=1`, o manager é desativado mesmo se solicitado.

## Estado por aplicação

Cada `VelaApp` possui `Router`, `ApiRouter`, `EventBus`, `LifecycleManager` e `HotReloadManager` próprios. `from vela.api import api` permanece como facade ergonômica, mas usa `contextvars` para delegar ao registry da aplicação corrente. Decorators importados antes da criação do app são tratados como blueprint de compatibilidade e clonados para novas aplicações.

O `vela.events.bus` global permanece apenas como compatibilidade; o core não depende dele.

## Lifecycle e shutdown

Fases:

```text
configure -> startup -> api_start -> window_start -> running -> shutdown
```

`LifecycleManager` controla callbacks de startup/shutdown. Shutdown é idempotente e executa callbacks em ordem reversa. O servidor HTTP e o EventBus da aplicação são registrados para cleanup.

`JobManager` possui backpressure por `BoundedSemaphore`, recusa submit após shutdown e encerra pools de IO/CPU com `cancel_futures=True`.

## Persistência

`SQLiteStore` preserva `foreign_keys=ON`, `busy_timeout=5000`, migrations ordenadas, SHA-256, imutabilidade da história e transação por migration. WAL + `synchronous=NORMAL` são habilitados quando o ambiente suporta. Dados da tabela `vela_migrations` são inseridos com parâmetros SQL.

## Plugins

`PluginManager` adiciona metadata mínima (`name`, `priority`, `enabled`) e contextualiza falhas por plugin/hook. Entry points continuam explicitamente executados somente quando o fluxo de build chama `apply_build_hooks()`.

## Compatibilidade

Os caminhos antigos principais continuam válidos: `vela.core.app.VelaApp`, `vela.core.router.Router`, `vela.core.api_router.ApiRouter`, `vela.template_engine.engine.render_template`, `from vela.api import api`, handlers `data/context` e `_config` em formato dict. O import recomendado passa a ser `from vela import VelaApp`.

# Arquitetura do Vela Framework

O Vela continua sendo um framework desktop leve: Python + HTML/CSS/JS + WebView, com Bottle/Waitress como adapters HTTP. A arquitetura foi ajustada a partir de problemas observados em aplicações consumidoras reais sem trocar o stack principal.

## Fluxo principal

```text
VelaApp (facade / composition root)
   |
   +--> ConfigLoader / VelaConfig
   +--> AppRegistry ----> AppConfig
   |                        |
   |                        +--> views / urls / api
   |                        +--> static / templates / resources
   |                        +--> reloadable / persistent modules
   |
   +--> Router ----------> TemplateEngine
   +--> ApiRouter -------> ApiServer -------> Bottle / Waitress
   |                          |
   |                          +--> StaticResolver / AssetManifest
   |
   +--> LifecycleManager
   +--> HotReloadManager
   +--> EventBus / JobManager
   +--> Bridge -----------> PlatformServices
   |                          |
   |                          +--> native clipboard
   |
   +--> DesktopWindow ----> pywebview ----> WebView engine
                                  |
                                  v
                            Vela UI Shell
                                  |
                             #vela-app-root
                                  |
                            application DOM
```

A regra arquitetural é: **Vela Runtime é obrigatório; Vela UI Shell é opcional**. Aplicações com shell próprio podem desabilitar sidebar/topbar sem carregar espaçadores ou resets visuais residuais.

## Registro de aplicações

O caminho legado continua aceito:

```python
app.register_app("apps.home")
```

Internamente ele é convertido para `AppConfig`. Aplicações novas podem declarar um manifesto explícito:

```python
from vela.apps import AppConfig

class NetworkConfig(AppConfig):
    def __init__(self):
        super().__init__(
            name="network",
            module="apps.network",
            reloadable_modules=("apps.network.views",),
            persistent_modules=("apps.network.services", "apps.network.providers"),
            hidden_imports=("some_optional_driver",),
        )
```

`register_app()` importa o módulo de API sob o registry da aplicação. Um projeto não precisa importar `apps.foo.api` apenas para provocar o side effect dos decorators.

## Routing e navegação

`Router` mantém índices `path -> Route` e `name -> Route`, com lookup O(1) médio. `RouteResult` representa explicitamente `ok`, `status`, `html`, `layout`, `theme` e `error_id`.

No frontend cada navegação recebe uma generation ID. Uma resposta antiga não pode substituir uma navegação mais recente. Cada página recebe `VelaPage.signal`, um `AbortSignal` cancelado ao sair da página, além dos hooks:

- `beforeMount`
- `mounted`
- `beforeUnmount`
- `unmounted`

O shell usa um único listener delegado para links Vela, evitando listeners globais acumulados a cada render.

## Shell boundary

O host visual é delimitado por `.vela-shell`; o conteúdo da aplicação começa em `#vela-app-root`. Estilos do framework não usam resets globais para `*`, `main`, `dialog`, `button`, `canvas`, `contenteditable` ou `.textLayer`.

O shell não desabilita `user-select`, não injeta padding no app root e não aplica `transform`, `filter`, `backdrop-filter` ou `contain` no container do conteúdo. Isso evita interferência em editores, seleção de texto, Canvas e WebGL.

## Templates

O template engine usa parser/AST/cache. `{{ value }}` e valores de loops são escapados por padrão; HTML intencionalmente confiável usa `mark_safe()`/`SafeHTML`.

`{{ static("css/app.css") }}` delega ao `StaticResolver`, para que o template não conheça o namespace interno de assets.

## Static e build

Os diretórios têm responsabilidades diferentes:

```text
apps/*/static     source static
staticfiles/      collected/runtime static
.vela-build/      workspace temporário de build
 dist/            distribuição final
```

`StaticResolver` define URL, resolução segura e roots. `AssetManifest` registra SHA-256 dos assets coletados. `vela assets verify` valida o contrato antes da distribuição.

## API HTTP

`ApiRouter` usa `dict[(method, path)] -> ApiRoute`, mantendo registro/lookup O(1) médio. O prefixo é responsabilidade do servidor: com `prefix="/api"`, `@api.get("/devices")` publica `/api/devices`. Declarar `/api/devices` no decorator falha cedo em vez de gerar `/api/api/devices`.

Métodos suportados: GET, HEAD, POST, PUT, PATCH, DELETE e OPTIONS. `Request` contém method, path, query, headers, json, body e `path_params`. `Response` centraliza status, headers e content type.

O limite do body é configurado por `API["max_body_size"]`; consumidores não precisam tocar `bottle.BaseRequest`.

## Lifecycle

Estados explícitos:

```text
created -> configured -> starting -> running -> stopping -> stopped
```

`app.stop()` é idempotente. Shutdown executa callbacks em ordem reversa e encerra servidor HTTP, janela quando o backend permite, hot reload, EventBus e demais recursos registrados.

## Hot reload

O Vela não faz mais reload indiscriminado de `apps.*`. `HotReloadManager` observa apenas módulos declarados. Views podem ser reloadable; sessions/providers/services podem ser persistentes. Modules persistentes preservam identidade e estado entre navegações e reloads de UI.

Veja `HOT_RELOAD.md`.

## WebView e bridge

`BaseBridge` é a facade JS/Python. Entrada JS é tratada como não confiável e recebe validação de tipo/tamanho. `Vela.platform.clipboard.writeText()` tenta clipboard nativo pela Bridge e usa fallback DOM seguro; não depende de `navigator.clipboard`.

`Vela.capabilities()` combina capabilities nativas com probes reais do browser para PointerEvent, Canvas, WebGL/WebGL2 e localStorage. O backend não declara capabilities de GPU apenas pelo sistema operacional.

## Compatibilidade

Continuam suportados:

- `from vela import VelaApp`
- `app.register_app("apps.foo")`
- `from vela.api import api`
- handlers legados `handler()`, `handler(data)`, `handler(context)`
- Bottle, Waitress e pywebview
- settings legados `APP_TITLE`, `LAYOUT`, `API`, `STATIC_ROOT`, `SHELL_MODE` etc.

Mudanças deliberadamente mais estritas são documentadas no CHANGELOG e nos documentos de segurança/build.

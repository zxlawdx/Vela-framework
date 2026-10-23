# Auditoria forense de arquitetura e hardening

## 1. Escopo

Auditoria realizada sobre a `main` no commit `175d54f8b8997c70ea34bb302acce038944c2d56`. Foram revisados core, template engine, API/HTTP, bridge/window, runtime, SQLite, plugins, CLI, testes, benchmarks e CI. O objetivo foi corrigir problemas no código, preservando a API pública quando razoável.

## 2. Estado anterior

A base já possuía decisões positivas: page router com dicts, Waitress, cache de leitura de templates, assinatura de handler calculada uma vez por rota HTTP, migrations com SHA-256/foreign keys/busy timeout, jobs, EventBus, plugins explícitos, build offline e `VELA_PRODUCTION`.

Os principais riscos vinham de fronteiras pouco explícitas entre dados e código, estado global e responsabilidades misturadas.

## 3. Achados

| Severidade | Achado | Efeito |
|---|---|---|
| P0 | template context renderizado com `str()` sem escape | HTML/JS injetável na WebView |
| P0 | loop de template também inseria valores crus | bypass equivalente em coleções |
| P0 | shell executava scripts do HTML após `innerHTML` | ampliava impacto de dados injetáveis |
| P0 | 404/500 interpolavam path/exception sem escape | HTML injetável em páginas internas |
| P0 | produção exibia exception da view | vazamento de paths/segredos/detalhes internos |
| P0 | `ModuleNotFoundError` amplo em settings/views | dependência quebrada podia parecer módulo opcional ausente |
| P0 | bridge sempre retornava `ok=True` | 404/500 pareciam sucesso |
| P1 | `ApiRouter` usava lista + busca de duplicata | registro R rotas O(R²) |
| P1 | `Route.render()` fazia hot reload | routing + runtime acoplados |
| P1 | bridge recarregava todos os `apps.*` por navegação | custo proporcional a módulos + side effects duplicados |
| P1 | `vela.api.api` era singleton de estado | vazamento entre apps/testes/reload |
| P1 | binder dependia do nome `data/context` | contrato frágil |
| P1 | serialização HTTP dispersa | comportamento inconsistente |
| P1 | body sem limite explícito | crescimento de memória por payload excessivo |
| P1 | `0.0.0.0` sem opt-in e CORS `*` em debug | exposição acidental |
| P1 | escolha dinâmica de porta fazia probe e fechava socket | race TOCTOU |
| P1 | EventBus da bridge diferente do global | escopo ambíguo |
| P1 | JobManager sem backpressure | fila não limitada |
| P2 | sidebar reordenada a cada leitura | O(R log R) repetido |
| P2 | migrations concatenavam metadata no script | risco de manutenção desnecessário |
| P2 | plugin errors sem metadata explícita | diagnóstico ruim |
| P2 | shell acumulava listener de página | crescimento por navegação |

## 4. Segurança

O risco mais importante era a cadeia:

```text
context não confiável -> str(value) -> HTML -> innerHTML -> script -> pywebview.api
```

Ela foi quebrada no renderer: valores são autoescapados; HTML cru exige `SafeHTML`. Rotas internas também escapam output, erros de produção são redigidos e o shell só executa scripts de uma rota de sucesso.

Paths de template/static agora são resolvidos e validados contra roots reais, incluindo symlinks. A API é loopback por padrão e bind remoto exige opt-in.

## 5. Complexidade

Antes, `ApiRouter.add_route()` varria `routes` para encontrar uma duplicata. Registrar R rotas era O(R²). O hot reload percorria `sys.modules` e recarregava todos os nomes `apps.*` em toda navegação, além do reload adicional em `Route.render()`.

O template engine fazia regex + `.replace()` sobre strings potencialmente crescentes e `rendered_items += rendered` em loops.

Depois:

- API keyed registry: O(1) médio por add/lookup, O(R) para registrar R rotas;
- page router permanece O(1) médio;
- sidebar ordena somente quando o registry muda;
- template AST usa append/join e cache de compilação;
- hot reload faz `stat` somente em módulos rastreados e reload somente nos dirty.

## 6. Problemas arquiteturais

`VelaApp` acumulava configuração, dynamic import, registry global de API, servidor e window startup. Router e Bridge também tinham responsabilidade de reload. A refatoração transformou `VelaApp` em composition root e introduziu fronteiras pequenas, sem DI container ou framework adicional.

## 7. Mudanças implementadas

- `SafeHTML`, `mark_safe()` e autoescaping;
- lexer/parser/AST/`CompiledTemplate`;
- `Route`/`RouteResult` e `ApiRoute` como dataclasses com slots;
- keyed `ApiRouter`;
- `Request`, `Response`, `ResponseEncoder`;
- `ConfigLoader` + configuração tipada;
- `LifecycleManager`;
- `HotReloadManager` seletivo;
- API facade com `contextvars` e router por app;
- HTTP/Window Protocols e adapters existentes preservados;
- bind Waitress real antes de publicar porta;
- remote API opt-in, CORS restrito, body limit;
- EventBus app-scoped, listener isolation/dedupe;
- JobManager bounded;
- WAL SQLite best effort e metadata de migration parametrizada;
- `PluginManager` + metadata/error context;
- lifecycle de página e listener delegado único;
- logging categorizado e error IDs.

## 8. Decisões arquiteturais

### Bottle e Waitress permanecem

O problema era acoplamento, não as bibliotecas. Criar a fronteira `HttpServer` permitiu isolar infraestrutura sem trocar stack.

### pywebview permanece

`DesktopWindow` continua sendo o adapter oficial. O boundary de bridge é documentado e os helpers internos continuam com underscore.

### Scripts inline permanecem por compatibilidade

Removê-los quebraria templates existentes. Em vez disso, a confiança foi explicitada e a origem acidental de script (context data) foi fechada por escaping.

### Sem token obrigatório nesta etapa

Exigir `X-Vela-Token` imediatamente quebraria fetches existentes. Bind loopback, opt-in remoto, CORS remoto explícito, body limit e error redaction foram aplicados agora; token de sessão fica como evolução que precisa de janela de depreciação.

### Sem “Clean Architecture” completa

Foram criadas interfaces apenas nos boundaries HTTP/Window e componentes com responsabilidade real. Router, rendering e SQLite continuam concretos e diretos.

## 9. Testabilidade

Novos testes cobrem XSS, SafeHTML, traversal/symlink, import errors, routing status, API registry, Request/Response, body limit, remote bind, EventBus, jobs, migrations, hot reload e lifecycle. O CI passa a executar lint/format/security check e matriz estratégica de Python/SO.

## 10. Dívidas restantes

- adapter Bottle de desenvolvimento ainda usa resolução consultiva de porta; a eliminação completa da TOCTOU está no caminho Waitress padrão;
- token de sessão HTTP não é obrigatório por compatibilidade com fetch legado;
- scripts inline continuam possíveis em templates confiáveis; CSP/nonce exigiria migração de aplicações;
- shutdown de pywebview é controlado pelo backend/event loop e não possui uma API cross-platform única equivalente ao servidor HTTP;
- plugins continuam código Python totalmente privilegiado por definição;
- parser de template é intencionalmente pequeno e não implementa expressão Python/`if` arbitrário.

# Histórico de alterações

## Unreleased — real-world consumer regressions

### Security

- Shell deixa de aplicar `user-select`/resets globais ao conteúdo da aplicação.
- `StaticResolver` centraliza URL/path e rejeita traversal, absolute paths Windows/POSIX e symlink escape.
- Bridge valida input de navegação/eventos/clipboard e limita payloads expostos pelo frontend.
- Shell de produção deixa de depender de CDN.

### Fixed

- Corrige seleção de texto/contenteditable/PDF text layer afetada pelo CSS global do shell.
- Corrige isolamento de layout para apps com sidebar/topbar desativadas e shell próprio.
- Corrige collectstatic no Windows para não executar shim POSIX de Node/Tailwind (`WinError 193`).
- Corrige API prefix para impedir `/api/api/...` silencioso.
- Request body grande passa a ser configurável por `API.max_body_size` sem patch direto de Bottle.
- Bottle development backend passa a possuir shutdown determinístico e liberar a porta.
- `register_app()` importa o módulo API oficialmente; import manual para side effect deixa de ser necessário.
- Hot reload deixa services/sessions/providers declarados persistentes intactos.
- Dynamic import do CLI não mascara dependência interna ausente.

### Changed

- Adiciona `AppConfig`/`AppRegistry` mantendo `register_app("apps.foo")` compatível.
- Lifecycle passa a usar estados `created/configured/starting/running/stopping/stopped` e `app.stop()` idempotente.
- Navegação frontend usa generation ID, `AbortController` e hooks `beforeMount/mounted/beforeUnmount/unmounted`.
- Static passa a distinguir source, collected runtime, build workspace e distribuição final.
- Asset manifest passa a usar SHA-256.

### Performance

- Mantém Router/ApiRouter O(1) médio e adiciona benchmark de AppConfig/StaticResolver ao corpus do core.
- Hot reload verifica somente módulos rastreados e recarrega apenas módulos dirty.

### Build

- Adiciona resolução cross-platform de Node tools com `.cmd/.exe/.bat` em Windows e `shell=False`.
- Adiciona `vela assets verify` / `python manage.py assets verify`.
- `buildapp` gera `dist/build-report.json`.
- CI cobre Linux e Windows; Windows executa um `npx.cmd` real e collectstatic real.

### WebView

- Adiciona `Vela.platform.clipboard.writeText()` com Bridge nativa e fallback DOM sem `navigator.clipboard`.
- Adiciona `Vela.capabilities()` com probes reais de PointerEvent, Canvas, WebGL/WebGL2 e localStorage.
- Shell evita efeitos globais de composição sobre Canvas/WebGL.

### Developer Experience

- Doctor mostra project root, Python executable, venv root, Vela install path/version, Node/npm/npx e componentes essenciais.
- Doctor alerta quando o virtualenv ativo pertence a outro projeto ou a instalação do Vela está incompleta.
- Adiciona `vela self-test` / `python manage.py self-test`.
- Adiciona corpus `tests/consumer_apps` baseado em DFD-style, app stateful e document editor.
- Adiciona documentação de assets/build, hot reload, WebView e regressões reais.

## Unreleased — hardening arquitetural

### Security

- Templates escapam valores de contexto por padrão, inclusive em loops; `SafeHTML`/`mark_safe()` é opt-in explícito.
- Páginas 404/500 e API redigem exceptions em produção e usam error IDs.
- API fora de loopback exige `allow_remote=True`; CORS wildcard remoto é rejeitado.
- Imports dinâmicos distinguem módulo alvo ausente de dependência interna quebrada.

### Changed

- `VelaApp` atua como composition root de configuração, routing, API, lifecycle, events e hot reload.
- Configuração interna usa dataclasses tipadas mantendo settings legados.
- API usa `Request`/`Response` e encoder centralizado, mantendo handlers `data/context` por compatibilidade.

### Performance

- `ApiRouter` usa registry keyed O(1) médio; registrar R rotas é O(R) médio.
- Sidebar é cacheada até mutação do registry.
- Template engine usa parser/AST/cache e append/join.

## 0.2.2 — reparo do runtime PyInstaller / pkg_resources

- Extra `[build]` instala dependências legadas necessárias ao loader `pkg_resources`.
- `buildapp` detecta/coleta dependências dinâmicas do `pkg_resources` e falha antecipadamente em venv incompleto.
- `doctor` identifica pacotes jaraco faltantes.
- CI exercita `pyi_rth_pkgres` no executável congelado.

## 0.2.1 — correção de pacotes Linux congelados

- Build valida bindings GTK ou QtPy/QtWebEngine antes do PyInstaller.
- Backend selecionado é passado explicitamente ao pywebview.
- PyInstaller coleta bindings do backend escolhido.
- Executável congelado executa `--self-test` antes da publicação do ZIP.

## 0.2.0 — prévia de desenvolvimento

- Build nativo Windows/Linux via PyInstaller.
- Doctor, wizard, install/uninstall e workflows iniciais.
- Waitress multithread e docs OpenAPI offline.
- Jobs, events, updates, plugins e SQLite migrations.

# Histórico de alterações

## Unreleased — hardening arquitetural

### Security

- Templates passam a escapar valores de contexto por padrão, inclusive em loops.
- Adiciona `SafeHTML`/`mark_safe()` como opt-in explícito para HTML confiável.
- Páginas 404/500 e debug da API escapam dados interpolados; produção não expõe exceptions internas e usa error IDs.
- Templates/static validam roots reais e rejeitam traversal e escape por symlink.
- API fora de loopback exige `allow_remote=True`; CORS wildcard remoto é rejeitado e request body possui limite configurável.
- Imports dinâmicos distinguem módulo opcional ausente de dependência interna quebrada.

### Changed

- `VelaApp` passa a atuar como composition root de configuração, routing, API, lifecycle, events e hot reload.
- Configuração interna usa dataclasses tipadas com validação antecipada, preservando settings legados.
- API adota contratos `Request`/`Response` e encoder centralizado, mantendo handlers `data/context` como compatibilidade.
- EventBus e ApiRouter passam a ter escopo por aplicação; facades globais permanecem apenas para compatibilidade/ergonomia.
- Plugins possuem manager/metadata e erros contextualizados.

### Fixed

- `RouteResult` diferencia 200, 404 e 500 e a bridge deixa de retornar `ok=True` em falhas.
- Hot reload deixa de ocorrer dentro de Router/Bridge e passa a recarregar somente módulos rastreados que mudaram.
- Listener delegado de links da página não é acumulado após navegações sucessivas.
- JobManager passa a aplicar backpressure e recusar submits após shutdown.
- Waitress faz bind da porta real antes de publicar a porta efetiva, reduzindo a race TOCTOU do fallback dinâmico.

### Performance

- `ApiRouter` troca lista + busca linear por registry keyed O(1) médio; registrar R rotas passa de O(R²) para O(R) médio.
- Sidebar é cacheada até mutação do registry.
- Template engine compila lexer/parser/AST e renderiza com append/join em vez de cadeias de `replace`/concatenação crescente.
- Signature/type hints de handlers são resolvidos uma vez por rota, fora do hot path HTTP.

### Deprecated

- Handlers de API dependentes exclusivamente dos nomes `data`/`context` continuam funcionando, mas o contrato recomendado é `request: Request` ou modelo tipado.

### Internal

- Adiciona `LifecycleManager`, `HotReloadManager`, Protocols HTTP/Window, testes de hardening e benchmark suite do core.
- SQLite habilita WAL/synchronous NORMAL quando suportado e parametriza metadata de migrations.

## 0.2.2 — reparo do runtime PyInstaller / pkg_resources

- O extra `[build]` instala dependencias legadas do carregador `pkg_resources` (setuptools anterior a 82, jaraco e more-itertools).
- `buildapp` detecta `pkg_resources` e inclui explicitamente suas dependencias dinamicas no executavel congelado; falha antecipadamente se o venv estiver incompleto.
- O assistente `doctor` identifica os pacotes jaraco faltantes, oferece a instalacao com consentimento e mostra erro de empacotamento com orientacoes mais especificas.
- CI passa a exercitar o runtime hook `pyi_rth_pkgres` com `pkg_resources` importado no aplicativo de teste.

## 0.2.1 — correção de pacotes Linux congelados

- Build aborta caso `gi` (GTK) ou `qtpy`/QtWebEngine (Qt) não estejam acessíveis no Python do desenvolvedor.
- Força o backend escolhido ao pywebview, sem depender da ordem padrão de detecção.
- PyInstaller coleta explicitamente QtPy (ou bindings GTK na opção correspondente).
- Executa `--self-test` no executável congelado antes de gerar o ZIP; testes agora verificam imports da GUI selecionada, e não apenas pastas copiadas.
- Documenta a distinção entre bibliotecas GTK do SO e os bindings `gi` usados por Python/venv.

## 0.2.0 — prévia de desenvolvimento (sem tag oficial)

- buildapp: build nativo Windows/Linux e ZIP SHA-256 usando PyInstaller.
- Assistente gráfico Next/Next: init-process:instalation (e installation).
- doctor: diagnóstico e correção com consentimento/Polkit.
- installapp: menu .desktop Linux, atalhos Windows e associação MIME opcional.
- Configuração centralizada de nome, versão, ícone, autor e extensões.
- makeworkflow: GitHub Actions Linux Qt6 e Windows e releases por tags.
- API: Waitress multithread, cache de introspecção e docs OpenAPI offline.
- Produção sem reload de módulos em cada navegação; cache de templates.
- Serviços opcionais: jobs, events, notificações, verificações de updates, hooks de build e SQLite com migrations.
- Testes em Python 3.10/3.12 e smoke build Qt6 no GitHub Actions.

### Limites conhecidos

- Instaladores MSI/DEB/RPM nativos e instalador macOS não inclusos nesta prévia; `--installer` cria scripts e integração no SO.
- Benchmark contra Django **não** foi concluído; performance depende da carga.
- Builds nativos exigem runner do próprio SO; Linux depende de bibliotecas gráficas/glibc compatíveis; a compilação do Qt6 usa fallback de software.

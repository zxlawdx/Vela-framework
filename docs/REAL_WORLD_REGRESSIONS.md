# Regressões de aplicações reais

Este corpus registra bugs de boundary observados em consumidores do Vela sem incorporar lógica de negócio desses projetos ao framework.

| Sintoma | Contexto onde apareceu | Root cause | Correção no Vela | Regressão automatizada |
|---|---|---|---|---|
| seleção de texto/PDF não funcionava | editor/document viewer | shell aplicava `user-select: none` e estilos globais | CSS namespaceado + `#vela-app-root`; sem reset global | `test_shell_isolation.py`, fixture `document_editor` |
| app precisava neutralizar padding/background/layout do shell | apps com shell próprio | runtime e UI padrão estavam acoplados visualmente | sidebar/topbar opcionais, app root neutro | `test_shell_isolation.py` |
| Canvas/WebGL podia herdar efeitos caros | dashboard 3D | estilos em ancestrais podiam criar composição adicional | sem transform/filter/backdrop-filter/contain no app root | shell + fixture stateful |
| clipboard via `navigator.clipboard` instável | aplicação técnica em Qt WebEngine | aplicação dependia diretamente da API do browser | Bridge de clipboard nativo + fallback DOM seguro | `test_webview_platform.py` |
| sessão/provider podia ser recriado em hot reload | aplicação stateful | reload amplo de módulos de app | classificação reloadable/persistent + dirty reload | `test_app_manifest_lifecycle.py`, fixture stateful |
| API precisava ser importada manualmente | app mínimo | decorators dependiam de import side effect fora do framework | `register_app()` importa API module sob registry app-scoped | fixture `minimal_dfd` |
| body grande exigia patch em Bottle | editor/document app | `BaseRequest.MEMFILE_MAX` vazava para consumidor | `API.max_body_size` + 413 padronizado | `test_api_real_world.py` |
| rota `/api/foo` virava `/api/api/foo` | APIs consumidoras | prefixo não tinha semântica explícita | prefixo aplicado uma vez; duplicação falha cedo | `test_api_real_world.py` |
| Windows executava shim POSIX de Node | collectstatic/build | seleção de executável não considerava `.cmd` | resolver cross-platform, argv list e `shell=False` | `test_static_assets.py` + CI Windows real |
| source/static/runtime URL divergiam | apps com assets grandes | não existia contrato único | `StaticResolver`, manifest SHA-256, `assets verify` | `test_static_assets.py`, `test_tooling_real_world.py` |
| artifact podia buildar e ainda ter ambiente incorreto | build desktop | exit code não registrava contexto suficiente | self-test, doctor expandido e `build-report.json` | CI Linux build smoke |
| terminal mostrava `.venv` de outro projeto | desenvolvimento local | prompt shell não prova `sys.executable` | doctor compara project root, venv root, Python e instalação Vela | `test_tooling_real_world.py` |
| instalação Vela parcial só falhava tarde | desenvolvimento/build | doctor não verificava módulos essenciais | self-check de core/CLI/shell/templates | `test_tooling_real_world.py` |
| lib JS moderna falhava em engine antigo | document/editor | versão de engine WebView difere por backend/host | capability probes + documento de compatibilidade; sem falsa promessa de transpile | `test_shell_isolation.py` + docs |

## O que não foi absorvido pelo framework

O Vela não contém parsers Huawei/ZTE/Juniper, lógica de DOCX/PDF/OCR, protocolos de rede ou regras de negócio dos consumidores. O corpus reduz somente responsabilidades de shell, runtime, API, build, assets e WebView.

## Fixtures

```text
tests/consumer_apps/
    minimal_dfd/
    stateful_access_manager/
    document_editor/
```

As fixtures são pequenas de propósito: cada uma reproduz o boundary histórico sem copiar os projetos originais.

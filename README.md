<div align="center">

# ⛵ Vela Framework

**Framework Python para aplicações desktop com HTML, CSS e JavaScript, usando WebView e sem Electron.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Vela](https://img.shields.io/badge/Vela-0.2.2-2563eb?style=for-the-badge)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-alpha-f59e0b?style=for-the-badge)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MPL--2.0-8b5cf6?style=for-the-badge)](LICENSE)

[![CI](https://github.com/zxlawdx/Vela-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/zxlawdx/Vela-framework/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/zxlawdx/Vela-framework?style=flat-square&color=f59e0b)](https://github.com/zxlawdx/Vela-framework/stargazers)
[![Issues](https://img.shields.io/github/issues/zxlawdx/Vela-framework?style=flat-square&color=ef4444)](https://github.com/zxlawdx/Vela-framework/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](https://github.com/zxlawdx/Vela-framework/pulls)

> **Python no backend. Tecnologias web na interface. Runtime desktop empacotável.**
>
> O Vela organiza aplicações desktop em torno de um runtime Python, uma WebView e uma camada web local. O objetivo é permitir que interfaces HTML/CSS/JS convivam com serviços Python, API local, persistência, jobs, eventos e distribuição nativa sem exigir Electron.

</div>

> [!IMPORTANT]
> A versão publicada no pacote é **0.2.2**. A branch `main` também contém alterações ainda não lançadas de hardening arquitetural e correções observadas em aplicações consumidoras reais. Consulte o [CHANGELOG](CHANGELOG.md) antes de fixar comportamento de produção.

---

## Índice

- [O que é o Vela](#o-que-é-o-vela)
- [Principais recursos](#principais-recursos)
- [Arquitetura](#arquitetura)
- [Instalação e primeiro projeto](#instalação-e-primeiro-projeto)
- [Estrutura de projeto](#estrutura-de-projeto)
- [Configuração](#configuração)
- [Apps, rotas e views](#apps-rotas-e-views)
- [API local](#api-local)
- [Templates e segurança](#templates-e-segurança)
- [Assets e collectstatic](#assets-e-collectstatic)
- [Runtime: jobs, eventos, banco e desktop](#runtime-jobs-eventos-banco-e-desktop)
- [Hot reload e lifecycle](#hot-reload-e-lifecycle)
- [Build e distribuição](#build-e-distribuição)
- [CLI](#cli)
- [Compatibilidade](#compatibilidade)
- [Documentação](#documentação)
- [Contribuindo](#contribuindo)
- [Licença e citação](#licença-e-citação)

---

## O que é o Vela

O Vela é um framework autoral em Python para construção de aplicações desktop cuja interface é escrita com tecnologias web. O frontend roda dentro de uma WebView e se comunica com o runtime Python por HTTP local e pela Bridge do `pywebview`.

O framework não tenta transformar uma página web em um executável por simples empacotamento. Ele fornece uma estrutura de aplicação com configuração, registro de apps, routing, templates, API, static pipeline, lifecycle, hot reload, serviços de desktop e ferramentas de build.

O princípio arquitetural atual é:

> **Vela Runtime é obrigatório; Vela UI Shell é opcional.**

Isso permite tanto aplicações que usam sidebar/topbar e navegação fornecidas pelo Vela quanto interfaces com shell totalmente próprio.

### Por que usar

| Área | O que o Vela fornece |
|---|---|
| Desktop | Janela via `pywebview`, com backend selecionável por plataforma |
| Frontend | HTML, CSS, JavaScript, Canvas/WebGL e integração com assets locais |
| Backend | Python, services, repositories, parsers e integrações externas |
| Navegação | Router visual, rotas nomeadas e lifecycle de página |
| API | Bottle/Waitress, OpenAPI 3.0.3 e documentação local offline |
| Templates | Engine própria com escaping por padrão e cache |
| Estado | Módulos persistentes separados de módulos recarregáveis |
| Dados | SQLite local com migrations versionadas por SHA-256 |
| Concorrência | Jobs de I/O e CPU com pools dedicados |
| Desktop services | Clipboard, notificações e consulta opt-in de updates |
| Build | PyInstaller, doctor, wizard, instalador e relatório de build |
| Distribuição | ZIP versionado, checksum SHA-256 e workflow Windows/Linux |

---

## Principais recursos

### Runtime e arquitetura

- `VelaApp` como composition root do runtime.
- `AppRegistry` e `AppConfig` para registro explícito de aplicações.
- Compatibilidade com `app.register_app("apps.meu_app")`.
- Router visual com lookup médio O(1) por path/nome.
- `ApiRouter` indexado por método + path.
- Lifecycle explícito: `created → configured → starting → running → stopping → stopped`.
- `app.stop()` idempotente e shutdown ordenado de recursos.

### Interface e WebView

- Shell opcional com sidebar/topbar.
- Conteúdo isolado em `#vela-app-root`.
- Sem resets globais que quebrem `canvas`, `contenteditable`, seleção de texto ou PDF text layer.
- Navegação com generation ID para impedir resposta antiga de sobrescrever uma navegação nova.
- `AbortController` por página.
- Hooks `beforeMount`, `mounted`, `beforeUnmount` e `unmounted`.
- `Vela.capabilities()` com probes reais de PointerEvent, Canvas, WebGL/WebGL2 e localStorage.
- `Vela.platform.clipboard.writeText()` com Bridge nativa e fallback DOM.

### API e dados

- Waitress multithread como servidor padrão da API local.
- Bottle disponível como backend alternativo.
- OpenAPI 3.0.3 gerado localmente.
- Pydantic 2 opcional para validação/schema.
- Body limit configurável.
- Bind remoto somente quando explicitamente habilitado.
- SQLite com migrations imutáveis e rastreadas por SHA-256.

### Build e DX

- `doctor` para diagnosticar Python, venv, instalação do Vela, GUI e ferramentas.
- `self-test` para smoke test do runtime.
- `assets verify` para validar assets offline e manifest.
- `buildapp` para gerar distribuição PyInstaller.
- `dist/build-report.json` com informações do ambiente de build.
- Wizard gráfico `init-process:installation` / `buildapp --wizard`.
- `installapp` / `uninstallapp`.
- `makeworkflow` para CI/build Windows e Linux.

---

## Arquitetura

```text
VelaApp
 │
 ├── ConfigLoader / VelaConfig
 ├── AppRegistry ───── AppConfig
 │                    ├── views / urls / api
 │                    ├── static / templates / resources
 │                    └── reloadable / persistent modules
 │
 ├── Router ───────── TemplateEngine
 ├── ApiRouter ────── ApiServer ───── Bottle / Waitress
 │                         │
 │                         └── StaticResolver / AssetManifest
 │
 ├── LifecycleManager
 ├── HotReloadManager
 ├── EventBus / JobManager
 ├── Bridge ───────── PlatformServices
 │                         └── clipboard / desktop integration
 │
 └── DesktopWindow ── pywebview ───── WebView engine
                                   │
                                   ▼
                              Vela UI Shell
                                   │
                             #vela-app-root
                                   │
                              Application DOM
```

A arquitetura completa, decisões de design, complexidade e limites estão em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Instalação e primeiro projeto

### 1. Instale o CLI global

O `pipx` é a forma recomendada para disponibilizar o comando `vela` sem misturar dependências com seus projetos:

```bash
python -m pip install pipx
pipx ensurepath
pipx install git+https://github.com/zxlawdx/Vela-framework.git
```

### 2. Crie o projeto

```bash
vela startproject meu_app
cd meu_app
```

### 3. Crie um ambiente virtual

Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> [!NOTE]
> Em Linux, um venv isolado é recomendado para builds com Qt6. Se você escolher GTK e depender do `python3-gi` fornecido pelo sistema, poderá precisar de um ambiente separado criado com `--system-site-packages`. Não altere `pyvenv.cfg` manualmente.

### 4. Instale o framework no projeto

Instalação básica:

```bash
python -m pip install "vela-framework @ git+https://github.com/zxlawdx/Vela-framework.git"
```

Linux com Qt6:

```bash
python -m pip install "vela-framework[qt6] @ git+https://github.com/zxlawdx/Vela-framework.git"
```

Ambiente de build com Qt6:

```bash
python -m pip install "vela-framework[qt6,build] @ git+https://github.com/zxlawdx/Vela-framework.git"
```

### 5. Prepare assets e execute

```bash
python manage.py collectstatic
python manage.py runapp
```

---

## Estrutura de projeto

```text
meu_app/
├── manage.py
├── config/
│   ├── settings.py
│   └── wsgi.py
│
├── apps/
│   └── meu_app/
│       ├── __init__.py
│       ├── api.py                 # opcional
│       ├── views/
│       │   ├── __init__.py
│       │   └── meu_app.py
│       ├── templates/
│       ├── static/
│       ├── services/              # convenção recomendada
│       ├── repositories/          # convenção recomendada
│       └── parsers/               # convenção recomendada
│
├── assets/                        # opcional; ícones/recursos de distribuição
├── migrations/                    # opcional; migrations SQLite
├── staticfiles/                   # gerado por collectstatic
├── .vela-build/                   # workspace temporário de build
└── dist/                          # artefatos distribuíveis
```

`services/`, `repositories/` e `parsers/` são convenções arquiteturais úteis para manter regra de negócio, acesso a dados e parsing fora das views/API.

---

## Configuração

Exemplo de `config/settings.py`:

```python
APP_TITLE = "Meu App Vela"
APP_VERSION = "0.2.0"
APP_ICON = "assets/logo.png"
APP_AUTHOR = "Meu nome"
APP_DESCRIPTION = "Descrição do aplicativo"
APP_FILE_EXTENSIONS = [".meuapp"]

ENTRY_ROUTE = "/home"

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

LAYOUT = {
    "sidebar": True,
    "topbar": True,
    "theme": "light",
}

API = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 8000,
    "auto_port": True,
    "server": "waitress",
    "workers": 4,
    "docs_enabled": True,
    "max_body_size": 2 * 1024 * 1024,
}

DEBUG = True
STATIC_ROOT = "staticfiles"
```

Com `auto_port=True`, a porta configurada é preferencial. Se estiver ocupada, o runtime pode selecionar outra porta livre e propagar a porta efetiva para API, assets e janela.

Em builds distribuídos, o launcher gerado define `VELA_PRODUCTION=1`; o runtime ignora `DEBUG=True`, desabilita hot reload e evita DevTools acidental.

---

## Apps, rotas e views

### Registro simples

`config/wsgi.py`:

```python
from vela.core.app import VelaApp

INSTALLED_APPS = [
    "apps.home",
    "apps.dashboard",
]


def run():
    app = VelaApp(settings_module="config.settings")

    for app_name in INSTALLED_APPS:
        app.register_app(app_name)

    app.run()
```

O registro de uma aplicação importa oficialmente seus componentes, incluindo o módulo de API quando existente. Não é necessário importar `apps.foo.api` manualmente apenas para disparar decorators.

### View

```python
from vela.template_engine import render_template


def home_view(params):
    return render_template(
        "apps/home/templates/index.html",
        {"titulo": "Home"},
        router=params["router"],
    )
```

`apps/home/views/__init__.py`:

```python
from .home import home_view


def register_routes(router):
    router.add(
        "/home",
        home_view,
        name="home",
        title="Home",
        layout="blank",
        show_in_sidebar=False,
    )
```

### AppConfig explícito

Aplicações stateful podem declarar o que é recarregável e o que deve persistir:

```python
from vela.apps import AppConfig


class NetworkConfig(AppConfig):
    def __init__(self):
        super().__init__(
            name="network",
            module="apps.network",
            reloadable_modules=("apps.network.views",),
            persistent_modules=(
                "apps.network.services",
                "apps.network.providers",
                "apps.network.sessions",
            ),
            hidden_imports=("some_optional_driver",),
        )
```

---

## API local

Endpoints ficam separados da navegação visual:

```python
from vela.api import api


@api.get("/clientes")
def listar_clientes():
    return {"clientes": []}


@api.post("/clientes")
def criar_cliente(data: dict):
    return {"recebido": data}
```

Com o prefixo padrão `/api`, esses endpoints ficam disponíveis em:

```text
GET  /api/clientes
POST /api/clientes
```

Não duplique o prefixo no decorator. `@api.get("/api/clientes")` é rejeitado cedo quando o servidor já usa `/api`.

Quando `docs_enabled=True`:

- `/api/docs` — documentação/teste local offline;
- `/api/openapi.json` — OpenAPI 3.0.3;
- `/api/health` — health check e uptime.

Pydantic 2 é opcional. Handlers tipados com um modelo podem usar `model_validate()` e ter schema refletido no OpenAPI.

> [!WARNING]
> O padrão é loopback (`127.0.0.1`). Bind fora de loopback exige configuração explícita e APIs remotas continuam responsáveis por autenticação. A documentação local não deve ser tratada como mecanismo de segurança.

Mais detalhes: [docs/API.md](docs/API.md).

---

## Templates e segurança

O template engine escapa valores por padrão:

```html
<h1>{{ titulo }}</h1>
<p>{{ usuario.nome }}</p>
```

O escaping também se aplica dentro de loops.

HTML intencionalmente confiável precisa ser marcado explicitamente:

```python
from vela.template_engine import mark_safe

context = {
    "conteudo": mark_safe("<strong>HTML confiável</strong>"),
}
```

> [!CAUTION]
> `mark_safe()` não sanitiza conteúdo. Não passe dados de usuário, rede, banco ou dispositivo sem sanitização adequada.

### Assets em templates

```html
<link rel="stylesheet" href="{{ static('meu_app/css/app.css') }}">
<script src="{{ static('meu_app/js/app.js') }}"></script>
```

Não concatene manualmente `/static/` ou `/__vela__/static/`. O `StaticResolver` centraliza URL/path e bloqueia traversal, paths absolutos e symlink escape.

Leia [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md).

---

## Assets e collectstatic

O Vela separa source, runtime, workspace e distribuição:

```text
apps/<app>/static/   source do app
staticfiles/         assets coletados usados pelo runtime
.vela-build/         staging temporário de build
dist/                artefato final
```

`collectstatic` é o entrypoint único para preparar assets:

```bash
python manage.py collectstatic
```

Um projeto pode declarar pipeline Node/Python em `config/settings.py`:

```python
ASSETS = {
    "node": {
        "install": "ci",
        "scripts": ["build:vendor"],
    },
    "hooks": ["tools.build_css:main"],
    "tailwind": False,
}
```

A execução pode validar `node_modules`, solicitar consentimento para `npm ci`/`npm install`, executar scripts declarados, hooks Python, Tailwind quando habilitado e finalmente coletar os arquivos.

O Vela **não instala Node.js/npm no sistema** e não usa `apt`, `choco`, `winget` ou `sudo` para isso.

CI não interativa:

```bash
python manage.py collectstatic --yes
```

Somente diagnóstico, sem instalar dependências locais:

```bash
python manage.py collectstatic --no-install
```

A coleta gera `staticfiles/manifest.json` com SHA-256.

Valide o pacote de assets com:

```bash
python manage.py assets verify
# ou globalmente
vela assets verify
```

Mais detalhes: [docs/ASSETS_AND_BUILD.md](docs/ASSETS_AND_BUILD.md).

---

## Runtime: jobs, eventos, banco e desktop

### Jobs

```python
from vela.jobs import JobManager

jobs = JobManager(io_workers=4, cpu_workers=2)
future = jobs.submit(minha_funcao, dados, mode="io")
```

`mode="cpu"` usa `ProcessPoolExecutor`. Callbacks não acontecem automaticamente na thread da interface.

### Eventos Python → JavaScript

Python:

```python
self.emit("progresso", {"etapa": 2, "total": 5})
```

JavaScript:

```javascript
window.addEventListener("vela:event", (event) => {
  if (event.detail.name === "progresso") {
    console.log(event.detail.payload)
  }
})
```

### SQLite e migrations

```python
from vela.database import SQLiteStore

store = SQLiteStore("meu-app")
store.migrate("migrations")

with store.connect() as db:
    db.execute("INSERT INTO exemplo(valor) VALUES(?)", ("valor",))
    db.commit()
```

CLI:

```bash
python manage.py dbmigrate --dir migrations
```

### Notificações e updates

```python
from vela.desktop import notify, check_for_updates

notify("Meu App", "Operação concluída")
info = check_for_updates("owner/repo", "0.2.0")
```

A consulta de updates é opt-in, usa GitHub Releases e não baixa nem instala atualizações silenciosamente.

Mais detalhes: [docs/RUNTIME.md](docs/RUNTIME.md).

---

## Hot reload e lifecycle

Hot reload é ferramenta de desenvolvimento, não lifecycle de serviços.

O Vela observa somente módulos classificados. Views podem ser recarregáveis enquanto conexões, sessions, providers e services permanecem vivos:

```python
persistent_modules=(
    "apps.access.services",
    "apps.access.providers",
    "apps.access.sessions",
)
```

Isso evita recriar conexão SSH, sessão HTTP autenticada ou provider de hardware a cada navegação.

Em produção, `VELA_PRODUCTION=1` desabilita hot reload.

Leia [docs/HOT_RELOAD.md](docs/HOT_RELOAD.md).

---

## Build e distribuição

O fluxo atual é feito pelo próprio CLI do Vela. **Não é necessário manter um `build.bat` artesanal nem um `launcher.py` manual.** O `buildapp` gera seu próprio entrypoint de produção e usa PyInstaller.

### Diagnóstico

```bash
python manage.py doctor --gui qt6
```

O doctor verifica projeto, interpretador Python, venv, instalação do Vela, backend GUI, Node/npm/npx quando relevantes e dependências necessárias ao build.

Correções que alteram o ambiente/sistema só acontecem com opção explícita:

```bash
python manage.py doctor --gui qt6 --fix
```

### Planejar e compilar

```bash
python manage.py buildapp --dry-run
python manage.py buildapp --gui qt6 --installer
```

Opções úteis:

```text
--gui auto|qt6|qt5|gtk|native
--icon <arquivo>
--installer
--output <diretório>
--dry-run
--tailwind
--plugins
--wizard
```

O build gera, conforme plataforma/opções:

```text
dist/
├── Meu-App/                    # bundle PyInstaller onedir
├── Meu-App-<versão>-<SO>.zip  # distribuição versionada
├── Meu-App-<...>.zip.sha256    # checksum
└── build-report.json           # ambiente, backend, apps, imports e warnings
```

Com `--installer`, o bundle recebe script de instalação do sistema (`Instalar.sh` ou `Instalar.cmd`). Isso **não** significa gerar MSI/EXE Inno Setup, DEB ou RPM.

O build também valida o backend escolhido e executa smoke/self-test do binário congelado antes da publicação do pacote quando aplicável.

### Wizard gráfico

```bash
python manage.py init-process:installation
```

O alias histórico continua disponível:

```bash
python manage.py init-process:instalation
```

Também é possível usar:

```bash
python manage.py buildapp --wizard
```

O wizard conduz seleção de backend, ícone, diagnóstico, build e instalação com confirmações separadas.

### Instalar

Instalação por usuário:

```bash
python manage.py installapp
```

Instalação de sistema:

```bash
python manage.py installapp --scope system
```

Remoção:

```bash
python manage.py uninstallapp --slug Meu-App --yes
```

### Workflow de release

```bash
python manage.py makeworkflow
```

O workflow gerado cria jobs nativos Windows/Linux e pode publicar artefatos para tags `v*`.

> [!IMPORTANT]
> O PyInstaller compila para o sistema operacional em que está sendo executado. Use runners nativos para gerar artefatos Windows e Linux. O suporte macOS ainda é experimental nesta versão.

Leia [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md).

---

## CLI

| Comando | Função |
|---|---|
| `vela startproject <nome>` | Cria um projeto Vela |
| `python manage.py runapp` | Inicia a aplicação desktop |
| `python manage.py startapp <nome>` | Cria um app em `apps/` |
| `python manage.py collectstatic` | Prepara e coleta assets |
| `python manage.py assets verify` | Valida shell, manifest e assets offline |
| `python manage.py self-test` | Executa smoke test do runtime |
| `python manage.py routes` | Lista rotas visuais |
| `python manage.py shell` | Abre shell Python do projeto |
| `python manage.py logs [N]` | Exibe linhas do log mais recente |
| `python manage.py version` | Exibe a versão instalada |
| `python manage.py doctor` | Diagnostica ambiente e backend |
| `python manage.py buildapp` | Gera distribuição e `build-report.json` |
| `python manage.py installapp` | Instala um bundle local |
| `python manage.py uninstallapp` | Remove uma instalação |
| `python manage.py makeworkflow` | Gera workflow de build/release |
| `python manage.py dbmigrate` | Aplica migrations SQLite |
| `python manage.py checkupdates --repo owner/repo` | Consulta release disponível |
| `python manage.py init-process:installation` | Abre wizard de build/instalação |

---

## Compatibilidade

O backend real importa. O Vela expõe capabilities em runtime em vez de assumir que todo engine suporta o mesmo conjunto de APIs.

| Ambiente | Situação atual |
|---|---|
| Linux + Qt6 WebEngine | Tier 1 para smoke de build/runtime na CI |
| Windows core/static/build tooling | Tier 1 na matriz atual |
| Windows WebView interativo | Tier 2; contrato testado, sem sessão gráfica completa na CI |
| Linux GTK/WebKit | Experimental |
| macOS | Experimental nesta versão |

Frontend:

```javascript
const caps = await Vela.capabilities()

if (caps.webgl2) {
  // habilitar recurso específico
}
```

O framework não promete compatibilidade universal entre bibliotecas JavaScript e engines antigos. Empacote seu frontend de acordo com o WebView que pretende suportar.

Mais detalhes: [docs/WEBVIEW_COMPATIBILITY.md](docs/WEBVIEW_COMPATIBILITY.md).

---

## Documentação

| Documento | Conteúdo |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitetura atual e contratos do runtime |
| [ARCHITECTURE_FORENSIC_AUDIT.md](docs/ARCHITECTURE_FORENSIC_AUDIT.md) | Auditoria arquitetural e histórico técnico |
| [API.md](docs/API.md) | API local, OpenAPI e Waitress |
| [ASSETS_AND_BUILD.md](docs/ASSETS_AND_BUILD.md) | Pipeline de assets, manifest e build report |
| [DISTRIBUTION.md](docs/DISTRIBUTION.md) | Build, wizard, instalação e distribuição |
| [HOT_RELOAD.md](docs/HOT_RELOAD.md) | Módulos reloadable/persistent |
| [PERFORMANCE.md](docs/PERFORMANCE.md) | Decisões e medições de desempenho |
| [REAL_WORLD_REGRESSIONS.md](docs/REAL_WORLD_REGRESSIONS.md) | Regressões encontradas em apps consumidores |
| [RUNTIME.md](docs/RUNTIME.md) | Jobs, eventos, SQLite, notificações e plugins |
| [SECURITY_MODEL.md](docs/SECURITY_MODEL.md) | Trust boundaries e hardening |
| [WEBVIEW_COMPATIBILITY.md](docs/WEBVIEW_COMPATIBILITY.md) | Backends e capability probes |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de mudanças e breaking changes |

---

## Contribuindo

Contribuições são bem-vindas.

```bash
git clone https://github.com/zxlawdx/Vela-framework.git
cd Vela-framework
python -m venv .venv
```

Instale dependências de desenvolvimento:

```bash
python -m pip install -e ".[dev]"
```

Execute a suíte antes de enviar alterações:

```bash
pytest
ruff check .
```

Fluxo sugerido:

1. Crie uma branch focada em uma mudança.
2. Adicione testes para correções ou novos contratos.
3. Atualize documentação quando comportamento público mudar.
4. Evite quebrar compatibilidade sem registrar a decisão no changelog.
5. Abra um Pull Request descrevendo comportamento anterior, mudança e validação.

---

## Licença e citação

Vela Framework é distribuído sob a **Mozilla Public License 2.0 (MPL-2.0)**.

Consulte:

- [LICENSE](LICENSE)
- [NOTICE.md](NOTICE.md)
- [docs/LICENSE_AND_CITATION.md](docs/LICENSE_AND_CITATION.md)
- [CITATION.cff](CITATION.cff)

Criador e mantenedor: **Marinaldo da Costa Barroso Filho**.

Para uso acadêmico, utilize o botão **Cite this repository** do GitHub ou os metadados de `CITATION.cff`.

A MPL preserva avisos de autoria nos arquivos cobertos, mas não obriga aplicações criadas com Vela a exibir créditos na interface. Código copiado/modificado a partir de arquivos do framework pode possuir obrigações próprias de redistribuição; confira a documentação de licença antes de distribuir software proprietário.

---

<div align="center">

**Vela Framework — desktop em Python com uma camada web, sem Electron.**

Feito com ☕, Python e muita iteração em aplicações reais.

</div>

## Aplicação inicial

Novos projetos abrem o [Starter App oficial](docs/STARTER_APP.md), com contador Python ↔ JavaScript, temas e assets locais.

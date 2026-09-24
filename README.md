> **Vela 0.2.0 (prévia)**: o framework agora inclui
> [assistente gráfico Next/Next](docs/DISTRIBUTION.md),
> [compilação nativa e instalação](docs/DISTRIBUTION.md),
> [API OpenAPI/Waitress](docs/API.md) e
> [serviços desktop](docs/RUNTIME.md).
> Execute \`python manage.py init-process:instalation\` na raiz do projeto;
> também estão disponíveis \`buildapp\`, \`doctor\`, \`installapp\` e
> \`makeworkflow\`. Consulte o [changelog](CHANGELOG.md) para limitações.

<div align="center">

<svg width="160" height="160" viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e3a5f"/>
    </linearGradient>
    <linearGradient id="sail1" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#cbd5e1"/>
    </linearGradient>
    <linearGradient id="sail2" x1="1" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e2e8f0"/>
      <stop offset="100%" stop-color="#94a3b8"/>
    </linearGradient>
    <linearGradient id="water" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1d4ed8"/>
      <stop offset="100%" stop-color="#1e3a8a"/>
    </linearGradient>
    <linearGradient id="hull" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <rect width="160" height="160" rx="24" fill="url(#sky)"/>
  <circle cx="20"  cy="18" r="1"   fill="white" opacity="0.7"/>
  <circle cx="45"  cy="10" r="0.8" fill="white" opacity="0.5"/>
  <circle cx="130" cy="14" r="1.2" fill="white" opacity="0.8"/>
  <circle cx="148" cy="28" r="0.7" fill="white" opacity="0.5"/>
  <circle cx="110" cy="8"  r="1"   fill="white" opacity="0.6"/>
  <circle cx="72"  cy="15" r="0.6" fill="white" opacity="0.4"/>
  <path d="M0 112 Q20 108 40 112 Q60 116 80 112 Q100 108 120 112 Q140 116 160 112 L160 160 L0 160Z" fill="url(#water)" opacity="0.9"/>
  <path d="M0 118 Q30 114 60 118 Q90 122 120 118 Q140 115 160 118 L160 160 L0 160Z" fill="#1e3a8a" opacity="0.7"/>
  <line x1="80" y1="30" x2="80" y2="110" stroke="#94a3b8" stroke-width="2" stroke-linecap="round"/>
  <path d="M80 35 L30 100 L80 100 Z" fill="url(#sail1)" opacity="0.95"/>
  <path d="M80 50 L120 95 L80 95 Z" fill="url(#sail2)" opacity="0.9"/>
  <path d="M38 110 Q50 118 80 120 Q110 118 122 110 L118 114 Q104 124 80 126 Q56 124 42 114Z" fill="url(#hull)"/>
  <line x1="40" y1="100" x2="120" y2="100" stroke="#64748b" stroke-width="1.5" stroke-linecap="round"/>
  <line x1="80" y1="30" x2="118" y2="100" stroke="#94a3b8" stroke-width="0.8" opacity="0.5" stroke-linecap="round"/>
  <line x1="80" y1="30" x2="42"  y2="100" stroke="#94a3b8" stroke-width="0.8" opacity="0.5" stroke-linecap="round"/>
  <ellipse cx="80" cy="120" rx="18" ry="3" fill="white" opacity="0.08"/>
</svg>

<br/>

# Vela Framework

**Framework Python para aplicações desktop modernas — HTML, TailwindCSS e JavaScript, sem navegador.**

<br/>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![pywebview](https://img.shields.io/badge/pywebview-6.2.1-2563eb?style=for-the-badge&logo=windowsterminal&logoColor=white)](https://pywebview.flowrl.com/)
[![Bottle](https://img.shields.io/badge/Bottle-0.13.4-22c55e?style=for-the-badge)](https://bottlepy.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-ready-06b6d4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-Windows%20build-e11d48?style=for-the-badge&logo=windows&logoColor=white)](https://pyinstaller.org/)

<br/>

[![License](https://img.shields.io/badge/license-MIT-f59e0b?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/zxlawdx/Vela-framework?style=flat-square&color=f59e0b)](https://github.com/zxlawdx/Vela-framework/stargazers)
[![Issues](https://img.shields.io/github/issues/zxlawdx/Vela-framework?style=flat-square&color=ef4444)](https://github.com/zxlawdx/Vela-framework/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](https://github.com/zxlawdx/Vela-framework/pulls)

<br/>

> **Desktop nativo. Tecnologias web. Zero Electron.**
>
> Construa aplicações desktop com o stack que você já conhece — Python, HTML, CSS e JavaScript —
> entregues numa janela nativa e leve via pywebview. Empacote para Windows com um único `.bat`.

</div>

---

## Índice

- [Por que Vela?](#por-que-vela)
- [Instalação rápida](#instalação-rápida)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Padrões de desenvolvimento](#padrões-de-desenvolvimento)
  - [settings.py](#settingspy)
  - [wsgi.py](#wsgipy)
  - [views — padrão moderno](#views--padrão-moderno)
  - [API com noc/api.py separado](#api-com-nocapipy-separado)
  - [Services e Repository](#services-e-repository)
  - [launcher.py (Windows/Qt)](#launcherpy-windowsqt)
- [Sistema de templates](#sistema-de-templates)
- [Fluxo completo](#fluxo-completo)
- [Build para Windows](#build-para-windows)
- [Compatibilidade](#compatibilidade)
- [FAQ](#faq)
- [Contribuindo](#contribuindo)

---

## Por que Vela?

<table>
<tr>
<td>

### ✦ Sem Electron
Nenhum Chromium empacotado. A janela usa o WebView **nativo** do SO — leve, rápido, sem overhead.

</td>
<td>

### ✦ Stack familiar
Python no backend, HTML/CSS/JS no frontend. Se você sabe fazer um site, sabe fazer um app Vela.

</td>
<td>

### ✦ Arquitetura limpa
Separação clara entre rotas, views e serviços. Estrutura opinionada para projetos de qualquer tamanho.

</td>
</tr>
</table>

---

## Instalação rápida

> [!NOTE]
> Você precisará do **pipx** instalado. Se não tiver: `pip install pipx && pipx ensurepath`

```bash
# 1. Instalar o CLI globalmente
pipx install git+https://github.com/zxlawdx/Vela-framework.git

# 2. Criar um novo projeto
vela startproject meu_app
cd meu_app

# 3. Criar e ativar o ambiente virtual
python3 -m venv venv --system-site-packages   # Linux/macOS
source venv/bin/activate

# py -3.13 -m venv venv                       # Windows
# venv\Scripts\activate.bat

# 4. Instalar o framework no projeto
pip install git+https://github.com/zxlawdx/Vela-framework.git

# 5. Coletar estáticos e rodar
python manage.py collectstatic
python manage.py runapp
```

> [!WARNING]
> No **Linux**, sempre crie o venv com `--system-site-packages`. Sem essa flag o GTK não funciona dentro do ambiente virtual.

---

## Estrutura do projeto

```
meu_app/
├── manage.py                   # CLI local do projeto
├── launcher.py                 # Ponto de entrada para build Windows (Qt)
│
├── config/
│   ├── settings.py             # Título, tamanho da janela, layout, debug…
│   └── wsgi.py                 # Apps instalados + boot do VelaApp
│
├── apps/
│   └── meu_app/
│       ├── __init__.py
│       ├── urls.py             # Registra rotas visuais (path)
│       ├── views/              # ← padrão moderno: views como pacote
│       │   ├── __init__.py
│       │   └── meu_app.py      # render_template + register_routes
│       ├── api.py              # Endpoints @api.get / @api.post
│       ├── services/           # Lógica de negócio, SSH, I/O, etc.
│       │   ├── __init__.py
│       │   └── meu_service.py
│       ├── repositories/       # Acesso a dados / fontes externas
│       │   └── meu_repo.py
│       ├── parsers/            # Parsing de output, protocolos, etc.
│       │   └── meu_parser.py
│       ├── templates/          # HTML do app
│       └── static/             # JS, CSS e assets do app
│
├── staticfiles/                # Gerado pelo collectstatic
├── data/                       # Dados persistidos localmente (JSON, etc.)
└── logs/
```

### Responsabilidade de cada camada

| Arquivo / pasta | Responsabilidade |
|---|---|
| `urls.py` | Registrar rotas visuais com `path()` |
| `views/` | `render_template` + `register_routes` para o router do Vela |
| `api.py` | Endpoints REST `@api.get` / `@api.post` — importado no `wsgi.py` |
| `services/` | Lógica de negócio, I/O, SSH, integrações externas |
| `repositories/` | Abstração de fontes de dados (OLTs, arquivos, APIs) |
| `parsers/` | Parsing de outputs CLI, protocolos, formatos externos |
| `templates/` | HTML (template engine próprio do Vela) |
| `static/` | JS, CSS e assets do app |
| `config/settings.py` | Configurações globais da janela e do projeto |
| `launcher.py` | Entrada do executável Windows — força pywebview com Qt |

---

## Padrões de desenvolvimento

### settings.py

```python
# config/settings.py

APP_TITLE    = "Meu App"
ENTRY_ROUTE  = "/"

WINDOW_WIDTH  = 1200
WINDOW_HEIGHT = 800

# Controla sidebar, topbar e tema da shell
LAYOUT = {
    "sidebar": False,   # True para apps com múltiplas seções
    "topbar":  False,
    "theme":   "dark",  # ou "light"
}

DEBUG       = False     # True = abre o DevTools do WebView
STATIC_ROOT = "staticfiles"

# Porta preferencial do servidor HTTP interno.
# Se 8000 já estiver em uso, o Vela escolhe outra porta livre automaticamente.
API = {
    "host": "127.0.0.1",
    "port": 8000,
    "auto_port": True,
}
```

---

> [!TIP]
> A porta em `API["port"]` é **preferencial**. Com `auto_port=True`, se outra instância ou processo já estiver usando essa porta, o Vela pede ao sistema operacional uma porta TCP livre e atualiza automaticamente o servidor, o router de assets e a URL da janela. Use `auto_port=False` se quiser falhar imediatamente quando a porta configurada estiver ocupada.

---

### wsgi.py

```python
# config/wsgi.py
from vela.core.app import VelaApp

# Importa os módulos de API para registrar os endpoints @api.*
import apps.meu_app.api  # noqa: F401

INSTALLED_APPS = [
    "apps.login",
    "apps.dashboard",
    "apps.meu_app",
]


def run():
    app = VelaApp(settings_module="config.settings")

    for app_name in INSTALLED_APPS:
        app.register_app(app_name)

    app.run()
```

> [!TIP]
> No `wsgi.py`, importe explicitamente os módulos `api.py` de cada app que define endpoints `@api.*`. O Vela não descobre esses módulos automaticamente — o import é o que registra os endpoints no servidor Bottle interno.

---

### views — padrão moderno

O padrão atual usa `views/` como **pacote** e expõe a função `register_routes` para o router visual do Vela.

```python
# apps/dashboard/views/dashboard.py
from vela.template_engine.engine import render_template
from apps.noc.context import olt_context


def dashboard_view(params: dict) -> str:
    return render_template(
        "apps/dashboard/templates/index.html",
        context=olt_context("Dashboard"),
        router=params["router"],
    )
```

```python
# apps/meu_app/views/__init__.py
from vela.urls import path
from apps.meu_app.views.meu_app import meu_app_view


urlpatterns = [
    path("/", meu_app_view),
]


def register_routes(router):
    """
    O Vela procura esta função dentro de apps.<app>.views.
    Sem ela, a navegação visual da janela retorna 404 mesmo com urls.py correto.
    """
    router.add(
        "/",
        meu_app_view,
        name="meu_app_home",
        title="Meu App",
        icon="🛠️",
        layout="blank",        # "blank" remove sidebar/topbar nessa rota
        show_in_sidebar=False,
    )
```

> [!IMPORTANT]
> A função `register_routes(router)` é o que conecta sua view ao roteador visual do Vela. Sem ela, as rotas do `urls.py` vão para a API interna mas a navegação da janela não as encontra.

---

### API com api.py separado

Para apps mais complexos, mantenha os endpoints em um `api.py` separado das views visuais:

```python
# apps/meu_app/api.py
from vela.api import api
from apps.meu_app.services.meu_service import MeuService

service = MeuService()


def _json(context: dict | None) -> dict:
    """Extrai o JSON do context com segurança."""
    if not context:
        return {}
    data = context.get("json") or {}
    return data if isinstance(data, dict) else {}


def _required(data: dict, *fields: str) -> str | None:
    """Retorna o primeiro campo ausente, ou None se tudo OK."""
    for field in fields:
        if data.get(field) in (None, ""):
            return field
    return None


def _safe_call(fn):
    """Wrapper que captura exceções e retorna {"error": ...}."""
    try:
        return fn()
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}


@api.get("/items/")
def list_items(context=None):
    return {"results": service.list()}


@api.post("/items/create/")
def create_item(context=None):
    data = _json(context)
    missing = _required(data, "name", "type")
    if missing:
        return {"error": f"Campo '{missing}' é obrigatório."}
    return _safe_call(lambda: service.create(data))


@api.post("/items/delete/")
def delete_item(context=None):
    data = _json(context)
    missing = _required(data, "id")
    if missing:
        return {"error": f"Campo '{missing}' é obrigatório."}
    return _safe_call(lambda: service.delete(data["id"]))
```

---

### Services e Repository

Para apps com acesso a dados ou integrações externas, o padrão é separar em camadas:

```python
# apps/meu_app/repositories/item_repository.py


class ItemNotFoundError(ValueError):
    pass


class ItemRepository:
    def list(self) -> list[dict]:
        # lê de arquivo, banco, API externa, etc.
        ...

    def get(self, name: str) -> dict:
        item = self._find(name)
        if not item:
            raise ItemNotFoundError(f"Item '{name}' não encontrado.")
        return item

    def exists(self, name: str) -> bool:
        return bool(name and self._find(name))
```

```python
# apps/meu_app/services/item_service.py
from apps.meu_app.repositories.item_repository import ItemRepository


class ItemService:
    def __init__(self, repository: ItemRepository | None = None):
        self.repository = repository or ItemRepository()

    def list(self) -> list[dict]:
        return self.repository.list()

    def create(self, data: dict) -> dict:
        # validações, transformações, persistência
        ...
```

---

### launcher.py (Windows/Qt)

O `launcher.py` é o **ponto de entrada do executável Windows**. Ele força o pywebview a usar Qt em vez do WebView2 nativo do Windows (que pode dar problemas de empacotamento com PyInstaller).

```python
# launcher.py
"""
Launcher desktop — força pywebview com Qt.
Evita Chromium/WebView2 e WinForms no executável final.
"""
import os
import sys
from pathlib import Path

# Força Qt antes de qualquer import do pywebview
os.environ["PYWEBVIEW_GUI"] = "qt"

# Importa explicitamente para o PyInstaller detectar e empacotar
from PyQt5.QtWidgets import QApplication       # noqa: F401
from PyQt5.QtWebEngineWidgets import QWebEngineView  # noqa: F401

import webview
import webview.platforms.qt  # noqa: F401

webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False

_original_start = webview.start


def start_qt(*args, **kwargs):
    kwargs["debug"] = False
    kwargs.pop("gui", None)
    return _original_start(*args, gui="qt", **kwargs)


webview.start = start_qt

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.wsgi import run

if __name__ == "__main__":
    run()
```

> [!NOTE]
> Em **desenvolvimento** (Linux/macOS), continue usando `python manage.py runapp`. O `launcher.py` só é necessário para o build Windows com PyInstaller.

---

## Sistema de templates

O Vela possui um template engine próprio com suporte a variáveis e loops.

### Variáveis

```html
<h1>{{ titulo }}</h1>
<p>Conectado como {{ usuario.nome }}</p>
```

### Loops

```html
<ul>
  {{ for("items") }}
  <li data-path="{{ item.path }}" data-type="{{ item.type }}">
      {{ item.icon }} {{ item.name }}
  </li>
  {{ endfor }}
</ul>
```

### Renderização server-side

```python
from vela.template_engine.engine import render_template


def minha_view(params: dict) -> str:
    return render_template(
        "apps/meu_app/templates/index.html",
        context={"titulo": "Meu App", "items": []},
        router=params["router"],
    )
```

### Estáticos nos templates

```html
<link rel="stylesheet" href="{{ static('meu_app/css/app.css') }}">
<script src="{{ static('meu_app/js/app.js') }}"></script>
```

> [!TIP]
> Sempre rode `python manage.py collectstatic` após adicionar ou modificar arquivos em `static/`. Os arquivos são copiados para `staticfiles/` e servidos em `/__vela__/static/`.

---

## Fluxo completo

```
JavaScript (fetch)
        │
        ▼
http://127.0.0.1:8000/api/…          ← servidor Bottle interno
        │
        ▼
api.py (@api.get / @api.post)         ← endpoint registrado via import no wsgi.py
        │
        ▼
services/                             ← lógica de negócio
        │
        ▼
repositories/ / parsers/              ← acesso a dados e parsing
        │
        ▼
JSON de retorno                       ← Vela serializa automaticamente
        │
        ▼
Frontend (JS atualiza o DOM)
```

A comunicação Python ↔ JS também está disponível via `window.pywebview.api`:

```javascript
const result = await window.pywebview.api.ping()
```

---

## Build para Windows

O Vela usa **PyInstaller + PyQt5** para empacotar a aplicação num executável Windows sem dependências externas. O processo completo está automatizado num script `.bat`.

> [!IMPORTANT]
> O build **deve rodar no próprio Windows**. Cross-compilation (gerar `.exe` a partir do Linux) não é suportada pelo PyInstaller de forma confiável.

### Pré-requisitos

- Python 3.10+ instalado (de preferência 3.13) — disponível no [python.org](https://www.python.org/downloads/windows/)
- Git instalado — disponível em [git-scm.com](https://git-scm.com/download/win)
- PowerShell habilitado (padrão no Windows 10/11)

### requirements.txt para build Windows

```
git+https://github.com/zxlawdx/Vela-framework.git
pyinstaller==6.11.1
pywebview
PyQt5
PyQtWebEngine
qtpy
# suas dependências de projeto abaixo:
# paramiko>=3.4,<4
# keyboard==0.13.5
# pyperclip==1.9.0
```

### build.bat

Crie este arquivo na raiz do projeto:

```bat
@echo off
setlocal
cd /d "%~dp0"

set PYTHONNOUSERSITE=1

echo.
echo Limpando builds anteriores...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist package rmdir /s /q package
if exist MeuApp-Windows.zip del MeuApp-Windows.zip

echo.
echo Preparando ambiente virtual...
if not exist venv (
    py -3.13 -m venv venv
)
call venv\Scripts\activate.bat

echo.
echo Instalando dependencias...
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-user -r requirements.txt
python -m pip install --no-user --force-reinstall pyinstaller pywebview PyQt5 PyQtWebEngine qtpy

echo.
echo Testando Qt...
python -c "import qtpy; from PyQt5.QtWidgets import QApplication; from PyQt5.QtWebEngineWidgets import QWebEngineView; print('Qt OK')"
if errorlevel 1 (
    echo ERRO: Qt nao funciona no venv. Verifique a instalacao.
    pause & exit /b 1
)

echo.
echo Coletando estaticos...
python manage.py collectstatic --noinput

echo.
echo Gerando executavel com PyInstaller...
python -m PyInstaller --noconfirm --clean --onedir --windowed ^
  --name MeuApp ^
  --add-data "apps;apps" ^
  --add-data "config;config" ^
  --add-data "staticfiles;staticfiles" ^
  --collect-all vela ^
  --collect-submodules vela ^
  --collect-all PyQt5 ^
  --collect-all PyQtWebEngine ^
  --collect-all webview ^
  --collect-all qtpy ^
  --hidden-import=vela ^
  --hidden-import=vela.core ^
  --hidden-import=vela.core.app ^
  --hidden-import=vela.template_engine ^
  --hidden-import=vela.template_engine.engine ^
  --hidden-import=webview ^
  --hidden-import=webview.platforms.qt ^
  --hidden-import=qtpy ^
  --hidden-import=qtpy.QtCore ^
  --hidden-import=qtpy.QtGui ^
  --hidden-import=qtpy.QtWidgets ^
  --hidden-import=PyQt5 ^
  --hidden-import=PyQt5.QtCore ^
  --hidden-import=PyQt5.QtGui ^
  --hidden-import=PyQt5.QtWidgets ^
  --hidden-import=PyQt5.QtWebEngineWidgets ^
  --hidden-import=PyQt5.QtWebEngineCore ^
  --hidden-import=PyQt5.QtWebChannel ^
  --exclude-module=webview.platforms.winforms ^
  --exclude-module=clr ^
  --exclude-module=pythonnet ^
  launcher.py

if errorlevel 1 (
    echo ERRO: PyInstaller falhou.
    pause & exit /b 1
)

echo.
echo Copiando arquivos do projeto para a dist...
robocopy apps         dist\MeuApp\apps         /E /XD __pycache__
robocopy config       dist\MeuApp\config       /E /XD __pycache__
robocopy staticfiles  dist\MeuApp\staticfiles  /E /XD __pycache__
:: Se tiver pasta de dados persistidos:
:: robocopy data dist\MeuApp\data /E /XD __pycache__

echo.
echo Preparando pacote final...
if exist package rmdir /s /q package
mkdir package
robocopy dist\MeuApp package\MeuApp /E /XD __pycache__

echo.
echo Gerando ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Sleep 3; Compress-Archive -Path '.\package\MeuApp' -DestinationPath '.\MeuApp-Windows.zip' -Force"

if not exist MeuApp-Windows.zip (
    echo ERRO: Nao foi possivel gerar o ZIP.
    echo Feche o MeuApp.exe e qualquer Explorer apontando para dist/ ou package/.
    pause & exit /b 1
)

echo.
echo Build finalizado: MeuApp-Windows.zip
pause
```

### Como rodar o build

```bat
REM No Windows, com o PowerShell ou CMD:
build.bat
```

O script:
1. Cria um venv limpo com Python 3.13
2. Instala todas as dependências (incluindo PyQt5 e PyInstaller)
3. Coleta os estáticos
4. Gera o executável com PyInstaller (`--onedir --windowed`)
5. Copia os arquivos do projeto para dentro da `dist/`
6. Empacota tudo em `MeuApp-Windows.zip` pronto para distribuição

### Resultado

```
dist/
└── MeuApp/
    ├── MeuApp.exe          ← executável principal
    ├── _internal/          ← DLLs, Python runtime, Qt, etc.
    ├── apps/               ← código dos apps (copiado pelo robocopy)
    ├── config/             ← settings e wsgi
    └── staticfiles/        ← HTML, CSS, JS coletados
```

> [!WARNING]
> **Não feche o Explorer apontando para `dist/` ou `package/`** durante o build — o PowerShell não consegue compactar pastas abertas no Explorer e o ZIP vai falhar. Se acontecer, feche o Explorer e rode `build.bat` de novo.

### Troubleshooting de build

<details>
<summary><strong>Qt/PyQtWebEngine não instala no venv</strong></summary>

```bat
python -m pip install --force-reinstall PyQt5 PyQtWebEngine qtpy
```

Se persistir, certifique-se de que o Python foi instalado **para todos os usuários** (não só para o usuário atual) e que o `pip` é o do venv, não o global.
</details>

<details>
<summary><strong>App abre e fecha imediatamente (sem janela)</strong></summary>

Rode via CMD para ver o erro:

```bat
cd dist\MeuApp
MeuApp.exe
```

O console vai mostrar o traceback. Geralmente é um `ModuleNotFoundError` de um `--hidden-import` faltando.
</details>

<details>
<summary><strong>Estáticos não carregam no executável</strong></summary>

Verifique se o `robocopy staticfiles dist\MeuApp\staticfiles` rodou sem erro (código de saída ≥ 8 = falha). Rode `python manage.py collectstatic` manualmente antes do build e confirme que `staticfiles/` está populado.
</details>

<details>
<summary><strong>Janela abre em branco / sem conteúdo</strong></summary>

Confirme que o `ENTRY_ROUTE` em `settings.py` bate com uma rota registrada via `register_routes`. Rode com `DEBUG = True` temporariamente para inspecionar no DevTools.
</details>

---

## Comandos do CLI

| Comando | Descrição |
|---|---|
| `vela startproject <nome>` | Cria um novo projeto |
| `python manage.py runapp` | Inicia a aplicação |
| `python manage.py startapp <nome>` | Cria um novo app dentro do projeto |
| `python manage.py collectstatic` | Copia estáticos de cada app para `staticfiles/` |
| `python manage.py routes` | Lista todas as rotas registradas |
| `python manage.py shell` | Abre um shell Python com o contexto do projeto |
| `python manage.py logs` | Exibe os logs do projeto |

---

## Compatibilidade

| Sistema operacional | Backend de renderização | Build |
|---|---|---|
| 🐧 Linux | GTK + WebKit2 | `python manage.py runapp` |
| 🪟 Windows (dev) | WebView2 (Edge) | `python launcher.py` |
| 🪟 Windows (dist) | Qt + QtWebEngine | `build.bat` → `.exe` |
| 🍎 macOS | WKWebView | `python manage.py runapp` |

### Dependências Linux (Ubuntu/Debian)

```bash
sudo apt install -y \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-3.0 \
  gir1.2-webkit2-4.1 \
  libgirepository-2.0-dev \
  libcairo2-dev \
  pkg-config \
  python3-dev
```

---

## FAQ

<details>
<summary><strong>No module named 'gi'</strong></summary>

```bash
sudo apt install python3-gi
```
</details>

<details>
<summary><strong>pywebview não abre a janela</strong></summary>

```bash
sudo apt install gir1.2-webkit2-4.1
```
</details>

<details>
<summary><strong>Comando `vela` não encontrado após pipx install</strong></summary>

```bash
pipx ensurepath
# Reabra o terminal
```
</details>

<details>
<summary><strong>No module named 'vela'</strong></summary>

```bash
pip install -e .
```
</details>

<details>
<summary><strong>Estáticos com caminho <code>file://</code></strong></summary>

Isso indica que o `collectstatic` não foi executado, ou que há uma instância duplicada de `VelaApp`. Verifique:

1. `python manage.py collectstatic` foi rodado?
2. `VelaApp` é instanciado **apenas uma vez** em `wsgi.py`?
</details>

<details>
<summary><strong>register_routes não é chamado / rota retorna 404</strong></summary>

Confirme que `views/__init__.py` (ou `views.py`) expõe a função `register_routes(router)`. O Vela procura por ela automaticamente ao registrar o app — sem ela, as rotas visuais não são conectadas mesmo com `urls.py` correto.
</details>

---

## Contribuindo

Contribuições são muito bem-vindas!

1. Faça um fork do repositório
2. Crie uma branch: `git checkout -b feat/minha-feature`
3. Commit suas mudanças: `git commit -m 'feat: adiciona minha feature'`
4. Push: `git push origin feat/minha-feature`
5. Abra um Pull Request

---

<div align="center">

Feito com ☕ e Python

[![GitHub](https://img.shields.io/badge/GitHub-zxlawdx-181717?style=flat-square&logo=github)](https://github.com/zxlawdx/Vela-framework)

</div>

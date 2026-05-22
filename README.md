# Vela Framework

> Framework Python para aplicações desktop usando HTML, TailwindCSS e JavaScript — sem navegador.

---

# O que é o Vela?

O **Vela Framework** é um framework desktop baseado em tecnologias web.

O desenvolvedor utiliza:

- Python para backend;
- HTML para estrutura;
- TailwindCSS/CSS para design;
- JavaScript para interações;
- pywebview para abrir tudo em uma janela desktop nativa.

O objetivo do Vela é permitir aplicações desktop modernas sem Electron e sem navegador aberto para o usuário final.

---

# Filosofia do Framework

O Vela tenta manter uma arquitetura simples e organizada:

```txt
Frontend (HTML/JS)
        ↓
API do Vela
        ↓
Views / Services
        ↓
Sistema operacional / banco / rede / arquivos
```

Separação das responsabilidades:

| Camada | Responsabilidade |
|---|---|
| urls.py | registrar endpoints |
| views.py | lógica das rotas |
| services.py | regra de negócio |
| templates/ | HTML |
| static/ | JS/CSS/imagens |

---

# Como o Vela funciona

O framework possui duas partes:

```txt
1. CLI global → vela
2. Projeto local → manage.py
```

---

# CLI global

Cria projetos:

```bash
vela startproject meu_app
```

---

# CLI local

Administra o projeto:

```bash
python manage.py runapp
```

---

# Fluxo completo

```bash
# instalar globalmente
pipx install git+https://github.com/zxlawdx/Vela-framework.git

# criar projeto
vela startproject meu_app

# entrar no projeto
cd meu_app

# criar ambiente virtual
python3 -m venv venv --system-site-packages

# ativar
source venv/bin/activate

# instalar framework
pip install git+https://github.com/zxlawdx/Vela-framework.git

# coletar arquivos estáticos
python manage.py collectstatic

# rodar aplicação
python manage.py runapp
```

---

# Estrutura do framework

```txt
Vela-framework/
├── README.md
├── pyproject.toml
├── requirements.txt
└── vela/
   ├── __init__.py
   ├── api.py
   ├── urls.py
   │
   ├── cli/
   │  ├── commands.py
   │  ├── collectstatic.py
   │  ├── main.py
   │  └── shell.py
   │
   ├── core/
   │  ├── app.py
   │  ├── api_loader.py
   │  ├── api_router.py
   │  ├── api_server.py
   │  ├── bridge.py
   │  ├── router.py
   │  ├── shell.html
   │  └── window.py
   │
   ├── log/
   │  └── logger.py
   │
   ├── template_engine/
   │  └── engine.py
   │
   └── templates/
      └── project/
```

---

# Estrutura de um projeto Vela

```txt
meu_app/
├── manage.py
│
├── config/
│  ├── settings.py
│  └── wsgi.py
│
├── apps/
│  ├── home/
│  ├── dashboard/
│  └── folder_tree/
│
├── staticfiles/
│
└── logs/
```

---

# Estrutura recomendada de um app

```txt
folder_tree/
├── services.py
├── urls.py
├── views.py
├── __init__.py
├── templates/
└── static/
```

---

# Responsabilidade de cada arquivo

## urls.py

Responsável por registrar endpoints.

Exemplo:

```python
from vela.urls import path
from apps.folder_tree.views import list_folders

urlpatterns = [
    path("/folders/", list_folders),
]
```

---

## views.py

Responsável pelas APIs e renderização.

---

## services.py

Responsável pela lógica de negócio.

Ideal para:

- leitura de arquivos;
- parsing;
- scanners;
- monitoramento;
- ping;
- banco de dados;
- integrações externas;
- validações.

---

# Sistema de URLs

O Vela utiliza:

```python
from vela.urls import path
```

Exemplo:

```python
urlpatterns = [
    path("/folders/", list_folders),
]
```

---

# Sistema de API

O framework possui decorators:

```python
@api.get()
@api.post()
```

Eles registram endpoints automaticamente no servidor Bottle interno do framework.

---

# Exemplo completo de API

## apps/folder_tree/views.py

```python
from pathlib import Path
import webview

from bottle import request

from vela.api import api
from vela.template_engine.engine import render_template


@api.post("/folders/")
def list_folders(context):
    """
    Lista arquivos e pastas de um diretório.
    """

    data = request.json or {}

    path = data.get("path")

    if not path:
        return {
            "error": "path não enviado"
        }

    p = Path(path)

    if not p.exists():
        return {
            "error": "pasta não existe"
        }

    items = []

    for item in p.iterdir():

        items.append({
            "name": item.name,
            "path": str(item),
            "type": "folder" if item.is_dir() else "file",
            "icon": "📁" if item.is_dir() else "📄",
            "arrow": "›" if item.is_dir() else ""
        })

    return items
```

---

# Explicação do endpoint

## request.json

Pega JSON enviado pelo frontend.

Exemplo:

```json
{
  "path": "/home/law"
}
```

---

## Path(path)

Transforma string em objeto pathlib.

---

## p.iterdir()

Lista arquivos e diretórios.

---

## return items

O Vela converte automaticamente para JSON.

---

# Selecionando pasta nativamente

O Vela consegue acessar recursos nativos do sistema via pywebview.

---

## Exemplo

```python
@api.get("/select-folder/")
def select_folder(context):

    folder = webview.windows[0].create_file_dialog(
        webview.FileDialog.FOLDER
    )

    if not folder:
        return {"path": None}

    return {"path": folder[0]}
```

---

# O que isso faz?

Abre o seletor de pastas nativo:

- Windows Explorer;
- Nautilus;
- Finder;
- etc.

---

# Renderização server-side

O Vela possui um template engine próprio.

---

# Exemplo

```python
@api.post("/render-folders/")
def render_folders(context):

    folders = context["json"].get("folders", [])

    html = render_template(
        "apps/home/templates/components/folders.html",
        {
            "folders": folders
        }
    )

    return html
```

---

# context["json"]

O Vela já entrega o JSON parseado automaticamente.

---

# render_template()

Renderiza HTML no backend.

---

# Exemplo de template

```html
{{ for("folders") }}

<li
    data-path="{{ item.path }}"
    data-name="{{ item.name }}"
    data-type="{{ item.type }}"
>
    {{ item.icon }}
    {{ item.name }}
</li>

{{ endfor }}
```

---

# Lendo conteúdo de arquivos

```python
@api.get("/file-content/")
def context_file(context):

    path = request.query.get("path")

    if not path:
        return {
            "error": "Path não enviada"
        }

    try:

        content = Path(path).read_text(
            encoding="utf-8"
        )

        return {
            "content": content
        }

    except Exception as e:

        return {
            "error": str(e)
        }
```

---

# request.query

Usado para parâmetros GET.

Exemplo:

```txt
/file-content/?path=/home/law/teste.py
```

---

# Fluxo frontend → backend

```txt
JavaScript
    ↓
fetch()
    ↓
API do Vela
    ↓
@api.post("/folders/")
    ↓
views.py
    ↓
services.py (opcional)
    ↓
JSON / HTML
    ↓
Frontend
```

---

# Exemplo frontend

```javascript
const response = await fetch(
    "http://127.0.0.1:8000/api/folders/",
    {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            path: "/home/law"
        })
    }
)

const data = await response.json()
```

---

# Organização recomendada

## Projetos pequenos

Pode deixar tudo em `views.py`.

---

## Projetos médios/grandes

Separar:

```txt
views.py
services.py
urls.py
```

---

# Exemplo ideal

## services.py

```python
from pathlib import Path


def get_folders(path):

    p = Path(path)

    return list(p.iterdir())
```

---

## views.py

```python
from vela.api import api

from apps.folder_tree.services import get_folders


@api.post("/folders/")
def list_folders(context):

    data = context["json"]

    folders = get_folders(
        data["path"]
    )

    return folders
```

---

# Sistema de templates

O template engine suporta:

## Variáveis

```html
{{ titulo }}
```

---

## Loops

```html
{{ for("items") }}

{{ item.name }}

{{ endfor }}
```

---

# Estáticos

Cada app possui:

```txt
static/
```

Exemplo:

```txt
apps/home/static/js/app.js
```

Depois:

```bash
python manage.py collectstatic
```

---

# Resultado

```txt
staticfiles/home/js/app.js
```

---

# Usando nos templates

```html
<script src="{{ static('home/js/app.js') }}"></script>
```

---

# Sistema interno HTTP

Internamente o Vela sobe um servidor Bottle:

```txt
http://127.0.0.1:8000
```

A shell do framework é aberta em:

```txt
/__vela__/shell
```

---

# Sistema de estáticos

Arquivos estáticos são servidos por:

```txt
/__vela__/static/
```

Isso evita problemas com:

```txt
file://
```

---

# Comunicação Python ↔ JS

O pywebview expõe:

```javascript
window.pywebview.api
```

---

# Exemplo

```javascript
const result = await window.pywebview.api.ping()
```

---

# Configurações

## config/settings.py

```python
APP_TITLE = "Meu App"

ENTRY_ROUTE = "/home"

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

DEBUG = True

STATIC_ROOT = "staticfiles"
```

---

# Registrando apps

## config/wsgi.py

```python
from vela.core.app import VelaApp

INSTALLED_APPS = [
    "apps.home",
    "apps.dashboard",
    "apps.folder_tree",
]


def run():

    app = VelaApp(
        settings_module="config.settings"
    )

    for app_name in INSTALLED_APPS:
        app.register_app(app_name)

    app.run()
```

---

# Dependências Python

## pyproject.toml

```toml
[project]
name = "vela-framework"
version = "0.1.0"
requires-python = ">=3.10"

dependencies = [
    "pywebview==6.2.1",
    "bottle==0.13.4",
    "proxy_tools==0.1.0",
    "typing_extensions==4.15.0"
]

[project.scripts]
vela = "vela.cli.main:main"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

---

# Linux

O pywebview depende de GTK/WebKit2.

---

# Ubuntu/Debian

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

# IMPORTANTE

No Linux:

```bash
python3 -m venv venv --system-site-packages
```

Sem isso o GTK pode não funcionar dentro do venv.

---

# Problemas comuns

## No module named gi

Instale:

```bash
sudo apt install python3-gi
```

---

## pywebview não abre

Instale:

```bash
gir1.2-webkit2-4.1
```

---

## vela não encontrado

```bash
pipx ensurepath
```

---

## No module named 'vela'

```bash
pip install -e .
```

---

## file:// nos estáticos

Isso normalmente significa que:

- `collectstatic` não foi executado;
- `base_url` não foi configurado;
- existe duplicação da classe `VelaApp`.

---

# Comandos do framework

## Criar projeto

```bash
vela startproject meu_app
```

---

## Rodar app

```bash
python manage.py runapp
```

---

## Criar app

```bash
python manage.py startapp dashboard
```

---

## Coletar estáticos

```bash
python manage.py collectstatic
```

---

## Ver rotas

```bash
python manage.py routes
```

---

## Shell

```bash
python manage.py shell
```

---

## Logs

```bash
python manage.py logs
```

---

# Compatibilidade

| Sistema | Backend |
|---|---|
| Linux | GTK + WebKit2 |
| Windows | WebView2 |
| macOS | WKWebView |

---

# Status atual do framework

O Vela atualmente possui:

- CLI global;
- CLI local;
- sistema de apps;
- sistema de rotas;
- APIs REST internas;
- template engine;
- renderização server-side;
- pywebview;
- integração Python ↔ JS;
- sistema de estáticos;
- layouts;
- suporte a TailwindCSS;
- Bottle integrado;
- hot reload simples;
- integração com filesystem;
- janelas desktop nativas.

# Vela Framework

> Framework Python para aplicações desktop usando HTML, CSS, Tailwind e JS — sem navegador.

---

# O que é o Vela?

O **Vela Framework** é um framework Python para criação de aplicações desktop com interface baseada em tecnologias web.

A ideia principal é permitir que o desenvolvedor use:

* Python para lógica, serviços, rotas e integração com o sistema;
* HTML para estrutura da interface;
* CSS/Tailwind para design;
* JavaScript para interações;
* pywebview para abrir tudo em uma janela desktop real.

O objetivo é criar aplicações com aparência moderna, responsiva e flexível, sem que o usuário final precise lidar com navegador.

---

# Como o Vela funciona

O Vela possui duas partes principais:

```txt
1. CLI global do framework
2. Projeto criado pelo framework
```

A CLI global é o comando:

```bash
vela
```

Ela serve para criar novos projetos:

```bash
vela startproject meu_app
```

Depois que o projeto é criado, ele possui seu próprio `manage.py`, responsável por rodar e administrar a aplicação:

```bash
python manage.py runapp
```

Esse modelo é parecido com o Django:

```bash
django-admin startproject meu_site
python manage.py runserver
```

No Vela:

```bash
vela startproject meu_app
python manage.py runapp
```

---

# Estrutura atual do framework

Estrutura recomendada do repositório principal do Vela:

```txt
vela_framework/
│
├── pyproject.toml
├── README.md
│
├── vela/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── app.py
│   │   ├── window.py
│   │   ├── bridge.py
│   │   ├── router.py
│   │   └── shell.html
│   │
│   ├── cli/
│   │   ├── main.py
│   │   ├── commands.py
│   │   └── shell.py
│   │
│   ├── log/
│   │   └── logger.py
│   │
│   ├── template_engine/
│   │   └── engine.py
│   │
│   └── templates/
│       └── project/
│           ├── manage.py
│           ├── pyproject.toml
│           ├── config/
│           └── apps/
│
├── logs/
└── .gitignore
```

---

# Estrutura de um projeto criado

Quando você executa:

```bash
vela startproject meu_app
```

O Vela gera algo parecido com:

```txt
meu_app/
│
├── manage.py
│
├── config/
│   ├── settings.py
│   └── wsgi.py
│
├── apps/
│   └── home/
│       ├── views/
│       │   ├── __init__.py
│       │   └── home.py
│       │
│       ├── templates/
│       │   └── index.html
│       │
│       └── static/
│
└── logs/
```

---

# Requisitos

* Python 3.10+
* pip
* pipx
* pywebview
* Dependências gráficas no Linux

---

# Instalando a CLI global do Vela

O recomendado é usar `pipx`.

## Ubuntu/Debian

```bash
sudo apt install pipx -y
pipx ensurepath
```

Depois:

```bash
source ~/.bashrc
```

Teste:

```bash
pipx --version
```

---

# Instalar o Vela globalmente

```bash
pipx install -e ~/Estudos/Personal/Frameworks/vela_framework
```

Reinstalar:

```bash
pipx install -e ~/Estudos/Personal/Frameworks/vela_framework --force
```

Teste:

```bash
vela --help
```

---

# Criando um projeto

```bash
vela startproject dockermanager
```

Depois:

```bash
cd dockermanager
```

---

# Instalando o framework no projeto criado

Crie o ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instale o framework:

```bash
pip install -e ~/Estudos/Personal/Frameworks/vela_framework
```

Depois rode:

```bash
python manage.py runapp
```

Resumo:

```txt
pipx instala o comando global: vela
venv instala a biblioteca: vela
```

---

# Fluxo completo de desenvolvimento local

```bash
# Instalar CLI global
pipx install -e ~/Estudos/Personal/Frameworks/vela_framework

# Criar projeto
vela startproject dockermanager

# Entrar no projeto
cd dockermanager

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar o framework
pip install -e ~/Estudos/Personal/Frameworks/vela_framework

# Rodar aplicação
python manage.py runapp
```

---

# Instalação via GitHub

Instalar CLI:

```bash
pipx install git+https://github.com/zxlawdx/Vela-framework.git
```

Criar projeto:

```bash
vela startproject meu_app
```

Instalar framework dentro do projeto:

```bash
cd meu_app

python3 -m venv venv
source venv/bin/activate

pip install git+https://github.com/zxlawdx/Vela-framework.git
```

Rodar:

```bash
python manage.py runapp
```

---

# Dependências Python

O Vela utiliza `pyproject.toml` como sistema principal de empacotamento.

Exemplo:

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

# Dependências no Windows

O Windows normalmente já possui WebView2.

Se necessário:

```txt
https://developer.microsoft.com/microsoft-edge/webview2/
```

Fluxo:

```bash
python -m venv venv
venv\Scripts\activate

pip install -e .

python manage.py runapp
```

---

# Dependências no Linux Ubuntu/Debian

O pywebview precisa do GTK/WebKit2.

Instale:

```bash
sudo apt update

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

Depois:

```bash
python3 -m venv venv
source venv/bin/activate

pip install -e .
```

---

# Problema comum no Linux

Erro:

```txt
ModuleNotFoundError: No module named 'gi'
```

ou:

```txt
webview.errors.WebViewException:
You must have either QT or GTK with Python extensions installed
```

Mesmo após instalar GTK via `apt`, o `venv` pode não enxergar os pacotes globais.

---

# Solução recomendada

Recrie o ambiente virtual:

```bash
deactivate
rm -rf venv

python3 -m venv venv --system-site-packages

source venv/bin/activate
```

Depois:

```bash
pip install -e .
```

Teste:

```bash
python -c "import gi; print('GTK OK')"
```

Se aparecer:

```txt
GTK OK
```

rode:

```bash
python manage.py runapp
```

---

# Importante sobre Linux + pywebview

No Linux:

* GTK
* WebKit2
* python3-gi

devem ser instalados via `apt`, não via `pip`.

---

# Dependências no macOS

```bash
python3 -m venv venv
source venv/bin/activate

pip install -e .

python manage.py runapp
```

---

# Comandos globais

```bash
vela startproject <nome>
```

Exemplo:

```bash
vela startproject dockermanager
```

---

# Comandos locais do projeto

```bash
python manage.py runapp
python manage.py shell
python manage.py startapp <nome>
python manage.py logs
python manage.py routes
python manage.py version
```

---

# Diferença entre vela e manage.py

```txt
vela
```

CLI global do framework.

---

```txt
manage.py
```

CLI local do projeto criado.

---

# Criando um novo app

```bash
python manage.py startapp dashboard
```

Estrutura:

```txt
apps/dashboard/
├── __init__.py
├── views/
├── templates/
└── static/
```

Registrar em:

```python
INSTALLED_APPS = [
    "apps.home",
    "apps.dashboard",
]
```

---

# Criando uma view

```python
def dashboard_view(params: dict) -> str:
    return '''
    <div>
        <h1 class="text-3xl font-bold">Dashboard</h1>
    </div>
    '''
```

Registrar:

```python
router.add("/dashboard", dashboard_view, title="Dashboard")
```

---

# Comunicação Python ↔ JS

```html
<button onclick="ping()">Ping</button>

<script>
async function ping() {
    const resposta = await window.pywebview.api.ping();
    console.log(resposta);
}
</script>
```

---

# Templates HTML

```python
from vela.template_engine.engine import render_template

def minha_view(params):
    return render_template(
        "apps/home/templates/index.html",
        {
            "titulo": "Olá"
        }
    )
```

Template:

```html
<h1>{{ titulo }}</h1>
```

---

# Compatibilidade

| Sistema | Backend       | Dependências        |
| ------- | ------------- | ------------------- |
| Windows | WebView2      | Normalmente nenhuma |
| Linux   | GTK + WebKit2 | GTK/WebKit2         |
| macOS   | WKWebView     | Normalmente nenhuma |

---

# Problemas comuns

## vela não encontrado

```bash
pipx ensurepath
source ~/.bashrc
```

---

## No module named 'vela'

Instale o framework no venv:

```bash
pip install -e ~/Estudos/Personal/Frameworks/vela_framework
```

---

## No module named 'gi'

Instale:

```bash
sudo apt install -y \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-3.0 \
  gir1.2-webkit2-4.1
```

---

## pywebview não encontra GTK

Recrie o venv:

```bash
python3 -m venv venv --system-site-packages
```

---

## QT não encontrado

```bash
pip install pywebview[qt]
```

ou:

```bash
pip install qtpy PyQt6
```

---

## externally-managed-environment

Use ambiente virtual:

```bash
python3 -m venv .venv

source .venv/bin/activate

pip install -e .
```

---

## build-backend incorreto

Errado:

```toml
build-backend = "setuptools.backends.legacy:build"
```

Correto:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

---

# Status atual

O Vela já possui:

* CLI global;
* CLI local;
* sistema de apps;
* sistema de rotas;
* bridge Python ↔ JS;
* pywebview;
* template engine;
* shell runtime;
* hot reload simples;
* suporte a layouts;
* empacotamento via pyproject.toml;
* instalação via pipx;
* desenvolvimento local via `pip install -e`.

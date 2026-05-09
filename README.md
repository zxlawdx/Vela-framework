# Vela Framework

> Framework Python para aplicações desktop usando HTML, CSS, Tailwind e JS — sem navegador.

---

## O que é o Vela?

O **Vela Framework** é um framework Python para criação de aplicações desktop com interface baseada em tecnologias web.

A ideia principal é permitir que o desenvolvedor use:

- Python para lógica, serviços, rotas e integração com o sistema;
- HTML para estrutura da interface;
- CSS/Tailwind para design;
- JavaScript para interações;
- pywebview para abrir tudo em uma janela desktop real.

O objetivo é criar aplicações com aparência moderna, responsiva e flexível, sem que o usuário final precise lidar com navegador.

---

## Como o Vela funciona

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

## Estrutura atual do framework

Estrutura recomendada do repositório principal do Vela:

```txt
vela_framework/
│
├── pyproject.toml               # Configuração do pacote Python
├── README.md
│
├── vela/                        # Core do framework
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── app.py               # VelaApp — classe principal
│   │   ├── window.py            # Janela desktop usando pywebview
│   │   ├── bridge.py            # Bridge Python ↔ JS
│   │   ├── router.py            # Sistema de rotas
│   │   └── shell.html           # Shell HTML base carregado pelo pywebview
│   │
│   ├── cli/
│   │   ├── main.py              # CLI global: comando vela
│   │   ├── commands.py          # Comandos usados pelo manage.py
│   │   └── shell.py             # Shell interativo
│   │
│   ├── log/
│   │   └── logger.py            # Sistema de logging
│   │
│   ├── template_engine/
│   │   └── engine.py            # Engine de templates HTML
│   │
│   └── templates/
│       └── project/             # Template usado pelo vela startproject
│           ├── manage.py
│           ├── config/
│           ├── apps/
│           └── requirements.txt
│
├── logs/                        # Gerado automaticamente, não deve ir para o pacote
└── .gitignore
```

---

## Estrutura de um projeto criado

Quando você executa:

```bash
vela startproject meu_app
```

O Vela gera uma estrutura parecida com:

```txt
meu_app/
│
├── manage.py                    # CLI local do projeto
│
├── config/
│   ├── settings.py              # Configurações do projeto
│   └── wsgi.py                  # Boot do app + INSTALLED_APPS
│
├── apps/
│   └── home/
│       ├── views/
│       │   ├── __init__.py      # register_routes()
│       │   └── home.py          # View que retorna HTML
│       ├── templates/
│       │   └── index.html
│       └── static/
│
├── logs/                        # Logs gerados automaticamente
└── requirements.txt
```

---

## Requisitos

- Python 3.10 ou superior
- pip
- pipx, recomendado para instalar a CLI global
- pywebview
- Dependências gráficas do sistema no Linux

---

## Instalando a CLI global do Vela

Durante o desenvolvimento local do framework, a melhor forma de instalar o comando `vela` globalmente no seu usuário é usando `pipx`.

### Instalar pipx no Ubuntu/Debian

```bash
sudo apt install pipx -y
pipx ensurepath
```

Depois, feche e abra o terminal.

Ou rode:

```bash
source ~/.bashrc
```

Teste:

```bash
pipx --version
```

---

### Instalar o Vela globalmente em modo desenvolvimento

Dentro do seu computador, apontando para a pasta onde está o framework:

```bash
pipx install -e ~/Estudos/Personal/Frameworks/vela_framework
```

Se ele já estiver instalado e você quiser reinstalar:

```bash
pipx install -e ~/Estudos/Personal/Frameworks/vela_framework --force
```

Depois teste:

```bash
vela --help
```

Saída esperada:

```txt
usage: vela [-h] {startproject} ...

CLI global do Vela Framework
```

---

## Criando um novo projeto

Em qualquer pasta:

```bash
vela startproject dockermanager
```

Depois:

```bash
cd dockermanager
```

---

## Instalando o framework dentro do projeto criado

O comando `vela` global serve para criar projetos.

Mas o projeto criado usa `manage.py`, e o `manage.py` importa o pacote `vela`.

Por isso, dentro do projeto criado, crie um ambiente virtual e instale o Vela também:

```bash
python3 -m venv venv
source venv/bin/activate

pip install -e ~/Estudos/Personal/Frameworks/vela_framework
```

Depois rode:

```bash
python manage.py runapp
```

Resumo:

```txt
pipx instala o comando global: vela
venv do projeto instala a biblioteca: vela
```

---

## Fluxo completo de desenvolvimento local

```bash
# 1. Instalar CLI global
pipx install -e ~/Estudos/Personal/Frameworks/vela_framework

# 2. Criar projeto
vela startproject dockermanager

# 3. Entrar no projeto
cd dockermanager

# 4. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 5. Instalar o framework no projeto
pip install -e ~/Estudos/Personal/Frameworks/vela_framework

# 6. Rodar aplicação
python manage.py runapp
```

---

## Instalação futura via GitHub

Quando o repositório estiver no GitHub, outro desenvolvedor poderá instalar a CLI global assim:

```bash
pipx install git+https://github.com/zxlawdx/Vela-framework.git
```

E criar um projeto:

```bash
vela startproject meu_app
```

Dentro do projeto criado:

```bash
cd meu_app
python3 -m venv venv
source venv/bin/activate
pip install git+https://github.com/zxlawdx/Vela-framework.git
python manage.py runapp
```

Também é possível colocar no `requirements.txt` do projeto:

```txt
git+https://github.com/zxlawdx/Vela-framework.git
```

Assim o dev só roda:

```bash
pip install -r requirements.txt
```

---

## Dependências Python

No `pyproject.toml` do framework:

```toml
[project]
name = "vela-framework"
version = "0.1.0"
description = "Framework Python para aplicações desktop com HTML, CSS, Tailwind e JS"
requires-python = ">=3.10"
dependencies = [
    "pywebview==6.2.1",
    "bottle==0.13.4",
    "proxy_tools==0.1.0",
    "typing_extensions==4.15.0"
]

[project.scripts]
vela = "vela.cli.main:main"

[tool.setuptools.packages.find]
include = ["vela*"]
exclude = ["logs*"]

[tool.setuptools.package-data]
vela = ["templates/project/**/*"]
```

---

## Dependências no Windows

O Windows geralmente já possui suporte ao WebView2 através do Edge Chromium.

Instalação comum:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py runapp
```

Se a janela não abrir por erro de WebView2, instale o runtime:

```txt
https://developer.microsoft.com/microsoft-edge/webview2/
```

---

## Dependências no Linux Ubuntu/Debian

No Linux, o pywebview precisa de um backend gráfico.

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

Depois crie o ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Se aparecer erro como:

```txt
ModuleNotFoundError: No module named 'gi'
```

Você pode recriar o ambiente virtual permitindo acesso aos pacotes do sistema:

```bash
deactivate
rm -rf venv

python3 -m venv venv --system-site-packages
source venv/bin/activate

pip install -r requirements.txt
```

Ou, se estiver desenvolvendo localmente:

```bash
pip install -e ~/Estudos/Personal/Frameworks/vela_framework
```

Depois:

```bash
python manage.py runapp
```

> Importante: no Linux, `python3-gi` normalmente deve ser instalado pelo `apt`, não pelo `pip`.

---

## Dependências no macOS

O macOS usa WebKit nativo.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runapp
```

---

## Comandos globais

Comando disponível depois de instalar via `pipx`:

```bash
vela startproject <nome>
```

Exemplo:

```bash
vela startproject dockermanager
```

---

## Comandos locais do projeto

Dentro de um projeto criado, use:

```bash
python manage.py runapp              # Inicia o app desktop
python manage.py shell               # Shell interativo com contexto do app
python manage.py startapp <nome>     # Cria um novo app
python manage.py logs                # Exibe os últimos 50 logs
python manage.py routes              # Lista todas as rotas registradas
python manage.py version             # Versão do framework
```

---

## Diferença entre vela e manage.py

```txt
vela
```

É a CLI global do framework.

Use para criar novos projetos:

```bash
vela startproject meu_app
```

---

```txt
manage.py
```

É a CLI local de cada projeto criado.

Use para administrar e rodar aquele projeto:

```bash
python manage.py runapp
python manage.py startapp dashboard
python manage.py routes
```

---

## Como criar um novo app

Dentro do projeto:

```bash
python manage.py startapp dashboard
```

Isso cria:

```txt
apps/dashboard/
├── __init__.py
├── views/
│   ├── __init__.py
│   └── dashboard.py
├── templates/
└── static/
```

Depois registre em `config/wsgi.py`:

```python
INSTALLED_APPS = [
    "apps.home",
    "apps.dashboard",
]
```

---

## Como criar uma view

Uma view no Vela é uma função Python que retorna HTML:

```python
# apps/dashboard/views/dashboard.py

def dashboard_view(params: dict) -> str:
    return '''
    <div>
        <h1 class="text-3xl font-bold">Dashboard</h1>
        <p class="text-zinc-400">Olá do Python!</p>
    </div>
    '''
```

Registre a rota em `views/__init__.py`:

```python
from apps.dashboard.views.dashboard import dashboard_view

def register_routes(router):
    router.add("/dashboard", dashboard_view, title="Dashboard")
```

---

## Comunicação Python ↔ JS

No HTML da sua view, você pode chamar funções Python diretamente:

```html
<button onclick="chamarPython()">Clique</button>
<p id="result"></p>

<script>
  async function chamarPython() {
    const resposta = await window.pywebview.api.ping();
    document.getElementById("result").textContent = resposta;
  }
</script>
```

Para expor novas funções Python ao JS, edite ou estenda a bridge:

```python
class MinhaBridge(BaseBridge):
    def minha_funcao(self) -> str:
        return "Olá do Python!"
```

---

## Templates HTML

Use `render_template` para carregar arquivos `.html` de `templates/`:

```python
from vela.template_engine.engine import render_template

def minha_view(params: dict) -> str:
    return render_template("apps/meuapp/templates/index.html", {
        "titulo": "Olá",
        "nome": params.get("nome", "Mundo"),
    })
```

No template:

```html
<h1>{{ titulo }}</h1>
<p>Olá, {{ nome }}!</p>
```

---

## Correção importante no carregamento do shell.html

Arquivos internos do framework não devem ser carregados com `Path.cwd()`.

Errado:

```python
shell_path = Path.cwd() / "vela" / "core" / "shell.html"
```

Certo:

```python
from pathlib import Path

shell_path = Path(__file__).resolve().parent / "shell.html"
```

Motivo:

```txt
Path.cwd()
```

aponta para a pasta onde o comando foi executado.

Já:

```txt
Path(__file__).resolve().parent
```

aponta para a pasta real do arquivo atual, mesmo que o framework esteja instalado em outro lugar.

---

## Compatibilidade

| Sistema      | Backend gráfico       | Instalação extra                         |
|--------------|-----------------------|------------------------------------------|
| Windows 10+  | WebView2              | Normalmente nenhuma                      |
| Linux Ubuntu | GTK + WebKit2         | `python3-gi`, GTK, WebKit2 e libs dev    |
| macOS 10.13+ | WKWebView             | Normalmente nenhuma                      |

---

## Problemas comuns

### Comando vela não encontrado

Rode:

```bash
pipx ensurepath
source ~/.bashrc
```

Teste:

```bash
vela --help
```

Se ainda não funcionar:

```bash
~/.local/bin/vela --help
```

---

### ModuleNotFoundError: No module named 'vela'

Isso acontece quando o `manage.py` está usando um ambiente virtual onde o pacote `vela` não foi instalado.

Resolva dentro do projeto:

```bash
source venv/bin/activate
pip install -e ~/Estudos/Personal/Frameworks/vela_framework
```

Ou via GitHub:

```bash
pip install git+https://github.com/zxlawdx/Vela-framework.git
```

---

### ModuleNotFoundError: No module named 'gi'

No Linux, o pywebview depende do GTK/WebKit2.

Instale as dependências do sistema:

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

---

### pywebview não encontra GTK mesmo após instalar pelo apt

Erro:

```txt
ModuleNotFoundError: No module named 'gi'
```

ou:

```txt
webview.errors.WebViewException:
You must have either QT or GTK with Python extensions installed
```

Isso pode acontecer porque o ambiente virtual (`venv`) não consegue enxergar os pacotes GTK instalados globalmente pelo sistema.

Mesmo após instalar:

```bash
sudo apt install -y \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-3.0 \
  gir1.2-webkit2-4.1
```

o Python dentro do `venv` pode continuar sem acesso ao módulo `gi`.

---

### Solução recomendada para Linux

Recrie o ambiente virtual usando:

```bash
python3 -m venv venv --system-site-packages
```

Exemplo completo:

```bash
deactivate
rm -rf venv

python3 -m venv venv --system-site-packages

source venv/bin/activate

pip install -e ~/Estudos/Personal/Frameworks/vela_framework
```

Depois teste:

```bash
python -c "import gi; print('GTK OK')"
```

Se aparecer:

```txt
GTK OK
```

o pywebview conseguirá usar GTK corretamente.

Depois rode:

```bash
python manage.py runapp
```

---

### Importante sobre Linux + pywebview

No Linux, o `pywebview` normalmente depende de:

* GTK
* WebKit2
* python3-gi

Esses pacotes devem ser instalados via `apt`, não via `pip`.

O `pip` normalmente NÃO consegue instalar corretamente o backend GTK do sistema.

---

### Não misture requirements.txt com pyproject.toml

O Vela está migrando para:

```txt
pyproject.toml
```

Então alguns projetos podem não possuir mais:

```txt
requirements.txt
```

Nesses casos, não rode:

```bash
pip install -r requirements.txt
```

Use:

```bash
pip install -e .
```

ou:

```bash
pip install git+https://github.com/zxlawdx/Vela-framework.git
```

---

### Após recriar o venv, reinstale o framework

Ao recriar o ambiente virtual, o pacote `vela` deixa de existir naquele ambiente.

Então é necessário reinstalar:

```bash
pip install -e ~/Estudos/Personal/Frameworks/vela_framework
```

Senão ocorrerá:

```txt
ModuleNotFoundError: No module named 'vela'
```

---

### WebView2 não encontrado no Windows

O Windows normalmente já possui WebView2 através do Microsoft Edge Chromium.

Se o app não abrir corretamente, instale manualmente:

```txt
https://developer.microsoft.com/microsoft-edge/webview2/
```

---

### QT não encontrado

Erro:

```txt
ModuleNotFoundError: No module named 'qtpy'
```

O Vela usa GTK por padrão no Linux.

Mas, se quiser usar Qt como backend alternativo:

```bash
pip install pywebview[qt]
```

ou:

```bash
pip install qtpy PyQt6
```

---

### Erro ao usar pip install -e .

Erro:

```txt
error: externally-managed-environment
```

Isso acontece em distribuições Linux modernas (Ubuntu/Debian) por causa da PEP 668.

Não instale o framework diretamente no Python global do sistema.

Use ambiente virtual:

```bash
python3 -m venv .venv

source .venv/bin/activate

pip install -e .
```

---

### Erro no build-backend do pyproject.toml

Erro:

```txt
ModuleNotFoundError: No module named 'setuptools.backends'
```

Isso acontece quando o `build-backend` do `pyproject.toml` está incorreto.

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


## Status atual

O Vela já possui:

- CLI global com `vela startproject`;
- CLI local via `manage.py`;
- sistema de apps;
- sistema de rotas;
- views Python retornando HTML;
- comunicação Python ↔ JS;
- shell HTML base;
- suporte a janela desktop com pywebview;
- empacotamento inicial via `pyproject.toml`;
- instalação global via `pipx`;
HEAD
- suporte a uso local com `pip install -e {pasta onde você clonou o repositório}`.


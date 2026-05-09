# Vela Framework

> Framework Python para aplicações desktop usando HTML, CSS, Tailwind e JS — sem navegador.

---

## Estrutura do Projeto

```
vela_framework/
│
├── manage.py                    # Ponto de entrada CLI
│
├── vela/                        # Core do framework (não mexa aqui no início)
│   ├── core/
│   │   ├── app.py               # VelaApp — classe principal
│   │   ├── window.py            # Janela desktop (pywebview)
│   │   ├── bridge.py            # Bridge Python ↔ JS
│   │   ├── router.py            # Sistema de rotas
│   │   └── shell.html           # Shell HTML base (carregado pelo pywebview)
│   ├── cli/
│   │   ├── commands.py          # Comandos do manage.py
│   │   └── shell.py             # Shell interativo
│   ├── log/
│   │   └── logger.py            # Sistema de logging
│   └── template_engine/
│       └── engine.py            # Engine de templates HTML
│
├── config/
│   ├── settings.py              # Configurações do projeto
│   └── wsgi.py                  # Boot do app + INSTALLED_APPS
│
├── apps/                        # Seus apps ficam aqui
│   └── home/                    # App exemplo
│       ├── views/
│       │   ├── __init__.py      # register_routes()
│       │   └── home.py          # View → retorna HTML
│       ├── templates/
│       │   └── index.html       # Template opcional
│       └── static/
│
├── logs/                        # Gerado automaticamente
└── requirements.txt
```

---

## Requisitos

- Python 3.10 ou superior
- pip

---

## Instalação

### Windows

O Windows já tem suporte nativo ao WebView2 (Edge Chromium). Só instalar as dependências Python:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Se a janela não abrir e der erro de WebView2, baixe o runtime em:
https://developer.microsoft.com/microsoft-edge/webview2/

---

### Linux (Ubuntu / Debian)

O Linux precisa de dependências do sistema **antes** de instalar o Python package:

```bash
# 1. Dependências do sistema (GTK + WebKit)
sudo apt install python3-gi python3-gi-cairo \
  gir1.2-gtk-3.0 gir1.2-webkit2-4.1 \
  libgirepository-2.0-dev -y

# Se der erro no passo acima, instale também:
sudo apt install libcairo2-dev pkg-config python3-dev -y

# 2. Cria o ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instala as dependências Python
pip install -r requirements.txt
```

> **Importante:** o `python3-gi` precisa ser instalado pelo `apt`, não pelo `pip`.
> É a ponte entre Python e o GTK do sistema — sem ele o pywebview não consegue abrir a janela.

---

### macOS

O macOS usa WebKit nativo, sem dependências extras do sistema:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Rodando o app

```bash
# Linux / macOS
source venv/bin/activate
python manage.py runapp

# Windows
venv\Scripts\activate
python manage.py runapp
```

---

## Comandos

```bash
python manage.py runapp              # Inicia o app desktop
python manage.py shell               # Shell interativo com contexto do app
python manage.py startapp <nome>     # Cria um novo app
python manage.py logs                # Exibe os últimos 50 logs
python manage.py routes              # Lista todas as rotas registradas
python manage.py version             # Versão do framework
```

---

## Como criar um novo app

```bash
python manage.py startapp dashboard
```

Isso cria:
```
apps/dashboard/
├── __init__.py
├── views/
│   ├── __init__.py      # register_routes()
│   └── dashboard.py     # sua view
├── templates/
└── static/
```

Depois, registre em `config/wsgi.py`:

```python
INSTALLED_APPS = [
    "apps.home",
    "apps.dashboard",   # ← adicione aqui
]
```

---

## Como criar uma view

Uma view é uma função Python que retorna HTML:

```python
# apps/dashboard/views/dashboard.py

def dashboard_view(params: dict) -> str:
    return """
    <div>
        <h1 class="text-3xl font-bold">Dashboard</h1>
        <p class="text-zinc-400">Olá do Python!</p>
    </div>
    """
```

E em `views/__init__.py`:

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

Para expor novas funções Python ao JS, edite `vela/core/bridge.py` ou crie sua própria Bridge:

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

## Compatibilidade

| Sistema      | Backend gráfico       | Instalação extra            |
|--------------|-----------------------|-----------------------------|
| Windows 10+  | WebView2 (Edge)       | Nenhuma (já vem no sistema) |
| Linux Ubuntu | GTK + WebKit2         | `sudo apt install ...` acima |
| macOS 10.13+ | WKWebView             | Nenhuma                     |
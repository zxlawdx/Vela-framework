"""
config/settings.py
Configurações globais da aplicação Vela.
"""

# ─── App ──────────────────────────────────────────────────────────────────────

APP_TITLE = "Meu App Vela"
APP_VERSION = "0.2.0"
APP_ICON = ""
APP_AUTHOR = ""
APP_DESCRIPTION = ""
APP_FILE_EXTENSIONS = []

# Rota inicial ao abrir o app
ENTRY_ROUTE = "/home"

# ─── Janela ───────────────────────────────────────────────────────────────────

WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 800

# ─── Layout global ────────────────────────────────────────────────────────────
# Controla quais componentes do shell são exibidos por padrão.
# Pode ser sobrescrito no VelaApp() ou por rota (layout="blank").

LAYOUT = {
    "sidebar": True,
    "topbar": True,
    "theme": "light",
}

# ─── API local ────────────────────────────────────────────────────────────────
# A porta configurada é preferencial. Se já estiver ocupada e auto_port=True,
# o Vela pede ao sistema operacional outra porta TCP livre automaticamente.

API = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 8000,
    "auto_port": True,
    "server": "waitress",
    "workers": 4,
    "docs_enabled": True,
}

# ─── Desenvolvimento ──────────────────────────────────────────────────────────

# True = abre o DevTools do navegador embutido
DEBUG = True

# Diretório de arquivos estáticos coletados (usado por {{ static() }})
STATIC_ROOT = "staticfiles"

"""
config/settings.py
Configurações globais da aplicação Vela.
"""

# ─── App ──────────────────────────────────────────────────────────────────────

APP_TITLE = "Meu App Vela"

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
}

# ─── Desenvolvimento ──────────────────────────────────────────────────────────

# True = abre o DevTools do navegador embutido
DEBUG = True

# Diretório de arquivos estáticos coletados (usado por {{ static() }})
STATIC_ROOT = "staticfiles"

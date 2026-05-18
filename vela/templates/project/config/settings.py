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
    "topbar":  True,
}

# ─── Desenvolvimento ──────────────────────────────────────────────────────────

# True = abre o DevTools do navegador embutido
DEBUG = True

# Diretório de arquivos estáticos coletados (usado por {{ static() }})
STATIC_ROOT = "staticfiles"

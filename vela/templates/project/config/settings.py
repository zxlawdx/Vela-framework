"""
config/settings.py
Configurações globais da aplicação Vela.
"""

# ─── App ──────────────────────────────────────────────────────────────────────

# Título principal da aplicação
APP_TITLE = "Meu App Vela"

# Host e porta do servidor HTTP interno do Vela.
#
# IMPORTANTE:
# O shell do frontend é servido por este servidor.
# Isso evita problemas de CORS causados por file://
#
# Exemplo:
#   http://127.0.0.1:8000
#
HOST = "127.0.0.1"
PORT = 8000

# Rota inicial ao abrir o app
#
# Exemplo:
#   "/"
#   "/dashboard"
#   "/home"
#
ENTRY_ROUTE = "/home"

# ─── Janela ───────────────────────────────────────────────────────────────────

# Largura inicial da janela desktop
WINDOW_WIDTH = 1280

# Altura inicial da janela desktop
WINDOW_HEIGHT = 800

# ─── Layout global ────────────────────────────────────────────────────────────
#
# Controla os componentes padrão do shell do Vela.
#
# Pode ser sobrescrito:
#
#   1. No VelaApp(layout={...})
#   2. Em rotas individuais:
#
#       @router.get("/login", layout="blank")
#
# Layouts disponíveis:
#
#   default → usa sidebar + topbar
#   blank   → esconde sidebar + topbar
#
LAYOUT = {
    "sidebar": True,
    "topbar": True,
}

# ─── Desenvolvimento ──────────────────────────────────────────────────────────

# True  → abre DevTools do navegador embutido
# False → produção
#
# OBS:
# Em Qt WebEngine, o DevTools pode abrir em janela separada.
#
DEBUG = True

# ─── Static files ─────────────────────────────────────────────────────────────
#
# Diretório onde os assets estáticos compilados são armazenados.
#
# Exemplos:
#   CSS compilado do Tailwind
#   JS do frontend
#   imagens
#   ícones
#
# Exemplo de uso:
#
#   {{ static("css/app.css") }}
#
STATIC_ROOT = "staticfiles"

# ─── Shell HTTP interno ───────────────────────────────────────────────────────
#
# Rota interna usada para servir o shell principal do Vela.
#
# O pywebview carrega esta rota ao invés de usar file://
#
# Isso resolve:
#
#   - CORS
#   - fetch() bloqueado
#   - problemas com Tailwind CDN
#   - problemas com assets externos
#
# Exemplo:
#
#   http://127.0.0.1:8000/__vela_shell__
#
SHELL_ROUTE = "/__vela_shell__"
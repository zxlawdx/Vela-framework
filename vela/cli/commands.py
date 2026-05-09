"""
vela.cli.commands
Dispatcher de comandos do manage.py
"""

import sys
import os
import importlib
from vela.log.logger import VelaLogger


HELP_TEXT = """
╔══════════════════════════════════════════════════╗
║          Vela Framework  —  manage.py            ║
╚══════════════════════════════════════════════════╝

Uso:
  python manage.py <comando> [argumentos]

Comandos disponíveis:

  runapp                    Inicia o app desktop
  shell                     Abre o shell interativo do Vela
  startapp <nome>           Cria um novo app dentro de apps/
  logs                      Exibe os logs mais recentes
  routes                    Lista as rotas registradas
  version                   Exibe a versão do framework
  help                      Exibe esta mensagem

Exemplos:
  python manage.py runapp
  python manage.py startapp dashboard
  python manage.py shell
  python manage.py logs
"""


class CommandRunner:
    def __init__(self):
        self.logger = VelaLogger("CLI")

    def execute(self, argv: list):
        if not argv:
            print(HELP_TEXT)
            return

        command = argv[0]
        args = argv[1:]

        commands = {
            "runapp": self.cmd_runapp,
            "shell": self.cmd_shell,
            "startapp": self.cmd_startapp,
            "logs": self.cmd_logs,
            "routes": self.cmd_routes,
            "version": self.cmd_version,
            "help": lambda _: print(HELP_TEXT),
        }

        handler = commands.get(command)
        if handler:
            handler(args)
        else:
            print(f"\n  Comando desconhecido: '{command}'")
            print(HELP_TEXT)

    # ─── runapp ────────────────────────────────────────────────────────────

    def cmd_runapp(self, args):
        self.logger.info("Iniciando aplicação Vela...")
        try:
            entry = importlib.import_module("config.wsgi")
            entry.run()
        except ModuleNotFoundError:
            print("\n  Erro: config/wsgi.py não encontrado.")
            print("  Crie o arquivo config/wsgi.py com a função run().\n")
            sys.exit(1)

    # ─── shell ─────────────────────────────────────────────────────────────

    def cmd_shell(self, args):
        from vela.cli.shell import VelaShell
        shell = VelaShell()
        shell.start()

    # ─── startapp ──────────────────────────────────────────────────────────

    def cmd_startapp(self, args):
        if not args:
            print("\n  Uso: python manage.py startapp <nome_do_app>\n")
            return

        app_name = args[0]
        self._create_app(app_name)

    def _create_app(self, name: str):
        base = os.path.join("apps", name)
        dirs = [
            base,
            os.path.join(base, "views"),
            os.path.join(base, "templates"),
            os.path.join(base, "static"),
        ]

        for d in dirs:
            os.makedirs(d, exist_ok=True)

        # __init__.py
        self._write(os.path.join(base, "__init__.py"), "")

        # views/__init__.py
        self._write(
            os.path.join(base, "views", "__init__.py"),
            f'''"""
{name} — views
Registra as rotas deste app no router do Vela.
"""

from apps.{name}.views.{name} import {name}_view


def register_routes(router):
    router.add("/{name}", {name}_view, title="{name.capitalize()}")
''',
        )

        # views/<name>.py
        name_cap = name.capitalize()
        self._write(
            os.path.join(base, "views", f"{name}.py"),
            f'''"""
apps.{name}.views.{name}
View principal do app {name}.
"""


def {name}_view(params: dict) -> str:
    """Retorna o HTML da página {name}."""
    return """
    <div>
        <h1 class="text-3xl font-bold mb-2">{name_cap}</h1>
        <p class="text-zinc-400">Página criada pelo Vela Framework.</p>
    </div>
    """
''',
        )

        # templates/index.html (opcional, para views mais complexas)
        self._write(
            os.path.join(base, "templates", "index.html"),
            f"<!-- Template do app {name} -->\n",
        )

        print(f"\n  App '{name}' criado em apps/{name}/")
        print(f"\n  Próximo passo: registre o app em config/wsgi.py:")
        print(f"    app.register_app('apps.{name}')\n")

    def _write(self, path: str, content: str):
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    # ─── logs ──────────────────────────────────────────────────────────────

    def cmd_logs(self, args):
        log_dir = "logs"
        if not os.path.isdir(log_dir):
            print("\n  Nenhum log encontrado ainda. Rode o app primeiro.\n")
            return

        log_files = sorted(os.listdir(log_dir), reverse=True)
        if not log_files:
            print("\n  Pasta logs/ está vazia.\n")
            return

        latest = os.path.join(log_dir, log_files[0])
        print(f"\n  Exibindo: {latest}\n  {'─' * 50}\n")

        lines = args[0] if args else "50"
        try:
            n = int(lines)
        except ValueError:
            n = 50

        with open(latest, encoding="utf-8") as f:
            all_lines = f.readlines()
            for line in all_lines[-n:]:
                print(line, end="")

        print()

    # ─── routes ────────────────────────────────────────────────────────────

    def cmd_routes(self, args):
        """Carrega o wsgi e lista as rotas registradas."""
        try:
            import config.wsgi as wsgi_module
            # Monta app temporário para listar rotas
            from vela.core.app import VelaApp
            app = VelaApp()
            if hasattr(wsgi_module, "INSTALLED_APPS"):
                for a in wsgi_module.INSTALLED_APPS:
                    try:
                        app.register_app(a)
                    except Exception:
                        pass
            routes = app.router.list_routes()
            print(f"\n  {'PATH':<25} {'HANDLER':<30} {'TITLE'}")
            print(f"  {'─'*25} {'─'*30} {'─'*20}")
            for r in routes:
                print(f"  {r['path']:<25} {r['handler']:<30} {r['title']}")
            print()
        except Exception as e:
            print(f"\n  Não foi possível listar rotas: {e}\n")

    # ─── version ───────────────────────────────────────────────────────────

    def cmd_version(self, args):
        import vela
        print(f"\n  Vela Framework v{vela.__version__}\n")

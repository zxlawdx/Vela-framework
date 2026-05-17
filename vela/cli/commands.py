"""
vela.cli.commands
=================
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
  collectstatic             Coleta estáticos dos apps para staticfiles/
  logs                      Exibe os logs mais recentes
  routes                    Lista as rotas registradas
  version                   Exibe a versão do framework
  help                      Exibe esta mensagem

Exemplos:
  python manage.py runapp
  python manage.py startapp dashboard
  python manage.py collectstatic
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
        args    = argv[1:]

        commands = {
            "runapp":        self.cmd_runapp,
            "shell":         self.cmd_shell,
            "startapp":      self.cmd_startapp,
            "collectstatic": self.cmd_collectstatic,
            "logs":          self.cmd_logs,
            "routes":        self.cmd_routes,
            "version":       self.cmd_version,
            "help":          lambda _: print(HELP_TEXT),
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
        self._create_app(args[0])

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

        self._write(os.path.join(base, "__init__.py"), "")

        self._write(
            os.path.join(base, "views", "__init__.py"),
            f'''"""
{name} — views
Registra as rotas deste app no router do Vela.
"""

from apps.{name}.views.{name} import {name}_view


def register_routes(router):
    router.add(
        "/{name}",
        {name}_view,
        name="{name}",
        title="{name.capitalize()}",
        icon="",
        layout="default",
        show_in_sidebar=True,
    )
''',
        )

        name_cap = name.capitalize()
        self._write(
            os.path.join(base, "views", f"{name}.py"),
            f'''"""
apps.{name}.views.{name}
View principal do app {name}.
"""

from vela.template_engine.engine import render_template


def {name}_view(params: dict) -> str:
    """Retorna o HTML da página {name_cap}."""
    return render_template(
        "apps/{name}/templates/index.html",
        {{"titulo": "{name_cap}"}},
    )
''',
        )

        self._write(
            os.path.join(base, "templates", "index.html"),
            f"""<!-- Template do app {name} -->
<section class="space-y-6">
    <h1 class="text-3xl font-bold">{{{{ titulo }}}}</h1>
    <p class="text-zinc-400">Página criada pelo Vela Framework.</p>
</section>
""",
        )

        self._write(
            os.path.join(base, "static", f"{name}.css"),
            f"/* Estilos do app {name} */\n",
        )

        print(f"\n  App '{name}' criado em apps/{name}/")
        print(f"\n  Registre em config/wsgi.py:")
        print(f"    app.register_app('apps.{name}')\n")

    def _write(self, path: str, content: str):
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    # ─── collectstatic ─────────────────────────────────────────────────────

    def cmd_collectstatic(self, args):
        """Coleta arquivos estáticos dos apps e compila Tailwind se necessário."""
        from vela.cli.collectstatic import collect_static

        output_dir    = "staticfiles"
        skip_tailwind = False
        minify        = False

        for arg in args:
            if arg.startswith("--output="):
                output_dir = arg.split("=", 1)[1]
            elif arg == "--no-tailwind":
                skip_tailwind = True
            elif arg == "--minify":
                minify = True

        collect_static(
            apps_dir="apps",
            output_dir=output_dir,
            verbose=True,
            skip_tailwind=skip_tailwind,
            minify=minify,
        )

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
        """Lista as rotas registradas."""
        try:
            import config.wsgi as wsgi_module
            from vela.core.app import VelaApp

            app = VelaApp()
            if hasattr(wsgi_module, "INSTALLED_APPS"):
                for a in wsgi_module.INSTALLED_APPS:
                    try:
                        app.register_app(a)
                    except Exception:
                        pass

            routes = app.router.list_routes()
            print(f"\n  {'PATH':<20} {'NAME':<20} {'TITLE':<20} {'LAYOUT':<10} SIDEBAR")
            print(f"  {'─'*20} {'─'*20} {'─'*20} {'─'*10} {'─'*7}")
            for r in routes:
                print(
                    f"  {r['path']:<20} {r['name']:<20} {r['title']:<20} "
                    f"{r['layout']:<10} {r['show_in_sidebar']}"
                )
            print()
        except Exception as e:
            print(f"\n  Não foi possível listar rotas: {e}\n")

    # ─── version ───────────────────────────────────────────────────────────

    def cmd_version(self, args):
        import vela
        print(f"\n  Vela Framework v{vela.__version__}\n")

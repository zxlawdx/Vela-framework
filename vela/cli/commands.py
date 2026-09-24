# SPDX-License-Identifier: MPL-2.0
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
  doctor [--gui qt6]        Diagnostica dependencias (--fix com consentimento)
  buildapp                  Gera executavel nativo e pacote ZIP
  buildapp --installer      Inclui instalador no pacote
  buildapp --dry-run        Exibe plano de build sem executar
  installapp [--bundle dir] Instala build e cria atalho no sistema
  uninstallapp --slug name  Remove instalacao Linux do usuario
  makeworkflow              Cria CI Linux/Windows + release por tags
  dbmigrate [--dir migrations] Aplica migrations locais SQLite
  checkupdates --repo user/repo Consulta GitHub Releases sob demanda
  init-process:instalation  Assistente grafico de build/instalacao (Next)
  init-process:installation Alias com grafia corrigida
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
            "buildapp":      self.cmd_buildapp,
            "doctor":        self.cmd_doctor,
            "installapp":    self.cmd_installapp,
            "uninstallapp":  self.cmd_uninstallapp,
            "makeworkflow":  self.cmd_makeworkflow,
            "dbmigrate":     self.cmd_dbmigrate,
            "checkupdates":  self.cmd_checkupdates,
            "init-process:instalation": self.cmd_wizard,
            "init-process:installation": self.cmd_wizard,
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


    # ─── Distribuicao e diagnostico ────────────────────────────────────────

    def cmd_buildapp(self, args):
        import argparse
        from vela.cli.build import BuildOptions, build_app
        parser = argparse.ArgumentParser(prog="python manage.py buildapp")
        parser.add_argument("--gui", choices=["auto", "qt6", "qt5", "gtk", "native"],
                            default="auto")
        parser.add_argument("--icon", default="")
        parser.add_argument("--installer", action="store_true")
        parser.add_argument("--output", default="dist")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--tailwind", action="store_true")
        parser.add_argument("--wizard", action="store_true")
        parser.add_argument("--plugins", action="store_true")
        parsed = parser.parse_args(args)
        if parsed.wizard:
            return self.cmd_wizard([])
        return build_app(options=BuildOptions(
            gui=parsed.gui, icon=parsed.icon, installer=parsed.installer,
            output=parsed.output, dry_run=parsed.dry_run, tailwind=parsed.tailwind,
            plugins=parsed.plugins))

    def cmd_doctor(self, args):
        import argparse
        import dataclasses
        import json
        from vela.cli.doctor import diagnose, print_report, remedy
        parser = argparse.ArgumentParser(prog="python manage.py doctor")
        parser.add_argument("--gui", choices=["auto", "qt6", "qt5", "gtk", "native"],
                            default="auto")
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--fix", action="store_true")
        parsed = parser.parse_args(args)
        checks = diagnose(backend=parsed.gui)
        if parsed.json:
            print(json.dumps([dataclasses.asdict(x) for x in checks],
                             ensure_ascii=False, indent=2))
        else:
            print_report(checks)
        if parsed.fix:
            remedy(checks)

    def cmd_installapp(self, args):
        import argparse
        from pathlib import Path
        from vela.cli.build import identity, read_settings
        from vela.cli.install import install_bundle
        parser = argparse.ArgumentParser(prog="python manage.py installapp")
        parser.add_argument("--bundle", default=None)
        parser.add_argument("--scope", choices=["user", "system"], default="user")
        parsed = parser.parse_args(args)
        if parsed.bundle:
            bundle = Path(parsed.bundle)
        else:
            meta = identity(read_settings(Path.cwd()))
            bundle = Path.cwd() / "dist" / meta["slug"]
        return install_bundle(bundle, parsed.scope)

    def cmd_uninstallapp(self, args):
        import argparse
        from vela.cli.install import uninstall_app
        parser = argparse.ArgumentParser(prog="python manage.py uninstallapp")
        parser.add_argument("--slug", required=True)
        parser.add_argument("--scope", choices=["user", "system"], default="user")
        parser.add_argument("--yes", action="store_true")
        parsed = parser.parse_args(args)
        if not parsed.yes:
            answer = input(f"Remover {parsed.slug} ({parsed.scope})? [s/N] ")
            if answer.strip().lower() not in ("s", "sim", "y"):
                print("Cancelado.")
                return
        uninstall_app(parsed.slug, parsed.scope)
        print("Aplicativo removido.")

    def cmd_makeworkflow(self, args):
        import argparse
        from vela.cli.workflow import generate_workflow
        parser = argparse.ArgumentParser(prog="python manage.py makeworkflow")
        parser.add_argument("--force", action="store_true")
        parsed = parser.parse_args(args)
        print(f"Workflow criado: {generate_workflow(force=parsed.force)}")

    def cmd_wizard(self, args):
        from vela.cli.wizard import launch_wizard
        return launch_wizard()

    def cmd_dbmigrate(self, args):
        import argparse
        from pathlib import Path
        from vela.database import SQLiteStore
        from vela.cli.build import identity, read_settings
        parser = argparse.ArgumentParser(prog="python manage.py dbmigrate")
        parser.add_argument("--dir", default="migrations")
        parser.add_argument("--database", default=None)
        opts = parser.parse_args(args)
        meta = identity(read_settings(Path.cwd()))
        store = SQLiteStore(meta["slug"], database=opts.database)
        migrated = store.migrate(opts.dir)
        print("Banco:", store.path)
        print("Migrations aplicadas:", ", ".join(migrated) if migrated else "nenhuma")

    def cmd_checkupdates(self, args):
        import argparse
        from pathlib import Path
        from vela.cli.build import read_settings
        from vela.desktop import check_for_updates
        parser = argparse.ArgumentParser(prog="python manage.py checkupdates")
        parser.add_argument("--repo", required=True)
        opts = parser.parse_args(args)
        current = str(getattr(read_settings(Path.cwd()), "APP_VERSION", "0.1.0"))
        result = check_for_updates(opts.repo, current)
        print("Instalada:", result["current"], "| Disponivel:", result["latest"])
        print("Nova versao:", "SIM" if result["available"] else "NAO")
        print("Release:", result["url"])

# SPDX-License-Identifier: MPL-2.0
"""Project-local Vela command dispatcher."""

from __future__ import annotations

import importlib
import json
import os
import sys

from vela.config import is_missing_target
from vela.log.logger import VelaLogger


HELP_TEXT = """
Vela Framework — manage.py

Uso:
  python manage.py <comando> [argumentos]

Comandos:
  runapp                    Inicia o app desktop
  shell                     Abre o shell interativo
  startapp <nome>           Cria app em apps/
  collectstatic             Coleta assets em staticfiles/
  assets verify             Valida shell, manifest e assets offline
  self-test                 Executa smoke test do runtime real
  routes                    Lista rotas visuais
  version                   Exibe versão
  doctor [--gui qt6]        Diagnostica projeto, venv, framework e backend
  buildapp                  Gera distribuição e build-report.json
  installapp / uninstallapp Instala ou remove build
  makeworkflow              Gera workflow
  dbmigrate                 Aplica migrations SQLite
  checkupdates              Consulta release sob demanda
  init-process:instalation  Assistente de build/instalação
  help                      Exibe ajuda
"""


class CommandRunner:
    def __init__(self):
        self.logger = VelaLogger("CLI")

    def execute(self, argv: list):
        if not argv:
            print(HELP_TEXT)
            return
        command, args = argv[0], argv[1:]
        commands = {
            "runapp": self.cmd_runapp,
            "shell": self.cmd_shell,
            "startapp": self.cmd_startapp,
            "collectstatic": self.cmd_collectstatic,
            "assets": self.cmd_assets,
            "self-test": self.cmd_self_test,
            "logs": self.cmd_logs,
            "routes": self.cmd_routes,
            "version": self.cmd_version,
            "buildapp": self.cmd_buildapp,
            "doctor": self.cmd_doctor,
            "installapp": self.cmd_installapp,
            "uninstallapp": self.cmd_uninstallapp,
            "makeworkflow": self.cmd_makeworkflow,
            "dbmigrate": self.cmd_dbmigrate,
            "checkupdates": self.cmd_checkupdates,
            "init-process:instalation": self.cmd_wizard,
            "init-process:installation": self.cmd_wizard,
            "help": lambda _: print(HELP_TEXT),
        }
        handler = commands.get(command)
        if handler is None:
            print(f"Comando desconhecido: {command!r}\n{HELP_TEXT}")
            return
        return handler(args)

    def cmd_runapp(self, args):
        self.logger.info("Iniciando aplicação Vela...")
        target = "config.wsgi"
        try:
            entry = importlib.import_module(target)
        except ModuleNotFoundError as exc:
            if not is_missing_target(exc, target):
                raise
            print("Erro: config/wsgi.py não encontrado.")
            return 1
        return entry.run()

    def cmd_shell(self, args):
        from vela.cli.shell import VelaShell

        return VelaShell().start()

    def cmd_startapp(self, args):
        if not args:
            print("Uso: python manage.py startapp <nome_do_app>")
            return 1
        name = args[0]
        if not name.replace("_", "").isalnum() or name[0].isdigit():
            raise ValueError("Nome de app inválido; use identificador Python simples.")
        base = os.path.join("apps", name)
        for path in (base, os.path.join(base, "views"), os.path.join(base, "templates"), os.path.join(base, "static")):
            os.makedirs(path, exist_ok=True)
        self._write(os.path.join(base, "__init__.py"), "")
        self._write(
            os.path.join(base, "views", "__init__.py"),
            f"from .{name} import {name}_view\n\n\ndef register_routes(router):\n    router.add('/{name}', {name}_view, name='{name}', title='{name.capitalize()}')\n",
        )
        self._write(
            os.path.join(base, "views", f"{name}.py"),
            f"from vela.template_engine import render_template\n\n\ndef {name}_view(params):\n    return render_template('apps/{name}/templates/index.html', {{'titulo': '{name.capitalize()}'}})\n",
        )
        self._write(
            os.path.join(base, "templates", "index.html"),
            f"<section><h1>{{{{ titulo }}}}</h1><p>App {name}</p></section>\n",
        )
        self._write(os.path.join(base, "static", f"{name}.css"), f"/* {name} */\n")
        print(f"App {name!r} criado em {base}/")
        return 0

    @staticmethod
    def _write(path: str, content: str):
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def cmd_collectstatic(self, args):
        from vela.cli.collectstatic import collect_static

        output = "staticfiles"
        skip_tailwind = "--no-tailwind" in args
        minify = "--minify" in args
        for arg in args:
            if arg.startswith("--output="):
                output = arg.split("=", 1)[1]
        return collect_static(
            apps_dir="apps",
            output_dir=output,
            verbose=True,
            skip_tailwind=skip_tailwind,
            minify=minify,
        )

    def cmd_assets(self, args):
        from vela.cli.assets import print_asset_report, verify_assets

        if args != ["verify"]:
            print("Uso: python manage.py assets verify")
            return 2
        return print_asset_report(verify_assets())

    def cmd_self_test(self, args):
        from vela.cli.selftest import run_self_test

        report = run_self_test()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    def cmd_logs(self, args):
        directory = "logs"
        if not os.path.isdir(directory):
            print("Nenhum log encontrado.")
            return 0
        files = sorted(os.listdir(directory), reverse=True)
        if not files:
            return 0
        try:
            count = int(args[0]) if args else 50
        except ValueError:
            count = 50
        with open(os.path.join(directory, files[0]), encoding="utf-8") as handle:
            print("".join(handle.readlines()[-count:]), end="")
        return 0

    def cmd_routes(self, args):
        from vela.core.app import VelaApp

        app = VelaApp()
        module = importlib.import_module("config.wsgi")
        for value in getattr(module, "INSTALLED_APPS", ()):
            app.register_app(value)
        for route in app.router.list_routes():
            print(f"{route['path']:<24} {route['name']:<24} {route['title']}")
        app.stop()
        return 0

    def cmd_version(self, args):
        import vela

        print(f"Vela Framework v{vela.__version__}")
        return 0

    def cmd_buildapp(self, args):
        import argparse

        from vela.cli.build import BuildOptions, build_app
        from vela.cli.build_report import write_build_report

        parser = argparse.ArgumentParser(prog="python manage.py buildapp")
        parser.add_argument("--gui", choices=["auto", "qt6", "qt5", "gtk", "native"], default="auto")
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
        plan = build_app(
            options=BuildOptions(
                gui=parsed.gui,
                icon=parsed.icon,
                installer=parsed.installer,
                output=parsed.output,
                dry_run=parsed.dry_run,
                tailwind=parsed.tailwind,
                plugins=parsed.plugins,
            )
        )
        report = write_build_report(plan)
        print(f"Build report: {report}")
        return plan

    def cmd_doctor(self, args):
        import argparse
        import dataclasses

        from vela.cli.doctor import diagnose, print_report, remedy

        parser = argparse.ArgumentParser(prog="python manage.py doctor")
        parser.add_argument("--gui", choices=["auto", "qt6", "qt5", "gtk", "native"], default="auto")
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--fix", action="store_true")
        parsed = parser.parse_args(args)
        checks = diagnose(backend=parsed.gui)
        if parsed.json:
            print(json.dumps([dataclasses.asdict(item) for item in checks], ensure_ascii=False, indent=2))
        else:
            print_report(checks)
        if parsed.fix:
            remedy(checks)
        return 0

    def cmd_installapp(self, args):
        import argparse
        from pathlib import Path

        from vela.cli.build import identity, read_settings
        from vela.cli.install import install_bundle

        parser = argparse.ArgumentParser(prog="python manage.py installapp")
        parser.add_argument("--bundle", default=None)
        parser.add_argument("--scope", choices=["user", "system"], default="user")
        parsed = parser.parse_args(args)
        bundle = Path(parsed.bundle) if parsed.bundle else Path.cwd() / "dist" / identity(read_settings(Path.cwd()))["slug"]
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
                return 0
        uninstall_app(parsed.slug, parsed.scope)
        return 0

    def cmd_makeworkflow(self, args):
        import argparse

        from vela.cli.workflow import generate_workflow

        parser = argparse.ArgumentParser(prog="python manage.py makeworkflow")
        parser.add_argument("--force", action="store_true")
        parsed = parser.parse_args(args)
        print(f"Workflow criado: {generate_workflow(force=parsed.force)}")
        return 0

    def cmd_wizard(self, args):
        from vela.cli.wizard import launch_wizard

        return launch_wizard()

    def cmd_dbmigrate(self, args):
        import argparse
        from pathlib import Path

        from vela.cli.build import identity, read_settings
        from vela.database import SQLiteStore

        parser = argparse.ArgumentParser(prog="python manage.py dbmigrate")
        parser.add_argument("--dir", default="migrations")
        parser.add_argument("--database", default=None)
        parsed = parser.parse_args(args)
        meta = identity(read_settings(Path.cwd()))
        store = SQLiteStore(meta["slug"], database=parsed.database)
        migrated = store.migrate(parsed.dir)
        print("Banco:", store.path)
        print("Migrations aplicadas:", ", ".join(migrated) if migrated else "nenhuma")
        return 0

    def cmd_checkupdates(self, args):
        import argparse
        from pathlib import Path

        from vela.cli.build import read_settings
        from vela.desktop import check_for_updates

        parser = argparse.ArgumentParser(prog="python manage.py checkupdates")
        parser.add_argument("--repo", required=True)
        parsed = parser.parse_args(args)
        current = str(getattr(read_settings(Path.cwd()), "APP_VERSION", "0.1.0"))
        result = check_for_updates(parsed.repo, current)
        print("Instalada:", result["current"], "| Disponível:", result["latest"])
        print("Nova versão:", "SIM" if result["available"] else "NÃO")
        print("Release:", result["url"])
        return 0

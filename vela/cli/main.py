# SPDX-License-Identifier: MPL-2.0
import argparse
import json
import shutil
from importlib.resources import files
from pathlib import Path


def startproject(project_name: str) -> Path | None:
    target = Path.cwd() / project_name
    if target.exists():
        print(f"Erro: a pasta '{project_name}' já existe.")
        return
    shutil.copytree(files("vela").joinpath("templates/project"), target)
    title = target.name.replace("-", " ").replace("_", " ").title()
    settings = target / "config" / "settings.py"
    settings.write_text(
        settings.read_text(encoding="utf-8").replace(
            '"__VELA_PROJECT_TITLE__"', json.dumps(title, ensure_ascii=False)
        ),
        encoding="utf-8",
    )
    print(f"Projeto '{project_name}' criado com sucesso!")
    print(f"Execute: cd {project_name} e python manage.py runapp")
    return target


def main():
    parser = argparse.ArgumentParser(prog="vela", description="CLI global do Vela Framework")
    subparsers = parser.add_subparsers(dest="command")
    start = subparsers.add_parser("startproject")
    start.add_argument("name")
    assets = subparsers.add_parser("assets")
    assets.add_argument("action", choices=["verify"])
    subparsers.add_parser("self-test")
    for name in (
        "buildapp",
        "installapp",
        "uninstallapp",
        "doctor",
        "makeworkflow",
        "dbmigrate",
        "checkupdates",
        "init-process:instalation",
        "init-process:installation",
        "runapp",
        "collectstatic",
        "routes",
        "version",
        "logs",
        "shell",
        "help",
    ):
        subparsers.add_parser(name, add_help=False)
    args, remaining = parser.parse_known_args()
    if args.command == "startproject":
        startproject(args.name)
    elif args.command == "assets":
        from vela.cli.assets import print_asset_report, verify_assets

        raise SystemExit(print_asset_report(verify_assets()))
    elif args.command == "self-test":
        from vela.cli.selftest import run_self_test

        report = run_self_test()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise SystemExit(0 if report["ok"] else 1)
    elif args.command:
        from vela.cli.commands import CommandRunner

        CommandRunner().execute([args.command, *remaining])
    else:
        parser.print_help()

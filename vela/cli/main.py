import argparse
import sys
import shutil
from pathlib import Path
from importlib.resources import files


def startproject(project_name: str):
    target = Path.cwd() / project_name

    if target.exists():
        print(f"Erro: a pasta '{project_name}' já existe.")
        return

    template = files("vela").joinpath("templates/project")

    shutil.copytree(template, target)

    print(f"Projeto '{project_name}' criado com sucesso!")
    print()
    print(f"Entre na pasta:")
    print(f"  cd {project_name}")
    print()
    print(f"Instale as dependências:")
    print(f"  pip install -r requirements.txt")
    print()
    print(f"Rode o app:")
    print(f"  python manage.py runapp")


def main():
    parser = argparse.ArgumentParser(
        prog="vela",
        description="CLI global do Vela Framework"
    )

    subparsers = parser.add_subparsers(dest="command")

    start = subparsers.add_parser("startproject")
    start.add_argument("name")

    for name in ("buildapp", "installapp", "uninstallapp", "doctor",
                 "makeworkflow", "init-process:instalation",
                 "init-process:installation", "runapp", "collectstatic", "routes",
                 "version", "logs", "shell", "help"):
        subparsers.add_parser(name, add_help=False)

    args, remaining = parser.parse_known_args()
    if args.command == "startproject":
        startproject(args.name)
    elif args.command:
        from vela.cli.commands import CommandRunner
        CommandRunner().execute([args.command, *remaining])
    else:
        parser.print_help()
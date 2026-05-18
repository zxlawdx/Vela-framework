import argparse
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

    args = parser.parse_args()

    if args.command == "startproject":
        startproject(args.name)
    else:
        parser.print_help()
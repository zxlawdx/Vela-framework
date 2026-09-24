# SPDX-License-Identifier: MPL-2.0
"""Cria workflow multiplataforma para GitHub Actions."""
from pathlib import Path

WORKFLOW = """name: Vela Build & Release

on:
  push:
    branches: [main, master]
    tags: ["v*"]
  pull_request:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Instalar dependencias
        run: |
          python -m pip install --upgrade pip
          if test -f requirements.txt; then
            python -m pip install -r requirements.txt
          else
            python -m pip install git+https://github.com/zxlawdx/Vela-framework.git
          fi
      - name: Compilar codigo Python
        run: python -m compileall -q apps config manage.py

  linux:
    needs: tests
    runs-on: ubuntu-22.04
    env:
      QT_API: pyqt6
      PYWEBVIEW_GUI: qt
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Bibliotecas Linux Qt
        run: |
          sudo apt-get update
          sudo apt-get install -y zip libgl1 libegl1 libopengl0 libnss3 libgbm1 \
            libdbus-1-3 libasound2 libxkbcommon-x11-0 libxcb-cursor0 \
            libxcb-xinerama0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 \
            libxcb-render-util0 libxcb-shape0 libgl1-mesa-dri
      - name: Instalar dependencias Python
        run: |
          python -m pip install --upgrade pip
          if test -f requirements.txt; then
            python -m pip install -r requirements.txt
          else
            python -m pip install git+https://github.com/zxlawdx/Vela-framework.git
          fi
          python -m pip install "PyInstaller>=6.16,<7" "PyQt6>=6.8,<7" \
            "PyQt6-WebEngine>=6.8,<7" "qtpy>=2.4,<3"
      - name: Compilar Linux
        run: python manage.py buildapp --gui qt6 --installer
      - uses: actions/upload-artifact@v4
        with:
          name: Vela-Linux
          path: |
            dist/*.zip
            dist/*.zip.sha256
          if-no-files-found: error

  windows:
    needs: tests
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Instalar dependencias
        shell: pwsh
        run: |
          python -m pip install --upgrade pip
          if (Test-Path requirements.txt) {
            python -m pip install -r requirements.txt
          } else {
            python -m pip install git+https://github.com/zxlawdx/Vela-framework.git
          }
          python -m pip install "PyInstaller>=6.16,<7"
      - name: Compilar Windows
        run: python manage.py buildapp --gui native --installer
      - uses: actions/upload-artifact@v4
        with:
          name: Vela-Windows
          path: |
            dist/*.zip
            dist/*.zip.sha256
          if-no-files-found: error

  release:
    needs: [linux, windows]
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: release
          merge-multiple: true
      - name: Publicar assets na tag
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create "$GITHUB_REF_NAME" release/*.zip release/*.sha256 \
            --repo "$GITHUB_REPOSITORY" --generate-notes --verify-tag
"""


def generate_workflow(root=None, force=False):
    root = Path(root or Path.cwd()).resolve()
    if not (root / "manage.py").is_file():
        raise FileNotFoundError("Execute makeworkflow na pasta de um projeto Vela")
    dest = root / ".github/workflows/vela-build.yml"
    if dest.exists() and not force:
        raise FileExistsError(f"{dest} existe. Use makeworkflow --force para substituir.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(WORKFLOW, encoding="utf-8")
    return dest

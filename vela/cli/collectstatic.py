"""
vela.cli.collectstatic
======================
Comando `collectstatic` do Vela — com pipeline Tailwind offline.

Responsabilidades:
  1. Coletar arquivos estáticos dos apps → staticfiles/<app>/
  2. Detectar uso de TailwindCSS no projeto (CDN ou classes utilitárias)
  3. Se Tailwind detectado:
       a. Verificar / criar tailwind.config.js
       b. Verificar / instalar Tailwind CLI via npm
       c. Gerar staticfiles/css/vela.bundle.css compilado localmente
       d. Emitir hint para substituir a tag CDN no shell.html
  4. Gerar staticfiles/manifest.json com hashes MD5 (base para cache busting)

Fluxo de uso:
    python manage.py collectstatic                 # modo normal
    python manage.py collectstatic --no-tailwind   # pula etapa Tailwind
    python manage.py collectstatic --minify        # CSS minificado (produção)

Estrutura de saída:
    staticfiles/
      css/
        vela.bundle.css          <- CSS Tailwind compilado localmente
      <app>/
        css/  js/  images/  ... <- Assets copiados dos apps
      manifest.json              <- Mapa { rel_path: md5_hash }

Compatibilidade:
    - Funciona offline apos primeira compilacao
    - Compativel com pywebview (file:// paths)
    - Preparado para PyInstaller / Briefcase / Nuitka
"""

import os
import re
import json
import shutil
import hashlib
import subprocess
from pathlib import Path
from vela.log.logger import VelaLogger


logger = VelaLogger("collectstatic")

# ─── Constantes ──────────────────────────────────────────────────────────────

_TAILWIND_CDN_RE = re.compile(
    r'cdn\.tailwindcss\.com|unpkg\.com/tailwindcss|jsdelivr.*tailwind',
    re.IGNORECASE,
)
_TAILWIND_CLASS_RE = re.compile(
    r'class=["\'][^"\']*(?:bg-|text-|flex|grid|p-\d|m-\d|w-|h-|'
    r'rounded|border|shadow|items-|justify-|gap-|space-|font-|'
    r'hover:|focus:|sm:|md:|lg:|xl:|dark:)',
)
_TEMPLATE_EXTS = {".html", ".htm", ".jinja", ".j2"}

_DEFAULT_TAILWIND_CONFIG = """\
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./apps/**/templates/**/*.html",
    "./apps/**/static/**/*.js",
    "./vela/core/shell.html",
    "./templates/**/*.html",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
"""

_TAILWIND_INPUT_CSS = """\
@tailwind base;
@tailwind components;
@tailwind utilities;
"""


# ─── Utilitarios ─────────────────────────────────────────────────────────────

def _file_hash(path: str) -> str:
    """Retorna o hash MD5 do conteudo de um arquivo."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _find_template_files(project_root: str) -> list:
    """Retorna todos os arquivos de template do projeto."""
    found = []
    skip = {"node_modules", "venv", ".venv", "staticfiles",
            "__pycache__", ".git", "dist", "build"}

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if Path(f).suffix in _TEMPLATE_EXTS:
                found.append(os.path.join(root, f))

    # Inclui o shell.html do framework instalado
    shell = Path(__file__).resolve().parent.parent / "core" / "shell.html"
    if shell.exists():
        found.append(str(shell))
    return found


def _detect_tailwind(project_root: str) -> dict:
    """
    Verifica se o projeto usa TailwindCSS.

    Retorna:
        {
            "found": bool,
            "reason": str,   # "cdn_tag" | "class_usage" | "config_file" | None
            "config_exists": bool,
        }
    """
    config_path = os.path.join(project_root, "tailwind.config.js")
    if os.path.exists(config_path):
        return {"found": True, "reason": "config_file", "config_exists": True}

    for fpath in _find_template_files(project_root):
        try:
            content = Path(fpath).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if _TAILWIND_CDN_RE.search(content):
            return {"found": True, "reason": "cdn_tag", "config_exists": False}

        if _TAILWIND_CLASS_RE.search(content):
            return {"found": True, "reason": "class_usage", "config_exists": False}

    return {"found": False, "reason": None, "config_exists": False}


# ─── Pipeline Tailwind ────────────────────────────────────────────────────────

def _ensure_node_available() -> bool:
    return all(shutil.which(cmd) is not None for cmd in ("node", "npm"))


def _ensure_tailwind_cli(project_root: str, verbose: bool) -> bool:
    """Garante que o Tailwind CLI esteja instalado. Retorna True se OK."""
    local_bin = os.path.join(project_root, "node_modules", ".bin", "tailwindcss")
    if os.path.exists(local_bin):
        return True

    if verbose:
        print("    -> Instalando Tailwind CLI via npm (apenas uma vez)...")

    try:
        result = subprocess.run(
            ["npm", "install", "--save-dev", "tailwindcss"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            if verbose:
                print(f"    x npm install falhou:\n{result.stderr}")
            logger.error(f"npm install tailwindcss falhou: {result.stderr}")
            return False

        if verbose:
            print("    * Tailwind CLI instalado.")
        return True

    except FileNotFoundError:
        if verbose:
            print("    x npm nao encontrado. Instale Node.js para usar Tailwind offline.")
        logger.error("npm nao encontrado.")
        return False
    except subprocess.TimeoutExpired:
        if verbose:
            print("    x npm install expirou (timeout 120s).")
        return False


def _create_tailwind_config(project_root: str, verbose: bool):
    config_path = os.path.join(project_root, "tailwind.config.js")
    if not os.path.exists(config_path):
        Path(config_path).write_text(_DEFAULT_TAILWIND_CONFIG, encoding="utf-8")
        if verbose:
            print("    * tailwind.config.js criado com configuracao padrao.")
        logger.info("tailwind.config.js criado.")


def _ensure_tailwind_input(project_root: str, output_dir: str, verbose: bool) -> str:
    css_dir = os.path.join(output_dir, "css")
    os.makedirs(css_dir, exist_ok=True)

    input_path = os.path.join(css_dir, "tailwind.input.css")
    if not os.path.exists(input_path):
        Path(input_path).write_text(_TAILWIND_INPUT_CSS, encoding="utf-8")
        if verbose:
            print("    * staticfiles/css/tailwind.input.css criado.")

    return input_path


def _compile_tailwind(
    project_root: str,
    input_css: str,
    output_css: str,
    minify: bool,
    verbose: bool,
) -> bool:
    """Executa o Tailwind CLI. Retorna True se bem-sucedido."""
    local_bin = os.path.join(project_root, "node_modules", ".bin", "tailwindcss")
    cmd = [local_bin, "-i", input_css, "-o", output_css]
    if minify:
        cmd.append("--minify")

    if verbose:
        mode = "minificado" if minify else "desenvolvimento"
        print(f"    -> Compilando Tailwind ({mode})...")

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            if verbose:
                print(f"    x Tailwind CLI falhou:\n{result.stderr}")
            logger.error(f"Tailwind CLI error: {result.stderr}")
            return False

        size_kb = os.path.getsize(output_css) / 1024
        if verbose:
            print(f"    * vela.bundle.css gerado ({size_kb:.1f} KB)")
        logger.info(f"Tailwind compilado -> {output_css} ({size_kb:.1f} KB)")
        return True

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        if verbose:
            print(f"    x Erro ao executar Tailwind CLI: {e}")
        logger.error(f"Tailwind CLI exec error: {e}")
        return False


def _print_shell_patch_hint(verbose: bool):
    """Emite instrucao para substituir a tag CDN no shell.html."""
    if not verbose:
        return
    print()
    print("  --- Integracao com shell.html ----------------------------")
    print("  Substitua a tag CDN do Tailwind no shell.html por:")
    print()
    print("    <link rel=\"stylesheet\" href=\"{{ static('css/vela.bundle.css') }}\">")
    print()
    print("  Ou, com pywebview usando file:// direto:")
    print()
    print("    <link rel=\"stylesheet\" href=\"file:///SEU_PROJETO/staticfiles/css/vela.bundle.css\">")
    print()
    print("  ----------------------------------------------------------")
    print()


def run_tailwind_pipeline(
    project_root: str,
    output_dir: str,
    minify: bool = False,
    verbose: bool = True,
) -> bool:
    """
    Pipeline completo:
      1. Detecta Tailwind
      2. Garante config + CLI
      3. Compila CSS
      4. Emite hint para shell.html

    Retorna True se bundle gerado com sucesso.
    """
    if verbose:
        print("\n  --- Pipeline Tailwind ------------------------------------")

    detection = _detect_tailwind(project_root)

    if not detection["found"]:
        if verbose:
            print("  Tailwind nao detectado no projeto — etapa ignorada.")
        return False

    reason_msg = {
        "cdn_tag":    "tag CDN do Tailwind encontrada",
        "class_usage":"classes utilitarias Tailwind detectadas",
        "config_file":"tailwind.config.js encontrado",
    }.get(detection["reason"], "detectado")

    if verbose:
        print(f"  * Tailwind detectado ({reason_msg}).")

    if not _ensure_node_available():
        if verbose:
            print(
                "  x Node.js nao encontrado.\n"
                "  Instale Node.js (https://nodejs.org) para compilar Tailwind offline.\n"
                "  O collectstatic continuara sem gerar o bundle CSS."
            )
        logger.warning("Node.js indisponivel — pipeline Tailwind ignorada.")
        return False

    _create_tailwind_config(project_root, verbose)

    if not _ensure_tailwind_cli(project_root, verbose):
        return False

    input_css  = _ensure_tailwind_input(project_root, output_dir, verbose)
    css_out    = os.path.join(output_dir, "css")
    os.makedirs(css_out, exist_ok=True)
    output_css = os.path.join(css_out, "vela.bundle.css")

    ok = _compile_tailwind(project_root, input_css, output_css, minify, verbose)

    if ok:
        _print_shell_patch_hint(verbose)

    return ok


# ─── Coleta de estaticos ──────────────────────────────────────────────────────

def _collect_app_statics(abs_apps_dir: str, abs_output: str, verbose: bool) -> dict:
    """
    Percorre apps/<app>/static/ e copia para staticfiles/<app>/.
    Retorna estatisticas { copied, skipped, errors }.
    """
    stats = {"copied": 0, "skipped": 0, "errors": 0}

    if not os.path.isdir(abs_apps_dir):
        msg = f"Diretorio de apps nao encontrado: {abs_apps_dir}"
        logger.error(msg)
        if verbose:
            print(f"\n  [erro] {msg}\n")
        stats["errors"] += 1
        return stats

    if verbose:
        rel_apps = os.path.relpath(abs_apps_dir)
        rel_out  = os.path.relpath(abs_output)
        print(f"\n  Coletando estaticos de {rel_apps}/ -> {rel_out}/\n")

    for app_name in sorted(os.listdir(abs_apps_dir)):
        app_path    = os.path.join(abs_apps_dir, app_name)
        static_path = os.path.join(app_path, "static")

        if not os.path.isdir(app_path) or not os.path.isdir(static_path):
            continue

        dest_root = os.path.join(abs_output, app_name)
        os.makedirs(dest_root, exist_ok=True)

        for root, dirs, files in os.walk(static_path):
            rel_root = os.path.relpath(root, static_path)
            dest_dir = os.path.join(dest_root, rel_root) if rel_root != "." else dest_root
            os.makedirs(dest_dir, exist_ok=True)

            for filename in files:
                if filename == "tailwind.input.css":
                    continue  # arquivo de entrada, nao deve ser copiado

                src  = os.path.join(root, filename)
                dest = os.path.join(dest_dir, filename)

                try:
                    if os.path.exists(dest) and _file_hash(src) == _file_hash(dest):
                        stats["skipped"] += 1
                        if verbose:
                            rel = os.path.relpath(dest, abs_output)
                            print(f"    ~ ignorado (sem mudancas): {rel}")
                        continue

                    shutil.copy2(src, dest)
                    stats["copied"] += 1

                    if verbose:
                        rel = os.path.relpath(dest, abs_output)
                        print(f"    * copiado: {rel}")

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Erro ao copiar {src}: {e}")
                    if verbose:
                        print(f"    x erro: {filename} ({e})")

    return stats


# ─── Manifest ─────────────────────────────────────────────────────────────────

def _generate_manifest(output_dir: str, verbose: bool) -> dict:
    """
    Gera staticfiles/manifest.json com hash MD5 de cada arquivo.

    Estrutura:
    {
        "version": 1,
        "files": {
            "css/vela.bundle.css": "a1b2c3d4...",
            "dashboard/dashboard.css": "e5f6...",
        }
    }

    Base para cache busting futuro: o runtime pode detectar mudancas
    de hash e invalidar caches em producao / build empacotada.
    """
    manifest = {"version": 1, "files": {}}
    skip = {"__pycache__"}

    for root, dirs, files in os.walk(output_dir):
        dirs[:] = [d for d in dirs if d not in skip]
        for filename in files:
            if filename == "manifest.json":
                continue
            fpath = os.path.join(root, filename)
            rel   = os.path.relpath(fpath, output_dir).replace("\\", "/")
            manifest["files"][rel] = _file_hash(fpath)

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    if verbose:
        n = len(manifest["files"])
        print(f"\n  * manifest.json gerado ({n} arquivo(s)).")
    logger.info(f"manifest.json gerado com {len(manifest['files'])} entradas.")

    return manifest


# ─── Ponto de entrada ─────────────────────────────────────────────────────────

def collect_static(
    apps_dir: str = "apps",
    output_dir: str = "staticfiles",
    verbose: bool = True,
    skip_tailwind: bool = False,
    minify: bool = False,
) -> dict:
    """
    Pipeline completo do collectstatic:
      1. Copia estaticos dos apps
      2. Detecta e compila Tailwind (se presente e Node disponivel)
      3. Gera manifest.json

    Args:
        apps_dir       Diretorio raiz dos apps (padrao: "apps")
        output_dir     Diretorio de saida     (padrao: "staticfiles")
        verbose        Se True, imprime relatorio detalhado
        skip_tailwind  Se True, pula etapa Tailwind
        minify         Se True, CSS minificado (recomendado em producao)

    Returns:
        {
            "copied": int,
            "skipped": int,
            "errors": int,
            "tailwind_bundle": bool,
            "manifest": dict,
        }
    """
    project_root = os.getcwd()
    abs_output   = os.path.join(project_root, output_dir)
    os.makedirs(abs_output, exist_ok=True)

    # 1. Estáticos dos apps
    stats = _collect_app_statics(
        abs_apps_dir=os.path.join(project_root, apps_dir),
        abs_output=abs_output,
        verbose=verbose,
    )

    # 2. Pipeline Tailwind
    tailwind_ok = False
    if not skip_tailwind:
        tailwind_ok = run_tailwind_pipeline(
            project_root=project_root,
            output_dir=abs_output,
            minify=minify,
            verbose=verbose,
        )

    # 3. Manifest
    manifest = _generate_manifest(abs_output, verbose)

    if verbose:
        print(
            f"\n  --- Resumo -----------------------------------------------\n"
            f"  Arquivos copiados : {stats['copied']}\n"
            f"  Ignorados (iguais): {stats['skipped']}\n"
            f"  Erros             : {stats['errors']}\n"
            f"  Bundle Tailwind   : {'gerado' if tailwind_ok else 'ignorado'}\n"
            f"  ----------------------------------------------------------\n"
        )

    return {
        **stats,
        "tailwind_bundle": tailwind_ok,
        "manifest": manifest,
    }

# SPDX-License-Identifier: MPL-2.0
"""Pontos de extensao explicitamente ativados por projetos confiaveis."""
from importlib.metadata import entry_points

_build_hooks = []


def register_build_hook(callback):
    if not callable(callback):
        raise TypeError("Hook deve ser chamavel")
    if callback not in _build_hooks:
        _build_hooks.append(callback)
    return callback


def apply_build_hooks(plan):
    """Somente execute hooks quando --plugins foi selecionado pelo desenvolvedor."""
    for hook in _build_hooks:
        hook(plan)
    # Pacotes instalados podem declarar [project.entry-points."vela.build_hooks"]
    for point in entry_points(group="vela.build_hooks"):
        point.load()(plan)
    return plan

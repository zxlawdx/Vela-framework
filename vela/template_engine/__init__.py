# SPDX-License-Identifier: MPL-2.0
"""API pública do template engine Vela."""

from vela.template_engine.engine import (
    CompiledTemplate,
    clear_template_cache,
    compile_template,
    render_string,
    render_template,
)
from vela.template_engine.safe import SafeHTML, mark_safe

__all__ = [
    "CompiledTemplate",
    "SafeHTML",
    "mark_safe",
    "compile_template",
    "render_string",
    "render_template",
    "clear_template_cache",
]

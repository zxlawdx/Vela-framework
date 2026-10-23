# SPDX-License-Identifier: MPL-2.0
"""Exceções públicas do núcleo do Vela."""


class VelaError(Exception):
    """Base para erros controlados do framework."""


class ConfigurationError(VelaError, ValueError):
    """Configuração inválida ou conflitante."""


class RouteNotFoundError(VelaError, LookupError):
    """Rota visual não encontrada."""


class RouteRenderError(VelaError):
    """Falha ao executar/renderizar uma view."""


class TemplateError(VelaError):
    """Falha de template."""


class TemplateSyntaxError(TemplateError, SyntaxError):
    """Sintaxe de template inválida."""


class ApiValidationError(VelaError, ValueError):
    """Payload de API inválido."""


class PluginError(VelaError):
    """Falha durante carregamento/execução de plugin."""


class LifecycleError(VelaError):
    """Falha em uma fase do lifecycle."""


class JobQueueFullError(VelaError):
    """Fila de jobs atingiu o limite configurado."""

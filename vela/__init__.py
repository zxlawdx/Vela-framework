# SPDX-License-Identifier: MPL-2.0
"""Vela — Desktop UI Framework."""

__version__ = "0.2.2"
__author__ = "Marinaldo da Costa Barroso Filho"
__all__ = ["VelaApp", "__version__"]


def __getattr__(name):
    if name == "VelaApp":
        from vela.core.app import VelaApp

        return VelaApp
    raise AttributeError(name)

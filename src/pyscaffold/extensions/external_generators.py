# -*- coding: utf-8 -*-
"""
Add extensions that use external generators in a mutually exclusive fashion.
"""
from __future__ import absolute_import

from . import cookiecutter, django
from ..api import Extension


class ExternalGenerators(Extension):
    """Handle external generatos like Django and Cookiecutter"""
    def augment_cli(self, parser):
        """Add Django and Cookiecutter in a way they cannot be called together."""
        group = parser.add_mutually_exclusive_group()
        cookiecutter.augment_cli(group)
        django.augment_cli(group)

    def activate(self, actions):
        raise RuntimeError("Implemented but never called!")






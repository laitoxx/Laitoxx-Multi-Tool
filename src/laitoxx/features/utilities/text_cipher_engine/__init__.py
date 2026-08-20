"""Composable DenCode-style text transformation engine."""

from .registry import SPECS, TransformSpec, transform

__all__ = ["SPECS", "TransformSpec", "transform"]

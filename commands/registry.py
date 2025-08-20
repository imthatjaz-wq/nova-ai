"""Command registry mapping names to handlers."""
from __future__ import annotations

from typing import Callable, Dict

_registry: Dict[str, Callable[..., str]] = {}


def register(name: str, func: Callable[..., str]) -> None:
    _registry[name] = func


def get(name: str) -> Callable[..., str] | None:
    return _registry.get(name)


def populate_defaults() -> None:
    from . import handlers

    register("open_url", handlers.open_url)
    register("create_file", handlers.create_file)
    register("open_app", handlers.open_app)
    register("set_reminder", handlers.set_reminder)
    register("search_local_files", handlers.search_local_files)
    register("show_logs", handlers.show_logs)

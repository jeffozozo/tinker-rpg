"""Resolve bundled assets and writable game data for source and installed apps."""

import sys
from pathlib import Path


ASSET_DIRECTORIES = ("tiles", "npcs", "objects")


def _is_asset_directory(path):
    return all((path / directory).is_dir() for directory in ASSET_DIRECTORIES)


def _app_bundle(executable):
    return next(
        (parent for parent in executable.parents if parent.suffix == ".app"),
        None,
    )


def asset_root():
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent

    executable = Path(sys.executable).resolve()
    app_bundle = _app_bundle(executable)
    if app_bundle is not None:
        bundled_assets = app_bundle / "Contents" / "Resources" / "TinkerData"
        if _is_asset_directory(bundled_assets):
            return bundled_assets

    for parent in executable.parents:
        bundled_assets = parent / "assets"
        if _is_asset_directory(bundled_assets):
            return bundled_assets
        if _is_asset_directory(parent):
            return parent

    return app_bundle.parent if app_bundle else executable.parent


def project_root():
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent

    executable = Path(sys.executable).resolve()
    app_bundle = _app_bundle(executable)
    for parent in executable.parents:
        if _is_asset_directory(parent):
            return parent

    data_directory = Path.home() / "Documents" / "Tinker RPG"
    for directory in ("areas", "games", "saves"):
        (data_directory / directory).mkdir(parents=True, exist_ok=True)
    return data_directory

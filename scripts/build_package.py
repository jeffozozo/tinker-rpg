#!/usr/bin/env python3
"""Build a portable Tinker RPG package for the current desktop platform."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRECTORIES = ("tiles", "npcs", "objects", "triggers", "sounds")
APPLICATIONS = (
    ("Tinker Editor", "tinker-edit.py"),
    ("Tinker Runner", "tinker-runner.py"),
)
INNO_SETUP_SCRIPT = ROOT / "packaging" / "windows-installer.iss"


def current_target():
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    raise RuntimeError(f"Package builds are not supported on {system}.")


def build_package(target):
    expected_target = current_target()
    if target != expected_target:
        raise RuntimeError(
            f"Cannot build the {target} package on {platform.system()}; "
            f"this machine builds {expected_target} packages."
        )

    output_directory = ROOT / "dist"
    output_directory.mkdir(exist_ok=True)
    package_directory = output_directory / f"Tinker-RPG-{target}-files"
    artifact_path = output_directory / (
        "Tinker-RPG-macos.dmg" if target == "macos"
        else "Tinker-RPG-windows-setup.exe"
    )

    if package_directory.exists():
        shutil.rmtree(package_directory)
    if artifact_path.exists():
        artifact_path.unlink()
    package_directory.mkdir()

    with tempfile.TemporaryDirectory(prefix="tinker-rpg-build-") as temp:
        temp_path = Path(temp)
        frozen_directory = temp_path / "frozen"
        work_directory = temp_path / "work"

        for application_name, entry_point in APPLICATIONS:
            command = [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--windowed",
                "--onedir",
                "--collect-all",
                "PIL",
                "--name",
                application_name,
                "--distpath",
                str(frozen_directory),
                "--workpath",
                str(work_directory),
                "--specpath",
                str(temp_path),
                str(ROOT / entry_point),
            ]
            build_environment = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(temp_path / "cache"))
            subprocess.run(command, cwd=ROOT, env=build_environment, check=True)
            built_name = f"{application_name}.app" if target == "macos" else application_name
            built_application = frozen_directory / built_name
            if not built_application.is_dir():
                raise RuntimeError(
                    f"PyInstaller did not create the expected application "
                    f"directory: {built_application}"
                )
            shutil.copytree(
                built_application,
                package_directory / built_name,
                symlinks=True,
            )

    if target == "macos":
        for application_name, _entry_point in APPLICATIONS:
            resources = (
                package_directory
                / f"{application_name}.app"
                / "Contents"
                / "Resources"
                / "TinkerData"
            )
            resources.mkdir(parents=True, exist_ok=True)
            for directory in ASSET_DIRECTORIES:
                shutil.copytree(ROOT / directory, resources / directory)
    else:
        assets_directory = package_directory / "assets"
        assets_directory.mkdir()
        for directory in ASSET_DIRECTORIES:
            shutil.copytree(ROOT / directory, assets_directory / directory)

    shutil.copy2(ROOT / "PACKAGE_README.txt", package_directory)

    if target == "macos":
        subprocess.run(
            ["osacompile", "-o", str(package_directory / "Install Tinker RPG.app"),
             str(ROOT / "packaging" / "macos-installer.applescript")],
            check=True,
        )
        # Assets are added after freezing, so refresh the local signatures.
        for app_bundle in package_directory.glob("*.app"):
            subprocess.run(
                ["codesign", "--force", "--deep", "--sign", "-", str(app_bundle)],
                check=True,
            )
        subprocess.run(
            [
                "hdiutil", "create",
                "-volname", "Tinker RPG",
                "-srcfolder", str(package_directory),
                "-ov", "-format", "UDZO",
                str(artifact_path),
            ],
            check=True,
        )
    else:
        if not INNO_SETUP_SCRIPT.is_file():
            raise RuntimeError(f"Missing Windows installer script: {INNO_SETUP_SCRIPT}")
        source_directory = str(package_directory)
        subprocess.run(
            [
                "iscc",
                f"/DTinkerSourceDir={source_directory}",
                str(INNO_SETUP_SCRIPT),
            ],
            cwd=ROOT,
            check=True,
        )
        generated_installer = ROOT / "dist" / "Tinker-RPG-windows-setup.exe"
        if not generated_installer.is_file():
            raise RuntimeError(
                f"Inno Setup did not create the expected installer: "
                f"{generated_installer}"
            )
    return artifact_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=("macos", "windows"),
        help="platform to package (must match the current build machine)",
    )
    args = parser.parse_args(argv)
    try:
        archive_path = build_package(args.target or current_target())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Package build failed: {error}", file=sys.stderr)
        return 1
    print(f"Created {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

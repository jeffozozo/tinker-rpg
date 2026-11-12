# Native installers

The package builder creates a macOS disk image (`.dmg`) or Windows installer
(`.exe`) containing the Editor and Runner.

## Build locally

Build on the target operating system; PyInstaller does not cross-compile.

```text
python -m pip install -r requirements-build.txt
python scripts/build_package.py
```

On Windows, install Inno Setup 6 and ensure `iscc` is on `PATH`. Outputs are:

- macOS: `dist/Tinker-RPG-macos.dmg`
- Windows: `dist/Tinker-RPG-windows-setup.exe`

## GitHub Actions

Run **Build downloadable packages** manually to create downloadable workflow
artifacts, or push a `v*` tag to attach the installer files to a GitHub Release.

Open the macOS DMG and double-click **Install Tinker RPG**. The installer
copies both apps to `~/Applications` and creates **Tinker Editor** and
**Tinker Runner** desktop icons. Python, Tk, and Pillow are bundled inside
the apps; users do not need a separate Python installation or internet access.
You can eject the DMG after installation. The apps can also be copied manually.
Build architecture follows the Python interpreter running PyInstaller (the
local build uses Apple silicon). Build on Intel for an Intel Mac package.
The Windows installer creates Start Menu shortcuts and optional desktop shortcuts.

Bundled art is installed with the applications. Editable games, areas, and
saves are stored under `Documents/Tinker RPG` so they remain writable and
survive application updates or removal.

These installers are not code-signed/notarized. macOS or Windows may display
security warnings; only proceed when the installer source is trusted.

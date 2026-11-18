"""Immediate, nonblocking playback of preloaded game sound effects."""

import atexit
import ctypes
import os
import shutil
import subprocess
import sys

from project_paths import asset_root, project_root
from wav_assets import read_sound_defaults, wav_path

SOUND_NAMES = ("step", "hit", "miss", "hurt", "step_hurt")


class _MacPlayer:
    """A prepared native player, independent of the system-alert sound service."""

    def __init__(self, path):
        ctypes.CDLL("/System/Library/Frameworks/AVFoundation.framework/AVFoundation")
        self.objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
        self.objc.objc_getClass.argtypes = [ctypes.c_char_p]
        self.objc.objc_getClass.restype = ctypes.c_void_p
        self.objc.sel_registerName.argtypes = [ctypes.c_char_p]
        self.objc.sel_registerName.restype = ctypes.c_void_p
        core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        core.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
        core.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        core.CFRelease.argtypes = [ctypes.c_void_p]
        core.CFRelease.restype = None
        self.player = None
        encoded = os.fsencode(path)
        url = core.CFURLCreateFromFileSystemRepresentation(None, encoded, len(encoded), False)
        if not url:
            raise OSError(f"Cannot load sound {path}")
        try:
            allocated = self._send(self.objc.objc_getClass(b"AVAudioPlayer"), "alloc")
            self.player = self._send(allocated, "initWithContentsOfURL:error:",
                                     (ctypes.c_void_p, ctypes.c_void_p), (url, None))
        finally:
            core.CFRelease(url)
        if not self.player:
            raise OSError(f"Cannot preload sound {path}")
        if not self._send(self.player, "prepareToPlay", result=ctypes.c_bool):
            self.close()
            raise OSError(f"Cannot prepare sound {path}")

    def _send(self, target, selector, types=(), args=(), result=ctypes.c_void_p):
        method = ctypes.CFUNCTYPE(result, ctypes.c_void_p, ctypes.c_void_p, *types)(
            ("objc_msgSend", self.objc))
        return method(target, self.objc.sel_registerName(selector.encode()), *args)

    def play(self):
        self._send(self.player, "stop", result=None)
        self._send(self.player, "setCurrentTime:", (ctypes.c_double,), (0.0,), result=None)
        if not self._send(self.player, "play", result=ctypes.c_bool):
            raise OSError("Cannot play sound")

    def close(self):
        if self.player:
            self._send(self.player, "stop", result=None)
            self._send(self.player, "release", result=None)
            self.player = None


class _MacSounds:
    """Rotate prepared voices so repeated steps start immediately, without queuing."""

    def __init__(self, paths):
        self.players = {}
        self.next_voice = {}
        try:
            for name, path in paths.items():
                self.players[name] = []
                self.next_voice[name] = 0
                for _ in range(4):
                    self.players[name].append(_MacPlayer(path))
        except Exception:
            self.close()
            raise

    def play(self, name):
        voices = self.players[name]
        index = self.next_voice[name]
        voices[index].play()
        self.next_voice[name] = (index + 1) % len(voices)

    def close(self):
        for voices in self.players.values():
            for player in voices:
                player.close()
        self.players.clear()
        self.next_voice.clear()


class _WindowsSounds:
    def __init__(self, paths):
        import winsound
        self.api = winsound
        self.paths = paths
        # Warm the filesystem cache before the first action.
        for path in paths.values():
            path.read_bytes()

    def play(self, name):
        self.api.PlaySound(str(self.paths[name]), self.api.SND_FILENAME | self.api.SND_ASYNC | self.api.SND_NODEFAULT)

    def close(self):
        self.api.PlaySound(None, 0)


class _LinuxSounds:
    """Use an installed audio player without retaining a backlog of effects."""

    def __init__(self, paths):
        self.paths = paths
        self.command = next((path for name in ("paplay", "aplay") if (path := shutil.which(name))), None)
        self.process = None
        self.retired = []

    def play(self, name):
        if not self.command:
            return
        self.retired = [process for process in self.retired if process.poll() is None]
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                self.retired.append(self.process)
        self.process = subprocess.Popen(
            [self.command, str(self.paths[name])],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def close(self):
        for process in [self.process, *self.retired]:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


class SoundEffects:
    def __init__(self, root=None, report=None):
        self.enabled = True
        self.backend = None
        paths = {name: asset_root() / "sounds" / f"{name}.wav" for name in SOUND_NAMES}
        root = root if root is not None else project_root()
        report = report if report is not None else lambda message: None
        try:
            settings = read_sound_defaults(root)
        except (OSError, ValueError) as error:
            report(f"Sound defaults: {error}")
            settings = {}
        self.attack_sound = ""
        overrides = {}
        for cue in (*SOUND_NAMES, "attack"):
            if cue in settings:
                try:
                    overrides[cue] = wav_path(root, settings[cue])
                except (OSError, ValueError) as error:
                    report(f"Sound default for {cue}: {error}")
        if "attack" in overrides:
            self.attack_sound = settings["attack"]
            del overrides["attack"]
        if "step_hurt" not in overrides and ("step" in overrides or "hurt" in overrides):
            overrides["step_hurt"] = overrides.get("hurt", paths["hurt"])
        backend = _MacSounds if sys.platform == "darwin" else _WindowsSounds if sys.platform == "win32" else _LinuxSounds
        try:
            self.backend = backend({**paths, **overrides})
        except (OSError, RuntimeError) as error:
            if overrides:
                report(f"Could not load custom sound defaults: {error}")
                try:
                    self.backend = backend(paths)
                except (OSError, RuntimeError):
                    pass
        atexit.register(self.close)

    def play(self, name):
        if self.enabled and self.backend is not None and name in SOUND_NAMES:
            try:
                self.backend.play(name)
            except (OSError, RuntimeError):
                pass

    def close(self):
        if self.backend is not None:
            self.backend.close()
            self.backend = None

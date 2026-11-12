"""Immediate, nonblocking playback of preloaded game sound effects."""

import atexit
import ctypes
import os
import shutil
import subprocess
import sys

from project_paths import asset_root

SOUND_NAMES = ("step", "hit", "miss", "hurt", "step_hurt")


class _MacSounds:
    """Register WAVs once with macOS; playback never launches a process."""

    def __init__(self, paths):
        self.ids = {}
        self.audio = ctypes.CDLL("/System/Library/Frameworks/AudioToolbox.framework/AudioToolbox")
        core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        core.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
        core.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        core.CFRelease.argtypes = [ctypes.c_void_p]
        core.CFRelease.restype = None
        self.audio.AudioServicesCreateSystemSoundID.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        self.audio.AudioServicesCreateSystemSoundID.restype = ctypes.c_int32
        self.audio.AudioServicesPlaySystemSound.argtypes = [ctypes.c_uint32]
        self.audio.AudioServicesPlaySystemSound.restype = None
        self.audio.AudioServicesDisposeSystemSoundID.argtypes = [ctypes.c_uint32]
        self.audio.AudioServicesDisposeSystemSoundID.restype = ctypes.c_int32
        try:
            for name, path in paths.items():
                encoded = os.fsencode(path)
                url = core.CFURLCreateFromFileSystemRepresentation(None, encoded, len(encoded), False)
                if not url:
                    raise OSError(f"Cannot load sound {path}")
                sound_id = ctypes.c_uint32()
                try:
                    status = self.audio.AudioServicesCreateSystemSoundID(url, ctypes.byref(sound_id))
                finally:
                    core.CFRelease(url)
                if status != 0:
                    raise OSError(f"Cannot preload sound {path}: {status}")
                self.ids[name] = sound_id.value
        except Exception:
            self.close()
            raise

    def play(self, name):
        self.audio.AudioServicesPlaySystemSound(self.ids[name])

    def close(self):
        for sound_id in self.ids.values():
            self.audio.AudioServicesDisposeSystemSoundID(sound_id)
        self.ids.clear()


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
    def __init__(self):
        self.enabled = True
        self.backend = None
        paths = {name: asset_root() / "sounds" / f"{name}.wav" for name in SOUND_NAMES}
        backend = _MacSounds if sys.platform == "darwin" else _WindowsSounds if sys.platform == "win32" else _LinuxSounds
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

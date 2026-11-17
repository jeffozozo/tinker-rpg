"""WAV playback for area music and triggered sounds."""

import ctypes
import sys

from wav_assets import wav_path
from sound_effects import _MacPlayer, _LinuxSounds


def music_path(root, name):
    return wav_path(root, name, 'music')


class _WindowsMusic:
    def __init__(self, path, alias='tinker_ambient'):
        self.api = ctypes.windll.winmm
        self.alias = alias
        self._command(f'open "{path}" type waveaudio alias {self.alias}')
        try:
            self.play()
        except OSError:
            self.close()
            raise

    def _command(self, command):
        if self.api.mciSendStringW(command, None, 0, None):
            raise OSError('Could not play ambient music.')

    def play(self):
        self._command(f'play {self.alias} from 0')

    def finished(self):
        result = ctypes.create_unicode_buffer(32)
        if self.api.mciSendStringW(f'status {self.alias} mode', result, len(result), None):
            raise OSError('Could not read ambient music playback state.')
        return result.value == 'stopped'

    def close(self):
        self.api.mciSendStringW(f'close {self.alias}', None, 0, None)


class AmbientMusic:
    def __init__(self, root, report, alias="tinker_ambient"):
        self.root = root
        self.report = report
        self.alias = alias
        self.loop = True
        self.backend = None
        self.selection = None
        self.enabled = True

    def update(self, project_root, name, loop=True, directory="music"):
        selection = (str(project_root), name, loop, directory) if self.enabled and name else None
        if selection == self.selection:
            return
        self.close()
        self.selection = selection
        if selection is None:
            return
        self.loop = loop
        try:
            if directory == "music":
                path = music_path(project_root, name)
            else:
                path = wav_path(project_root, name, directory)
            if sys.platform == 'darwin':
                self.backend = _MacPlayer(path)
                self.backend._send(self.backend.player, 'setNumberOfLoops:',
                                   (ctypes.c_long,), (-1 if loop else 0,), result=None)
                self.backend.play()
            elif sys.platform == 'win32':
                self.backend = _WindowsMusic(path, alias=self.alias)
                self._repeat()
            else:
                self.backend = _LinuxSounds({'music': path})
                if not self.backend.command:
                    raise OSError('WAV playback requires paplay or aplay.')
                self.backend.play('music')
                self._repeat()
        except (OSError, RuntimeError, ValueError) as error:
            self.close()
            self.selection = selection
            self.report(f'Audio playback: {error}')

    def _repeat(self):
        backend = self.backend
        try:
            if isinstance(backend, _WindowsMusic):
                if backend.finished():
                    if not self.loop:
                        self._finish()
                        return
                    backend.play()
            elif isinstance(backend, _LinuxSounds):
                if backend.process is not None and backend.process.poll() is not None:
                    if backend.process.returncode:
                        raise OSError('Audio player could not play this WAV file.')
                    if not self.loop:
                        self._finish()
                        return
                    backend.play('music')
            else:
                return
            self.timer = self.root.after(100, self._repeat)
        except (OSError, RuntimeError) as error:
            selection = self.selection
            self.close()
            self.selection = selection
            self.report(f'Audio playback: {error}')

    def _finish(self):
        selection = self.selection
        self.close()
        self.selection = selection

    def close(self):
        timer = getattr(self, 'timer', None)
        if timer is not None:
            self.root.after_cancel(timer)
            self.timer = None
        if self.backend is not None:
            self.backend.close()
            self.backend = None
        self.selection = None

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ambient_music import AmbientMusic, music_path, _WindowsMusic


class AmbientMusicTests(unittest.TestCase):
    def test_switching_tracks_and_silence_close_previous_player(self):
        root = Mock()
        report = Mock()
        music = AmbientMusic(root, report)
        with patch('ambient_music.sys.platform', 'darwin'), \
                patch('ambient_music.music_path', return_value=Path('track.wav')), \
                patch('ambient_music._MacPlayer') as player:
            first, second = Mock(), Mock()
            player.side_effect = [first, second]
            music.update('/project', 'forest.wav')
            first.play.assert_called_once()
            music.update('/project', 'forest.wav')
            self.assertEqual(player.call_count, 1)
            music.update('/project', 'castle.wav')
            first.close.assert_called_once()
            second.play.assert_called_once()
            music.update('/project', '')
            second.close.assert_called_once()
            self.assertIsNone(music.backend)
        report.assert_not_called()

    def test_missing_music_reports_once_and_keeps_game_running(self):
        report = Mock()
        music = AmbientMusic(Mock(), report)
        with patch('ambient_music.music_path', side_effect=FileNotFoundError('missing')):
            music.update('/project', 'missing.wav')
            music.update('/project', 'missing.wav')
        report.assert_called_once()
        self.assertIsNone(music.backend)

    def test_disabling_and_enabling_restarts_selected_track(self):
        music = AmbientMusic(Mock(), Mock())
        with patch('ambient_music.sys.platform', 'darwin'), \
                patch('ambient_music.music_path', return_value=Path('track.wav')), \
                patch('ambient_music._MacPlayer') as player:
            music.update('/project', 'forest.wav')
            music.enabled = False
            music.update('/project', 'forest.wav')
            player.return_value.close.assert_called_once()
            music.enabled = True
            music.update('/project', 'forest.wav')
            self.assertEqual(player.call_count, 2)

    def test_library_resolution_and_path_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory) / 'music'
            library.mkdir()
            track = library / 'forest.wav'
            track.touch()
            self.assertEqual(music_path(directory, 'forest.wav'), track)
            with self.assertRaises(ValueError):
                music_path(directory, '../forest.wav')

    def test_mac_play_once_and_loop_use_native_loop_counts(self):
        music = AmbientMusic(Mock(), Mock())
        with patch('ambient_music.sys.platform', 'darwin'), \
                patch('ambient_music.wav_path', return_value=Path('bell.wav')), \
                patch('ambient_music._MacPlayer') as player:
            for loop, expected in ((False, 0), (True, -1)):
                music.update('/project', 'bell.wav', loop=loop, directory='sounds')
                call = player.return_value._send.call_args
                self.assertEqual(call.args[1], 'setNumberOfLoops:')
                self.assertEqual(call.args[3], (expected,))
                music.close()

    def test_finished_windows_sound_repeats_only_when_loop_is_enabled(self):
        for loop in (False, True):
            with self.subTest(loop=loop):
                root = Mock()
                music = AmbientMusic(root, Mock())
                player = object.__new__(_WindowsMusic)
                player.finished = Mock(return_value=True)
                player.play = Mock()
                player.close = Mock()
                music.backend = player
                music.loop = loop
                music.selection = ('bell.wav', loop)
                music._repeat()
                if loop:
                    player.play.assert_called_once()
                    root.after.assert_called_once()
                else:
                    player.play.assert_not_called()
                    player.close.assert_called_once()
                    root.after.assert_not_called()
                    self.assertEqual(music.selection, ('bell.wav', loop))

    def test_import_wav_copies_valid_audio_and_reuses_identical_import(self):
        import wave
        from wav_assets import import_wav
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'bell.wav'
            with wave.open(str(source), 'wb') as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(22050)
                output.writeframes(b'\0\0' * 100)
            library = Path(directory) / 'sounds'
            name = import_wav(source, library)
            self.assertEqual((library / name).read_bytes(), source.read_bytes())
            self.assertEqual(import_wav(source, library), name)
            self.assertEqual(list(library.iterdir()), [library / name])

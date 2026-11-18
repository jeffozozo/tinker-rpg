from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from sound_effects import SoundEffects, _MacSounds
from wav_assets import save_sound_defaults


class SoundPlaybackTests(unittest.TestCase):
    @patch("sound_effects._MacPlayer")
    def test_mac_repeated_steps_start_a_prepared_voice_every_time(self, player):
        voices = [Mock() for _ in range(4)]
        player.side_effect = voices
        sounds = _MacSounds({"step": "step.wav"})
        for _ in range(21):
            sounds.play("step")
        self.assertEqual([voice.play.call_count for voice in voices], [6, 5, 5, 5])
        self.assertEqual(player.call_count, 4)
        sounds.close()
        sounds.close()
        for voice in voices:
            voice.close.assert_called_once()

    def test_walking_sample_matches_reference_and_combined_cue(self):
        import wave
        directory = Path(__file__).resolve().parents[1] / "sounds"
        self.assertEqual((directory / "step.wav").read_bytes(),
                         (directory / "sources/ultima_iv_walk_normal_c64.wav").read_bytes())
        with wave.open(str(directory / "step.wav")) as step, wave.open(str(directory / "step_hurt.wav")) as combined:
            self.assertEqual(step.getframerate(), combined.getframerate())
            self.assertEqual(step.readframes(step.getnframes()), combined.readframes(step.getnframes()))

    @patch("sound_effects.atexit.register")
    @patch("sound_effects._MacSounds")
    @patch("sound_effects.sys.platform", "darwin")
    def test_project_defaults_choose_assets_and_keep_missing_cue_fallbacks(self, backend, register):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sounds").mkdir()
            (root / "music").mkdir()
            step = root / "sounds" / "custom-step.wav"
            attack = root / "music" / "swing.wav"
            step.touch()
            attack.touch()
            save_sound_defaults(root, {
                "step": step.name, "attack": "music/swing.wav", "miss": "unknown.wav",
            })
            report = Mock()
            sounds = SoundEffects(root, report)
            paths = backend.call_args.args[0]
            self.assertEqual(paths["step"], step)
            self.assertEqual(paths["miss"].name, "miss.wav")
            self.assertEqual(paths["step_hurt"], paths["hurt"])
            self.assertEqual(sounds.attack_sound, "music/swing.wav")
            report.assert_called_once()
            sounds.close()

    @patch("sound_effects.atexit.register")
    @patch("sound_effects._MacSounds")
    @patch("sound_effects.sys.platform", "darwin")
    def test_effects_are_preloaded_once_and_played_synchronously_without_a_queue(self, backend, register):
        sounds = SoundEffects()
        self.assertEqual(set(backend.call_args.args[0]), {"step", "hit", "miss", "hurt", "step_hurt"})
        for name in ("step", "hit", "step", "miss"):
            sounds.play(name)
            backend.return_value.play.assert_called_with(name)
        backend.assert_called_once()
        self.assertEqual(backend.return_value.play.call_count, 4)
        sounds.enabled = False
        sounds.play("hit")
        sounds.enabled = True
        sounds.play("unknown")
        self.assertEqual(backend.return_value.play.call_count, 4)
        sounds.close()
        sounds.close()
        backend.return_value.close.assert_called_once()

    @patch("sound_effects.atexit.register")
    @patch("sound_effects._MacSounds", side_effect=OSError("Audio unavailable"))
    @patch("sound_effects.sys.platform", "darwin")
    def test_unavailable_audio_does_not_block_actions_or_start_external_players(self, backend, register):
        sounds = SoundEffects()
        self.assertIsNone(sounds.backend)
        sounds.play("step")
        sounds.close()

import unittest
from unittest.mock import Mock, patch

from sound_effects import SoundEffects


class SoundPlaybackTests(unittest.TestCase):
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

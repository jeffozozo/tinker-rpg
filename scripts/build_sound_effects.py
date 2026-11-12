"""Rebuild the game's original, short retro WAV effects using only Python."""

import math
from pathlib import Path
import random
import struct
import wave


def build_sounds():
    directory = Path(__file__).resolve().parents[1] / "sounds"
    directory.mkdir(exist_ok=True)
    rate = 22050
    for name, duration in (("step", 0.035), ("hit", 0.12), ("miss", 0.14), ("hurt", 0.16)):
        rng = random.Random(1500)
        samples = []
        phase = 0.0
        for index in range(int(duration * rate)):
            t = index / rate
            progress = t / duration
            envelope = min(1, t / 0.004) * (1 - progress) ** 2
            noise = rng.uniform(-1, 1)
            if name == "step":
                # A tiny, dry square-wave click rather than a low footstep thud.
                phase += 2 * math.pi * 1650 / rate
                envelope = min(1, t / 0.0005) * (1 - progress) ** 2
                value = 0.85 * (1 if math.sin(phase) > 0 else -1) + 0.15 * noise
                volume = 0.28
            elif name == "hit":
                frequency = 520 - 420 * progress
                phase += 2 * math.pi * frequency / rate
                value = 0.65 * (1 if math.sin(phase) > 0 else -1) + 0.35 * noise
                volume = 0.26
            elif name == "miss":
                frequency = 950 - 650 * progress
                phase += 2 * math.pi * frequency / rate
                value = 0.8 * math.sin(phase) + 0.2 * noise
                volume = 0.20
            else:
                frequency = 200 if progress < 0.45 else 110
                phase += 2 * math.pi * frequency / rate
                value = 0.8 * (1 if math.sin(phase) > 0 else -1) + 0.2 * noise
                volume = 0.23
            samples.append(struct.pack("<h", int(32767 * volume * envelope * value)))
        with wave.open(str(directory / f"{name}.wav"), "wb") as output:
            output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            output.writeframes(b"".join(samples))

    # One preloaded cue preserves both events when a move causes contact damage.
    # The click starts immediately; the impact follows without a playback queue.
    with wave.open(str(directory / "step.wav")) as source:
        step = struct.unpack("<" + "h" * source.getnframes(), source.readframes(source.getnframes()))
    with wave.open(str(directory / "hurt.wav")) as source:
        hurt = struct.unpack("<" + "h" * source.getnframes(), source.readframes(source.getnframes()))
    samples = list(step) + list(hurt)
    with wave.open(str(directory / "step_hurt.wav"), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(struct.pack("<" + "h" * len(samples), *samples))


if __name__ == "__main__":
    build_sounds()

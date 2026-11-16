"""Build game effects, preserving the credited Ultima IV walking sample."""

import math
from pathlib import Path
import random
import struct
import wave


def build_sounds():
    directory = Path(__file__).resolve().parents[1] / "sounds"
    directory.mkdir(exist_ok=True)
    rate = 22050
    # Keep the walking sample unchanged; do not synthesize a pitched replacement.
    source = directory / "sources" / "ultima_iv_walk_normal_c64.wav"
    (directory / "step.wav").write_bytes(source.read_bytes())
    for name, duration in (("hit", 0.12), ("miss", 0.14), ("hurt", 0.16)):
        rng = random.Random(1500)
        samples = []
        phase = 0.0
        for index in range(int(duration * rate)):
            t = index / rate
            progress = t / duration
            envelope = min(1, t / 0.004) * (1 - progress) ** 2
            noise = rng.uniform(-1, 1)
            if name == "hit":
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
        step_rate = source.getframerate()
        step = struct.unpack("<" + "h" * source.getnframes(), source.readframes(source.getnframes()))
    with wave.open(str(directory / "hurt.wav")) as source:
        hurt_rate = source.getframerate()
        hurt = struct.unpack("<" + "h" * source.getnframes(), source.readframes(source.getnframes()))
    # The original walking sample is 44.1 kHz; generated effects use 22.05 kHz.
    # Resample only the hurt tail so the click remains bit-for-bit identical.
    tail = []
    for index in range(round(len(hurt) * step_rate / hurt_rate)):
        position = index * hurt_rate / step_rate
        left = int(position)
        fraction = position - left
        right = min(left + 1, len(hurt) - 1)
        tail.append(round(hurt[left] * (1 - fraction) + hurt[right] * fraction))
    samples = list(step) + tail
    with wave.open(str(directory / "step_hurt.wav"), "wb") as output:
        output.setparams((1, 2, step_rate, 0, "NONE", "not compressed"))
        output.writeframes(struct.pack("<" + "h" * len(samples), *samples))


if __name__ == "__main__":
    build_sounds()

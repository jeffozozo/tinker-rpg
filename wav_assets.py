"""Validate and import project WAV assets."""

import hashlib
from pathlib import Path
import os
import tempfile
import wave

from project_paths import asset_root


def validate_wav_name(name):
    if (not isinstance(name, str) or not name or '/' in name or '\\' in name
            or not name.lower().endswith('.wav')):
        raise ValueError('Choose a WAV file from the sound library.')


def wav_path(root, name, directory='sounds'):
    validate_wav_name(name)
    for library in (Path(root) / directory, asset_root() / directory):
        path = library / name
        if path.is_file():
            return path
    raise FileNotFoundError(f'WAV file is missing: {name}')


def import_wav(source, library):
    source = Path(source)
    with wave.open(str(source), 'rb') as audio:
        if audio.getnframes() == 0:
            raise ValueError('Choose a WAV file containing audio.')
    contents = source.read_bytes()
    digest = hashlib.sha256(contents).hexdigest()[:12]
    name = f'{source.stem}-{digest}.wav'
    library = Path(library)
    library.mkdir(parents=True, exist_ok=True)
    target = library / name
    if not target.exists():
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=library, delete=False) as output:
                temporary = Path(output.name)
                output.write(contents)
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return name


def sound_trigger_settings(parameters):
    name = parameters.get('file')
    validate_wav_name(name)
    loop = parameters.get('loop', False)
    if type(loop) is not bool:
        raise ValueError('Loop must be true or false.')
    return name, loop

"""Validate and import project WAV assets."""

import hashlib
import io
import json
from pathlib import Path
import os
import tempfile
import wave

from project_paths import asset_root


def validate_wav_name(name):
    if (not isinstance(name, str) or not name or '/' in name or '\\' in name
            or '\0' in name or not name.lower().endswith('.wav')):
        raise ValueError('Choose a WAV file from the sound library.')


def split_sound_reference(reference, default_directory='sounds'):
    if isinstance(reference, str):
        directory, separator, name = reference.partition('/')
        if separator and directory in ('sounds', 'music'):
            validate_wav_name(name)
            return directory, name
    validate_wav_name(reference)
    return default_directory, reference


def wav_path(root, name, directory='sounds'):
    directory, name = split_sound_reference(name, directory)
    for library in (Path(root) / directory, asset_root() / directory):
        path = library / name
        if path.is_file():
            return path
    raise FileNotFoundError(f'WAV file is missing: {name}')


def sound_library(root):
    references = set()
    for base in (Path(root), asset_root()):
        for directory in ('sounds', 'music'):
            for path in (base / directory).glob('*'):
                if path.is_file() and path.suffix.lower() == '.wav' and '\\' not in path.name:
                    references.add(path.name if directory == 'sounds' else f'music/{path.name}')
    return sorted(references, key=str.casefold)


def _wav_contents(source):
    contents = Path(source).read_bytes()
    with wave.open(io.BytesIO(contents), 'rb') as audio:
        frames = audio.getnframes()
        if not frames or len(audio.readframes(frames)) != frames * audio.getnchannels() * audio.getsampwidth():
            raise ValueError('Choose a complete WAV file containing audio.')
    return contents


def _write_asset(target, contents):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(contents)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def import_wav(source, library):
    source = Path(source)
    contents = _wav_contents(source)
    library = Path(library)
    name = f'{source.stem}.wav'
    validate_wav_name(name)
    target = library / name
    bundled = asset_root() / library.name
    suffix = hashlib.sha256(contents).hexdigest()[:12]
    counter = 0
    while target.exists() or (bundled / target.name).exists():
        existing = target if target.exists() else bundled / target.name
        if existing.is_file() and existing.read_bytes() == contents:
            return target.name
        counter += 1
        version = suffix if counter == 1 else f'{suffix}-{counter}'
        target = library / f'{source.stem}-{version}.wav'
    _write_asset(target, contents)
    return target.name


def replace_wav(root, reference, source):
    directory, name = split_sound_reference(reference)
    _write_asset(Path(root) / directory / name, _wav_contents(source))


def read_sound_defaults(root):
    path = Path(root) / 'sounds' / 'defaults.json'
    try:
        with path.open(encoding='utf-8') as source:
            settings = json.load(source)
    except FileNotFoundError:
        return {}
    if not isinstance(settings, dict) or not all(isinstance(value, str) for value in settings.values()):
        raise ValueError('Sound defaults must map sound cues to WAV files.')
    return settings


def save_sound_defaults(root, settings):
    contents = json.dumps(settings, indent=2, sort_keys=True) + '\n'
    _write_asset(Path(root) / 'sounds' / 'defaults.json', contents.encode('utf-8'))


def sound_trigger_settings(parameters):
    name = parameters.get('file')
    split_sound_reference(name)
    loop = parameters.get('loop', False)
    if type(loop) is not bool:
        raise ValueError('Loop must be true or false.')
    return name, loop

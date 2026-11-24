# Run this as a NEW CODE CELL in the SAME completed Kaggle notebook session.
# It does not rerun the experiment; the runner already wrote this 32-byte key.
from pathlib import Path
import hashlib
from IPython.display import FileLink, display

_work = Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()
_out = Path(globals().get('OUT', _work / 'matched-editguard-validation-v1'))
_key_source = _out / 'public-key.bin'
if not _key_source.is_file():
    raise FileNotFoundError(
        f'Could not find {_key_source}. Run this in the original completed Kaggle '
        'session; do not rerun the GPU experiment just to regenerate this key.'
    )

_key_bytes = _key_source.read_bytes()
if len(_key_bytes) != 32:
    raise ValueError(f'Expected a raw 32-byte Ed25519 public key, got {len(_key_bytes)} bytes')

# Copy to a simple downloadable path and display its SHA-256 for transfer checks.
_key_download = _work / 'matched-editguard-validation-v1-public-key.bin'
_key_download.write_bytes(_key_bytes)
print('File:', _key_download.name)
print('Bytes:', len(_key_bytes))
print('SHA-256:', hashlib.sha256(_key_bytes).hexdigest())
display(FileLink(str(_key_download)))

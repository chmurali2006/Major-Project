"""Source-bound same32-input detached binary baseline; original notebook unchanged."""
import json
from build_grid_control_notebook import build,FILES,ROOT


def build_binary():
    original=list(FILES)
    try:
        FILES.extend(['src/signed_manifest.py','src/binary_signed_grid.py','scripts/experiment_binary_grid.py'])
        nb=build()
    finally:FILES[:]=original
    nb['cells'][0]['source']=['# Compact binary signed-grid baseline — same32 images\n',
        'CPU only. Attach the same image dataset; no checkpoint or training.\n',
        'Ed25519 signatures plus SHA256 tile digests at4×4/8×8; no pixel embedding.\n',
        'Counts header, signature and raw digests, excluding trusted-key distribution.\n',
        'Standard control, not a new research contribution.\n']
    for c in nb['cells']:
        if c['cell_type']!='code':continue
        text=''.join(c['source']).replace("OUT=WORK/'grid-control32-v1'","OUT=WORK/'binary-grid32-v1'")
        text=text.replace("CODE/'scripts/experiment_grid_tradeoff.py'","CODE/'scripts/experiment_binary_grid.py'")
        text=text.replace('grid-results.json','binary-grid-results.json').replace('grid-control32-results.zip','binary-grid32-results.zip')
        c['source']=text.splitlines(True)
    return nb


if __name__=='__main__':
    out=ROOT/'deliverables/binary_grid32.ipynb';out.write_text(json.dumps(build_binary(),indent=1)+'\n');print(out)

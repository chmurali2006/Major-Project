"""Compile notebook cells; optionally run its extracted source on synthetic data."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--execute-wiring', action='store_true')
    args=ap.parse_args()
    notebook=json.loads((ROOT/'notebooks/keyswm_isic2019.ipynb').read_text())
    cells=[c for c in notebook['cells'] if c['cell_type']=='code']
    for i,c in enumerate(cells):
        compile(''.join(c['source']),f'<cell {i}>','exec')
    print(f'{len(cells)} code cells compile')
    if not args.execute_wiring: return
    import cv2
    import numpy as np
    with tempfile.TemporaryDirectory() as temp:
        base=Path(temp)
        project=base/'project'
        first=''.join(cells[0]['source']).replace("Path('/kaggle/working/keyswm-project')",f'Path({str(project)!r})')
        exec(compile(first,'<source extraction>','exec'),{})
        data=base/'synthetic-data'
        data.mkdir()
        rows=['image,NV']
        rng=np.random.default_rng(7)
        for i in range(64):
            name=f'ISIC_TEST_{i:04d}'
            cv2.imwrite(str(data/f'{name}.jpg'),rng.integers(30,220,(64,64,3),dtype=np.uint8))
            rows.append(f'{name},1')
        metadata=data/'labels.csv'
        metadata.write_text('\n'.join(rows)+'\n')
        cmd=[sys.executable,str(project/'scripts/run_suite.py'),'--data',str(data),
             '--metadata',str(metadata),'--out',str(base/'runs'),'--cache',str(base/'cache'),
             '--train-n','7','--val-n','7','--test-n','7','--epochs','1','--width','4',
             '--device','cpu','--seeds','0','--sanity','--probes']
        subprocess.run(cmd+['--execute-configs','C8'],check=True,cwd=project)
        assert not (base/'runs'/'seed-0'/'C12.json').exists()
        first_checkpoint=(base/'runs'/'seed-0'/'C8_checkpoint.pt').read_bytes()
        subprocess.run(cmd+['--execute-configs','C12','--resume'],check=True,cwd=project)
        assert (base/'runs'/'seed-0'/'C8_checkpoint.pt').read_bytes() == first_checkpoint
        print('Separate C8/C12 sessions with one immutable experiment PASS')
        cached = {p: p.stat().st_mtime_ns for p in (base/'cache').rglob('*.npz')}
        subprocess.run(cmd+['--resume'],check=True,cwd=project)
        assert all(p.stat().st_mtime_ns == stamp for p,stamp in cached.items())
        # Moving the same experiment is supported; altered data/source is not.
        manifest=json.loads((base/'runs'/'seed-0'/'manifest.json').read_text())
        image=data/(manifest['train'][0]+'.jpg')
        original=image.read_bytes()
        image.write_bytes(original+b'changed-input')
        failed=subprocess.run(cmd+['--resume'],cwd=project,capture_output=True,text=True)
        assert failed.returncode != 0 and 'resume refused' in failed.stdout+failed.stderr
        image.write_bytes(original)
        module=project/'src'/'protocol.py'
        original=module.read_bytes()
        module.write_bytes(original+b'\n# altered source\n')
        failed=subprocess.run(cmd+['--resume'],cwd=project,capture_output=True,text=True)
        assert failed.returncode != 0 and 'resume refused' in failed.stdout+failed.stderr
        module.write_bytes(original)
        print('Cache reuse and changed-data/source resume rejection PASS')
        subprocess.run([sys.executable,str(project/'scripts/export_results.py'),
                        '--runs',str(base/'runs'),'--out',str(base/'results.zip')],check=True)
        for cid in ('C8','C12'):
            receipt=json.loads((base/'runs'/'seed-0'/f'{cid}.json').read_text())
            assert not receipt['usable'] and receipt['provenance']['sanity']
            assert 'rekey' in receipt and 'wrong_key' in receipt
        print('Portable ZIP: source verification, train, probes, resume and export PASS (synthetic only).')


if __name__=='__main__': main()

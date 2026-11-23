"""Compile notebook cells; optionally run its extracted source on synthetic data."""
import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def validate_defaults(cells):
    expected = {'STAGE': 'diagnostic', 'DIAGNOSTIC_EPOCHS': 20, 'AUTHENTIC_EPOCHS': 2,
                'RESTORE_FROM': None, 'INSTALL_MISSING': False,
                'ALLOW_LABELLED_SUBSET': False, 'ACKNOWLEDGE_EXPERIMENTAL_PROTOCOL_V2': False,
                'SEED': 0}
    tree = ast.parse(''.join(cells[1]['source']))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in expected:
                found[name] = ast.literal_eval(node.value)
    for name, value in expected.items():
        if name not in found or type(found[name]) is not type(value) or found[name] != value:
            raise ValueError(f'Unsafe manual handoff default: {name}; expected {value!r}')
    print('Manual handoff defaults verified: diagnostic only, full corpus audit, no restore/install/full-study acknowledgement')


def execute_diagnostic_cells(cells, context, base):
    """CPU synthetic analogue: explicit GPU-only adaptations, no product edits."""
    work, temp, inputs = base/'working', base/'temporary', base/'input'
    work.mkdir(); temp.mkdir()
    def adapt(source):
        return source.replace('/kaggle/working', str(work)).replace('/kaggle/temp', str(temp)).replace('/kaggle/input', str(inputs))
    config = adapt(''.join(cells[1]['source']))
    assert "DIAGNOSTIC_EPOCHS = 20" in config and "ALLOW_LABELLED_SUBSET = False" in config
    config = config.replace('DIAGNOSTIC_EPOCHS = 20', 'DIAGNOSTIC_EPOCHS = 1')
    config = config.replace('ALLOW_LABELLED_SUBSET = False', 'ALLOW_LABELLED_SUBSET = True')
    exec(compile(config, '<CPU diagnostic configuration>', 'exec'), context)
    dependencies = adapt(''.join(cells[2]['source']))
    start = dependencies.index('if not torch.cuda.is_available():')
    stop = dependencies.index("print('Multiple GPUs", start)
    dependencies = dependencies[:start] + "print('CPU synthetic integration only; CUDA NOT verified')\n" + dependencies[stop:]
    exec(compile(dependencies, '<CPU dependency adaptation>', 'exec'), context)
    audit = adapt(''.join(cells[3]['source']))
    assert audit.count("'--require-gpu',") == 1
    audit = audit.replace("'--require-gpu',", '')
    exec(compile(audit, '<CPU fixture audit>', 'exec'), context)
    for i in (4, 5):
        code = adapt(''.join(cells[i]['source']))
        code = code.replace("'--device', 'cuda'", "'--device', 'cpu'")
        exec(compile(code, f'<diagnostic cell {i}>', 'exec'), context)
    final = adapt(''.join(cells[6]['source']))
    final = final.replace('from IPython.display import FileLink, display', '')
    context.update(FileLink=lambda value: value, display=print)
    exec(compile(final, '<diagnostic summary display>', 'exec'), context)
    import hashlib
    import zipfile
    with zipfile.ZipFile(context['archive']) as z:
        manifest = json.loads(z.read('ARTIFACT_MANIFEST.json'))
        assert set(manifest) == set(z.namelist()) - {'ARTIFACT_MANIFEST.json'}
        for name, expected in manifest.items():
            assert hashlib.sha256(z.read(name)).hexdigest() == expected
        assert not any(name.endswith(('.jpg', '.png')) or '/cache/' in name for name in manifest)
        assert 'SOURCE_MANIFEST.json' in manifest
        summary = json.loads(z.read('diagnostic-summary.json'))
        raw = json.loads(z.read('training-only/diagnostic.json'))
        assert summary['run_complete'] is True and summary['study_ready'] is False
        assert len(summary['models']) == 2
        assert raw['environment']['selected_device'] == 'cpu'
        assert not json.loads(z.read('dataset_audit.json'))['full_official_count_profile']
    print('All seven notebook cells exercised with explicit CPU/subset/one-epoch/display adaptations PASS')
    print('Source extraction, discovery, label audit, preflight, both models, summary and every exported hash PASS')
    print('Synthetic fixture only. CUDA, Kaggle network/mounts and ISIC performance NOT verified.')


def main():
    ap=argparse.ArgumentParser(__doc__)
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--execute-wiring', action='store_true')
    mode.add_argument('--execute-diagnostic', action='store_true', help='CPU synthetic run of all notebook cells with explicit test adaptations')
    ap.add_argument('--exercise-ablations', action='store_true')
    args=ap.parse_args()
    notebook=json.loads((ROOT/'notebooks/keyswm_isic2019.ipynb').read_text())
    cells=[c for c in notebook['cells'] if c['cell_type']=='code']
    for i,c in enumerate(cells):
        compile(''.join(c['source']),f'<cell {i}>','exec')
    print(f'{len(cells)} code cells compile')
    validate_defaults(cells)
    if not (args.execute_wiring or args.execute_diagnostic): return
    import cv2
    import numpy as np
    with tempfile.TemporaryDirectory() as temp:
        base=Path(temp)
        project=base/'project'
        first=''.join(cells[0]['source']).replace("Path('/kaggle/working/keyswm-project')",f'Path({str(project)!r})')
        context={}
        exec(compile(first,'<source extraction>','exec'),context)
        data=(base/'input'/'fixture') if args.execute_diagnostic else base/'synthetic-data'
        data.mkdir(parents=True)
        rows=['image,MEL,NV,BCC,AK,BKL,DF,VASC,SCC']
        rng=np.random.default_rng(7)
        for i in range(64):
            name=f'ISIC_TEST_{i:04d}'
            cv2.imwrite(str(data/f'{name}.jpg'),rng.integers(30,220,(64,64,3),dtype=np.uint8))
            rows.append(f'{name},0,1,0,0,0,0,0,0')
        metadata=data/'labels.csv'
        metadata.write_text('\n'.join(rows)+'\n')
        if args.execute_diagnostic:
            execute_diagnostic_cells(cells, context, base)
            return
        cmd=[sys.executable,str(project/'scripts/run_suite.py'),'--data',str(data),
             '--metadata',str(metadata),'--out',str(base/'runs'),'--cache',str(base/'cache'),
             '--train-n','7','--val-n','7','--test-n','7','--epochs','1','--width','4',
             '--device','cpu','--seeds','0','--sanity','--probes']
        if args.exercise_ablations: cmd.append('--ablations')
        subprocess.run(cmd+['--execute-configs','C8'],check=True,cwd=project)
        assert not (base/'runs'/'seed-0'/'C12.json').exists()
        first_checkpoint=(base/'runs'/'seed-0'/'C8_checkpoint.pt').read_bytes()
        subprocess.run(cmd+['--execute-configs','C12','--resume'],check=True,cwd=project)
        assert (base/'runs'/'seed-0'/'C8_checkpoint.pt').read_bytes() == first_checkpoint
        print('Separate main/attention sessions with one immutable experiment PASS')
        cached = {p: p.stat().st_mtime_ns for p in (base/'cache').rglob('*.npz')}
        subprocess.run(cmd+['--resume'],check=True,cwd=project)
        assert all(p.stat().st_mtime_ns == stamp for p,stamp in cached.items())
        # Corrupted evaluation artifacts must not be skipped or force retraining.
        state=base/'runs'/'seed-0'/'C8_state.pt'
        verdict=base/'runs'/'seed-0'/'C8_verdicts.npz'
        with np.load(verdict,allow_pickle=False) as z:
            previous_iou=z['iou'].copy()
        state.write_bytes(b'truncated-state')
        repaired=subprocess.run(cmd+['--resume'],cwd=project,capture_output=True,text=True)
        assert repaired.returncode==0, repaired.stdout+repaired.stderr
        assert 'Loaded completed epoch 1/1' in repaired.stdout
        assert (base/'runs'/'seed-0'/'C8_checkpoint.pt').read_bytes()==first_checkpoint
        with np.load(verdict,allow_pickle=False) as z:
            np.testing.assert_array_equal(previous_iou,z['iou'])
        print('Damaged model artifact recovered from checkpoint without retraining PASS')
        if args.exercise_ablations:
            sys.path.insert(0,str(project))
            from src.ablations import ABLATIONS
            for variant in ABLATIONS:
                subprocess.run(cmd+['--resume','--execute-configs',variant],check=True,cwd=project)
                r=json.loads((base/'runs'/'seed-0'/f'{variant}.json').read_text())
                assert r['ablation']['variant']==variant
                assert r['strict_authentication']['matches_measured_edit_labels']
                assert not r['usable']
                with np.load(base/'runs'/'seed-0'/f'{variant}_verdicts.npz',allow_pickle=False) as packet:
                    np.testing.assert_array_equal(packet['authentication_failed'],packet['tampered'].astype(bool))
                    np.testing.assert_array_equal(packet['strict_integrity_verdict'],
                        np.where(packet['authentication_failed'],'FAILED_INTEGRITY','VERIFIED'))
            print('All seven constituent removals trained/evaluated in separate resumed CPU jobs PASS (synthetic only)')
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

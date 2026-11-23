"""New fault-isolation tests; these do not certify watermark security."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from src.isic_meta import Metadata
from src.persistence import seal_artifacts
from summarize_isic_study import summarize
from compare_paired import compare


@pytest.mark.parametrize('zero,one',[('0.00','1.00'),('0e0','1e0'),('0','1')])
def test_numeric_one_hot_not_string_truthiness(tmp_path,zero,one):
    p=tmp_path/'labels.csv'
    p.write_text(f'image,MEL,NV,BCC,AK,BKL,DF,VASC,SCC\nISIC_x,{zero},{one},{zero},{zero},{zero},{zero},{zero},{zero}\n')
    assert Metadata(p).dx_of('ISIC_x')=='NV'


def test_summary_keeps_corrupt_receipt_visible(tmp_path):
    (tmp_path/'seed-0').mkdir()
    (tmp_path/'seed-0'/'C8.json').write_text('{broken')
    value=summarize(tmp_path)
    assert not value['complete']
    assert value['invalid_receipts'][0]['path'].endswith('C8.json')


def make_complete_artifact_fixture(root,heldout_source='A',heldout_manifest='M'):
    # Storage fixtures, not trained results. Deliberately not marked usable.
    for seed in range(3):
        folder=root/f'seed-{seed}'
        folder.mkdir()
        for config in ('C0_count','C0_B','C8','C12'):
            make_receipt(folder,config,seed,'A','M')
        for a,b in [('C0_count','C0_B'),('C0_count','C8'),('C8','C12')]:
            bound={side:hashlib.sha256((folder/f'{name}_verdicts.npz').read_bytes()).hexdigest()
                   for side,name in [('a',a),('b',b)]}
            (folder/f'{b}_vs_{a}.json').write_text(json.dumps({'input_sha256':bound,'measured_masks_verified':True}))
    heldout=root/'heldout-T5';heldout.mkdir()
    make_receipt(heldout,'C8',0,heldout_source,heldout_manifest,heldout=True)


def make_receipt(folder,config,seed,source,manifest,heldout=False):
    value={'n':7,'n_tampered':6,'n_intact':1,'iou_tampered_mean':.5,
           'balanced_accuracy':.7,'tpr':.4,'fpr':0.,'usable':False,
           'parameters':dict(train_n=7,val_n=7,test_n=7,epochs=1,ae_epochs=2,width=4,sanity=True),
           'provenance':{'seed':seed,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'manifest_sha256':hashlib.sha256(manifest.encode()).hexdigest()}}
    if heldout:value['heldout']={'family':'T5','n':1,'iou_tampered_mean':.5,'training_families':['T1','none']}
    (folder/f'{config}.json').write_text(json.dumps(value))
    np.savez(folder/f'{config}_verdicts.npz',placeholder=[1])
    suffixes=['.json','_verdicts.npz']
    if not config.startswith('C0'):
        (folder/f'{config}_state.pt').write_bytes(b'storage-only fixture')
        np.savez(folder/f'{config}_validation.npz',placeholder=[1])
        suffixes.extend(['_state.pt','_validation.npz'])
    seal_artifacts(folder,config,suffixes)


@pytest.mark.parametrize('source,manifest,flag',[('B','M','mixed_source_versions'),('A','N','mixed_split_manifests')])
def test_heldout_cannot_escape_summary_lineage_checks(tmp_path,source,manifest,flag):
    make_complete_artifact_fixture(tmp_path,source,manifest)
    value=summarize(tmp_path)
    assert not value['complete'] and value[flag]
    assert not value['three_seed_aggregates']


def test_comparison_binding_and_missing_comparison(tmp_path):
    make_complete_artifact_fixture(tmp_path)
    assert summarize(tmp_path)['complete']  # existence/integrity, NOT scientific approval
    p=tmp_path/'seed-0'/'C8_vs_C0_count.json'
    p.unlink()
    assert not summarize(tmp_path)['complete']
    assert summarize(tmp_path)['comparison_failures']


def test_compare_hashes_current_packets(tmp_path):
    packet={'image_id':['a','b'],'tampered':[0,1],'prediction':[0,1],
            'iou':[1.,.5],'family':['none','T1'],'gt_sha256':['x','y']}
    a,b=tmp_path/'a.npz',tmp_path/'b.npz'
    np.savez(a,**packet);np.savez(b,**packet)
    value=compare(a,b,draws=5,strict=True)
    assert value['input_sha256']=={'a':hashlib.sha256(a.read_bytes()).hexdigest(),'b':hashlib.sha256(b.read_bytes()).hexdigest()}
    assert value['delta']['iou_tampered']['estimate']==0.


@pytest.mark.parametrize('study_rc,summary_fail,export_fail',[(1,True,False),(1,True,True),(0,True,False),(0,False,True)])
@pytest.mark.parametrize('diagnostic', [False, True])
def test_finalization_attempts_export_and_preserves_primary_failure(study_rc,summary_fail,export_fail,diagnostic,tmp_path):
    tree=ast.parse((ROOT/'scripts/build_notebook.py').read_text())
    cell=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Constant)
              and isinstance(node.value,str) and node.value.startswith('cmd = [sys.executable'))
    calls=[]
    def run(cmd,**kwargs):
        script=Path(cmd[1]).name
        calls.append(script)
        if (script in ('summarize_isic_study.py','summarize_diagnostic.py') and summary_fail) or (script=='export_results.py' and export_fail):
            raise subprocess.CalledProcessError(2,cmd)
        return SimpleNamespace(returncode=0)
    child=SimpleNamespace(wait=lambda:study_rc,poll=lambda:study_rc,stdout=['training output\n'])
    fake=SimpleNamespace(Popen=lambda *a,**kw:child,run=run,PIPE=subprocess.PIPE,STDOUT=subprocess.STDOUT)
    ns=dict(subprocess=fake,sys=sys,Path=Path,PROJECT=ROOT,DATA=Path('/fresh/data'),CANONICAL_CSV=Path('/fresh/labels.csv'),
            RUNS=tmp_path,CACHE=Path('/fresh/cache'),SEED=0,TRAIN_N=7,VAL_N=7,TEST_N=7,EPOCHS=1,
            AUTHENTIC_EPOCHS=2,WIDTH=4,RESUME=False,SANITY=True,STAGE='check',RUN_NAME='fresh-check',
            shutil=SimpleNamespace(copy2=Mock()),json=json,DIAGNOSTIC=diagnostic,DIAGNOSTIC_EPOCHS=1)
    if study_rc or export_fail or summary_fail:
        with pytest.raises(RuntimeError) as exc:
            exec(compile(cell,'<fresh finalization probe>','exec'),ns)
        assert str(exc.value).startswith('Study failed:' if study_rc else 'Finalization failed:')
    else:
        exec(compile(cell,'<fresh finalization probe>','exec'),ns)
    assert calls == (['summarize_diagnostic.py','export_results.py'] if diagnostic else ['summarize_isic_study.py','export_results.py'])
    assert 'training output' in (tmp_path/'execution.log').read_text()


def test_mixed_training_recipe_cannot_be_aggregated(tmp_path):
    make_complete_artifact_fixture(tmp_path)
    path=tmp_path/'seed-1'/'C8.json'
    value=json.loads(path.read_text());value['parameters']['width']=16
    path.write_text(json.dumps(value))
    seal_artifacts(path.parent,'C8',['.json','_verdicts.npz','_state.pt','_validation.npz'])
    result=summarize(tmp_path)
    assert result['mixed_training_settings'] and not result['complete']
    assert not result['three_seed_aggregates']


def test_notebook_full_stages_require_unresolved_design_acknowledgment():
    tree=ast.parse((ROOT/'scripts/build_notebook.py').read_text())
    cell=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Constant)
              and isinstance(node.value,str) and node.value.startswith('ACKNOWLEDGE_EXPERIMENTAL'))
    ns={'Path':Path}
    exec(cell,ns)
    assert ns['SANITY'] and ns['TRAIN_N']==ns['VAL_N']==ns['TEST_N']==7
    with pytest.raises(RuntimeError,match='Full run blocked'):
        exec(cell.replace("STAGE = 'diagnostic'", "STAGE = 'main-model'"),{'Path':Path})


def test_notebook_rejects_unknown_cached_modules_before_extracting(tmp_path):
    notebook=json.loads((ROOT/'notebooks/keyswm_isic2019.ipynb').read_text())
    first=next(''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code')
    project=tmp_path/'fresh-project'
    first=first.replace("Path('/kaggle/working/keyswm-project')",f'Path({str(project)!r})')
    # This process already imported src above, but has no verified notebook
    # source-bundle identity. File verification must not bless those cached imports.
    with pytest.raises(RuntimeError,match='Restart the kernel'):
        exec(compile(first,'<fresh cached-module probe>','exec'),{})
    assert not project.exists()


def test_requested_ablations_are_required_for_study_completeness(tmp_path):
    make_complete_artifact_fixture(tmp_path)
    (tmp_path/'study.json').write_text(json.dumps({'ablations':True}))
    result=summarize(tmp_path)
    assert not result['complete']
    assert len(result['missing'])==21
    assert any('without-ae' in p for p in result['missing'])



def test_documentation_stays_small_and_local_links_resolve():
    import re
    expected={'README.md','RUNNING.md','PROTOCOL_V2.md','docs/DESIGN_REVIEW.md',
              'docs/LITERATURE.md','project-context/README.md'}
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*.md')
            if not any(part.startswith('.') or part=='node_modules' for part in p.relative_to(ROOT).parts)}
    assert actual==expected
    for name in expected:
        path=ROOT/name
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',path.read_text()):
            if '://' not in target and not target.startswith('#'):
                assert (path.parent/target.split('#')[0]).exists(), (name,target)



def test_portable_source_contains_retained_nested_classical_modules(tmp_path):
    import zipfile
    from package_project import build
    archive=build(tmp_path/'source.zip')
    with zipfile.ZipFile(archive) as z:
        assert 'src/battery/conditions.py' in z.namelist()
        assert 'src/legacy_carriers.py' in z.namelist()
        assert 'src/legacy_metrics.py' in z.namelist()

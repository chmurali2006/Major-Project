"""Build a small TRAIN-only feasibility handoff; never regenerate sent notebooks."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_classifier_impact_notebook import build as template
FILES=['src/__init__.py','src/isic_classifier_training.py','src/persistence.py','src/diagnostic_impact.py',
       'src/paper_aligned_operators.py','src/signed_manifest.py','src/binary_signed_grid.py',
       'src/diagnostic_constrained_embedding.py','src/diagnostic_correction_controls.py',
       'scripts/prepare_adapted_isic_cohort.py','scripts/experiment_diagnostic_embedding.py']


def build(checkpoint_sha256):
    notebook=template(checkpoint_sha256,files=FILES)
    cells=notebook['cells']
    cells[0]['source']=('''# Diagnostic-constrained embedding — TRAIN feasibility pilot v2

Attach the SAME completed classifier output directory containing best.pt and summary.json, plus ONE original ISIC2019 dataset. Enable GPU. No Internet/model downloads or retraining. Only the first 12 fixed TRAIN images enter the experiment; preparation may rebuild the fixed cohort including other splits, but validation/test images are not used for model outcomes here.

Six variants: fixed QIM, weaker QIM, energy-matched random correction, guided correction, forward-query-matched random search and distortion-gated correction. Twelve guide steps; default bounds and seeds are embedded in the frozen code. No parameter tuning in this notebook. Expected 72 image–variant rows and 720 operator-recovery entries. Full signed4 sidecars add 524378 bytes per image–variant (about 37.8 MB total before ZIP). No medical image pixels are exported.

This is numerical feasibility on the classifier TRAIN split, NOT independent medical efficacy. No independent evaluator is available in this handoff: the summary must say independent_evaluator_tested=false. The random control matches forward queries, not gradient compute or energy. Every nonzero non-carrier correction adds squared distortion; the strict distortion gate consequently returns the fixed baseline. Retain this failure/limitation rather than hiding it.

Run All and save the output ZIP. GPU runtime is not measured; this is smaller in image count than the earlier evaluation but includes optimisation and CPU verification. Do not promise a fixed completion time. Output is incomplete unless summary.json exists, completed=true, and row counts pass the final cell. No final-test access or clinical/novelty/SOTA claim.
''').splitlines(True)
    for cell in cells[1:]:
        text=''.join(cell['source']).replace("OUT=WORK/'adapted-isic2500-classifier-impact-v1'","OUT=WORK/'diagnostic-embedding-train12-v2'").replace('classifier-impact-code-','diagnostic-embedding-code-')
        cell['source']=text.splitlines(True)
    cells[3]['source']=('''# Fail before any experiment if a required dependency is missing.
import cryptography, numpy, PIL
process=subprocess.run([sys.executable,str(CODE/'scripts/experiment_diagnostic_embedding.py'),
    '--preparation',str(PREPARATION),'--cohort',str(CODE/'cohort.json'),
    '--guide-training',str(TRAINING),'--guide-sha256',EXPECTED_CHECKPOINT_SHA256,
    '--out',str(OUT),'--device','cuda'])
print('Exit code:',process.returncode,'; nonzero means incomplete/error')
''').splitlines(True)
    cells[4]['source']=('''PACKAGE=WORK/(OUT.name+'-results.zip')
assert OUT.exists(), 'Resolve preflight failure before exporting'
assert not PACKAGE.exists(), 'Do not overwrite previous export'
with zipfile.ZipFile(PACKAGE,'x',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(OUT.rglob('*')):
        if path.is_file():z.write(path,str(path.relative_to(OUT)))
    z.write(CODE/'cohort.json','cohort.json')
    z.write(PREPARATION/'preparation.json','preparation.json')
    for path in sorted(CODE.rglob('*.py')):z.write(path,'code/'+str(path.relative_to(CODE)))
print('Upload:',PACKAGE,'Bytes:',PACKAGE.stat().st_size)
from IPython.display import FileLink,display
display(FileLink(str(PACKAGE)))
assert process.returncode==0 and (OUT/'summary.json').is_file(), 'Incomplete run; ZIP retained for debugging, not results'
summary=json.loads((OUT/'summary.json').read_text())
assert summary['completed'] is True and summary['images']==12 and summary['rows']==72
assert summary['test_evaluated'] is False and summary['independent_evaluator_tested'] is False
print('Completed TRAIN feasibility pilot. Upload ZIP for review before interpretation.')
''').splitlines(True)
    return notebook

if __name__=='__main__':
    reviewed=json.loads((ROOT/'deliverables/verification-evidence/adapted-classifier-return-v1/review.json').read_text())
    out=ROOT/'deliverables/diagnostic_embedding_train12_v2.ipynb'
    out.write_text(json.dumps(build(reviewed['checkpoint_sha256']),indent=1)+'\n');print(out)

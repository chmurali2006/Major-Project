"""Build a gated 32-image follow-up; preserves original pilot and frozen study."""
import json
from pathlib import Path
from build_editguard_pilot_notebook import build, cell, FILES, ROOT


def build_followup():
    original_files=list(FILES)
    try:
        if 'src/grouping_audit.py' not in FILES:
            FILES.append('src/grouping_audit.py')
        notebook=build()
    finally:
        FILES[:]=original_files
    prior=set()
    for relative in ['editguard-isic-mirror-pilot-v1/preparation.json','kaggle-editguard-local-pilot-v1/preparation.json']:
        p=ROOT/'deliverables/verification-evidence'/relative
        if not p.exists():raise ValueError('required prior evaluation receipt missing: '+relative)
        prior.update(x['image_id'] for x in json.loads(p.read_text())['selected'])
    for c in notebook['cells']:
        text=''.join(c['source'])
        if 'PER_CLASS=1' in text:
            start=text.index('PRIOR_EVALUATION_IDS=')
            end=text.index('\n',start)
            text=text[:start]+'PRIOR_EVALUATION_IDS='+repr(sorted(prior))+text[end:]
            text=text.replace('PER_CLASS=1','PER_CLASS=4\nRUN_EVALUATION=False  # first run is metadata audit only; review before enabling')
            text=text.replace("OUT=WORK/'local-isic-editguard-pilot'","OUT=WORK/'local-isic-editguard-followup32'")
        if '# Preflight runs BEFORE' in text:
            pos=text.index('if METADATA is not None or GROUP_FIELD is not None:')
            text=text[:pos]+'''from src.grouping_audit import audit_grouping
metadata_audit=audit_grouping(LABELS,METADATA,PRIOR_EVALUATION_IDS)
audit_path=WORK/'grouping-audit.json'
audit_path.write_text(json.dumps(metadata_audit,indent=2))
print(json.dumps(metadata_audit,indent=2))
try:
    from IPython.display import display, FileLink
    display(FileLink(str(audit_path)))
except ImportError:
    print(audit_path)
if not RUN_EVALUATION:
    raise RuntimeError('Metadata audit saved to grouping-audit.json. STOP before inference: review coverage and documented grouping semantics, then explicitly enable RUN_EVALUATION if justified.')
'''+text[pos:]
        if 'subprocess.run(command,check=True)' in text:
            text=text.replace('subprocess.run(command,check=True)', '''# Persist exact pre-execution commitment; no threshold tuning on outcomes.
config={'schema':'followup32-config-v1','source_archive_sha256':EXPECTED_SOURCE_ARCHIVE_SHA256,
        'seed':SEED,'per_class':PER_CLASS,'prior_ids':PRIOR_EVALUATION_IDS,
        'group_field':GROUP_FIELD,'allow_image_level':ALLOW_IMAGE_LEVEL_PILOT,
        'labels_sha256':metadata_audit['labels_sha256'],'metadata_sha256':metadata_audit['metadata_sha256'],
        'threshold':.2,'checkpoint':'official clean','cases':['intact','one-bit','brightness32','replace64','copy64','jpeg75'],
        'scope':'bounded32-image followup, not powered clinical or population superiority study'}
commitment=json.dumps(config,sort_keys=True,separators=(',',':')).encode()
config_path=WORK/'followup32-config.json'
if config_path.exists() and config_path.read_bytes()!=commitment:
    raise RuntimeError('Existing commitment differs; use a fresh working directory, never overwrite.')
config_path.write_bytes(commitment)
print('Pre-execution configuration SHA256',hashlib.sha256(commitment).hexdigest())
subprocess.run(command,check=True)''')
        if "package=WORK/'editguard-local-pilot-results.zip'" in text:
            text=text.replace("editguard-local-pilot-results.zip","editguard-followup32-results.zip")
            text += "\n# Keep protocol/audit separate so the strict results auditor retains its existing format.\ndisplay(FileLink(str(config_path)))\ndisplay(FileLink(str(audit_path)))\n"
        c['source']=text.splitlines(True)
    notebook['cells'].insert(0,cell('markdown','''# Gated 32-image follow-up and metadata audit
First run stops after writing grouping-audit.json, before installs/inference.
Supply documented metadata explicitly; no automatic patient-ID inference. Lesion
independence is not patient independence. Missing metadata permits only an explicitly
acknowledged image-level follow-up, never a grouped claim. Known16 preceding image
IDs are excluded along with their supplied groups. Add any other development IDs.

Four images per diagnosis is a bounded engineering comparison, NOT a powered
population/clinical study. CPU budget estimate: roughly20–40minutes from prior
8-image execution; environment-dependent, not a measured32-image runtime.
Thresholds, preprocessing and six cases are unchanged; no training or retuning.
Download the config and grouping audit alongside the results ZIP. A pre-execution
hash records configuration consistency, not an independently timestamped registration.'''))
    return notebook


if __name__=='__main__':
    out=ROOT/'deliverables/editguard_followup32.ipynb'
    out.write_text(json.dumps(build_followup(),indent=1)+'\n')
    print(out)

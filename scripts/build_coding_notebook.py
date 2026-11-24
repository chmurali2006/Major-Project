"""Matched coding development run, reusing exact32 selection/preprocessing."""
import json
from build_grid_control_notebook import build,FILES,ROOT


def build_coding():
    original=list(FILES)
    try:
        FILES.extend(['src/signed_manifest.py','src/binary_signed_grid.py','src/sparse_refinement.py',
            'src/index_syndrome.py','src/bounded_syndrome.py','src/bounded_acceleration.py',
            'scripts/experiment_coding_real.py'])
        nb=build()
    finally:FILES[:]=original
    nb['cells'][0]['source']=['# Matched coding controls — same32 development images\n',
        'CPU only. No GPU/training/checkpoint or EditGuard rerun. Attach same dataset.\n',
        'Compare bounded radius289, index288buckets, set330buckets and full signed4grid.\n',
        'All failures retained; signatures and tile maps exported, never source pixels/private keys.\n',
        'Not independent final data, novelty proof, clinical evidence or SOTA comparison.\n',
        'Allow roughly15–30CPUminutes: estimate from local fixtures, not a measured Kaggle run.\n']
    for c in nb['cells']:
        if c['cell_type']!='code':continue
        text=''.join(c['source']).replace("OUT=WORK/'grid-control32-v1'","OUT=WORK/'coding32-development-v1'")
        text=text.replace("CODE/'scripts/experiment_grid_tradeoff.py'","CODE/'scripts/experiment_coding_real.py'")
        text=text.replace('grid-results.json','coding-results.json').replace('grid-control32-results.zip','coding32-development-results.zip')
        text=text.replace("str(OUT/'coding-results.json')],check=True)","str(OUT/'coding-results.json'),'--artifacts',str(OUT/'artifacts')],check=True)")
        text=text.replace("len(result['rows'])==64","len(result['rows'])==768")
        text=text.replace("    z.write(OUT/'preparation.json','preparation.json')", "    z.write(OUT/'preparation.json','preparation.json')\n    for path in sorted((OUT/'artifacts').iterdir()):z.write(path,'artifacts/'+path.name)")
        text=text.replace('Only numeric receipts exported, never input/prepared pixels.','Export receipts, signatures and tile masks, never input/prepared pixels.')
        text=text.replace('import base64,hashlib,io,json,zipfile,sys,subprocess','import os\nos.environ["OMP_NUM_THREADS"]="2"\nos.environ["MKL_NUM_THREADS"]="2"\nimport base64,hashlib,io,json,zipfile,sys,subprocess')
        c['source']=text.splitlines(True)
    return nb


if __name__=='__main__':
    out=ROOT/'deliverables/coding32_development.ipynb';out.write_text(json.dumps(build_coding(),indent=1)+'\n');print(out)

"""Same32-source sparse-sketch development notebook; no training or checkpoint."""
import json
from build_grid_control_notebook import build,FILES,ROOT


def build_sparse():
    original=list(FILES)
    try:
        FILES.extend(['src/signed_manifest.py','src/binary_signed_grid.py','src/sparse_refinement.py','scripts/experiment_sparse_real.py'])
        nb=build()
    finally:FILES[:]=original
    nb['cells'][0]['source']=['# Sparse authenticated refinement — development experiment\n',
      'Attach the same image dataset. CPU only, no training/checkpoint/EditGuard rerun.\n',
      'Reuses exact32-source selection and hashes. Three sketch budgets; all decoder failures retained.\n',
      'No embedding distortion. This is standard IBLT-style reconciliation plus signed commitment, NOT a novel method claim.\n',
      'No final held-out, patient independence or clinical-safety claim. Allow several CPU minutes (estimate).\n']
    for c in nb['cells']:
        if c['cell_type']!='code':continue
        text=''.join(c['source']).replace("OUT=WORK/'grid-control32-v1'","OUT=WORK/'sparse32-development-v1'")
        text=text.replace("CODE/'scripts/experiment_grid_tradeoff.py'","CODE/'scripts/experiment_sparse_real.py'")
        text=text.replace('grid-results.json','sparse-results.json').replace('grid-control32-results.zip','sparse32-development-results.zip')
        text=text.replace("len(result['rows'])==64","len(result['rows'])==576")
        c['source']=text.splitlines(True)
    return nb


if __name__=='__main__':
    out=ROOT/'deliverables/sparse32_development.ipynb';out.write_text(json.dumps(build_sparse(),indent=1)+'\n');print(out)

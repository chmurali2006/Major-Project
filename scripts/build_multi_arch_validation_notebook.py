"""Build the T1 Kaggle notebook; raw pixels and weights are external inputs."""
import base64, hashlib, io, json, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/__init__.py','src/multi_arch_classifier.py','src/diagnostic_impact.py',
       'src/paper_aligned_operators.py','src/editguard_adapter.py']
COHORT='deliverables/verification-evidence/adapted-isic2019-cohort-v1.json'
PREPARATION='deliverables/verification-evidence/adapted-isic2500-preparation-v2/preparation.json'

def build():
    cohort_bytes=(ROOT/COHORT).read_bytes()
    cohort_sha=hashlib.sha256(cohort_bytes).hexdigest()
    expected='c524a43fce2951dbd68514a94d60610a8daa4f88fd40b8b93c53ee1f03f5aa42'
    if cohort_sha!=expected: raise ValueError('fixed cohort source hash mismatch')
    full=json.loads(cohort_bytes)
    trainval=[r for r in full['selected'] if r.get('split') in ('train','validation')]
    counts={s:sum(r['split']==s for r in trainval) for s in ('train','validation')}
    if counts!={'train':1500,'validation':500}: raise ValueError('fixed TRAIN/validation manifest mismatch')
    sanitized={'schema':'t1-trainval-cohort-manifest-v1','source_cohort_sha256':expected,'selected':trainval}
    prep=json.loads((ROOT/PREPARATION).read_text())
    if prep.get('cohort_sha256')!=expected: raise ValueError('prepared-source receipt cohort mismatch')
    sources=[r for r in prep['selected'] if r.get('split') in ('train','validation')]
    identity=lambda r:(r['image_id'],r['lesion_id'],r['split'],r['melanoma_label'])
    if len(sources)!=2000 or [identity(r) for r in sources]!=[identity(r) for r in trainval]:
        raise ValueError('prepared-source receipt membership mismatch')
    source_safe={'schema':'t1-trainval-source-hashes-v1','cohort_sha256':expected,
                 'selected':[{k:r[k] for k in ('image_id','lesion_id','diagnosis','split','melanoma_label','source_file_sha256','source_decoded_rgb_sha256','prepared_rgb_sha256')} for r in sources]}
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name in FILES:z.writestr(name,(ROOT/name).read_bytes())
        z.writestr('cohort_trainval.json',json.dumps(sanitized,separators=(',',':')))
        z.writestr('source_trainval.json',json.dumps(source_safe,separators=(',',':')))
    bundle=buf.getvalue(); b64=base64.b64encode(bundle).decode(); digest=hashlib.sha256(bundle).hexdigest()
    cells=[]
    def cell(kind,text):
        cells.append({'cell_type':kind,'metadata':{},'source':text.splitlines(True),**({'execution_count':None,'outputs':[]} if kind=='code' else {})})
    cell('markdown','''# T1 — Augmented ISIC classifier comparison (TRAIN/validation only)

We train DenseNet121-Aug and ResNet50-Aug on the fixed 1,500-image TRAIN split and select checkpoints using the fixed 500-image validation split. This notebook never opens TEST image pixels or computes TEST predictions. The old internal holdout remains excluded from confirmatory claims.

Attach the authorized original ISIC 2019 images, the reviewed EditGuard `clean.pth`, and the original baseline checkpoint dataset folder (`best.pt` plus `summary.json`) or its `adapted-isic2500-classifier-v1-results.zip` as Kaggle inputs. Choose a single T4/P100 GPU and enable Internet. The notebook pins Pillow 13.0.0 to match the retained source-to-RGB preparation hashes, downloads official torchvision ImageNet weights, and checks out pinned EditGuard code. Preflight verifies the exact baseline checkpoint SHA and EditGuard MD5, verifies the cohort SHA, and stops before training if any prerequisite is missing. The source-image scan opens only the 2,000 TRAIN/validation IDs; the historical preparation script that iterates all splits is not used.

Augmentation uses geometric flips, random quarter-turns, and mild brightness/contrast/saturation jitter. JPEG, blur, and rescaling are excluded from training. Both models use the same TRAIN-only class weights, AdamW schedule, 20 epochs, seed 4101, and validation balanced-accuracy selection. Evaluation covers the ten deterministic original-image operators plus paired EditGuard contrasts for intact, copy32, JPEG70, JPEG85, and Gaussian05. These are validation development results, not clinical or external validation.

The historical baseline is not retrained or replaced. The notebook exports its two new models and per-image results only; the old baseline comparison must be joined from retained records using verified image/case IDs. No augmented-model outcome is claimed until this notebook has completed and its ZIP has been ingested.
''')
    cell('code','''import os
os.environ['OMP_NUM_THREADS']='2'; os.environ['MKL_NUM_THREADS']='2'
from pathlib import Path
import base64, hashlib, importlib.util, io, json, shutil, subprocess, sys, zipfile
from importlib.metadata import version
# The retained prepared-pixel hashes were produced with Pillow 13.0.0.
if version('Pillow')!='13.0.0':
    subprocess.run([sys.executable,'-m','pip','install','--quiet','Pillow==13.0.0'],check=True)
import torch, torchvision, numpy as np, PIL
assert PIL.__version__=='13.0.0', 'Restart kernel after Pillow installation, then rerun from the top.'
WORK=Path('/kaggle/working'); INPUT=Path('/kaggle/input')
assert torch.cuda.is_available(), 'Enable a single GPU; no CPU fallback.'
assert shutil.disk_usage(WORK).free > 8*1024**3, 'Need at least 8 GiB free.'
print('GPU:',torch.cuda.get_device_name(0),'torch:',torch.__version__,'torchvision:',torchvision.__version__)
''')
    cell('code',f'''raw=base64.b64decode({b64!r})
assert hashlib.sha256(raw).hexdigest()=={digest!r}
CODE=WORK/('t1-code-'+{digest[:12]!r}); CODE.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    for info in z.infolist():
        target=(CODE/info.filename).resolve()
        assert target.is_relative_to(CODE.resolve()) and not info.is_dir()
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(z.read(info))
COHORT=CODE/'cohort_trainval.json'; SOURCE_HASHES=CODE/'source_trainval.json'; PREP=WORK/'t1-trainval-preparation-v1'
RUNS=WORK/'t1-model-runs-v1'; RESULTS=WORK/'t1-results-v1.zip'; WEIGHTS=WORK/'t1-checkpoints-v1.zip'
BASELINE_DIR=WORK/'t1-baseline-v0'
assert not any(p.exists() for p in (PREP,RUNS,RESULTS,WEIGHTS,BASELINE_DIR)), 'Use fresh output paths; no overwrite.'
''')
    cell('code','''# Fail-closed model/source preflight before data processing or GPU work.
import hashlib, subprocess, sys
checkpoints=[p for p in INPUT.rglob('*') if p.is_file() and p.name.lower().startswith('clean') and p.suffix.lower()=='.pth']
unique=sorted({str(p.resolve()):p.resolve() for p in checkpoints}.values())
assert len(unique)==1, f'Expected exactly one EditGuard clean.pth input; found {len(unique)}.'
EDITGUARD_CHECKPOINT=unique[0]
assert hashlib.md5(EDITGUARD_CHECKPOINT.read_bytes()).hexdigest()=='fd8c6987d67071d3e629133499b44765', 'Unreviewed EditGuard checkpoint.'
BASELINE_SHA='38d52ca825472cb525c4c2745f9f7e2e047ddcbc34a6fe6cdcbfbdc0786ba57e'
# Accept either the provided checkpoint dataset folder (best.pt + summary.json)
# or its original results ZIP; exact checkpoint bytes and completion metadata are mandatory.
base_bytes=[]
for best in INPUT.rglob('best.pt'):
    summary_path=best.parent/'summary.json'
    if not summary_path.is_file(): continue
    summary=json.loads(summary_path.read_text())
    digest=hashlib.sha256(best.read_bytes()).hexdigest()
    if (summary.get('completed') is True and summary.get('test_evaluated') is False
        and summary.get('checkpoint_sha256')==BASELINE_SHA and digest==BASELINE_SHA):
        base_bytes.append(best.read_bytes())
if not base_bytes:
    for archive in INPUT.rglob('*.zip'):
        try:
            with zipfile.ZipFile(archive) as z:
                names=z.namelist();bests=[n for n in names if Path(n).name=='best.pt'];summaries=[n for n in names if Path(n).name=='summary.json']
                if len(bests)!=1 or len(summaries)!=1: continue
                summary=json.loads(z.read(summaries[0]));blob=z.read(bests[0])
                if (summary.get('completed') is True and summary.get('test_evaluated') is False
                    and summary.get('checkpoint_sha256')==BASELINE_SHA and hashlib.sha256(blob).hexdigest()==BASELINE_SHA):
                    base_bytes.append(blob)
        except (OSError,zipfile.BadZipFile): continue
assert base_bytes, 'Original baseline checkpoint not found. Add checkpoint input folder containing best.pt + summary.json, or the original results ZIP.'
assert all(hashlib.sha256(b).hexdigest()==BASELINE_SHA for b in base_bytes), 'Ambiguous baseline checkpoint input.'
BASELINE_DIR.mkdir(); BASELINE_CHECKPOINT=BASELINE_DIR/'best.pt'; BASELINE_CHECKPOINT.write_bytes(base_bytes[0])
assert importlib.util.find_spec('skimage') is not None, 'SSIM dependency unavailable.'
if importlib.util.find_spec('einops') is None or importlib.util.find_spec('yaml') is None:
    subprocess.run([sys.executable,'-m','pip','install','einops==0.8.0','PyYAML>=6,<7'],check=True)
CHECKOUT=WORK/'EditGuard-reviewed'
if not CHECKOUT.exists():
    subprocess.run(['git','clone','--filter=blob:none','--sparse','https://github.com/xuanyuzhang21/EditGuard.git',str(CHECKOUT)],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'fetch','origin','174778fb371640bb31b32fcb9f7bfd440c88766b'],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'checkout','--detach','174778fb371640bb31b32fcb9f7bfd440c88766b'],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'sparse-checkout','set','code'],check=True)
assert subprocess.check_output(['git','-C',str(CHECKOUT),'rev-parse','HEAD'],text=True).strip()=='174778fb371640bb31b32fcb9f7bfd440c88766b'
# Download official ImageNet initializations now, before reading medical pixels or spending GPU time.
sys.path.insert(0,str(CODE))
from src.multi_arch_classifier import make_model, _weight_provenance
for arch,weight in [('densenet121_aug','IMAGENET1K_V1'),('resnet50_aug','IMAGENET1K_V2')]:
    m,_,_=make_model(arch,weight);identity=_weight_provenance(arch)
    print('Verified torchvision initialization:',identity['weights_enum'],identity['sha256'])
    del m
''')
    cell('code','''sys.path.insert(0,str(CODE))
from src.editguard_adapter import EditGuard
from src.multi_arch_classifier import prepare_trainval, build_editguard_marked_cache, load_baseline_densenet, evaluate_standard, evaluate_editguard_pairs
adapter=EditGuard(CHECKOUT,EDITGUARD_CHECKPOINT,'cuda')
print('Pinned EditGuard checkpoint:',adapter.provenance['checkpoint_sha256'])
prep=prepare_trainval(COHORT,INPUT,PREP,SOURCE_HASHES)
assert prep['split_counts']=={'train':1500,'validation':500} and prep['test_pixels_opened'] is False
print('Prepared TRAIN/validation only:',prep['split_counts'])
MARKED_CACHE=WORK/'t1-editguard-cache-v1'
build_editguard_marked_cache(adapter,PREP,MARKED_CACHE)
RUNS.mkdir(exist_ok=False)
model0,model0_identity=load_baseline_densenet(BASELINE_CHECKPOINT,COHORT,'cuda')
base_standard=evaluate_standard(model0,PREP,RUNS/'densenet121_base'/'operator-evaluation','densenet121_base',device='cuda',repetitions=2000)
base_editguard=evaluate_editguard_pairs(model0,PREP,MARKED_CACHE,RUNS/'densenet121_base'/'editguard-paired','densenet121_base',device='cuda',repetitions=2000)
(RUNS/'densenet121_base'/'model-identity.json').write_text(json.dumps(model0_identity,indent=2))
print('Model 0 checkpoint:',model0_identity['checkpoint_sha256'])
del model0; torch.cuda.empty_cache()

''')
    cell('code','''from src.multi_arch_classifier import fit_one
for arch,weight in [('densenet121_aug','IMAGENET1K_V1'),('resnet50_aug','IMAGENET1K_V2')]:
    result=fit_one(arch,weight,PREP,RUNS/arch,device='cuda')
    print('Training summary:',json.dumps(result,indent=2))
''')
    cell('code','''from src.multi_arch_classifier import make_model, evaluate_standard, evaluate_editguard_pairs
for arch,weight in [('densenet121_aug','IMAGENET1K_V1'),('resnet50_aug','IMAGENET1K_V2')]:
    model,_,_=make_model(arch,weight)
    ck=torch.load(RUNS/arch/'best.pt',map_location='cpu',weights_only=True)
    model.load_state_dict(ck['state_dict'],strict=True); model.to('cuda').eval()
    standard=evaluate_standard(model,PREP,RUNS/arch/'operator-evaluation',arch,device='cuda',repetitions=2000)
    editguard=evaluate_editguard_pairs(model,PREP,MARKED_CACHE,RUNS/arch/'editguard-paired',arch,device='cuda',repetitions=2000)
    print('Operator summary:',arch,json.dumps(standard['cases'],indent=2))
    print('EditGuard paired summary:',arch,json.dumps(editguard['cases'],indent=2))
    del model,ck; torch.cuda.empty_cache()
''')
    cell('code','''# Export six authorized qualitative cases to Kaggle output only; never commit medical pixels.
import matplotlib.pyplot as plt
from src.paper_aligned_operators import operators
VIS=WORK/'defense_visuals'; VIS.mkdir(exist_ok=False)
valrows=[r for r in prep['selected'] if r['split']=='validation']
chosen=[]
for label in (1,0):
    chosen.extend([r for r in valrows if r['melanoma_label']==label][:3])
assert len(chosen)==6 and sum(r['melanoma_label']==1 for r in chosen)==3
for i,r in enumerate(chosen):
    with PIL.Image.open(PREP/'prepared'/(r['image_id']+'.png')) as im: original=np.asarray(im.convert('RGB'))
    with PIL.Image.open(MARKED_CACHE/'marked'/(r['image_id']+'.png')) as im: marked=np.asarray(im.convert('RGB'))
    op=next(q for q in operators(original,2301+valrows.index(r)) if q['case']=='copy32')
    _,predicted=adapter.localize(op['received'],threshold=.2)
    overlay=op['received'].copy();overlay[predicted]=(.65*overlay[predicted]+.35*np.array([255,0,0])).astype(np.uint8)
    fig,ax=plt.subplots(1,5,figsize=(18,4))
    images=[original,marked,np.clip(np.abs(marked.astype(np.int16)-original.astype(np.int16))*15,0,255).astype(np.uint8),op['pixel_truth'],overlay]
    titles=['Original','EditGuard marked','|marked-original| x15','Copy32 pixel truth','EditGuard map on Copy32']
    for a,img,title in zip(ax,images,titles):a.imshow(img,cmap='gray' if img.ndim==2 else None);a.set_title(title);a.axis('off')
    fig.suptitle(f"{r['image_id']} | {'MEL' if r['melanoma_label'] else 'nonMEL'} | validation")
    fig.tight_layout();fig.savefig(VIS/(r['image_id']+'_panel.png'),dpi=300,bbox_inches='tight');plt.close(fig)

# Export clean ZIPs: metrics/results plus authorized defense visuals; no source dataset or raw weights.
with zipfile.ZipFile(RESULTS,'x',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(RUNS.rglob('*')):
        if p.is_file() and p.name!='best.pt': z.write(p,p.relative_to(RUNS))
    z.write(PREP/'preparation.json','preparation.json')
    z.write(MARKED_CACHE/'cache.json','editguard-marking-fidelity.json')
    for p in sorted(VIS.glob('*.png')): z.write(p,'defense_visuals/'+p.name)
    for p in sorted(CODE.rglob('*.py')): z.write(p,'code/'+str(p.relative_to(CODE)))
with zipfile.ZipFile(WEIGHTS,'x',zipfile.ZIP_DEFLATED) as z:
    for arch in ('densenet121_aug','resnet50_aug'):
        z.write(RUNS/arch/'best.pt',arch+'/best.pt')
        z.write(RUNS/arch/'protocol.json',arch+'/protocol.json')
for archive in (RESULTS,WEIGHTS):
    assert archive.stat().st_size<500_000_000, 'Unexpected archive size; inspect before export.'
    print(archive,archive.stat().st_size,'bytes')
from IPython.display import FileLink,display
PART=80*1024**2
if WEIGHTS.stat().st_size<=PART: weight_files=[WEIGHTS]
else:
    weight_files=[]
    with WEIGHTS.open('rb') as f:
        index=1
        while True:
            block=f.read(PART)
            if not block: break
            part=WORK/f't1-checkpoints-v1.zip.part{index:03d}';part.write_bytes(block);weight_files.append(part);index+=1
    assert all(p.stat().st_size<=PART for p in weight_files)
display(FileLink(str(RESULTS)))
for p in weight_files: display(FileLink(str(p)))
''')
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}

if __name__=='__main__':
    out=ROOT/'deliverables/kaggle_t1_multi_arch_validation.ipynb'
    out.write_text(json.dumps(build(),indent=1)+'\n')
    print(out)

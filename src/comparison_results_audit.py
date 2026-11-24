"""Bounded, non-executing comparison receipt ingestion and map recomputation.

Checks internal consistency, not truth provenance, author identity or clinical safety.
Never extracts archive members to disk or executes included HTML/Python/pickle.
"""
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import re
import zipfile
import numpy as np

CASES={'intact':'intact','one-bit':'edit','brightness32':'edit','replace64':'edit','copy64':'edit','jpeg75':'benign-lossy'}
METHODS=('EditGuard clean','Classical baseline','Signed grid 8')
CHECKPOINT_SHA256='b967b91b94a464ab73f82db63a57ee818e6fc5d99d7ae6aa094a1777cac977d5'


def _json(raw):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON constant')))


class Input:
    def __init__(self,path):
        self.path=Path(path);self.archive=None
        if self.path.is_dir():
            self.prefix=''
            if not (self.path/'report.json').is_file():raise ValueError('directory must contain report.json')
        else:
            self.archive=zipfile.ZipFile(self.path)
            items=self.archive.infolist();names=[i.filename for i in items]
            if len(names)!=len(set(names)) or len(items)>512:raise ValueError('duplicate/too many archive members')
            if sum(i.file_size for i in items)>256*1024**2:raise ValueError('archive decompression limit exceeded')
            for item in items:
                p=PurePosixPath(item.filename)
                if p.is_absolute() or '..' in p.parts or '\\' in item.filename or item.flag_bits&1:
                    raise ValueError('unsafe or encrypted archive member')
                if not item.is_dir() and not (item.filename in ('preparation.json','results/report.json','results/index.html','report.json','index.html') or re.fullmatch(r'(results/)?maps-\d+-\d+\.npz',item.filename)):
                    raise ValueError('unexpected archive member; do not include image pixels or executable code')
            reports=[n for n in names if n in ('report.json','results/report.json')]
            if len(reports)!=1:raise ValueError('exactly one comparison report required')
            self.prefix='results/' if reports[0].startswith('results/') else ''

    def read(self,name,limit):
        if not re.fullmatch(r'(report\.json|maps-\d+-\d+\.npz)',name):raise ValueError('invalid requested artifact name')
        if self.archive:
            info=self.archive.getinfo(self.prefix+name)
            if info.file_size>limit:raise ValueError('artifact size limit exceeded')
            return self.archive.read(info)
        p=(self.path/name).resolve()
        if not p.is_relative_to(self.path.resolve()) or p.stat().st_size>limit:raise ValueError('unsafe or oversized artifact')
        return p.read_bytes()

    def close(self):
        if self.archive:self.archive.close()


def _arrays(raw,expected):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        items=z.infolist()
        if len(items)!=len(expected) or {i.filename for i in items}!={n+'.npy' for n in expected}:raise ValueError('unexpected or duplicate map arrays')
        if sum(i.file_size for i in items)>16*1024**2:raise ValueError('numeric map decompression limit exceeded')
        arrays={}
        for item in items:
            with z.open(item) as f:
                version=np.lib.format.read_magic(f)
                if version==(1,0):shape,fortran,dtype=np.lib.format.read_array_header_1_0(f)
                elif version==(2,0):shape,fortran,dtype=np.lib.format.read_array_header_2_0(f)
                else:raise ValueError('unsupported numeric array header')
                if shape!=(512,512) or dtype.kind not in 'bfiu':raise ValueError('512px finite numeric/bool map arrays required; objects forbidden')
                name=item.filename[:-4]
                if name.endswith(('_truth','_prediction')) and dtype!=np.bool_:raise ValueError('truth/prediction maps must be boolean')
                needed=512*512*dtype.itemsize
                payload=f.read(needed+1)
                if len(payload)!=needed:raise ValueError('array payload size mismatch')
                arr=np.frombuffer(payload,dtype=dtype).reshape(shape,order='F' if fortran else 'C')
                if not np.isfinite(arr).all():raise ValueError('nonfinite map values')
                arrays[name]=arr
        return arrays


def audit(path):
    source=Input(path)
    try:
        raw=source.read('report.json',8*1024**2);report=_json(raw)
        if report.get('schema')!='editguard-matched-smoke-v1' or report.get('complete') is not True:raise ValueError('complete supported comparison receipt required')
        if report.get('threshold',{}).get('value')!=.2:raise ValueError('fixed official clean threshold .2 required')
        if report.get('editguard',{}).get('checkpoint_sha256')!=CHECKPOINT_SHA256 or report['editguard'].get('strict_state_dict') is not True:
            raise ValueError('expected clean-checkpoint provenance declaration required')
        samples=report['samples']
        if not 1<=len(samples)<=32 or len({s['id'] for s in samples})!=len(samples):raise ValueError('1..32 unique sample IDs required')
        if len({s['source'] for s in samples})!=len(samples):raise ValueError('duplicate evaluated source names')
        prep=report.get('input_preparation')
        prepared={}
        if prep:
            if prep.get('complete') is not True:raise ValueError('incomplete input preparation declaration')
            prepared={r['image_id']+'.png':r['prepared_rgb_sha256'] for r in prep['selected']}
            if len(prepared)!=len(prep['selected']) or set(prepared)!={s['source'] for s in samples}:
                raise ValueError('evaluated sources differ from declared preparation selection')
        verified=[];used=set()
        for sample in samples:
            if len(sample['methods'])!=3 or {m['method'] for m in sample['methods']}!=set(METHODS):raise ValueError('all three distinct methods required')
            if len({m['source_rgb_sha256'] for m in sample['methods']})!=1:raise ValueError('methods do not share same decoded source')
            if prepared and sample['methods'][0]['source_rgb_sha256']!=prepared[sample['source']]:
                raise ValueError('decoded source differs from preparation hash')
            seeds={}
            for idx,m in enumerate(sample['methods']):
                if len(m['cases'])!=6 or {c['case'] for c in m['cases']}!=set(CASES):raise ValueError('every case must appear exactly once')
                filename=f'maps-{sample["id"]}-{idx}.npz';used.add(filename)
                data=source.read(filename,16*1024**2)
                if hashlib.sha256(data).hexdigest()!=report['artifacts'].get(filename):raise ValueError('numeric artifact checksum mismatch')
                expected={case+suffix for case in CASES for suffix in ('_truth','_prediction','_score')}
                arrays=_arrays(data,expected)
                for row in m['cases']:
                    name=row['case'];t=arrays[name+'_truth'];p=arrays[name+'_prediction'];score=arrays[name+'_score']
                    if (score<0).any() or (score>1).any():raise ValueError('score map outside [0,1]')
                    if m['method']!='EditGuard clean' and not np.array_equal(score,p.astype(float)):
                        raise ValueError('classical score must equal expanded binary prediction')
                    if row['family']!=CASES[name]:raise ValueError('case-family relabelling detected')
                    if name in seeds and seeds[name]!=row['source_operator_seed']:raise ValueError('unpaired operator seeds')
                    seeds[name]=row['source_operator_seed']
                    if hashlib.sha256(t.tobytes()).hexdigest()!=row['truth_sha256']:raise ValueError('truth hash mismatch')
                    counts={'tp':int((t&p).sum()),'fp':int((~t&p).sum()),'fn':int((t&~p).sum()),'tn':int((~t&~p).sum())}
                    union=int((t|p).sum());den=2*counts['tp']+counts['fp']+counts['fn']
                    expected_values={'confusion':counts,'changed_pixels':int(t.sum()),'highlighted_pixels':int(p.sum()),
                        'pixel_iou':counts['tp']/union if union else None,'pixel_f1':2*counts['tp']/den if den else None,
                        'missed_edit_fraction':counts['fn']/int(t.sum()) if t.any() else None,'predicted_image_positive':bool(p.any())}
                    if any(row.get(k)!=v for k,v in expected_values.items()):raise ValueError('reported metrics differ from recomputed maps')
                    if name=='intact' and t.any():raise ValueError('intact case contains edits')
                    if m['method']=='EditGuard clean' and not np.array_equal(score>.2,p):raise ValueError('prediction differs from declared score threshold')
                    verified.append({'sample':sample['id'],'source':sample['source'],'method':m['method'],'case':name,'family':row['family'],**expected_values})
        if set(report['artifacts'])!=used:raise ValueError('extra/missing declared numerical artifacts')
        summaries=[];paired=[]
        for method in METHODS:
            for case in CASES:
                rows=[r for r in verified if r['method']==method and r['case']==case]
                values=[r['pixel_iou'] for r in rows if r['pixel_iou'] is not None]
                summaries.append({'method':method,'case':case,'family':CASES[case],'n':len(rows),'defined_iou_cases':len(values),
                    'mean_iou_defined_cases':float(np.mean(values)) if values else None,
                    'missed_pixels':sum(r['confusion']['fn'] for r in rows),'extra_pixels':sum(r['confusion']['fp'] for r in rows),
                    'any_highlight_images':sum(r['predicted_image_positive'] for r in rows)})
        for case in CASES:
            differences=[]
            for sample in samples:
                rows={r['method']:r for r in verified if r['sample']==sample['id'] and r['case']==case}
                a,b=rows['EditGuard clean']['pixel_iou'],rows['Classical baseline']['pixel_iou']
                if a is not None and b is not None:differences.append(a-b)
            paired.append({'case':case,'defined_pairs':len(differences),'mean_editguard_minus_classical_iou':float(np.mean(differences)) if differences else None,
                           'editguard_higher_pairs':sum(v>0 for v in differences),'classical_higher_pairs':sum(v<0 for v in differences),'tied_pairs':sum(v==0 for v in differences)})
        return {'schema':'comparison-results-independent-audit-v1','input_report_sha256':hashlib.sha256(raw).hexdigest(),
                'verified_cases':len(verified),'sample_count':len(samples),'synthetic':report['synthetic'],
                'summary':summaries,'paired_iou_differences':paired,'all_case_metrics':verified,
                'safety_or_superiority_established':False,'limitations':[
                    'Internal consistency only: no source pixels/weights included, so truth correctness and actual model execution cannot be independently proved.',
                    'No population confidence intervals without verified independent sampling/groups.',
                    'Empty-union IoU remains undefined; paired comparisons omit undefined pairs and disclose counts.',
                    'Any-highlight positivity is not a calibrated published image-level detection rule.',
                    'JPEG remains separate from edits; method-specific protected references/truth differ.',
                    'A checksum does not establish authorship, provenance, native-original identity or clinical safety.']}
    finally:source.close()

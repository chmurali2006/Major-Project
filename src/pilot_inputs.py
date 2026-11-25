"""Dependency-free attachment preflight. Never picks between ambiguous datasets."""
import csv
import hashlib
import os
from pathlib import Path
CLASSES=('MEL','NV','BCC','AK','BKL','DF','VASC','SCC')
CLEAN_MD5='fd8c6987d67071d3e629133499b44765'
CHECKPOINT_SOURCE='the official EditGuard clean.pth obtained through an authorized source'


def resolve_inputs(root,*,data=None,labels=None,checkpoint=None):
    root=Path(root)
    if not root.is_dir():raise ValueError('Input attachment root does not exist: '+str(root))
    all_files=list(root.rglob('*'))
    csvs=[]
    for p in all_files:
        if p.suffix.lower()!='.csv' or not p.is_file():continue
        try:
            with p.open(newline='',encoding='utf-8-sig') as f:header=next(csv.reader(f),[])
            if {'image',*CLASSES}.issubset(header):csvs.append(p)
        except (OSError,UnicodeError):continue
    if labels is None:
        if len(csvs)!=1:raise ValueError('Expected one matching eight-class ground-truth CSV. Set LABELS explicitly. Candidates: '+str([str(p) for p in csvs]))
        labels=csvs[0]
    labels=Path(labels)
    if not labels.is_file():raise ValueError('LABELS does not exist: '+str(labels))
    ids=set()
    with labels.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not {'image',*CLASSES}.issubset(reader.fieldnames or []):raise ValueError('LABELS must contain image and all eight diagnosis columns')
        for row in reader:
            ident=Path((row.get('image') or '').strip()).stem
            if not ident:raise ValueError('Empty labelled image ID')
            ids.add(ident)
    if not ids:raise ValueError('Empty labels attachment')
    if data is not None:
        data=Path(data)
        if not data.is_dir():raise ValueError('DATA directory does not exist: '+str(data))
        files=list(data.rglob('*'))
    else:files=all_files
    matches={}
    for p in files:
        if p.suffix.lower() in ('.jpg','.jpeg','.png') and p.stem in ids and p.is_file():matches.setdefault(p.stem,[]).append(p)
    missing=sorted(ids-set(matches));duplicates=[i for i,paths in matches.items() if len(paths)!=1]
    if missing:raise ValueError(f'{len(missing)} labelled images not found. Set DATA to the extracted matching image root; archives are not implicitly extracted. First missing: {missing[:3]}')
    if duplicates:raise ValueError('Multiple images match the same IDs. Set DATA to one attachment only. First ambiguous IDs: '+str(duplicates[:3]))
    if data is None:data=Path(os.path.commonpath([str(paths[0].parent) for paths in matches.values()]))
    # The preparation step rejects any duplicate stems, even unlabelled ones.
    stems=set()
    for p in data.rglob('*'):
        if p.suffix.lower() not in ('.jpg','.jpeg','.png') or not p.is_file():continue
        if p.stem in stems:raise ValueError('DATA contains duplicate image stems; select a narrower image root')
        stems.add(p.stem)
    if checkpoint is None:
        candidates=[p for p in all_files if p.is_file() and p.name=='clean.pth']
        if len(candidates)!=1:raise ValueError('Attach official EditGuard clean.pth or set CHECKPOINT explicitly. Candidates: '+str([str(p) for p in candidates])+'. Expected source: '+CHECKPOINT_SOURCE)
        checkpoint=candidates[0]
    checkpoint=Path(checkpoint)
    if not checkpoint.is_file():raise ValueError('CHECKPOINT does not exist: '+str(checkpoint)+'. Expected source: '+CHECKPOINT_SOURCE)
    digest=hashlib.md5()
    with checkpoint.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
    if digest.hexdigest()!=CLEAN_MD5:raise ValueError('CHECKPOINT bytes do not match reviewed official clean.pth; do not substitute arbitrary weights')
    return {'data':data,'labels':labels,'checkpoint':checkpoint,'labelled_image_ids':len(ids),
            'identity_limitation':'Path/ID matching and checkpoint checksum do not verify original ISIC pixels or patient grouping.'}

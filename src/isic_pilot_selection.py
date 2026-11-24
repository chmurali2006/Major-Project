"""Deterministic label-balanced mirror pilot selection; no official-data claim."""
import hashlib
from .dataset_audit import CLASSES


def select(rows, available, per_class=1, seed=29):
    if type(per_class) is not int or not 1<=per_class<=4:raise ValueError('pilot per_class must be 1..4')
    if type(seed) is not int:raise ValueError('integer seed required')
    selected=[]
    for name in CLASSES:
        candidates=[ident for ident,values in rows.items() if ident in available and values[CLASSES.index(name)]==1.]
        # Hash-order deterministic across Python/numpy releases. No pixel/model access.
        candidates.sort(key=lambda ident:(hashlib.sha256(f'{seed}/{ident}'.encode()).hexdigest(),ident))
        if len(candidates)<per_class:raise ValueError(f'insufficient labelled available images for {name}')
        selected.extend({'image_id':ident,'diagnosis':name,'label':CLASSES.index(name)} for ident in candidates[:per_class])
    return selected

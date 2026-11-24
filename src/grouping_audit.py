"""Inspect supplied grouping CSVs without guessing identity or group semantics."""
import csv
import hashlib
from collections import Counter
from pathlib import Path


def audit_grouping(labels, metadata=None, prior_ids=()):
    labels = Path(labels)
    with labels.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if 'image' not in (reader.fieldnames or []):
            raise ValueError('labels require image column')
        ids = [Path(r['image']).stem for r in reader]
    if not ids or any(not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('label image IDs must be nonempty and unique')
    target = set(ids)
    result = {'schema': 'supplied-grouping-audit-v1', 'label_ids': len(ids),
              'labels_sha256': hashlib.sha256(labels.read_bytes()).hexdigest(),
              'metadata_sha256': None, 'fields': {}, 'ready_fields': [],
              'limitations': ['CSV contents do not establish official identity or patient independence.',
                             'A lesion ID is not a patient ID. Column names are not verified semantics.',
                             'Prior ID exclusions are only as complete as the supplied development ledger.']}
    if metadata is None:
        result['status'] = 'metadata_missing'
        return result
    metadata = Path(metadata)
    result['metadata_sha256'] = hashlib.sha256(metadata.read_bytes()).hexdigest()
    with metadata.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if 'image' not in (reader.fieldnames or []):
            raise ValueError('metadata requires image column')
        fields = [k for k in ('patient_id', 'lesion_id') if k in reader.fieldnames]
        rows = {}
        for row in reader:
            ident = Path(row['image']).stem
            if ident in rows:
                raise ValueError('duplicate metadata image ID; resolve before evaluation')
            rows[ident] = row
    for field in fields:
        groups = {i: (rows.get(i, {}).get(field) or '').strip() for i in target}
        counts = Counter(v for v in groups.values() if v)
        excluded = {groups[i] for i in prior_ids if groups.get(i)}
        missing = sum(not v for v in groups.values())
        result['fields'][field] = {'missing_labelled_ids': missing, 'distinct_groups': len(counts),
                                  'multi_image_groups': sum(n > 1 for n in counts.values()),
                                  'largest_group': max(counts.values(), default=0),
                                  'prior_groups_excluded': len(excluded),
                                  'remaining_candidate_ids': sum(bool(v) and v not in excluded and i not in prior_ids for i,v in groups.items())}
        if not missing:
            result['ready_fields'].append(field)
    result['status'] = 'complete_supplied_groups_available' if result['ready_fields'] else 'no_complete_supplied_groups'
    return result

"""Audit actual attached ISIC 2019 ground truth and images, not dataset slugs."""
import csv
from collections import Counter
import hashlib
from pathlib import Path

CLASSES = ('MEL','NV','BCC','AK','BKL','DF','VASC','SCC')
OFFICIAL = dict(zip(CLASSES,(4522,12875,3323,867,2624,239,253,628)))


def label_rows(path):
    rows = {}
    total = 0
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not {'image', *CLASSES}.issubset(reader.fieldnames or []):
            raise ValueError(f'{path}: expected image and all eight ISIC class columns')
        for row in reader:
            total += 1
            ident = Path(row['image'].strip()).stem
            if not ident:
                raise ValueError('empty image identifier')
            try:
                values = tuple(float(row[c]) for c in CLASSES)
                unknown = float(row.get('UNK') or 0)
            except (ValueError, TypeError):
                raise ValueError(f'invalid labels for {ident}')
            if any(v not in (0., 1.) for v in values) or sum(values) != 1 or unknown != 0:
                raise ValueError(f'{ident}: expected exactly one known diagnosis')
            if ident in rows and rows[ident] != values:
                raise ValueError(f'conflicting duplicate labels for {ident}')
            rows[ident] = values
    if not rows:
        raise ValueError('ground truth is empty')
    return rows, total


def discover(input_root):
    """Return candidate roots/CSVs without guessing among ambiguous attachments."""
    root = Path(input_root)
    csvs = []
    for p in sorted(root.rglob('*.csv')):
        try:
            with p.open(encoding='utf-8-sig', newline='') as f:
                header = next(csv.reader(f), [])
            if {'image', *CLASSES}.issubset(header):
                csvs.append(p)
        except (OSError, UnicodeError):
            continue
    # One input dataset can have nested image folders; collapse to attachment root.
    roots = sorted({root / p.relative_to(root).parts[0] for p in root.rglob('*.jpg')})
    archives = sorted(root.rglob('*.zip'))
    return {'image_roots': [str(p) for p in roots],
            'ground_truth_csvs': [str(p) for p in csvs],
            'zip_archives': [str(p) for p in archives]}


def audit(data, labels, canonical_csv, allow_subset=False):
    data, labels, canonical_csv = map(Path, (data, labels, canonical_csv))
    paths = sorted(data.rglob('*.jpg'))
    if not paths:
        raise ValueError('no extracted lowercase .jpg images; attach/extract the training images first')
    image_ids = [p.stem for p in paths]
    if len(image_ids) != len(set(image_ids)):
        raise ValueError('duplicate image ids across image folders; choose the training input root only')
    rows, total = label_rows(labels)
    missing = sorted(set(rows) - set(image_ids))
    if missing:
        raise ValueError(f'{len(missing)} labelled images missing, e.g. {missing[:3]}')
    counts = Counter(CLASSES[vals.index(1.)] for vals in rows.values())
    full = len(rows) == 25331 and dict(counts) == OFFICIAL and len(paths) == 25331
    if not full and not allow_subset:
        raise ValueError(f'not the complete official class/count profile: {len(paths)} images, '
                         f'{len(rows)} labels, counts={dict(counts)}. '
                         'Attach complete ISIC 2019 training input/ground truth, or explicitly allow a labelled subset.')
    canonical_csv.parent.mkdir(parents=True, exist_ok=True)
    with canonical_csv.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['image', *CLASSES])
        writer.writerows([ident, *rows[ident]] for ident in sorted(rows))
    # Decode all selected experiment images later; here inspect a small fixed sample.
    import cv2
    for p in paths[::max(1,len(paths)//16)]:
        if cv2.imread(str(p)) is None:
            raise ValueError(f'unreadable image: {p}')
    return {'image_root':str(data), 'ground_truth':str(labels), 'image_files':len(paths),
            'label_rows':total, 'unique_labels':len(rows), 'class_counts':dict(counts),
            'full_official_count_profile':full, 'allow_subset':allow_subset,
            'canonical_csv':str(canonical_csv),
            'canonical_label_sha256':hashlib.sha256(canonical_csv.read_bytes()).hexdigest(),
            'identity_limitation':'Class counts/ids are audited; this does not prove mirror authenticity or absence of lesion leakage.'}

"""Acquire the public mirror outside the workspace and audit overlapping labels."""
import argparse
import base64
import csv
import json
from pathlib import Path
import subprocess


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--destination', type=Path, required=True)
    args = ap.parse_args()
    dest = args.destination.resolve()
    root = Path(__file__).resolve().parents[1]
    if dest == root or root in dest.parents:
        raise ValueError('dataset pixels must be outside the repository')
    if not dest.exists():
        subprocess.run(['git','clone','--depth','1',
                        'https://github.com/Sushma7890creator/ISIC-2019-dataset.git',str(dest)],check=True)
    rows = {}
    columns = None
    count = 0
    for part in range(1,6):
        endpoint = f'repos/UdaykiranReddy-1/FedExBC/contents/Dataset/ISIC_2019_Training_Input/split_part_{part}.csv'
        response = json.loads(subprocess.check_output(['gh','api',endpoint],text=True))
        text = base64.b64decode(response['content']).decode('utf-8-sig')
        reader = csv.DictReader(text.splitlines())
        if columns is not None and reader.fieldnames != columns:
            raise ValueError('inconsistent label schemas')
        columns = reader.fieldnames
        for row in reader:
            count += 1
            ident = row['image']
            if ident in rows and rows[ident] != row:
                raise ValueError(f'conflicting diagnosis for {ident}')
            rows[ident] = row
    images = {p.stem:p for p in dest.rglob('*.jpg')}
    missing = sorted(set(rows)-set(images))
    if missing:
        raise ValueError(f'{len(missing)} labels do not resolve to images')
    with (dest/'ISIC_2019_GroundTruth_deduplicated.csv').open('w') as fh:
        writer=csv.DictWriter(fh,fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows[k] for k in sorted(rows))
    audit={'image_files':len(images),'label_rows':count,'unique_labels':len(rows),
           'missing_images':len(missing),'image_source':'Sushma7890creator/ISIC-2019-dataset',
           'label_source':'UdaykiranReddy-1/FedExBC split_part_1..5.csv'}
    (dest/'acquisition.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    main()

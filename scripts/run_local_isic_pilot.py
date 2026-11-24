"""Prepare caller-supplied images and run the fixed EditGuard pilot in manifest order."""
import argparse
import csv
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.local_isic_pilot import prepare


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--data',type=Path,required=True)
    ap.add_argument('--labels',type=Path,required=True)
    ap.add_argument('--metadata',type=Path)
    ap.add_argument('--group-field',choices=['patient_id','lesion_id'])
    ap.add_argument('--allow-image-level-pilot',action='store_true')
    ap.add_argument('--exclude-csv',type=Path,help='previously evaluated IDs; column image_id')
    ap.add_argument('--per-class',type=int,default=1)
    ap.add_argument('--seed',type=int,default=73)
    ap.add_argument('--out',type=Path,required=True,help='new directory outside repository and image root')
    ap.add_argument('--prepare-only',action='store_true')
    ap.add_argument('--checkout',type=Path)
    ap.add_argument('--checkpoint',type=Path)
    args=ap.parse_args();out=args.out.resolve()
    if out==ROOT or ROOT in out.parents:ap.error('output containing prepared pixels must be outside repository')
    if not args.prepare_only and (not args.checkout or not args.checkpoint):ap.error('checkout/checkpoint required unless prepare-only')
    excluded=[]
    if args.exclude_csv:
        with args.exclude_csv.open(newline='') as f:
            reader=csv.DictReader(f)
            if 'image_id' not in (reader.fieldnames or []):ap.error('exclusion CSV requires image_id')
            excluded=[r['image_id'] for r in reader]
            if any(not i.strip() for i in excluded):ap.error('empty exclusion ID')
    report=prepare(args.data,args.labels,out,metadata=args.metadata,group_field=args.group_field,
                   allow_image_level=args.allow_image_level_pilot,per_class=args.per_class,seed=args.seed,exclude_ids=excluded)
    print('Preparation complete:',out,flush=True)
    if args.prepare_only:return
    subprocess.run([sys.executable,str(ROOT/'scripts/compare_editguard.py'),
                    '--checkout',str(args.checkout),'--checkpoint',str(args.checkpoint),
                    '--preparation',str(out/'preparation.json'),'--out',str(out/'results'),
                    '--images',*[str(out/'prepared'/(r['image_id']+'.png')) for r in report['selected']]],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/report_editguard_comparison.py'),
                    '--receipts',str(out/'results/report.json'),'--out',str(out/'results/index.html')],check=True)


if __name__=='__main__':main()

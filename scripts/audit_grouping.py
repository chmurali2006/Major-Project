"""Audit attached CSV metadata locally; does not run models or infer patient IDs."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.grouping_audit import audit_grouping


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--labels',type=Path,required=True)
    p.add_argument('--metadata',type=Path)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    report=audit_grouping(args.labels,args.metadata)
    with args.out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
    print(report['status'])


if __name__=='__main__':main()

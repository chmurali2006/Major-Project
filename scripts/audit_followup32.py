"""Audit returned32-image ZIP plus separately downloaded config and grouping JSON."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.comparison_results_audit import Input, _json, audit
from src.followup_protocol import check_protocol
from src.comparison_failure_ledger import failure_ledger, cost_summary, render_ledger
from src.persistence import source_digest
from audit_comparison_results import render


def bounded_json(path):
    raw=Path(path).read_bytes()
    if len(raw)>2**20:raise ValueError('companion JSON exceeds1MiB')
    return _json(raw),hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ('input','config','grouping','out'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.out.suffix!='.json' or args.out.exists() or args.out.with_suffix('.html').exists():p.error('new JSON/HTML paths required')
    config,config_hash=bounded_json(args.config);grouping,group_hash=bounded_json(args.grouping)
    source=Input(args.input)
    try:report=_json(source.read('report.json',16*1024**2))
    finally:source.close()
    prior=[]
    for name in ('editguard-isic-mirror-pilot-v1','kaggle-editguard-local-pilot-v1'):
        prep=json.loads((ROOT/'deliverables/verification-evidence'/name/'preparation.json').read_text())
        prior.extend(s['image_id'] for s in prep['selected'])
    protocol=check_protocol(config,grouping,report,prior)
    result=audit(args.input)
    result.update(protocol_check=protocol,config_file_sha256=config_hash,grouping_file_sha256=group_hash,audit_source_sha256=source_digest(ROOT))
    result['failure_ledger']=failure_ledger(result)
    result['recorded_costs']=cost_summary(report)
    page=render(result).replace('</header>','<p>Follow-up protocol declarations matched:32 sources, four per class, known exclusions and companion hashes. This is not independent registration or patient-independence certification.</p></header>',1)
    page=page.replace('</html>',render_ledger(result['failure_ledger'],result['recorded_costs'])+'</html>')
    with args.out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    with args.out.with_suffix('.html').open('x') as f:f.write(page)
    print('Protocol and saved maps passed:',result['verified_cases'],'cases')


if __name__=='__main__':main()

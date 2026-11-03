"""Sequential portable study with logs, restart support and paired summaries."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.persistence import atomic_json, source_digest
from src.ablations import ABLATIONS

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(__doc__)
    for name in ('data','out','cache'):
        ap.add_argument('--'+name, type=Path, required=True)
    ap.add_argument('--metadata', type=Path, required=True)
    ap.add_argument('--seeds', default='0,1,2')
    ap.add_argument('--ablations', action='store_true', help='freeze/enable registered matched constituent removals')
    ap.add_argument('--configs', default='C8,C12')
    ap.add_argument('--execute-configs', default=None)
    ap.add_argument('--only-heldout', action='store_true')
    ap.add_argument('--train-n', type=int, default=2000)
    ap.add_argument('--val-n', type=int, default=150)
    ap.add_argument('--test-n', type=int, default=1000)
    ap.add_argument('--epochs', type=int, default=3)
    ap.add_argument('--ae-epochs', type=int, default=2)
    ap.add_argument('--width', type=int, default=16)
    ap.add_argument('--device', choices=['auto','cpu','cuda'], default='auto')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--sanity', action='store_true')
    ap.add_argument('--probes', action='store_true')
    ap.add_argument('--heldout-run', action='store_true')
    args=ap.parse_args()
    if args.ablations: args.configs=','.join(dict.fromkeys(args.configs.split(',')+list(ABLATIONS)))
    args.out.mkdir(parents=True, exist_ok=True)
    contract = {k:v for k,v in vars(args).items() if k not in (
        'data','metadata','out','cache','seeds','execute_configs','only_heldout','heldout_run','resume','device')}
    contract['source_sha256'] = source_digest(ROOT)
    contract_path = args.out/'study.json'
    if contract_path.exists() and json.loads(contract_path.read_text()) != contract:
        raise ValueError('resume refused: study source or frozen training settings changed; use a new output directory')
    atomic_json(contract_path, contract)
    logs=args.out/'logs'
    logs.mkdir(exist_ok=True)
    def execute(script, options, log):
        cmd=[sys.executable, '-u', str(ROOT/'scripts'/script), *map(str,options)]
        print(f'Running {script}; log: {log}', flush=True)
        with log.open('a',encoding='utf-8') as fh:
            fh.write('\nCOMMAND '+json.dumps(cmd)+'\n')
            child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            try:
                for line in child.stdout:
                    print(line,end='',flush=True)
                    fh.write(line)
                    fh.flush()
                rc=child.wait()
                if rc:
                    raise subprocess.CalledProcessError(rc,cmd)
            except BaseException:
                child.terminate()
                child.wait()
                raise
    seeds=[int(s) for s in args.seeds.split(',')]
    if not seeds or len(seeds) != len(set(seeds)) or any(s < 0 for s in seeds):
        raise ValueError('seeds must be distinct nonnegative integers')
    jobs=[] if args.only_heldout else [(f'seed-{s}',s,None,args.configs) for s in seeds]
    if args.heldout_run or args.only_heldout:
        jobs.append(('heldout-T5',0,'T5','C8'))
    for name,seed,heldout,configs in jobs:
        out=args.out/name
        options=['--data',args.data,'--metadata',args.metadata,'--out',out,
                 '--cache',args.cache,'--seed',seed,'--configs',configs,'--device',args.device]
        for key in ('train_n','val_n','test_n','epochs','ae_epochs','width'):
            options.extend(['--'+key.replace('_','-'),getattr(args,key)])
        if args.execute_configs and not heldout: options.extend(['--execute-configs',args.execute_configs])
        if args.resume: options.append('--resume')
        if args.sanity: options.append('--sanity')
        if args.probes: options.append('--probes')
        if heldout: options.extend(['--heldout',heldout])
        execute('run_isic_study.py',options,logs/f'{name}.log')
        for a,b in [('C0_count','C0_B'),('C0_count','C8'),('C8','C12')] + ([('C8',v) for v in ABLATIONS] if args.ablations else []):
            pa,pb=out/f'{a}_verdicts.npz',out/f'{b}_verdicts.npz'
            if pa.exists() and pb.exists():
                execute('compare_paired.py',['--a',pa,'--b',pb,'--out',out/f'{b}_vs_{a}.json','--strict'],logs/f'{name}.log')
    execute('summarize_isic_study.py',['--root',args.out,'--out',args.out/'summary.json'],logs/'summary.log')
    print('Finished requested jobs. Keep the entire output directory, including checkpoints.')


if __name__=='__main__':
    main()

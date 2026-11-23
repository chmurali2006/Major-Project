"""Summarize completed or partial TRAIN diagnostics without loading checkpoints."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.diagnostic_report import summarize
from src.persistence import atomic_json


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.input.resolve() == args.out.resolve():
        ap.error('summary must not overwrite the raw diagnostic')
    if args.input.exists():
        result = summarize(json.loads(args.input.read_text()))
    else:
        result = {'schema': 'train-diagnostic-summary-v1', 'run_complete': False, 'study_ready': False,
                  'scope': 'TRAIN-only debugging', 'models': [],
                  'problems': ['Diagnostic receipt missing; inspect execution.log for the original failure.']}
    atomic_json(args.out, result)
    print('Diagnostic execution complete:', result['run_complete'], '| study ready:', result['study_ready'])
    for row in result['models']:
        print(row['model'], '| selected epoch', row['selected_epoch'], '/', row['last_completed_epoch'],
              '| shared TRAIN IoU', row['shared_rule_training_iou'],
              '| pixel-only TRAIN IoU', row['pixel_only_training_iou'])
        for observation in row['observations']:
            print('  -', observation)
    for problem in result['problems']:
        print('INCOMPLETE:', problem)


if __name__ == '__main__':
    main()

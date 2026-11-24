import copy
import json
from pathlib import Path
from src.comparison_failure_ledger import failure_ledger,cost_summary,render_ledger
ROOT=Path(__file__).resolve().parents[1]


def test_actual_pilot_failure_ledger_keeps_catastrophic_copy_failure():
    root=ROOT/'deliverables/verification-evidence/kaggle-editguard-local-pilot-v1'
    audit=json.loads((root/'independent-audit.json').read_text())
    report=json.loads((root/'report.json').read_text())
    ledger=failure_ledger(audit);cost=cost_summary(report)
    copyrow=next(r for r in ledger['rows'] if r['method']=='EditGuard clean' and r['case']=='copy64')
    assert copyrow['complete_target_misses']==1
    assert copyrow['missed_pixels']==4145
    assert copyrow['worst_by_missed_fraction'][0]['missed_fraction']==1
    assert copyrow['worst_by_missed_fraction'][0]['source']=='ISIC_0058884.png'
    assert all(r['family']=='benign-lossy' for r in ledger['rows'] if r['case']=='jpeg75')
    classical=next(r for r in cost['methods'] if r['method']=='Classical baseline')
    assert classical['localization_seconds']['recorded']==48
    assert 'not independently timed' in render_ledger(ledger,cost)


def test_empty_truth_never_counts_as_complete_miss_and_html_escaped():
    row={'method':'<script>','case':'intact','family':'intact','source':'bad',
         'changed_pixels':0,'confusion':{'tp':0,'fn':0,'fp':2}}
    ledger=failure_ledger({'all_case_metrics':[row]})
    assert ledger['rows'][0]['complete_target_misses']==0
    assert ledger['rows'][0]['worst_by_missed_fraction']==[]
    assert '<script>' not in render_ledger(ledger,{'methods':[],'limits':[]})


def test_missing_costs_stay_missing():
    report={'samples':[{'methods':[{'method':'test','cases':[{}]}]}]}
    cost=cost_summary(report)['methods'][0]
    assert cost['localization_seconds']=={'recorded':0,'expected':1,'mean':None,'maximum':None}

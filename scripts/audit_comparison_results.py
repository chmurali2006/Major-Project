"""Validate a returned comparison ZIP/directory and render independently recomputed metrics."""
import argparse
import html
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.comparison_results_audit import audit
from src.persistence import atomic_json,source_digest


def render(result):
    esc=lambda x:html.escape(str(x))
    rows=[]
    for r in result['summary']:
        vals=[r['method'],r['case'],r['family'],r['n'],r['defined_iou_cases'],
              round(r['mean_iou_defined_cases'],6) if r['mean_iou_defined_cases'] is not None else 'undefined',
              r['missed_pixels'],r['extra_pixels'],r['any_highlight_images']]
        rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in vals)+'</tr>')
    pairs=[]
    for r in result['paired_iou_differences']:
        vals=[r['case'],r['defined_pairs'],round(r['mean_editguard_minus_classical_iou'],6) if r['mean_editguard_minus_classical_iou'] is not None else 'undefined',r['editguard_higher_pairs'],r['classical_higher_pairs'],r['tied_pairs']]
        pairs.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in vals)+'</tr>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Independent result-map audit</title><style>body{font:15px/1.6 system-ui;max-width:1300px;margin:36px auto;padding:0 24px;color:#171717}h1,h2{font-family:Georgia,serif}header{border-bottom:1px solid #333}strong{color:#215c71}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:9px;text-align:left;border-bottom:1px solid #bbb}</style><header><h1>Independent result-map audit</h1><p><strong>Metrics recomputed from saved numeric arrays. No superiority or clinical-safety conclusion.</strong></p><p>'''+esc(result['sample_count'])+' sources; '+esc(result['verified_cases'])+''' cases. Input report SHA256: <code>'''+esc(result['input_report_sha256'])+'''</code></p></header><h2>Per-case-family results</h2><p>JPEG is separate from edits. Empty unions remain undefined. Any-highlight counts are not a calibrated image-level detection metric.</p><div class="scroll"><table><tr><th>Method</th><th>Case</th><th>Family</th><th>Inputs</th><th>Defined IoUs</th><th>Mean IoU</th><th>Missed pixels</th><th>Extra pixels</th><th>Any-highlight inputs</th></tr>'''+''.join(rows)+'''</table></div><h2>Paired source-level IoU differences</h2><p>Positive difference favours EditGuard IoU only; this does not account for distortion, missed pixels, trust or storage. No confidence intervals or population inference are claimed.</p><div class="scroll"><table><tr><th>Case</th><th>Defined pairs</th><th>Mean EditGuard − classical</th><th>EditGuard higher</th><th>Classical higher</th><th>Tied</th></tr>'''+''.join(pairs)+'''</table></div><h2>Limits</h2><ul>'''+''.join('<li>'+esc(x)+'</li>' for x in result['limitations'])+'</ul></html>'


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--input',type=Path,required=True,help='returned ZIP or directory containing report.json')
    ap.add_argument('--out',type=Path,required=True,help='new JSON output; HTML written beside it')
    args=ap.parse_args()
    if args.out.suffix!='.json' or args.out.exists() or args.out.with_suffix('.html').exists():ap.error('new JSON and HTML output paths required')
    result=audit(args.input)
    result['audit_source_sha256']=source_digest(ROOT)
    atomic_json(args.out,result);args.out.with_suffix('.html').write_text(render(result))
    print('Independently recomputed cases:',result['verified_cases'])
    print(args.out)


if __name__=='__main__':main()

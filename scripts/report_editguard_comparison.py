"""Render executed paired receipts; never inject paper-reported scores."""
import argparse
import html
import json
from pathlib import Path


def render(reports):
    esc=lambda x:html.escape(str(x))
    sections=[]
    for label,report in reports:
        if report.get('complete') is not True:raise ValueError('complete comparison receipts required')
        rows=[]
        for sample in report['samples']:
            for m in sample['methods']:
                for c in m['cases']:
                    vals=[sample['source']+(' / '+sample['diagnosis'] if sample.get('diagnosis') else ''),m['method'],c['case'],c['family'],c['changed_pixels'],
                          c['highlighted_pixels'],c['confusion']['fn'],c['confusion']['fp'],
                          round(c['pixel_iou'],5) if c['pixel_iou'] is not None else 'undefined (empty union)',
                          round(c['localization_seconds'],3)]
                    rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in vals)+'</tr>')
        fidelity=[]
        for sample in report['samples']:
            for m in sample['methods']:
                vals=[sample['source'],m['method'],round(m['embedding_mse'],6),
                      round(m['embedding_psnr_db'],3) if m['embedding_psnr_db'] is not None else 'no distortion',
                      m['sidecar_bytes'],round(m['setup_seconds'],3)]
                fidelity.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in vals)+'</tr>')
        sections.append('<h2>'+esc(label)+'</h2><p>'+('SYNTHETIC ENGINEERING SMOKE' if report['synthetic'] else (('CALLER-SUPPLIED LOCAL PILOT — supplied metadata, no verified held-out/clinical claim' if report['input_preparation'].get('schema')=='local-isic-pilot-preparation-v1' else 'UNVERIFIED ISIC MIRROR PILOT — resized data, no held-out/clinical claim') if report.get('input_preparation') else 'UPSTREAM EXAMPLE / USER-PREPARED INPUT — not verified medical data'))+'</p><div class="scroll"><table><tr><th>Input</th><th>Method</th><th>MSE</th><th>PSNR dB</th><th>Sidecar bytes</th><th>Setup seconds</th></tr>'+''.join(fidelity)+'</table></div><details open><summary>Every case, including intact and JPEG</summary><div class="scroll"><table><tr><th>Input</th><th>Method</th><th>Case</th><th>Family</th><th>Changed pixels</th><th>Highlighted pixels</th><th>Missed pixels</th><th>Extra pixels</th><th>Pixel IoU</th><th>Localise seconds</th></tr>'+''.join(rows)+'</table></div></details>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EditGuard execution audit</title><style>body{font:15px/1.6 system-ui;color:#171717;max-width:1400px;margin:36px auto;padding:0 24px}h1,h2{font-family:Georgia,serif}header{border-bottom:1px solid #222}strong{color:#215c71}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:8px;border-bottom:1px solid #bbb;text-align:left}details{margin:24px 0}</style><header><h1>EditGuard: executed published-baseline comparison</h1><p><strong>Compatibility/engineering pilot only. Not a reproduced paper benchmark, ISIC study or superiority claim.</strong></p></header><p>Official clean.pth, strict full checkpoint load, threshold 0.2 from upstream instructions. The adapter applies device portability and unused-import patches only, and matches upstream scale-option handling. Identical source/operator/coordinates; each method has its own protected reference and measured changed-pixel truth.</p>'''+''.join(sections)+'''<h2>How to interpret this</h2><ul><li>Inspect each edit family, not a pooled average that hides misses. Some large patches can favour learned boundaries; small exact changes can favour fragile authentication.</li><li>Exact-match HMAC and signed digests are not equivalent to robust learned localisation. The learned mask is not a cryptographic verdict.</li><li>JPEG is reported separately. This uses EditGuard clean weights, not the degradation-trained checkpoint; do not generalise to the latter.</li><li>Any-pixel image positivity is a diagnostic here, not the published method's calibrated image-level decision.</li><li>No verified native-original ISIC study or clinical evaluation established. Consult preparation receipts for resizing, conversion and provenance limits.</li><li>CPU timings are descriptive, not statistically stable latency benchmarks. Signature sidecar storage and embedded pixel distortion are distinct costs.</li><li>No model is declared the winner. These results establish runnable baseline inference, not a new contribution.</li></ul></html>'''


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--receipts',nargs='+',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists():ap.error('new report path required')
    rendered=render([(p.parent.name,json.loads(p.read_text())) for p in args.receipts])
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(rendered)
    print(args.out)


if __name__=='__main__':main()

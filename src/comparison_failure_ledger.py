"""Descriptive failure ledger over independently recomputed rows; no inference."""
import html
from collections import defaultdict
from statistics import mean


def failure_ledger(audited):
    buckets=defaultdict(list)
    for row in audited['all_case_metrics']:
        buckets[(row['method'],row['case'],row['family'])].append(row)
    result=[]
    for (method,case,family),rows in buckets.items():
        changed=[r for r in rows if r['changed_pixels']>0]
        misses=[r for r in changed if r['confusion']['fn']>0]
        complete=[r for r in changed if r['confusion']['tp']==0]
        worst=sorted(changed,key=lambda r:(-r['confusion']['fn']/r['changed_pixels'],str(r['source'])))[:3]
        result.append({'method':method,'case':case,'family':family,'sources':len(rows),
                       'changed_sources':len(changed),'sources_with_missed_pixels':len(misses),
                       'complete_target_misses':len(complete),
                       'missed_pixels':sum(r['confusion']['fn'] for r in rows),
                       'extra_pixels':sum(r['confusion']['fp'] for r in rows),
                       'worst_by_missed_fraction':[{'source':r['source'],'changed_pixels':r['changed_pixels'],
                           'missed_pixels':r['confusion']['fn'],
                           'missed_fraction':r['confusion']['fn']/r['changed_pixels']} for r in worst]})
    return {'schema':'comparison-failure-ledger-v1','rows':result,
            'limits':['Complete target miss means zero overlap with changed pixels, even if unrelated pixels are highlighted.',
                      'JPEG rows describe changed RGB under recompression, not benign-tolerance success.',
                      'Counts are descriptive for these selected inputs, not population failure probabilities.']}


def cost_summary(report):
    buckets=defaultdict(list)
    for sample in report['samples']:
        for method in sample['methods']:buckets[method['method']].append(method)
    result=[]
    for method,rows in buckets.items():
        times=[c.get('localization_seconds') for r in rows for c in r['cases']]
        psnr=[r.get('embedding_psnr_db') for r in rows]
        setup=[r.get('setup_seconds') for r in rows]
        def stats(values):
            defined=[v for v in values if isinstance(v,(int,float)) and not isinstance(v,bool)]
            return {'recorded':len(defined),'expected':len(values),
                    'mean':mean(defined) if defined else None,'maximum':max(defined) if defined else None}
        result.append({'method':method,'setup_seconds':stats(setup),'localization_seconds':stats(times),
                       'embedding_psnr_db':stats(psnr),
                       'embedding_mse':stats([r.get('embedding_mse') for r in rows]),
                       'sidecar_bytes':stats([r.get('sidecar_bytes') for r in rows])})
    return {'schema':'comparison-recorded-costs-v1','methods':result,
            'limits':['Costs are reported by the submitted run, not independently reproduced timings.',
                      'Null PSNR is not automatically zero distortion; consult the method MSE receipt.',
                      'Sidecar bytes exclude keys, model weights and transport overhead; zero sidecar is not zero deployment cost.',
                      'No paired confidence intervals, clinical interpretation or hardware-normalised speed claim.']}


def render_ledger(ledger,costs):
    esc=lambda value:html.escape(str(value))
    rows=[]
    for r in ledger['rows']:
        vals=[r[k] for k in ('method','case','family','changed_sources','sources_with_missed_pixels','complete_target_misses','missed_pixels','extra_pixels')]
        rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in vals)+'</tr>')
    costrows=[]
    for r in costs['methods']:
        values=[r['method']]
        for k in ('setup_seconds','localization_seconds','embedding_psnr_db','embedding_mse','sidecar_bytes'):
            s=r[k];values.append(('unavailable' if s['mean'] is None else format(s['mean'],'.5g'))+' ('+str(s['recorded'])+'/'+str(s['expected'])+' recorded)')
        costrows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    return '<h2>Failure ledger: means do not hide complete misses</h2><div class="scroll"><table><tr><th>Method</th><th>Case</th><th>Family</th><th>Changed sources</th><th>Any missed pixels</th><th>Complete target misses</th><th>Missed pixels</th><th>Extra pixels</th></tr>'+''.join(rows)+'</table></div><h2>Submitted-run costs (not independently timed)</h2><div class="scroll"><table><tr><th>Method</th><th>Setup s</th><th>Localisation s</th><th>PSNR dB</th><th>MSE</th><th>Sidecar bytes</th></tr>'+''.join(costrows)+'</table></div><ul>'+''.join('<li>'+esc(v)+'</li>' for v in ledger['limits']+costs['limits'])+'</ul>'

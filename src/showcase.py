"""CPU-only demonstration of current authentication, not a learned-model benchmark.

All scenarios use the same protected input. Truth is measured by RGB differences;
verification itself never receives the original, the change mask, or the scenario.
"""
import base64
import hashlib
import html
import io
import json
import time

import numpy as np
from PIL import Image
from . import authentication as A

DEMO_KEY = b'public-showcase-key-not-for-production'
IMAGE_ID = 4242


def png_bytes(rgb):
    out = io.BytesIO()
    Image.fromarray(rgb).save(out, format='PNG')
    return out.getvalue()


def data_uri(rgb):
    return 'data:image/png;base64,' + base64.b64encode(png_bytes(rgb)).decode('ascii')


def block_truth(changed):
    h, w = changed.shape
    return changed.reshape(h//8, 8, w//8, 8).any(axis=(1, 3))


def confusion(pred, truth):
    return {'tp': int((pred & truth).sum()), 'fp': int((pred & ~truth).sum()),
            'fn': int((~pred & truth).sum()), 'tn': int((~pred & ~truth).sum())}


def mask_iou(pred, truth):
    union = int((pred | truth).sum())
    return float((pred & truth).sum() / union) if union else None


def overlay(rgb, mask):
    out = rgb.copy()
    out[mask] = np.rint(.55 * rgb[mask] + .45 * np.array([180, 25, 25])).astype(np.uint8)
    return out


def scenarios(protected, image_id=IMAGE_ID):
    h, w = protected.shape[:2]
    y, x = (h//16)*8, (w//16)*8
    yield 'intact', 'Untouched protected image', protected.copy(), DEMO_KEY, image_id, 'content'
    one = protected.copy()
    one[y, x, 0] ^= np.uint8(1)
    yield 'one-pixel', 'One pixel: one embedded bit changed', one, DEMO_KEY, image_id, 'content'
    bright = protected.copy()
    bright[y:y+8, x:x+8] = np.clip(bright[y:y+8, x:x+8].astype(np.int16)+12, 0, 255).astype(np.uint8)
    yield 'brightness', 'Local brightness change (+12, clipped)', bright, DEMO_KEY, image_id, 'content'
    boundary = protected.copy()
    boundary[y-1:y+2, x-2:x+3, 0] ^= np.uint8(1)
    yield 'boundary-patch', '15-pixel edit crossing block boundaries', boundary, DEMO_KEY, image_id, 'content'
    copied = protected.copy()
    copied[y:y+8, x:x+8] = protected[:8, :8]
    yield 'copy-move', 'Protected block copied to a different address', copied, DEMO_KEY, image_id, 'content'
    encoded = io.BytesIO()
    Image.fromarray(protected).save(encoded, format='JPEG', quality=75, subsampling=0)
    with Image.open(io.BytesIO(encoded.getvalue())) as decoded:
        jpeg = np.array(decoded.convert('RGB'))
    yield 'jpeg75', 'JPEG quality 75: lossless contract violated', jpeg, DEMO_KEY, image_id, 'content'
    yield 'wrong-key', 'Unchanged pixels, wrong verification key', protected.copy(), b'wrong-public-key', image_id, 'context'
    yield 'wrong-id', 'Unchanged pixels, wrong trusted version identifier', protected.copy(), DEMO_KEY, image_id+1, 'context'


def build_report(rgb, source_label, synthetic=False):
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError('HxWx3 uint8 RGB required')
    if min(rgb.shape[:2]) < 32:
        raise ValueError('showcase requires dimensions >=32 pixels')
    protected = A.embed(rgb, DEMO_KEY, IMAGE_ID)
    protected_bytes = png_bytes(protected)
    with Image.open(io.BytesIO(protected_bytes)) as stored:
        protected = np.array(stored.convert('RGB'))
    error = protected.astype(np.float64) - rgb.astype(np.float64)
    mse = float(np.mean(error**2))
    report = {'schema': 'rgb-auth-showcase-v1', 'scheme': A.SCHEME,
              'scope': 'single-image demonstration; not a benchmark or clinical validation',
              'synthetic': bool(synthetic), 'source_label': source_label,
              'input_rgb_sha256': hashlib.sha256(rgb.tobytes()).hexdigest(),
              'protected_png_sha256': hashlib.sha256(protected_bytes).hexdigest(),
              'shape': list(rgb.shape), 'trusted_image_id': IMAGE_ID,
              'key_policy': 'public demonstration key; not a deployed secret',
              'embedding': {'mse': mse, 'psnr_db': float(10*np.log10(255.**2/mse)) if mse else None,
                            'maximum_absolute_channel_change': int(np.abs(error).max())},
              'limitations': ['Only lossless storage preserves this fragile watermark.',
                              'Failed integrity does not prove malicious intent.',
                              'The overlay marks suspect 8x8 blocks, not exact altered pixels.',
                              'Key and expected image/version identifier must be trusted externally.',
                              'Replay of an older valid block at the same ID/address is not prevented.',
                              'Not reversible watermarking; PSNR is not evidence of clinical safety.',
                              'No learned-model, novelty, or superiority claim is made.'],
              'cases': []}
    views = []
    for ident, label, received, key, image_id, kind in scenarios(protected):
        started = time.perf_counter()
        failed = A.failures(received, key, image_id)
        elapsed = time.perf_counter() - started
        changed = np.any(received != protected, axis=2)
        truth_blocks = block_truth(changed)
        expanded = failed.repeat(8, 0).repeat(8, 1)
        row = {'id': ident, 'label': label, 'scenario_type': kind,
               'verdict': 'FAILED_INTEGRITY' if failed.any() else 'VERIFIED',
               'changed_pixels': int(changed.sum()), 'failed_blocks': int(failed.sum()),
               'total_blocks': int(failed.size), 'verification_ms': elapsed*1000,
               'received_rgb_sha256': hashlib.sha256(received.tobytes()).hexdigest(),
               'failed_block_sha256': hashlib.sha256(failed.tobytes()).hexdigest(),
               'localisation': {'block_confusion': confusion(failed, truth_blocks),
                                'block_iou': mask_iou(failed, truth_blocks),
                                'expanded_block_pixel_iou': mask_iou(expanded, changed)} if kind == 'content' else None}
        report['cases'].append(row)
        views.append({'received': data_uri(received), 'overlay': data_uri(overlay(received, expanded)),
                      'truth': data_uri(np.repeat((changed*255).astype(np.uint8)[..., None], 3, axis=2))})
    return report, protected_bytes, views, data_uri(rgb), data_uri(protected)


def render_html(report, views, original_uri, protected_uri):
    # Labels are user-controlled: HTML-escape text and escape JSON script closers.
    packet = json.dumps({'report': report, 'views': views}, allow_nan=False).replace('<', '\\u003c')
    source = html.escape(report['source_label'])
    scope = 'SYNTHETIC FIXTURE — not ISIC2019 evidence' if report['synthetic'] else 'USER-SUPPLIED IMAGE — dataset membership unverified'
    notes = ''.join('<li>' + html.escape(note) + '</li>' for note in report['limitations'])
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Medical image integrity — current method demonstration</title>
<style>
*{box-sizing:border-box}body{margin:0 auto;padding:32px 24px;max-width:1180px;color:#151515;background:#fff;font:16px/1.5 system-ui,sans-serif}h1{font:36px/1.15 Georgia,serif;margin:12px 0}h2{font:24px Georgia,serif}small,figcaption,.note{color:#555;font-size:14px}header{border-bottom:1px solid #333;padding-bottom:20px}.steps{letter-spacing:.12em;font-size:12px}select,button{font:inherit;background:#fff;border:1px solid #555;padding:10px;max-width:100%;border-radius:0}select{margin:16px 0;width:100%}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}figure{margin:0}img{width:100%;height:auto;image-rendering:auto;border:1px solid #bbb}figcaption{padding:8px 0}#verdict{font-family:monospace;font-size:23px}dl{display:grid;grid-template-columns:1fr 1fr;gap:6px}dt,dd{margin:0;border-bottom:1px solid #ddd;padding:8px 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;border-bottom:1px solid #ccc;padding:9px 6px}section{margin:28px 0}#warning{border-left:3px solid #a01919;padding-left:12px}details{margin:22px 0}a{color:#8d1717}.scroll{overflow-x:auto}@media(max-width:720px){.grid{grid-template-columns:1fr}h1{font-size:29px}}
</style><header><div class="steps">PROTECT → ALTER → VERIFY</div>
<h1>Medical image tamper detection</h1><p>Block-local RGB HMAC verification. No neural checkpoint required.</p>
<strong>''' + scope + '''</strong><div class="note">''' + source + ''' · Single-image demonstration, not a performance study.</div></header>
<section><details><summary>1. Protection: original and losslessly stored watermarked image</summary><div class="grid">
<figure><img alt="Original input" src="''' + original_uri + '''"><figcaption>Original input to embedding.</figcaption></figure>
<figure><img alt="Protected PNG" src="''' + protected_uri + '''"><figcaption>Watermarked input; not reversible. <a href="protected.png" download>Download protected PNG</a>.</figcaption></figure></div><p id="fidelity"></p></details>
<label for="scenario"><strong>2. Choose a controlled change or a verification-context failure</strong></label><select id="scenario"></select>
<div id="verdict" role="status" aria-live="polite"></div><p id="warning"></p>
<div class="grid"><figure><img id="received" alt="Received image"><figcaption>Received image supplied to verification.</figcaption></figure>
<figure><img id="overlay" alt="Failed-block overlay"><figcaption>Red: failed 8×8 blocks. Not an exact pixel segmentation.</figcaption></figure>
<figure><img id="truth" alt="Measured changed-pixel mask"><figcaption>White: actual changed RGB pixels. Used only for evaluation, never supplied to the verifier.</figcaption></figure></div>
<h2>3. Inspect measured evidence</h2><dl id="metrics"></dl></section>
<section><h2>All scenarios, including limitations</h2><div class="scroll"><table><thead><tr><th>Scenario</th><th>Verdict</th><th>Changed pixels</th><th>Failed blocks</th></tr></thead><tbody id="all"></tbody></table></div>
<p class="note">The verifier receives only the received RGB image, key and expected image/version identifier. It does not know the attack name or the original image. Timings describe this one local execution.</p></section>
<section><h2>What this does not establish</h2><ul>''' + notes + '''</ul>
<p>The main watermark-verification model and attention-enhanced model remain experiments. Their localisation quality is not established; neither is used to generate these overlays.</p>
<a href="report.json" download>Download the numerical receipt</a></section>
<script id="evidence" type="application/json">''' + packet + '''</script>
<script>
const data=JSON.parse(document.getElementById('evidence').textContent),r=data.report;
const select=document.getElementById('scenario');
r.cases.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=c.label;select.append(o);
const tr=document.createElement('tr');[c.label,c.verdict,c.changed_pixels,c.failed_blocks+'/'+c.total_blocks].forEach(t=>{const td=document.createElement('td');td.textContent=t;tr.append(td)});document.getElementById('all').append(tr)});
const e=r.embedding;document.getElementById('fidelity').textContent='Embedding PSNR: '+(e.psnr_db===null?'infinite (no pixel difference)':e.psnr_db.toFixed(2)+' dB')+'; maximum channel change: '+e.maximum_absolute_channel_change+'. This measures numerical distortion, not clinical safety.';
function show(){const i=Number(select.value),c=r.cases[i],v=data.views[i];['received','overlay','truth'].forEach(k=>document.getElementById(k).src=v[k]);
document.getElementById('verdict').textContent=c.verdict;
document.getElementById('warning').textContent=c.scenario_type==='context'?'No image content changed. Verification failed because the key or expected identifier is wrong. Failure alone cannot identify the cause.':c.id==='jpeg75'?'JPEG recompression changes pixels and fails the lossless integrity contract. This is not proof of malicious editing.':'Verification authenticates the received protected pixels; it does not certify their medical meaning.';
const m=document.getElementById('metrics');m.replaceChildren();const pairs=[['Changed RGB pixels',c.changed_pixels],['Failed / total blocks',c.failed_blocks+' / '+c.total_blocks],['Verification time (single execution)',c.verification_ms.toFixed(2)+' ms']];
if(c.localisation){let l=c.localisation;const fmt=x=>x===null?'N/A — empty union':x.toFixed(4);pairs.push(['Failed-block IoU vs changed blocks',fmt(l.block_iou)],['Expanded-block pixel IoU',fmt(l.expanded_block_pixel_iou)],['Block TP / FP / FN / TN',Object.values(l.block_confusion).join(' / ')])}else pairs.push(['Localisation comparison','N/A — verification context mismatch']);
pairs.forEach(([k,v])=>{const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=k;dd.textContent=v;m.append(dt,dd)})}
select.onchange=show;show();
</script></html>'''

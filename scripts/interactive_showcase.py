"""Local interactive RGB integrity workspace. Ephemeral keys/pixels, no disk uploads."""
import argparse
import base64
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import sys
import threading
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
from src import authentication as A
from src.showcase import png_bytes

MAX_BODY=8*1024**2
SESSIONS={}
LOCK=threading.Lock()
TTL=3600


def decode(text):
    raw=base64.b64decode(text,validate=True)
    with Image.open(io.BytesIO(raw)) as im:
        if im.format!='PNG' or im.mode!='RGB' or getattr(im,'n_frames',1)!=1:
            raise ValueError('single-frame RGB PNG required')
        if min(im.size)<32 or any(n%8 for n in im.size) or im.width*im.height>512**2:
            raise ValueError('dimensions must be multiples of8, >=32 and <=262144 pixels')
        return np.array(im)


def encode(rgb):return base64.b64encode(png_bytes(rgb)).decode()


def protect(rgb):
    key=secrets.token_bytes(32);ident=secrets.randbits(64)
    start=time.perf_counter();protected=A.embed(rgb,key,ident)
    elapsed=(time.perf_counter()-start)*1000
    token=secrets.token_urlsafe(32);now=time.monotonic()
    with LOCK:
        for k in list(SESSIONS):
            if now-SESSIONS[k]['created']>TTL:del SESSIONS[k]
        if len(SESSIONS)>=32:raise ValueError('workspace full; retry after sessions expire')
        SESSIONS[token]={'key':key,'ident':ident,'shape':rgb.shape,'created':now}
    mse=float(np.mean((protected.astype(float)-rgb.astype(float))**2))
    return {'session':token,'png':encode(protected),'embedding_ms':elapsed,'mse':mse,
            'psnr_db':float(10*np.log10(255**2/mse)) if mse else None}


def verify(rgb,token):
    with LOCK:s=SESSIONS.get(token)
    if s is None or time.monotonic()-s['created']>TTL:
        raise ValueError('session missing/expired; protect again. No authenticity verdict available.')
    if rgb.shape!=s['shape']:raise ValueError('geometry differs; no verification map available')
    start=time.perf_counter();failed=A.failures(rgb,s['key'],s['ident'])
    elapsed=(time.perf_counter()-start)*1000
    return {'verdict':'FAILED_INTEGRITY' if failed.any() else 'VERIFIED',
            'failed_blocks':int(failed.sum()),'total_blocks':int(failed.size),
            'map':failed.astype(int).tolist(),'verification_ms':elapsed}


class Handler(BaseHTTPRequestHandler):
    def reply(self,status,body,kind='application/json'):
        self.send_response(status);self.send_header('Content-Type',kind)
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(body)

    def do_GET(self):
        if self.path in ('/','/index.html'):
            return self.reply(200,(ROOT/'src/interactive_showcase.html').read_bytes(),'text/html; charset=utf-8')
        self.reply(404,b'{}')

    def do_POST(self):
        try:
            # Custom header forces browser cross-origin requests through preflight.
            if self.headers.get('X-Integrity-Workspace')!='1':raise ValueError('workspace header required')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=MAX_BODY:raise ValueError('request too large or empty')
            data=json.loads(self.rfile.read(length));rgb=decode(data['png'])
            if self.path=='/api/protect':result=protect(rgb)
            elif self.path=='/api/verify':result=verify(rgb,data['session'])
            else:return self.reply(404,b'{}')
            self.reply(200,json.dumps(result,allow_nan=False).encode())
        except (ValueError,KeyError,TypeError,OSError) as e:
            self.reply(400,json.dumps({'error':str(e)}).encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--port',type=int,default=8081);args=p.parse_args()
    print('Interactive workspace: ephemeral one-hour sessions, no medical validation.',flush=True)
    ThreadingHTTPServer(('0.0.0.0',args.port),Handler).serve_forever()


from __future__ import annotations
import json, os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from rhenium_engine.orchestrator import compose_work, export_composition
from rhenium_engine.registry import list_engines, layer_map

ROOT=Path(__file__).resolve().parents[1]
EXPORTS=ROOT/'exports'
STATIC=ROOT/'static'
PORT=int(os.environ.get('RHENIUM_PORT','8777'))
LAST=None

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path == '/' or path.startswith('/static'):
            rel=path.replace('/static/','') if path.startswith('/static/') else 'index.html'
            return str(STATIC/rel)
        return str(ROOT/path.lstrip('/'))
    def _json(self, payload, code=200):
        data=json.dumps(payload,indent=2,default=str).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path == '/api/health':
            return self._json({'ok':True,'engine':'Rhenium','port':PORT})
        if parsed.path == '/api/engines':
            return self._json({'engines':list_engines(),'layers':layer_map()})
        if parsed.path == '/api/last':
            return self._json(LAST or {'status':'empty'})
        return super().do_GET()
    def do_POST(self):
        global LAST
        n=int(self.headers.get('Content-Length','0'))
        body=self.rfile.read(n).decode('utf-8',errors='replace')
        try: payload=json.loads(body) if body else {}
        except Exception: payload={'text':body}
        if self.path == '/api/compose':
            text=payload.get('text','')
            LAST=compose_work(text)
            paths=export_composition(LAST, EXPORTS/'last')
            LAST['export_paths']=paths
            return self._json(LAST)
        return self._json({'error':'not found'},404)

def main():
    print(f'Rhenium Engine serving http://127.0.0.1:{PORT}/')
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()

if __name__ == '__main__': main()

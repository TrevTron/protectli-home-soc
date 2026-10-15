"""Owned loopback, read-only synthetic workbench. No inference endpoints."""
import http.server
import json
from pathlib import Path
from workbench import HERE
from display import render_page


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') == '127.0.0.1:8771' and self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        if self.headers.get('Host') != '127.0.0.1:8771' or self.path != '/':
            self.send_error(404)
            return
        results = []
        for path in sorted(HERE.glob('development-*/[0-9]*-*/outcome.json')):
            row = json.loads(path.read_text())
            proposal = json.loads((path.parent.parent / 'requests' / (row['name'] + '.json')).read_text())
            row['actual_request'] = proposal['request']
            row['skill_hashes'] = proposal['skill_hashes']
            results.append(row)
        for path in sorted((HERE / 'ling-isolated').glob('soc-development-*/[0-9]*-*/outcome.json')):
            results.append(json.loads(path.read_text()))
        body = render_page(results).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', 8771), Handler).serve_forever()

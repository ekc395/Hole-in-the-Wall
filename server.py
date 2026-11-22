"""Local API: run python3 server.py, then npm run dev in another terminal."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from server.search import SearchService, tokenize


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, payload, status=200):
            body = json.dumps(payload, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == '/api/health':
                return self.send_json({'status': 'ok', **service.status})
            if url.path != '/api/search':
                return self.send_json({'error': 'Not found'}, 404)
            params = parse_qs(url.query)
            try:
                limit = int(params.get('limit', ['20'])[0])
                if not 1 <= limit <= 100:
                    raise ValueError
            except ValueError:
                return self.send_json({'error': 'limit must be an integer between 1 and 100'}, 400)
            try:
                lat, lon, radius = (float(params[k][0]) if k in params else None for k in ('lat', 'lon', 'radius'))
                if (lat is None) != (lon is None) or (radius is not None and lat is None):
                    raise ValueError
                if lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError
                if radius is not None and not radius > 0:
                    raise ValueError
            except ValueError:
                return self.send_json({'error': 'lat and lon must be given together; radius (miles, > 0) requires them'}, 400)
            query = params.get('q', [''])[0]
            city = params.get('city', [None])[0]
            results = service.search(query, city, limit, lat=lat, lon=lon, radius=radius)
            expansions = service.expand_query(tokenize(query))
            self.send_json({'query': query, 'city': city, 'total': len(results), 'expansions': expansions,
                            'results': results, 'data_status': service.status})
    return Handler


if __name__ == '__main__':
    service = SearchService()
    print(f"API ready at http://127.0.0.1:8000 ({service.status})", flush=True)
    try:
        ThreadingHTTPServer(('127.0.0.1', 8000), make_handler(service)).serve_forever()
    except KeyboardInterrupt:
        pass

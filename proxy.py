# Kleiner ADS-B-Vermittler fuer den Raspberry Pi.
# Holt die Daten mit der Wohnanschluss-Adresse des Pi - die akzeptieren
# die Netze, im Gegensatz zu Rechenzentren - und hebt jede Antwort
# 12 Sekunden auf, damit das Limit von einer Anfrage pro Sekunde haelt.
import json, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT  = 8081
CACHE = {}
TTL   = 12
UA    = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
         "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")

def sources(la, lo, di):
    return [
        ("api.adsb.lol",       f"https://api.adsb.lol/v2/point/{la}/{lo}/{di}"),
        ("api.airplanes.live", f"https://api.airplanes.live/v2/point/{la}/{lo}/{di}"),
        ("opendata.adsb.fi",   f"https://opendata.adsb.fi/api/v3/lat/{la}/lon/{lo}/dist/{di}"),
    ]

def fetch(la, lo, di):
    errs = []
    for name, url in sources(la, lo, di):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            raw = urllib.request.urlopen(req, timeout=8).read()
            data = json.loads(raw)
            ac = data.get("ac") or data.get("aircraft")
            if isinstance(ac, list):
                return {"ac": ac, "src": name}
        except Exception as e:
            errs.append(f"{name} {type(e).__name__}")
    return {"ac": [], "src": "keine", "error": " · ".join(errs)}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q  = parse_qs(urlparse(self.path).query)
        la = f'{float(q.get("lat", ["48.22868"])[0]):.3f}'
        lo = f'{float(q.get("lon", ["16.39602"])[0]):.3f}'
        di = f'{float(q.get("dist", ["8.1"])[0]):.1f}'

        key, now = (la, lo, di), time.time()
        if key in CACHE and now - CACHE[key][0] < TTL:
            body = CACHE[key][1]
        else:
            body = json.dumps(fetch(la, lo, di)).encode()
            CACHE[key] = (now, body)

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

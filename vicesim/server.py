"""Zero-dependency HTTP server: ticks the world in a thread and serves the dashboard + JSON API."""
import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .engine import SCENARIOS, SEVERITY, World

DASH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard"))


class Sim:
    def __init__(self):
        self.world, self.lock, self.tps, self.paused = World(), threading.Lock(), 8, False

    def run(self):
        while True:
            if not self.paused:
                with self.lock:
                    self.world.step()
            time.sleep(1 / self.tps)


def make_handler(sim):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, body, ctype="application/json", code=200):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            p = urlparse(self.path).path
            with sim.lock:
                if p == "/api/state":
                    return self.send({**sim.world.snapshot(), "paused": sim.paused, "tps": sim.tps})
                if p == "/api/map":
                    c = sim.world.city
                    rows = ["".join("RBP"[t] for t in row) for row in c.grid]
                    return self.send({"w": c.w, "h": c.h, "grid": rows,
                                      "places": [[q["kind"], *q["pos"]] for q in c.places],
                                      "scenarios": list(SCENARIOS)})
            if p in ("/", "/index.html"):
                with open(os.path.join(DASH, "index.html"), "rb") as f:
                    return self.send(f.read(), "text/html; charset=utf-8")
            self.send({"error": "not found"}, code=404)

        def do_POST(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            with sim.lock:
                if u.path == "/api/crime":  # the outlaw commits a crime where it stands
                    kind = q.get("kind", ["robbery"])[0]
                    if kind in SEVERITY and sim.world.outlaw.state != "jailed":
                        sim.world.commit_crime(kind, sim.world.outlaw.pos)
                elif u.path == "/api/scenario":
                    sim.world = World(q.get("name", ["default"])[0])
                elif u.path == "/api/speed":
                    sim.tps = max(1, min(60, int(q.get("v", ["8"])[0])))
                elif u.path == "/api/pause":
                    sim.paused = not sim.paused
                else:
                    return self.send({"error": "not found"}, code=404)
            self.send({"ok": True})

    return H


def main():
    ap = argparse.ArgumentParser(description="VICE-SIM living-city simulation")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    sim = Sim()
    threading.Thread(target=sim.run, daemon=True).start()
    print(f"VICE-SIM running at http://{a.host}:{a.port}  (Ctrl+C to stop)")
    ThreadingHTTPServer((a.host, a.port), make_handler(sim)).serve_forever()

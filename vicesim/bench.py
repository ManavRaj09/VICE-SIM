"""Headless benchmark: python -m vicesim.bench"""
import time

from .engine import World

for name in ("default", "rush_hour", "panic"):
    w, n = World(name), 1000
    t = time.perf_counter()
    for _ in range(n):
        w.step()
    dt = time.perf_counter() - t
    print(f"{name:11s} {len(w.civs)} civs, {len(w.cars)} cars, {len(w.cops)} cops: {n / dt:7.0f} ticks/sec")

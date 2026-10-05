"""Procedural city: a grid of roads, parks and buildings with doors on the road network."""
import random

ROAD, BLDG, PARK = 0, 1, 2


class City:
    def __init__(self, w=49, h=33, seed=7):
        self.w, self.h = w, h
        r = random.Random(seed)
        self.grid = [[BLDG] * w for _ in range(h)]
        self.kind = {}
        self.places = []
        for y in range(h):
            for x in range(w):
                if x % 8 == 0 or y % 8 == 0:
                    self.grid[y][x] = ROAD
        for by in range(0, h - 1, 8):
            for bx in range(0, w - 1, 8):
                if r.random() < 0.18:
                    for y in range(by + 1, by + 8):
                        for x in range(bx + 1, bx + 8):
                            self.grid[y][x] = PARK
        for y in range(h):
            for x in range(w):
                if self.grid[y][x] != BLDG:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if self.is_road(nx, ny) and r.random() < 0.35:
                        k = r.choices(["home", "shop", "work"], [6, 2, 3])[0]
                        self.places.append({"kind": k, "pos": (x, y), "door": (nx, ny)})
                        break
        cx, cy = w // 2, h // 2
        station = min(self.places, key=lambda p: abs(p["pos"][0] - cx) + abs(p["pos"][1] - cy))
        station["kind"] = "police"
        for p in self.places:
            self.kind[p["pos"]] = p["kind"]

    def is_road(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h and self.grid[y][x] == ROAD

    def walkable(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h and self.grid[y][x] != BLDG

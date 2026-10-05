"""Simulation core: civilians with needs, police with a wanted-level state machine,
traffic lights, rumours and a crime-driven micro-economy.  1 tick = 10 sim-minutes."""
import random

from .city import City, PARK
from .pathfinding import astar

SCENARIOS = {
    "default": dict(civ=60, cop=5, cars=18, crime=0.02, start=7),
    "rush_hour": dict(civ=90, cop=4, cars=45, crime=0.01, start=8),
    "crime_wave": dict(civ=60, cop=8, cars=18, crime=0.08, start=21),
    "panic": dict(civ=100, cop=6, cars=25, crime=0.15, start=12),
}
SEVERITY = {"theft": 1, "assault": 2, "robbery": 3, "shooting": 4}
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Agent:
    def __init__(self, i, role, pos, r):
        self.id, self.role, self.pos = i, role, pos
        self.path, self.state, self.target = [], "idle", None
        self.timer, self.panic, self.threat, self.rumor = 0, 0, None, None
        self.hunger, self.energy = r.uniform(0, 40), 80
        self.money = r.randint(10, 60)
        self.home = self.work = pos


class Car:
    def __init__(self, pos, d):
        self.pos, self.d = pos, d


class World:
    def __init__(self, scenario="default", seed=7):
        self.name = scenario if scenario in SCENARIOS else "default"
        self.cfg = SCENARIOS[self.name]
        self.r = random.Random(seed)
        self.city = City(seed=seed)
        self.tick = self.cfg["start"] * 6
        self.wanted = self.unseen = 0
        self.saw = False
        self.last_known = (0, 0)
        self.events, self.heat, self.traffic = [], {}, {}
        self.stats = {"crimes": 0, "busts": 0, "reports": 0, "revenue": 0}
        c, P, g = self.cfg, self.city.places, self.city.grid
        self.roads = [(x, y) for y in range(self.city.h) for x in range(self.city.w) if self.city.is_road(x, y)]
        door = lambda k: [p["door"] for p in P if p["kind"] == k] or self.roads
        homes, self.shops, works = door("home"), door("shop"), door("work")
        self.station = door("police")[0]
        self.parks = [(x, y) for y in range(self.city.h) for x in range(self.city.w) if g[y][x] == PARK] or self.roads
        self.civs = []
        for i in range(c["civ"]):
            a = Agent(i, "civ", self.r.choice(homes), self.r)
            a.home, a.work = a.pos, self.r.choice(works)
            self.civs.append(a)
        self.cops = []
        for i in range(c["cop"]):
            a = Agent(1000 + i, "cop", self.station, self.r)
            a.state = "patrol"
            self.cops.append(a)
        self.outlaw = Agent(2000, "outlaw", self.r.choice(self.roads), self.r)
        self.cars = []
        for _ in range(c["cars"]):
            while True:
                x, y = self.r.choice(self.roads)
                if (x % 8 == 0) != (y % 8 == 0):
                    break
            d = self.r.choice([(1, 0), (-1, 0)]) if y % 8 == 0 else self.r.choice([(0, 1), (0, -1)])
            self.cars.append(Car((x, y), d))

    # ---------- helpers ----------
    def log(self, msg):
        self.events.append(f"{int(self.tick / 6) % 24:02d}:{(self.tick % 6) * 10:02d}  {msg}")
        self.events = self.events[-30:]

    def near(self, center, rad):
        pool = [p for p in self.roads if dist(p, center) <= rad]
        return self.r.choice(pool or self.roads)

    def cell(self, pos):
        return (pos[0] // 4, pos[1] // 4)

    # ---------- crime & police ----------
    def commit_crime(self, kind, pos):
        sev = SEVERITY[kind]
        self.stats["crimes"] += 1
        self.heat[self.cell(pos)] = self.heat.get(self.cell(pos), 0) + sev * 3
        self.log(f"{kind} at {pos}")
        witnesses = [a for a in self.civs if dist(a.pos, pos) <= 6]
        for a in witnesses:
            a.panic, a.threat, a.path = 8 + self.r.randint(0, 4), pos, []
            a.rumor = {"kind": kind, "at": pos, "t": self.tick}
        if sev >= 3 or (witnesses and self.r.random() < 0.8):
            self.stats["reports"] += 1
            self.wanted = min(5, self.wanted + sev)
            self.unseen, self.last_known = 0, pos
            self.log(f"Witness report - wanted level {self.wanted}")
            for c in sorted(self.cops, key=lambda c: dist(c.pos, pos))[: self.wanted + 1]:
                c.state, c.path = "respond", astar(self.city, c.pos, pos)

    def bust(self):
        o = self.outlaw
        self.stats["busts"] += 1
        self.log(f"BUSTED - outlaw arrested at {o.pos}")
        o.state, o.timer, o.path, o.pos = "jailed", 25, [], self.station
        self.wanted = self.unseen = 0
        for c in self.cops:
            c.state, c.path = "return", astar(self.city, c.pos, self.station)

    def outlaw_ai(self):
        o = self.outlaw
        if o.state == "jailed":
            o.timer -= 1
            if o.timer <= 0:
                o.state, o.pos = "roam", self.r.choice(self.roads)
                self.log("Outlaw is back on the streets")
            return
        if self.wanted < 3 and self.r.random() < self.cfg["crime"] and any(dist(a.pos, o.pos) <= 4 for a in self.civs):
            self.commit_crime(self.r.choice(list(SEVERITY)), o.pos)
        if self.wanted > 0:
            o.state = "flee"
            if not o.path or self.tick % 4 == 0:  # run to the road tile farthest from all cops
                cands = self.r.sample(self.roads, 8)
                tgt = max(cands, key=lambda p: min((dist(p, c.pos) for c in self.cops), default=0))
                o.path = astar(self.city, o.pos, tgt)
        elif not o.path:
            o.state = "roam"
            o.path = astar(self.city, o.pos, self.r.choice(self.civs).pos)
        if o.path:
            o.pos = o.path.pop(0)

    def cop_ai(self, c):
        o = self.outlaw
        seen = self.wanted > 0 and o.state != "jailed" and dist(c.pos, o.pos) <= 8
        if seen:  # line of sight -> chase
            self.saw, self.unseen, self.last_known, c.state = True, 0, o.pos, "chase"
            if not c.path or self.tick % 3 == 0:
                c.path = astar(self.city, c.pos, o.pos)
        elif c.state == "chase":  # lost them -> search last known position
            c.state, c.timer = "search", 20
            c.path = astar(self.city, c.pos, self.last_known)
        for _ in range(2 if self.wanted >= 3 and c.state in ("chase", "respond") else 1):  # backup = faster
            if c.path:
                c.pos = c.path.pop(0)
        if self.wanted > 0 and o.state != "jailed" and dist(c.pos, o.pos) <= 1:
            self.bust()
            return
        if c.path:
            return
        if c.state == "respond":
            c.state, c.timer = "search", 15
        if c.state == "search":
            c.timer -= 1
            if c.timer <= 0 or self.wanted == 0:
                c.state, c.path = "return", astar(self.city, c.pos, self.station)
            else:
                c.path = astar(self.city, c.pos, self.near(self.last_known, 6))
        elif c.state in ("return", "idle"):
            c.state = "patrol"
        elif c.state == "patrol":
            c.path = astar(self.city, c.pos, self.near(c.pos, 10))

    # ---------- civilians ----------
    def mood(self, a):
        h = self.heat.get(self.cell(a.pos), 0)
        return max(0, 100 - a.hunger * 0.3 - (100 - a.energy) * 0.2 - a.panic * 3 - min(30, h * 2))

    def civ_ai(self, a, hour):
        a.hunger, a.energy = min(100, a.hunger + 0.5), max(0, a.energy - 0.25)
        if a.rumor and self.tick - a.rumor["t"] > 60:
            a.rumor = None
        if a.panic > 0:  # flee from the threat
            a.panic -= 1
            a.state = "panic"
            opts = [n for n in ((a.pos[0] + dx, a.pos[1] + dy) for dx, dy in DIRS) if self.city.walkable(*n)]
            if opts:
                a.pos = max(opts, key=lambda n: dist(n, a.threat) + self.r.random())
            return
        if a.path:
            a.pos = a.path.pop(0)
            return
        here = a.pos == a.target
        if a.state == "shop" and here and a.money >= 5:
            if self.r.random() >= min(0.6, self.heat.get(self.cell(a.pos), 0) / 10):  # crime scares customers away
                a.money, a.hunger = a.money - 5, 0
                self.stats["revenue"] += 5
        elif a.state == "work" and here:
            a.money += 2
        elif a.state == "home" and here:
            a.energy = min(100, a.energy + 3)
        if a.hunger > 70 and a.money >= 5:
            goal = ("shop", self.r.choice(self.shops))
        elif a.state == "work" and here and 9 <= hour < 17:
            return
        elif a.state == "home" and here and (hour >= 22 or hour < 6):
            return
        elif 9 <= hour < 17:
            goal = ("work", a.work)
        elif hour >= 22 or hour < 6:
            goal = ("home", a.home)
        else:
            goal = self.r.choice([("park", self.r.choice(self.parks)), ("shop", self.r.choice(self.shops)), ("home", a.home)])
        a.state, a.target = goal
        a.path = astar(self.city, a.pos, a.target)

    def spread_rumors(self):
        for a in [a for a in self.civs if a.rumor]:
            for b in self.civs:
                if not b.rumor and dist(a.pos, b.pos) <= 2 and self.r.random() < 0.3:
                    b.rumor = a.rumor

    # ---------- traffic ----------
    def move_cars(self):
        occ = {c.pos: c.d for c in self.cars}
        phase = (self.tick // 6) % 2  # 0: east-west green, 1: north-south green
        for c in self.cars:
            x, y = c.pos
            nx, ny = x + c.d[0], y + c.d[1]
            if not self.city.is_road(nx, ny):
                c.d = self.r.choice([d for d in DIRS if self.city.is_road(x + d[0], y + d[1])])
                continue
            at_junction = nx % 8 == 0 and ny % 8 == 0
            if at_junction and (phase == 0) != (c.d[0] != 0):  # red light
                continue
            if occ.get((nx, ny)) == c.d:  # car ahead
                continue
            occ.pop(c.pos, None)
            c.pos = (nx, ny)
            occ[c.pos] = c.d
            self.traffic[c.pos] = self.traffic.get(c.pos, 0) + 1
            if at_junction:
                c.d = self.r.choice([d for d in DIRS if d != (-c.d[0], -c.d[1]) and self.city.is_road(nx + d[0], ny + d[1])])

    # ---------- main loop ----------
    def step(self):
        self.tick += 1
        self.saw = False
        for d, k_decay in ((self.heat, 0.985), (self.traffic, 0.96)):
            for k in list(d):
                d[k] *= k_decay
                if d[k] < 0.05:
                    del d[k]
        hour = (self.tick / 6) % 24
        self.move_cars()
        for a in self.civs:
            self.civ_ai(a, hour)
        self.spread_rumors()
        self.outlaw_ai()
        for c in self.cops:
            self.cop_ai(c)
        if self.wanted > 0 and not self.saw:
            self.unseen += 1
            if self.unseen >= 25:
                self.wanted, self.unseen = self.wanted - 1, 0
                self.log(f"Wanted level dropped to {self.wanted}")

    def snapshot(self):
        o = self.outlaw
        agents = [[a.id, "panic" if a.panic else "civ", *a.pos] for a in self.civs]
        agents += [[c.id, "cop", *c.pos] for c in self.cops] + [[o.id, "outlaw", *o.pos]]
        n = len(self.civs)
        return {
            "tick": self.tick, "time": f"{int(self.tick / 6) % 24:02d}:{(self.tick % 6) * 10:02d}",
            "scenario": self.name, "phase": (self.tick // 6) % 2, "wanted": self.wanted,
            "agents": agents, "cars": [list(c.pos) for c in self.cars],
            "heat": [[k[0], k[1], round(v, 1)] for k, v in self.heat.items()],
            "traffic": [[k[0], k[1], round(v, 1)] for k, v in self.traffic.items()],
            "events": self.events[-12:][::-1],
            "stats": {**self.stats, "mood": round(sum(self.mood(a) for a in self.civs) / n),
                      "rumor_pct": round(100 * sum(1 for a in self.civs if a.rumor) / n),
                      "outlaw": o.state, "cops_busy": sum(1 for c in self.cops if c.state != "patrol")},
        }

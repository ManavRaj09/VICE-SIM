import json
import unittest

from vicesim.city import City
from vicesim.engine import SCENARIOS, World
from vicesim.pathfinding import astar


class SimTests(unittest.TestCase):
    def test_astar_path_is_connected(self):
        c = City()
        p = astar(c, (0, 0), (48, 32))
        self.assertEqual(p[-1], (48, 32))
        prev = (0, 0)
        for t in p:
            self.assertEqual(abs(t[0] - prev[0]) + abs(t[1] - prev[1]), 1)
            self.assertTrue(c.walkable(*t))
            prev = t

    def test_deterministic_with_seed(self):
        a, b = World(seed=3), World(seed=3)
        for _ in range(150):
            a.step()
            b.step()
        self.assertEqual(json.dumps(a.snapshot()), json.dumps(b.snapshot()))

    def test_crime_raises_wanted_and_dispatches_cops(self):
        w = World()
        w.commit_crime("shooting", w.outlaw.pos)
        self.assertGreaterEqual(w.wanted, 4)
        self.assertTrue(any(c.state == "respond" for c in w.cops))

    def test_agents_never_enter_buildings_and_cars_stay_on_roads(self):
        for name in SCENARIOS:
            w = World(name)
            for _ in range(300):
                w.step()
            for a in w.civs + w.cops + [w.outlaw]:
                self.assertTrue(w.city.walkable(*a.pos), (name, a.id, a.pos))
            for car in w.cars:
                self.assertTrue(w.city.is_road(*car.pos))

    def test_wanted_level_decays_when_unseen(self):
        w = World()
        w.wanted = 2
        w.cops, w.outlaw.pos = [], (0, 0)  # nobody can see the outlaw
        w.civs = w.civs[:5]
        for _ in range(60):
            w.step()
        self.assertEqual(w.wanted, 0)


if __name__ == "__main__":
    unittest.main()

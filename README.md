# VICE-SIM

**A GTA-style living-city simulation where every NPC thinks, remembers and reacts, with a live neon dashboard.**

Open-world games feel alive because of the AI under the hood: pedestrians with routines, police that investigate, traffic that obeys lights. VICE-SIM rebuilds those ideas from scratch in plain Python with **zero dependencies**, so you can read, test and extend every system.

> Fan-inspired project. Not affiliated with or endorsed by Rockstar Games. All code and visuals are original.

## Run it in 60 seconds

```bash
git clone https://github.com/<your-username>/vice-sim.git
cd vice-sim
python -m vicesim            # then open http://127.0.0.1:8000
```

Or with Docker: `docker build -t vice-sim . && docker run -p 8000:8000 vice-sim`

## What is simulated

| System | How it works |
|---|---|
| **Civilians** | Hunger, energy, money and mood. Daily routine: work 9-17, shop when hungry, sleep at night, wander parks. |
| **Pathfinding** | A\* over a procedurally generated road/park grid. |
| **Crime and witnesses** | Crimes (theft to shooting) have severity. Nearby civilians panic and flee; most report it. |
| **Police AI** | State machine: `patrol -> respond -> chase -> search -> return`. Wanted level 3+ calls backup (officers move faster). |
| **Wanted level** | Rises with reported crime, decays after 25 ticks without line of sight. |
| **Outlaw** | An autonomous criminal that picks targets in crowds and flees to the spot farthest from police. |
| **Traffic** | Cars follow lanes, obey alternating traffic lights, queue behind each other. |
| **Rumours** | Witnesses spread news to nearby civilians, and it expires after about 10 sim-hours. |
| **Economy** | Crime creates heat zones. Heat lowers mood and scares customers away, so shop revenue drops. |

## Architecture

```
dashboard (canvas) --polls--> HTTP API (server.py) --locks--> World.step() (engine.py)
                                                               |- city.py         (map generation)
                                                               |- pathfinding.py  (A*)
                                                               '- agents: civilians / police / outlaw / cars
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/state` | Full world snapshot (agents, cars, heat, stats, events) |
| GET | `/api/map` | Static city layout |
| POST | `/api/crime?kind=theft\|assault\|robbery\|shooting` | Outlaw commits a crime now |
| POST | `/api/scenario?name=default\|rush_hour\|crime_wave\|panic` | Reset with a scenario |
| POST | `/api/speed?v=1-60` | Ticks per second |
| POST | `/api/pause` | Toggle pause |

## Test and benchmark

```bash
python -m unittest discover -s tests -t .
python -m vicesim.bench        # headless ticks/sec
```

The simulation is deterministic for a given seed, which is covered by a test.

## Roadmap

- [ ] Replace the hand-written rules with a learned policy for the outlaw (reinforcement learning)
- [ ] Optional LLM layer for in-character NPC dialogue and rumours
- [ ] Day/night and weather effects on crowds
- [ ] Gangs and territory control
- [ ] Record and replay timeline in the dashboard
- [ ] FastAPI + WebSocket streaming for 5,000+ agents

## License

MIT

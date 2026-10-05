"""A* on the 4-connected walkable grid (roads + parks)."""
import heapq


def astar(city, start, goal):
    """Return the list of tiles from start (exclusive) to goal (inclusive), or [] if none."""
    if start == goal:
        return []
    openq = [(0, 0, start)]
    came, g = {start: None}, {start: 0}
    while openq:
        _, gc, cur = heapq.heappop(openq)
        if cur == goal:
            break
        if gc > g[cur]:
            continue
        x, y = cur
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if city.walkable(*n):
                ng = gc + 1
                if ng < g.get(n, 1e9):
                    g[n], came[n] = ng, cur
                    f = ng + abs(n[0] - goal[0]) + abs(n[1] - goal[1])
                    heapq.heappush(openq, (f, ng, n))
    if goal not in came:
        return []
    path, c = [], goal
    while c != start:
        path.append(c)
        c = came[c]
    return path[::-1]

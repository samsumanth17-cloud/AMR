"""
Global Path Planning Engine for Industrial AMR
Implements Cost-Aware A* with Diagonal Transitions, Obstacle Weighting, and Path Smoothing.
"""

import heapq
import math

class AStarPlanner:
    def __init__(self, costmap):
        self.costmap = costmap

    def heuristic(self, a, b):
        # Octile distance heuristic for 8-connected grid
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)

    def plan(self, start_x, start_y, goal_x, goal_y, congestion_zones=None):
        """
        Plans optimal path from (start_x, start_y) to (goal_x, goal_y) in world coordinates.
        congestion_zones: list of circular zones [x, y, radius, penalty] to temporarily avoid.
        """
        start_grid = self.costmap.world_to_grid(start_x, start_y)
        goal_grid = self.costmap.world_to_grid(goal_x, goal_y)

        # Ensure goal is not lethal; if lethal, find nearest free cell
        if self.costmap.master_costmap[goal_grid[1], goal_grid[0]] >= 254:
            goal_grid = self._find_nearest_free_cell(goal_grid)
            if not goal_grid:
                return []

        # 8-connected motion primitives: (dx, dy, base_cost)
        motions = [
            (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (-1, -1, 1.414)
        ]

        open_set = []
        heapq.heappush(open_set, (0.0, start_grid))

        came_from = {}
        g_score = {start_grid: 0.0}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal_grid:
                raw_path = self._reconstruct_path(came_from, current)
                world_path = [list(self.costmap.grid_to_world(gx, gy)) for gx, gy in raw_path]
                return self._smooth_path(world_path)

            for dx, dy, move_cost in motions:
                neighbor = (current[0] + dx, current[1] + dy)

                # Boundary check
                if not (0 <= neighbor[0] < self.costmap.nx and 0 <= neighbor[1] < self.costmap.ny):
                    continue

                cell_cost = int(self.costmap.master_costmap[neighbor[1], neighbor[0]])
                if cell_cost >= 250: # Lethal obstacle or very tight space
                    continue

                # Inflation penalty + base step cost
                cost_penalty = (cell_cost / 50.0) ** 2

                # Congestion zone penalties
                if congestion_zones:
                    wx, wy = self.costmap.grid_to_world(neighbor[0], neighbor[1])
                    for cz in congestion_zones:
                        dist_cz = math.hypot(wx - cz['x'], wy - cz['y'])
                        if dist_cz < cz.get('radius', 3.0):
                            cost_penalty += cz.get('penalty', 10.0)

                tentative_g = g_score[current] + move_cost + cost_penalty

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + 1.2 * self.heuristic(neighbor, goal_grid)
                    heapq.heappush(open_set, (f_score, neighbor))

        # No path found
        return []

    def _find_nearest_free_cell(self, target_grid, search_radius=6):
        """Spiral outwards to find nearest walkable cell if destination is blocked."""
        gx, gy = target_grid
        for r in range(1, search_radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < self.costmap.nx and 0 <= ny < self.costmap.ny:
                        if self.costmap.master_costmap[ny, nx] < 180:
                            return (nx, ny)
        return None

    def _reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def _smooth_path(self, world_path):
        """
        String-pulling / line-of-sight shortcutting to eliminate jagged grid stepping.
        """
        if len(world_path) <= 2:
            return world_path

        smoothed = [world_path[0]]
        i = 0
        while i < len(world_path) - 1:
            furthest_visible = i + 1
            for j in range(i + 2, min(i + 12, len(world_path))):
                if self._line_of_sight(world_path[i], world_path[j]):
                    furthest_visible = j
            smoothed.append(world_path[furthest_visible])
            i = furthest_visible

        return smoothed

    def _line_of_sight(self, p1, p2):
        """Check if straight line between p1 and p2 is obstacle-free."""
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        steps = max(2, int(dist / (self.costmap.resolution * 0.5)))
        for s in range(1, steps):
            t = s / float(steps)
            x = p1[0] + t * (p2[0] - p1[0])
            y = p1[1] + t * (p2[1] - p1[1])
            if self.costmap.get_cost(x, y) >= 200:
                return False
        return True

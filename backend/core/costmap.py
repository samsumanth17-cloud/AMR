"""
Costmap Management Engine for Industrial AMR
Implements 2D Occupancy Grid with Static Racks, Dynamic Obstacle Layer, and Inflation.
"""

import math
import numpy as np
from scipy.ndimage import distance_transform_edt

class Costmap2D:
    def __init__(self, width_m=50.0, height_m=30.0, resolution=0.5, inflation_radius=1.2):
        self.width_m = width_m
        self.height_m = height_m
        self.resolution = resolution
        self.inflation_radius = inflation_radius
        self.inflation_cells = int(math.ceil(inflation_radius / resolution))

        self.nx = int(math.ceil(width_m / resolution))
        self.ny = int(math.ceil(height_m / resolution))

        # 0 = Free, 1-253 = Inflated, 254 = Lethal Obstacle
        self.static_grid = np.zeros((self.ny, self.nx), dtype=np.uint8)
        self.dynamic_grid = np.zeros((self.ny, self.nx), dtype=np.uint8)
        self.master_costmap = np.zeros((self.ny, self.nx), dtype=np.uint8)

    def world_to_grid(self, x, y):
        gx = int(x / self.resolution)
        gy = int(y / self.resolution)
        return np.clip(gx, 0, self.nx - 1), np.clip(gy, 0, self.ny - 1)

    def grid_to_world(self, gx, gy):
        x = (gx + 0.5) * self.resolution
        y = (gy + 0.5) * self.resolution
        return float(x), float(y)

    def initialize_static_map(self, static_rectangles):
        """Mark static warehouse boundaries and rack structures as lethal obstacles (254)."""
        self.static_grid.fill(0)

        # Boundary perimeter walls
        self.static_grid[0, :] = 254
        self.static_grid[-1, :] = 254
        self.static_grid[:, 0] = 254
        self.static_grid[:, -1] = 254

        # Static racks
        for rect in static_rectangles:
            gx_min, gy_min = self.world_to_grid(rect['x'] - rect['w']/2.0, rect['y'] - rect['h']/2.0)
            gx_max, gy_max = self.world_to_grid(rect['x'] + rect['w']/2.0, rect['y'] + rect['h']/2.0)
            self.static_grid[gy_min:gy_max+1, gx_min:gx_max+1] = 254

        self.recompute_master_costmap()

    def update_dynamic_obstacles(self, dynamic_circles):
        """Clear dynamic layer and stamp dynamic obstacles (humans, forklifts, other AMRs)."""
        self.dynamic_grid.fill(0)
        for obs in dynamic_circles:
            cx, cy = self.world_to_grid(obs['x'], obs['y'])
            radius_cells = max(1, int(math.ceil(obs['radius'] / self.resolution)))
            for dy in range(-radius_cells, radius_cells + 1):
                for dx in range(-radius_cells, radius_cells + 1):
                    if dx*dx + dy*dy <= radius_cells*radius_cells:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < self.ny and 0 <= nx < self.nx:
                            self.dynamic_grid[ny, nx] = 254

        self.recompute_master_costmap()

    def recompute_master_costmap(self):
        """
        Merge static and dynamic lethal obstacles, then compute Euclidean Distance Transform
        to generate exponential inflation cost gradient.
        """
        lethal_mask = (self.static_grid == 254) | (self.dynamic_grid == 254)
        
        # Invert mask for distance transform (distance from obstacles)
        free_space = ~lethal_mask
        dist_in_cells = distance_transform_edt(free_space)
        dist_in_meters = dist_in_cells * self.resolution

        # Compute cost: lethal = 254, decay within inflation_radius
        cost = np.zeros_like(self.static_grid, dtype=np.uint8)
        cost[lethal_mask] = 254

        in_inflation = (dist_in_meters <= self.inflation_radius) & (~lethal_mask)
        # Exponential cost decay function: C = 253 * exp(-3.0 * (d / r_infl))
        decay_factor = np.exp(-3.0 * (dist_in_meters[in_inflation] / self.inflation_radius))
        cost[in_inflation] = np.clip(253 * decay_factor, 1, 253).astype(np.uint8)

        self.master_costmap = cost

    def get_cost(self, x, y):
        gx, gy = self.world_to_grid(x, y)
        return int(self.master_costmap[gy, gx])

    def is_lethal(self, x, y):
        return self.get_cost(x, y) >= 254

    def is_free(self, x, y, max_cost=150):
        return self.get_cost(x, y) < max_cost

    def to_downsampled_grid(self, factor=2):
        """Return downsampled grid for efficient web visualization."""
        sub = self.master_costmap[::factor, ::factor]
        return sub.tolist()

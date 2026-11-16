"""
Local Trajectory Planner for Industrial AMR
Implements Dynamic Window Approach (DWA) with Dynamic Obstacle Velocity Prediction.
"""

import math
import numpy as np

class DynamicWindowLocalPlanner:
    def __init__(self, kinematics, sim_time=1.8, time_step=0.2,
                 heading_weight=0.45, clearance_weight=0.35, velocity_weight=0.20):
        self.kin = kinematics
        self.sim_time = sim_time
        self.dt = time_step
        self.num_steps = int(sim_time / time_step)
        
        self.w_heading = heading_weight
        self.w_clearance = clearance_weight
        self.w_velocity = velocity_weight

    def compute_velocity_command(self, current_pose, current_vel, local_target, costmap, dynamic_obstacles):
        """
        Calculates optimal (v, omega) command using DWA.
        current_pose: [x, y, theta]
        current_vel: [v, w]
        local_target: [gx, gy] (waypoint ahead on global path)
        """
        cur_x, cur_y, cur_th = current_pose
        cur_v, cur_w = current_vel

        # 1. Compute Dynamic Window of achievable velocities
        v_min = max(-self.kin.max_v * 0.3, cur_v - self.kin.max_a_lin * self.dt)
        v_max = min(self.kin.max_v, cur_v + self.kin.max_a_lin * self.dt)
        w_min = max(-self.kin.max_w, cur_w - self.kin.max_a_ang * self.dt)
        w_max = min(self.kin.max_w, cur_w + self.kin.max_a_ang * self.dt)

        v_samples = np.linspace(v_min, v_max, 10)
        w_samples = np.linspace(w_min, w_max, 15)

        best_score = -float('inf')
        best_v = 0.0
        best_w = 0.0
        best_trajectory = []

        # Check immediate safety
        immediate_danger = False
        for obs in dynamic_obstacles:
            dist = math.hypot(cur_x - obs['x'], cur_y - obs['y'])
            if dist < (obs.get('radius', 0.5) + self.kin.L / 2.0 + 0.15):
                immediate_danger = True
                break

        if immediate_danger:
            # Immediate stop or retreat
            return 0.0, 0.0, []

        for v in v_samples:
            for w in w_samples:
                traj, min_clearance, is_collision = self._simulate_trajectory(
                    cur_x, cur_y, cur_th, v, w, costmap, dynamic_obstacles
                )

                if is_collision:
                    continue

                # Heading score: cosine similarity to local target
                final_x, final_y, final_th = traj[-1]
                target_angle = math.atan2(local_target[1] - final_y, local_target[0] - final_x)
                angle_diff = abs(math.atan2(math.sin(target_angle - final_th), math.cos(target_angle - final_th)))
                heading_score = math.pi - angle_diff

                # Clearance score: distance to nearest obstacle
                clearance_score = min(min_clearance, 3.0)

                # Velocity score: higher forward speed preferred
                velocity_score = max(0.0, v)

                # Total weighted score
                total_score = (self.w_heading * heading_score +
                               self.w_clearance * clearance_score +
                               self.w_velocity * velocity_score)

                if total_score > best_score:
                    best_score = total_score
                    best_v = v
                    best_w = w
                    best_trajectory = traj

        return float(best_v), float(best_w), best_trajectory

    def _simulate_trajectory(self, x, y, th, v, w, costmap, dynamic_obstacles):
        """Roll out trajectory and verify clearances against static & moving obstacles."""
        traj = []
        min_clearance = float('inf')
        is_collision = False

        cx, cy, cth = x, y, th

        for step in range(1, self.num_steps + 1):
            t = step * self.dt
            cx, cy, cth = self.kin.integrate_runge_kutta_4(cx, cy, cth, v, w, self.dt)
            traj.append([cx, cy, cth])

            # Check static costmap clearance
            cost = costmap.get_cost(cx, cy)
            if cost >= 240:
                is_collision = True
                break
            
            static_dist = 0.5 if cost > 150 else 1.5
            min_clearance = min(min_clearance, static_dist)

            # Check dynamic moving obstacles (extrapolating their positions)
            for obs in dynamic_obstacles:
                # Dynamic obstacle velocity prediction
                obs_vx = obs.get('vx', 0.0)
                obs_vy = obs.get('vy', 0.0)
                predicted_obs_x = obs['x'] + obs_vx * t
                predicted_obs_y = obs['y'] + obs_vy * t

                dist = math.hypot(cx - predicted_obs_x, cy - predicted_obs_y)
                effective_radius = obs.get('radius', 0.5) + (self.kin.L / 2.0)

                if dist < effective_radius:
                    is_collision = True
                    break

                min_clearance = min(min_clearance, dist - effective_radius)

            if is_collision:
                break

        return traj, min_clearance, is_collision

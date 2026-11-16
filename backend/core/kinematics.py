"""
Kinematics and Motion Dynamics Engine for Differential Drive AMR
Implements forward/inverse kinematics, acceleration limits, and odometry simulation.
"""

import math
import numpy as np

class DifferentialDriveKinematics:
    def __init__(self, wheel_base=0.65, wheel_radius=0.10, 
                 max_v=1.2, max_w=1.5, max_a_lin=0.8, max_a_ang=1.2):
        self.L = wheel_base
        self.r = wheel_radius
        self.max_v = max_v
        self.max_w = max_w
        self.max_a_lin = max_a_lin
        self.max_a_ang = max_a_ang

    def forward_kinematics(self, w_left, w_right):
        """
        Compute robot body velocities (v, omega) from left/right wheel angular velocities (rad/s).
        v = r/2 * (w_right + w_left)
        omega = r/L * (w_right - w_left)
        """
        v = (self.r / 2.0) * (w_right + w_left)
        w = (self.r / self.L) * (w_right - w_left)
        return float(v), float(w)

    def inverse_kinematics(self, v, w):
        """
        Compute required left and right wheel angular velocities (rad/s) for target (v, w).
        w_left = (v - w * L / 2) / r
        w_right = (v + w * L / 2) / r
        """
        w_left = (v - (w * self.L / 2.0)) / self.r
        w_right = (v + (w * self.L / 2.0)) / self.r
        return float(w_left), float(w_right)

    def enforce_dynamic_limits(self, current_v, current_w, target_v, target_w, dt):
        """
        Enforce max acceleration and velocity limits on command inputs over timestep dt.
        """
        # Linear velocity limit
        target_v = np.clip(target_v, -self.max_v * 0.5, self.max_v) # Reverse speed is capped
        delta_v = target_v - current_v
        max_dv = self.max_a_lin * dt
        v_next = current_v + np.clip(delta_v, -max_dv, max_dv)

        # Angular velocity limit
        target_w = np.clip(target_w, -self.max_w, self.max_w)
        delta_w = target_w - current_w
        max_dw = self.max_a_ang * dt
        w_next = current_w + np.clip(delta_w, -max_dw, max_dw)

        return float(v_next), float(w_next)

    def integrate_runge_kutta_4(self, x, y, theta, v, w, dt):
        """
        4th-Order Runge-Kutta integration for differential drive pose [x, y, theta].
        Provides superior numerical stability over Euler integration during curved motions.
        """
        def derivatives(pose, linear_v, angular_w):
            _, _, th = pose
            dx = linear_v * math.cos(th)
            dy = linear_v * math.sin(th)
            dth = angular_w
            return np.array([dx, dy, dth])

        pose = np.array([x, y, theta], dtype=float)
        
        k1 = derivatives(pose, v, w)
        k2 = derivatives(pose + 0.5 * dt * k1, v, w)
        k3 = derivatives(pose + 0.5 * dt * k2, v, w)
        k4 = derivatives(pose + dt * k3, v, w)

        next_pose = pose + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        
        # Normalize theta to [-pi, pi]
        next_pose[2] = math.atan2(math.sin(next_pose[2]), math.cos(next_pose[2]))
        return float(next_pose[0]), float(next_pose[1]), float(next_pose[2])

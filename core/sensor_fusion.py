"""
Sensor Fusion and Simulation Engine for Industrial AMR
Implements Extended Kalman Filter (EKF), 2D LiDAR Raycasting, and RGB-D Depth Camera.
"""

import math
import numpy as np

class ExtendedKalmanFilter:
    """
    EKF estimating robot state: x_hat = [x, y, theta, v, w]^T
    Fuses wheel odometry, IMU gyro/accel, and scan-matching pose corrections.
    """
    def __init__(self, init_x=0.0, init_y=0.0, init_theta=0.0):
        # State vector: [x, y, theta, v, w]
        self.x = np.array([init_x, init_y, init_theta, 0.0, 0.0], dtype=float)

        # State covariance P
        self.P = np.diag([0.05, 0.05, 0.02, 0.01, 0.01])

        # Process noise covariance Q
        self.Q = np.diag([0.02, 0.02, 0.01, 0.05, 0.05])

        # Measurement noise covariance R for Odometry [x_odom, y_odom, theta_odom]
        self.R_odom = np.diag([0.08, 0.08, 0.03])

        # Measurement noise covariance R for IMU [gyro_w]
        self.R_imu = np.array([[0.01]])

    def predict(self, dt):
        """Nonlinear state prediction step"""
        x, y, th, v, w = self.x

        # Kinematic model
        dx = v * math.cos(th) * dt
        dy = v * math.sin(th) * dt
        dth = w * dt

        self.x[0] += dx
        self.x[1] += dy
        self.x[2] = math.atan2(math.sin(th + dth), math.cos(th + dth))

        # Jacobian of motion model F
        F = np.eye(5)
        F[0, 2] = -v * math.sin(th) * dt
        F[0, 3] = math.cos(th) * dt
        F[1, 2] = v * math.cos(th) * dt
        F[1, 3] = math.sin(th) * dt
        F[2, 4] = dt

        self.P = F @ self.P @ F.T + self.Q

    def update_odometry(self, z_odom):
        """Measurement update with wheel odometry [x, y, theta]"""
        # Measurement matrix H
        H = np.zeros((3, 5))
        H[0, 0] = 1.0
        H[1, 1] = 1.0
        H[2, 2] = 1.0

        y = z_odom - (H @ self.x)
        # Wrap angle difference
        y[2] = math.atan2(math.sin(y[2]), math.cos(y[2]))

        S = H @ self.P @ H.T + self.R_odom
        K = self.P @ H.T @ np.linalg.inv(S)

        self.x = self.x + K @ y
        self.x[2] = math.atan2(math.sin(self.x[2]), math.cos(self.x[2]))
        self.P = (np.eye(5) - K @ H) @ self.P

    def update_imu(self, gyro_w):
        """Measurement update with IMU gyroscope measurement"""
        H = np.zeros((1, 5))
        H[0, 4] = 1.0

        y = np.array([gyro_w]) - (H @ self.x)
        S = H @ self.P @ H.T + self.R_imu
        K = self.P @ H.T @ np.linalg.inv(S)

        self.x = self.x + K @ y
        self.P = (np.eye(5) - K @ H) @ self.P

    def get_estimated_pose(self):
        return float(self.x[0]), float(self.x[1]), float(self.x[2])


class LidarSimulator:
    """
    Simulates a 2D Planar 360-degree LiDAR scanner using geometric ray-intersection.
    Detects static warehouse walls, storage racks, and dynamic obstacles.
    """
    def __init__(self, samples=180, range_min=0.15, range_max=12.0, noise_std=0.02):
        self.samples = samples
        self.range_min = range_min
        self.range_max = range_max
        self.noise_std = noise_std
        self.angles = np.linspace(-math.pi, math.pi, samples, endpoint=False)

    def scan(self, robot_x, robot_y, robot_theta, static_rectangles, dynamic_circles):
        """
        Cast simulated rays against warehouse rectangular obstacles and dynamic circular obstacles.
        Returns array of ranges and (x, y) hit points in global coordinates.
        """
        ranges = np.full(self.samples, self.range_max, dtype=float)
        hit_points = []

        cos_thetas = np.cos(robot_theta + self.angles)
        sin_thetas = np.sin(robot_theta + self.angles)

        for i in range(self.samples):
            ray_dx = cos_thetas[i]
            ray_dy = sin_thetas[i]
            min_dist = self.range_max

            # 1. Intersect warehouse bounding walls [0, 50] x [0, 30]
            if ray_dx > 1e-4:
                d = (50.0 - robot_x) / ray_dx
                if 0 < d < min_dist: min_dist = d
            elif ray_dx < -1e-4:
                d = (0.0 - robot_x) / ray_dx
                if 0 < d < min_dist: min_dist = d

            if ray_dy > 1e-4:
                d = (30.0 - robot_y) / ray_dy
                if 0 < d < min_dist: min_dist = d
            elif ray_dy < -1e-4:
                d = (0.0 - robot_y) / ray_dy
                if 0 < d < min_dist: min_dist = d

            # 2. Intersect static rectangular obstacles (racks)
            for rect in static_rectangles:
                rx1 = rect['x'] - rect['w']/2.0
                rx2 = rect['x'] + rect['w']/2.0
                ry1 = rect['y'] - rect['h']/2.0
                ry2 = rect['y'] + rect['h']/2.0

                # Ray-AABB intersection
                t_min = 0.0
                t_max = min_dist

                if abs(ray_dx) > 1e-6:
                    tx1 = (rx1 - robot_x) / ray_dx
                    tx2 = (rx2 - robot_x) / ray_dx
                    t_min = max(t_min, min(tx1, tx2))
                    t_max = min(t_max, max(tx1, tx2))
                elif robot_x < rx1 or robot_x > rx2:
                    continue

                if abs(ray_dy) > 1e-6:
                    ty1 = (ry1 - robot_y) / ray_dy
                    ty2 = (ry2 - robot_y) / ray_dy
                    t_min = max(t_min, min(ty1, ty2))
                    t_max = min(t_max, max(ty1, ty2))
                elif robot_y < ry1 or robot_y > ry2:
                    continue

                if t_max >= t_min and t_min > 0 and t_min < min_dist:
                    min_dist = t_min

            # 3. Intersect dynamic circular obstacles (humans, forklifts, other AMRs)
            for circ in dynamic_circles:
                cx, cy, radius = circ['x'], circ['y'], circ['radius']
                oc_x = robot_x - cx
                oc_y = robot_y - cy

                b = 2.0 * (oc_x * ray_dx + oc_y * ray_dy)
                c = oc_x**2 + oc_y**2 - radius**2
                disc = b**2 - 4 * c

                if disc >= 0:
                    sqrt_disc = math.sqrt(disc)
                    t1 = (-b - sqrt_disc) / 2.0
                    t2 = (-b + sqrt_disc) / 2.0
                    if t1 > 0 and t1 < min_dist:
                        min_dist = t1
                    elif t2 > 0 and t2 < min_dist:
                        min_dist = t2

            # Add Gaussian noise
            if min_dist < self.range_max:
                noisy_dist = min_dist + np.random.normal(0, self.noise_std)
                ranges[i] = max(self.range_min, min(self.range_max, noisy_dist))
                hit_x = robot_x + ranges[i] * ray_dx
                hit_y = robot_y + ranges[i] * ray_dy
                hit_points.append([round(float(hit_x), 2), round(float(hit_y), 2)])

        return ranges.tolist(), hit_points

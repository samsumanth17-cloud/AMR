"""
Autonomous Mobile Robot (AMR) High-Level Agent
Integrates Kinematics, Sensor Fusion (EKF), Costmap, Global & Local Planners,
Battery Management, Material Handling, and Recovery Behaviors into a unified autonomous entity.
"""

import math
import time
import numpy as np
from config import ROBOT_PHYSICS, SENSOR_CONFIG, INFRASTRUCTURE
from core.kinematics import DifferentialDriveKinematics
from core.sensor_fusion import ExtendedKalmanFilter, LidarSimulator
from core.path_planner import AStarPlanner
from core.local_planner import DynamicWindowLocalPlanner
from core.recovery_system import RecoveryBehaviorTree
from core.battery_manager import BatterySubsystem
from core.material_handler import LifterMechanism

class AMR:
    def __init__(self, amr_id, name, color, initial_pose, battery_soc=90.0, 
                 payload_capacity_kg=500, role="transport", costmap=None):
        self.id = amr_id
        self.name = name
        self.color = color
        self.role = role
        self.payload_capacity_kg = payload_capacity_kg
        self.costmap = costmap

        # Ground truth pose [x, y, theta]
        self.pose = list(initial_pose)
        self.velocity = [0.0, 0.0] # [v, w]
        self.target_pose = None
        self.status = "IDLE"       # IDLE, NAV_PICKUP, DOCKING, LIFTING, NAV_DROPOFF, LOWERING, CHARGING, RECOVERY, ESTOP, MANUAL
        self.mode = "AUTONOMOUS"   # AUTONOMOUS or MANUAL
        self.manual_v = 0.0
        self.manual_w = 0.0
        self.manual_cmd_time = 0.0

        # Core subsystems
        self.kinematics = DifferentialDriveKinematics(
            wheel_base=ROBOT_PHYSICS["wheel_base"],
            wheel_radius=ROBOT_PHYSICS["wheel_radius"],
            max_v=ROBOT_PHYSICS["max_linear_velocity"],
            max_w=ROBOT_PHYSICS["max_angular_velocity"],
            max_a_lin=ROBOT_PHYSICS["max_linear_acceleration"],
            max_a_ang=ROBOT_PHYSICS["max_angular_acceleration"]
        )

        self.ekf = ExtendedKalmanFilter(init_x=self.pose[0], init_y=self.pose[1], init_theta=self.pose[2])
        self.lidar = LidarSimulator(
            samples=SENSOR_CONFIG["lidar"]["samples"],
            range_min=SENSOR_CONFIG["lidar"]["range_min"],
            range_max=SENSOR_CONFIG["lidar"]["range_max"],
            noise_std=SENSOR_CONFIG["lidar"]["noise_std_dev"]
        )

        self.global_planner = AStarPlanner(self.costmap) if self.costmap else None
        self.local_planner = DynamicWindowLocalPlanner(self.kinematics)
        self.recovery_tree = RecoveryBehaviorTree()
        self.battery_subsystem = BatterySubsystem(initial_soc=battery_soc)
        self.lifter = LifterMechanism()

        # Mission state
        self.active_task = None
        self.carrying_pallet = None
        self.global_path = []
        self.path_index = 0
        self.local_trajectory = []
        self.lidar_hit_points = []
        self.breadcrumbs = [] # [(x, y)] history
        self.traffic_yield_active = False
        self.yield_reason = ""
        self.total_distance_traveled = 0.0

    def assign_mission(self, task):
        """Assigns material transport task to AMR."""
        self.active_task = task
        self.plan_path_to(task.pallet.pickup_x, task.pallet.pickup_y)
        self.status = "NAV_PICKUP"

    def plan_path_to(self, target_x, target_y, congestion_zones=None):
        """Generates global A* path to target coordinates."""
        self.target_pose = [target_x, target_y]
        if self.global_planner:
            path = self.global_planner.plan(self.pose[0], self.pose[1], target_x, target_y, congestion_zones)
            if path:
                self.global_path = path
                self.path_index = 0
                return True
        return False

    def update(self, dynamic_obstacles, dt):
        """Main update loop executed at simulation frequency (e.g. 10Hz - 20Hz)."""
        # 1. Update Battery and Lifter
        is_charging_pad = self._is_at_charging_pad()
        current_payload_kg = self.carrying_pallet.weight_kg if self.carrying_pallet else 0.0
        soc, voltage, power_w = self.battery_subsystem.update(
            self.velocity[0], self.velocity[1], current_payload_kg, is_charging_pad, dt
        )
        self.lifter.update(dt)

        # 2. Battery Safety Preemption: Reroute to charger if critical
        if self.battery_subsystem.is_critical() and self.status not in ["NAV_CHARGER", "CHARGING", "ESTOP"]:
            self._route_to_charging_station("Critical Battery (<18%)")

        if is_charging_pad and self.status == "NAV_CHARGER":
            self.status = "CHARGING"
            self.velocity = [0.0, 0.0]

        if self.status == "CHARGING":
            if self.battery_subsystem.is_fully_charged():
                self.status = "IDLE"
            return

        if self.status == "ESTOP":
            self.velocity = [0.0, 0.0]
            return

        # 3. Simulate LiDAR raycast
        ranges, hit_points = self.lidar.scan(
            self.pose[0], self.pose[1], self.pose[2],
            INFRASTRUCTURE["storage_racks"],
            dynamic_obstacles
        )
        self.lidar_hit_points = hit_points[::3] # Subsample for telemetry bandwidth

        # Manual Override Execution
        if self.mode == "MANUAL" or self.status == "MANUAL":
            self.status = "MANUAL"
            # Deadman's timeout: stop if no fresh command within 1.0s
            if time.time() - self.manual_cmd_time > 1.0:
                self.manual_v = 0.0
                self.manual_w = 0.0

            v_next, w_next = self.kinematics.enforce_dynamic_limits(
                self.velocity[0], self.velocity[1], self.manual_v, self.manual_w, dt
            )
            self.velocity = [v_next, w_next]
            self._apply_motion(v_next, w_next, dt)
            return

        # 4. Check Recovery Behavior Tree
        is_navigating = (self.status in ["NAV_PICKUP", "NAV_DROPOFF", "NAV_CHARGER"])
        rec_override, rec_v, rec_w, rec_msg = self.recovery_tree.update(self.pose, is_navigating, dt)
        if rec_override:
            self.status = "RECOVERY"
            self.velocity = [rec_v, rec_w]
            self._apply_motion(rec_v, rec_w, dt)
            if "Global Replan" in rec_msg and self.target_pose:
                # Add virtual penalty around current blockage
                self.plan_path_to(self.target_pose[0], self.target_pose[1], 
                                  congestion_zones=[{"x": self.pose[0], "y": self.pose[1], "radius": 2.5, "penalty": 40.0}])
                self.status = "NAV_PICKUP" if self.carrying_pallet is None else "NAV_DROPOFF"
            return

        # 5. Handle Traffic Yield
        if self.traffic_yield_active:
            self.velocity = [0.0, 0.0]
            self.traffic_yield_active = False # Reset for next cycle
            return

        # 6. Execute Navigation along Global Path
        if is_navigating and self.global_path:
            self._navigate_step(dynamic_obstacles, dt)
        elif self.status == "LIFTING":
            if self.lifter.is_raised():
                # Pallet secured
                if self.active_task and self.carrying_pallet:
                    self.carrying_pallet.status = "IN_TRANSIT"
                    self.plan_path_to(self.carrying_pallet.dropoff_x, self.carrying_pallet.dropoff_y)
                    self.status = "NAV_DROPOFF"
        elif self.status == "LOWERING":
            if self.lifter.is_lowered():
                # Pallet successfully dropped off
                if self.carrying_pallet:
                    self.carrying_pallet.status = "DELIVERED"
                    self.carrying_pallet.carried_by = None
                    self.carrying_pallet = None
                if self.active_task:
                    self.active_task.status = "COMPLETED"
                    self.active_task = None
                self.status = "IDLE"

    def _navigate_step(self, dynamic_obstacles, dt):
        """Follow global path waypoints with DWA local avoidance."""
        if self.path_index >= len(self.global_path):
            self._on_reached_destination()
            return

        current_target = self.global_path[self.path_index]
        dist_to_waypoint = math.hypot(self.pose[0] - current_target[0], self.pose[1] - current_target[1])

        # Advance waypoint if within tolerance
        if dist_to_waypoint < 0.7:
            self.path_index += 1
            if self.path_index >= len(self.global_path):
                self._on_reached_destination()
                return
            current_target = self.global_path[self.path_index]

        # Run DWA Local Planner
        cmd_v, cmd_w, traj = self.local_planner.compute_velocity_command(
            self.pose, self.velocity, current_target, self.costmap, dynamic_obstacles
        )
        self.local_trajectory = traj

        # Smooth dynamic acceleration limits
        v_next, w_next = self.kinematics.enforce_dynamic_limits(
            self.velocity[0], self.velocity[1], cmd_v, cmd_w, dt
        )
        self.velocity = [v_next, w_next]
        self._apply_motion(v_next, w_next, dt)

    def _apply_motion(self, v, w, dt):
        # 1. Update ground truth with RK4
        old_x, old_y = self.pose[0], self.pose[1]
        nx, ny, nth = self.kinematics.integrate_runge_kutta_4(self.pose[0], self.pose[1], self.pose[2], v, w, dt)
        self.pose = [nx, ny, nth]

        # Track odometer
        step_dist = math.hypot(nx - old_x, ny - old_y)
        self.total_distance_traveled += step_dist

        # 2. Update EKF Sensor Fusion (with simulated sensor noise)
        self.ekf.predict(dt)
        noisy_odom = np.array([nx + np.random.normal(0, 0.015),
                               ny + np.random.normal(0, 0.015),
                               nth + np.random.normal(0, 0.01)])
        self.ekf.update_odometry(noisy_odom)
        self.ekf.update_imu(w + np.random.normal(0, 0.005))

        # Record breadcrumbs
        if len(self.breadcrumbs) == 0 or math.hypot(nx - self.breadcrumbs[-1][0], ny - self.breadcrumbs[-1][1]) > 0.4:
            self.breadcrumbs.append([round(nx, 2), round(ny, 2)])
            if len(self.breadcrumbs) > 40:
                self.breadcrumbs.pop(0)

        # Update carried pallet coordinates
        if self.carrying_pallet:
            self.carrying_pallet.current_x = nx
            self.carrying_pallet.current_y = ny

    def _on_reached_destination(self):
        self.velocity = [0.0, 0.0]
        self.global_path = []

        if self.status == "NAV_PICKUP":
            # Docking under pallet and lifting
            self.status = "LIFTING"
            if self.active_task:
                self.carrying_pallet = self.active_task.pallet
                self.carrying_pallet.status = "PICKING_UP"
                self.carrying_pallet.carried_by = self.id
            self.lifter.raise_lift()

        elif self.status == "NAV_DROPOFF":
            # Lowering pallet
            self.status = "LOWERING"
            self.lifter.lower_lift()

        elif self.status == "NAV_CHARGER":
            self.status = "CHARGING"

    def _route_to_charging_station(self, reason):
        for station in INFRASTRUCTURE["charging_stations"]:
            if self.plan_path_to(station["x"], station["y"]):
                self.status = "NAV_CHARGER"
                break

    def _is_at_charging_pad(self):
        for station in INFRASTRUCTURE["charging_stations"]:
            if math.hypot(self.pose[0] - station["x"], self.pose[1] - station["y"]) < 1.0:
                return True
        return False

    def set_manual_teleop(self, v, w):
        """Inject manual teleoperation command with deadman timer."""
        self.mode = "MANUAL"
        self.status = "MANUAL"
        self.manual_v = float(v)
        self.manual_w = float(w)
        self.manual_cmd_time = time.time()

    def set_control_mode(self, mode):
        """Switch between AUTONOMOUS and MANUAL control modes."""
        self.mode = mode.upper()
        if self.mode == "AUTONOMOUS":
            self.manual_v = 0.0
            self.manual_w = 0.0
            if self.status == "MANUAL":
                self.status = "IDLE" if not self.global_path else ("NAV_PICKUP" if not self.carrying_pallet else "NAV_DROPOFF")
        else:
            self.status = "MANUAL"
            self.velocity = [0.0, 0.0]
            self.manual_v = 0.0
            self.manual_w = 0.0

    def manual_lift(self, action):
        """Trigger lifter mechanism up or down manually."""
        if action.upper() in ["RAISE", "UP"]:
            self.lifter.raise_lift()
        elif action.upper() in ["LOWER", "DOWN"]:
            self.lifter.lower_lift()

    def apply_traffic_yield(self, reason):
        self.traffic_yield_active = True
        self.yield_reason = reason

    def to_telemetry(self):
        est_x, est_y, est_th = self.ekf.get_estimated_pose()
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "role": self.role,
            "mode": self.mode,
            "status": self.status,
            "pose": [round(p, 3) for p in self.pose],
            "estimated_pose": [round(est_x, 3), round(est_y, 3), round(est_th, 3)],
            "velocity": [round(v, 3) for v in self.velocity],
            "battery": round(self.battery_subsystem.soc, 1),
            "voltage": round(self.battery_subsystem.voltage, 1),
            "is_charging": self.battery_subsystem.is_charging,
            "lifter_height": round(self.lifter.height, 3),
            "lifter_state": self.lifter.state,
            "carrying_pallet": self.carrying_pallet.to_dict() if self.carrying_pallet else None,
            "path": self.global_path,
            "path_index": self.path_index,
            "local_trajectory": [[round(p[0], 2), round(p[1], 2)] for p in self.local_trajectory],
            "lidar_hits": self.lidar_hit_points,
            "breadcrumbs": self.breadcrumbs,
            "recovery_tier": self.recovery_tree.current_tier,
            "total_distance_m": round(self.total_distance_traveled, 1),
            "yield_reason": self.yield_reason if self.traffic_yield_active else ""
        }

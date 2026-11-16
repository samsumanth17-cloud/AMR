"""
Configuration parameters for AI-Powered Autonomous Mobile Robot (AMR) System
Industrial Warehouse Environment & Fleet Specifications
"""

import os

# Server & Network Configuration
SERVER_HOST = os.getenv("AMR_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("AMR_PORT", 5000))
DEBUG_MODE = os.getenv("AMR_DEBUG", "True").lower() == "true"

# Gemini AI API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

# Warehouse Grid & Environment Dimensions (meters)
MAP_WIDTH = 50.0       # X-axis (50 meters)
MAP_HEIGHT = 30.0      # Y-axis (30 meters)
GRID_RESOLUTION = 0.5   # 0.5m per cell -> 100 x 60 grid cells
COSTMAP_INFLATION_RADIUS = 1.0  # Robot radius + safety margin (meters)

# Fixed Warehouse Infrastructure Locations (X, Y) in meters
INFRASTRUCTURE = {
    "charging_stations": [
        {"id": "CHARGE_01", "name": "Charging Bay Alpha", "x": 3.0, "y": 3.0, "occupied_by": None},
        {"id": "CHARGE_02", "name": "Charging Bay Beta",  "x": 3.0, "y": 7.0, "occupied_by": None},
    ],
    "loading_docks": [
        {"id": "DOCK_A", "name": "Inbound Dock A",  "x": 46.0, "y": 6.0,  "type": "inbound"},
        {"id": "DOCK_B", "name": "Outbound Dock B", "x": 46.0, "y": 24.0, "type": "outbound"},
    ],
    "storage_racks": [
        # Rack Aisle 1 (Left-Center)
        {"id": "RACK_A1", "x": 12.0, "y": 6.0, "w": 2.0, "h": 8.0},
        {"id": "RACK_A2", "x": 18.0, "y": 6.0, "w": 2.0, "h": 8.0},
        # Rack Aisle 2 (Right-Center)
        {"id": "RACK_B1", "x": 26.0, "y": 6.0, "w": 2.0, "h": 8.0},
        {"id": "RACK_B2", "x": 32.0, "y": 6.0, "w": 2.0, "h": 8.0},
        # Rack Aisle 3 (Upper Racks)
        {"id": "RACK_C1", "x": 12.0, "y": 18.0, "w": 2.0, "h": 8.0},
        {"id": "RACK_C2", "x": 18.0, "y": 18.0, "w": 2.0, "h": 8.0},
        {"id": "RACK_D1", "x": 26.0, "y": 18.0, "w": 2.0, "h": 8.0},
        {"id": "RACK_D2", "x": 32.0, "y": 18.0, "w": 2.0, "h": 8.0},
    ],
    "staging_zones": [
        {"id": "STAGE_1", "name": "Sorting Area 1", "x": 7.0, "y": 15.0},
        {"id": "STAGE_2", "name": "Packaging Area", "x": 40.0, "y": 15.0},
    ]
}

# AMR Physical and Kinematic Constraints
ROBOT_PHYSICS = {
    "length": 1.0,               # Length in meters
    "width": 0.8,                # Width in meters
    "height": 0.35,              # Chassis height in meters
    "wheel_base": 0.65,          # Distance between drive wheels (differential drive)
    "wheel_radius": 0.10,        # Wheel radius in meters
    "max_linear_velocity": 1.2,  # m/s
    "max_linear_acceleration": 0.8,  # m/s^2
    "max_angular_velocity": 1.5, # rad/s
    "max_angular_acceleration": 1.2, # rad/s^2
    "safety_stop_distance": 0.8, # Emergency stop buffer (meters)
    "slowdown_distance": 2.2,    # Dynamic obstacle avoidance deceleration zone
}

# Sensor Specifications for Simulation & Sensor Fusion
SENSOR_CONFIG = {
    "lidar": {
        "range_min": 0.15,
        "range_max": 12.0,
        "fov_deg": 360,
        "samples": 180,           # 2-degree resolution
        "noise_std_dev": 0.02,    # Gaussian noise in meters
    },
    "depth_camera": {
        "fov_deg": 70,
        "range_max": 6.0,
        "mounting_offset_x": 0.45, # Mounted front bumper
        "noise_std_dev": 0.03,
    },
    "imu": {
        "gyro_noise_std_dev": 0.01, # rad/s
        "accel_noise_std_dev": 0.05,# m/s^2
    },
    "wheel_encoders": {
        "ticks_per_rev": 2048,
        "slip_probability": 0.02,
    }
}

# Battery & Power Consumption Model
BATTERY_CONFIG = {
    "capacity_wh": 1200.0,            # 1.2 kWh LiFePO4 battery pack
    "nominal_voltage": 24.0,          # Volts
    "critical_threshold": 15.0,       # % SOC -> Immediate abort & charge
    "warning_threshold": 30.0,        # % SOC -> Reroute to charging after current leg
    "full_threshold": 98.0,           # % SOC -> Fully charged
    "idle_power_w": 25.0,             # Base electronics, computer, LiDAR
    "motion_power_per_mps_w": 180.0,  # Motor draw proportional to speed
    "payload_power_w_per_kg": 0.9,    # Extra load power
    "charging_power_w": 600.0,        # 600W Fast Inductive Docking Charger
}

# Default Multi-Robot Fleet Setup
DEFAULT_FLEET = [
    {
        "id": "AMR-01",
        "name": "Alpha-Hauler",
        "color": "#00E5FF",      # Cyber Cyan
        "initial_pose": [6.0, 4.0, 0.0], # [x, y, theta_rad]
        "battery": 92.0,
        "payload_capacity_kg": 500,
        "role": "heavy_transport"
    },
    {
        "id": "AMR-02",
        "name": "Beta-Courier",
        "color": "#76FF03",      # Neon Green
        "initial_pose": [6.0, 8.0, 0.0],
        "battery": 78.0,
        "payload_capacity_kg": 300,
        "role": "express_delivery"
    },
    {
        "id": "AMR-03",
        "name": "Gamma-Tugger",
        "color": "#FF9100",      # Vivid Orange
        "initial_pose": [6.0, 12.0, 0.0],
        "battery": 45.0,
        "payload_capacity_kg": 400,
        "role": "cross_dock"
    }
]

# Dynamic Obstacles (Simulated Pedestrians & Industrial Forklifts)
DYNAMIC_OBSTACLES = [
    {
        "id": "HUMAN_01",
        "type": "worker",
        "name": "Warehouse Worker 1",
        "x": 22.0,
        "y": 10.0,
        "speed": 0.7,
        "radius": 0.45,
        "waypoints": [
            [22.0, 6.0],
            [22.0, 22.0],
            [22.0, 6.0]
        ]
    },
    {
        "id": "FORKLIFT_01",
        "type": "forklift",
        "name": "Heavy Forklift FL-2",
        "x": 38.0,
        "y": 20.0,
        "speed": 1.1,
        "radius": 1.2,
        "waypoints": [
            [38.0, 25.0],
            [38.0, 5.0],
            [38.0, 25.0]
        ]
    }
]

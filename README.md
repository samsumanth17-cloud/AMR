# 🤖 AI-Powered Autonomous Mobile Robot (AMR) for Intelligent Industrial Logistics

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Three.js](https://img.shields.io/badge/3D%20Digital%20Twin-Three.js%20WebGL-00e5ff.svg)](https://threejs.org/)
[![AI Orchestration](https://img.shields.io/badge/AI%20Commander-Google%20Gemini%20API-a855f7.svg)](https://aistudio.google.com/)
[![ROS 2 Compatible](https://img.shields.io/badge/Robotics-ROS%202%20Humble%2FIron-22c55e.svg)](https://www.ros.org/)

---

## 📌 Problem Statement & Detailed Description

In high-throughput modern manufacturing and warehouse fulfillment facilities, traditional Automated Guided Vehicles (AGVs) restricted to magnetic floor tapes or fixed optical lines create severe logistics bottlenecks when confronted with dynamic obstacles, shifting production layouts, or traffic deadlocks.

This system delivers an **intelligent Autonomous Mobile Robot (AMR) Fleet Solution** capable of operating in dynamic warehouse environments without continuous human supervision. It autonomously transports materials between multiple pickup and delivery locations while negotiating crowded aisles, avoiding moving pedestrians and heavy forklifts, collaboratively arbitrating traffic with peer robots, recovering from deadlocks, and optimizing battery lifecycle.

The system features an interactive **Photorealistic 3D WebGL Digital Twin** and an integrated **Google Gemini AI Fleet Commander** for natural language task dispatching and spatial bottleneck diagnostics.

---

## 🌟 The 8 Key Challenges & Algorithmic Solutions

| # | Challenge | Implemented Solution | Mathematical / Architectural Formulation |
|---|---|---|---|
| **1** | **Autonomous Navigation & Sensor Fusion** | **Extended Kalman Filter (EKF) + Planar 360° LiDAR Raycasting** | Non-linear motion model prediction fused with noisy wheel encoder odometry and IMU angular velocity: $\hat{x}_{k} = f(\hat{x}_{k-1}, u_k)$, $K_k = P_k H^T (H P_k H^T + R)^{-1}$. |
| **2** | **Dynamic Obstacle Avoidance** | **Dynamic Window Approach (DWA) + Velocity Extrapolation** | Searches reachable $(v, \omega)$ velocity space respecting acceleration limits, extrapolating dynamic pedestrian and forklift vectors over prediction horizon $T=1.8\text{s}$. |
| **3** | **AI-Based Path Planning & Rerouting** | **Cost-Aware A\* with Diagonal Shortcuts & Gemini AI** | Octile distance heuristic path planning with dynamic costmap inflation and automatic line-of-sight string-pulling shortcutting. Gemini AI optimizes fleet flow. |
| **4** | **Multi-Robot Coordination** | **Auction-Based Task Allocation & Right-of-Way Arbitration** | Minimizes global mission cost: $J_{i, j} = \alpha \cdot d(P_i, T_j) + \beta \cdot (100 - \text{SOC}_i) - \gamma \cdot \text{Prio}_j$. Loaded AMRs hold right-of-way over empty AMRs. |
| **5** | **Intelligent Material Handling** | **Automated Scissor Lift & RFID Payload State Machine** | 9-state lifter transition model (`APPROACH` $\to$ `DOCK_UNDER` $\to$ `LIFT` $\to$ `TRANSIT` $\to$ `LOWER` $\to$ `VERIFY`). Dynamically updates robot mass and braking limits. |
| **6** | **Deadlock Detection & Recovery** | **5-Tier Hierarchical Recovery Behavior Tree** | Detects progress stall ($<0.2\text{m}$ in $3.5\text{s}$). Tiers: 1) Costmap Purge $\to$ 2) $360^\circ$ Rotation Scan $\to$ 3) Reverse Retreat ($0.6\text{m}$) $\to$ 4) A\* Replan $\to$ 5) Inter-Robot Yield. |
| **7** | **Battery-Aware Mission Planning** | **Continuous SOC Physics Model & Fast Inductive Docking** | Non-linear LiFePO4 discharge: $P_{\text{tot}} = P_{\text{idle}} + P_{\text{drive}}(v, \omega) + P_{\text{load}}(m)$. Auto-preempts at $<18\%$ SOC to reserve nearest inductive charging pad. |
| **8** | **Real-Time Monitoring & Digital Twin** | **Centralized WebGL Cockpit with Multi-Camera Feeds** | Three.js 3D Digital Twin with real-time telemetry, Orbit / Tactical / Chase Cam / Sensor POV, live point clouds, planned path ribbons, and DWA velocity cones. |

---

## 🏛️ System Architecture

```
                                  +---------------------------------------+
                                  |     Google Gemini AI Fleet Commander  |
                                  |    (Natural Language & Task Dispatch) |
                                  +-------------------+-------------------+
                                                      |  REST / JSON
                                                      v
+-------------------------------------------------------------------------------------------------------+
|                                    CENTRALIZED FLEET SIMULATION ENGINE                                |
|                                                                                                       |
|  +---------------------------+   +-------------------------------+   +-----------------------------+  |
|  |   Multi-Robot Coordinator |   |   Costmap2D Manager           |   |   Dynamic Obstacle Engine   |  |
|  | - Auction Task Allocator  |   | - Static Infrastructure Racks |   | - Worker 1 (Patrol 0.7 m/s) |  |
|  | - Right-of-Way Arbiter   |   | - Dynamic Inflation Layer     |   | - Forklift FL-2 (1.1 m/s)   |  |
|  +-------------+-------------+   +---------------+---------------+   +--------------+--------------+  |
|                |                                 |                                  |                 |
|                +---------------------------------+----------------------------------+                 |
|                                                  |                                                    |
|                                                  v                                                    |
|  +-------------------------------------------------------------------------------------------------+  |
|  |                                  AUTONOMOUS MOBILE ROBOT (AMR-01/02/03)                         |  |
|  |                                                                                                 |  |
|  |  [360° LiDAR & RGB-D Camera]  ->  [Extended Kalman Filter (EKF)]  ->  [Estimated Pose x, y, θ]  |  |
|  |                                                                                |                |  |
|  |  [Global A* Planner (Waypoints)]  <--------------------------------------------+                |  |
|  |                |                                                                                |  |
|  |                v                                                                                |  |
|  |  [Dynamic Window Approach (DWA Local Planner)]  ->  [Kinematics & RK4 Integrator]               |  |
|  |                ^                                                    |                           |  |
|  |                |                                                    v                           |  |
|  |  [5-Tier Deadlock Recovery Tree]                      [Diff-Drive Velocities v, ω]              |  |
|  |                                                                     |                           |  |
|  |  [LiFePO4 Battery Model & Autonomous Docking]  <--------------------+                           |  |
|  |  [Automated Scissor Lifter & Pallet Handler]                                                    |  |
|  +-------------------------------------------------------------------------------------------------+  |
+--------------------------------------------------+----------------------------------------------------+
                                                   |  JSON Telemetry (12.5 Hz)
                                                   v
+-------------------------------------------------------------------------------------------------------+
|                               3D DIGITAL TWIN WEB APPLICATION (THREE.JS)                              |
|                                                                                                       |
|  - CAD-Grade 3D AMR Robot (Chassis, Scissor Lifter, Wheels, Spinning LiDAR, Halo Safety Light Ring)  |
|  - Photorealistic Industrial Warehouse (Pallet Racks, Charging Bays, Loading Docks A/B, Crosswalks) |
|  - Real-Time Sensor Overlays (LiDAR Point Cloud, Laser Ray Fan, A* Ribbon, DWA Prediction Cones)     |
|  - Multi-Camera Views: 3D Orbit, Top-Down Tactical, AMR Chase Cam, Front LiDAR Sensor POV           |
|  - Cockpit Dashboard: Battery % Gauges, Odometer, Velocity, Task Queue, D-Pad Manual Teleoperation    |
+-------------------------------------------------------------------------------------------------------+
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** (Tested with Python 3.11)
- Standard web browser (Chrome, Edge, Firefox)

### 2. Run with One Click
Simply double-click:
```powershell
run_simulation.bat
```
Or run from terminal:
```powershell
python run_simulation.py
```

This will automatically:
1. Initialize the background simulation engine, EKF, dynamic costmap, and AMR fleet.
2. Launch the Flask REST API on `http://127.0.0.1:5000`.
3. Open your default web browser directly to the **3D Digital Twin Fleet Command Cockpit**.

---

## 🧠 Google Gemini API Integration

The system natively integrates the **Google Gemini API** (`gemini-2.5-flash`) to act as the Central AI Fleet Intelligence Officer.

### How to Configure API Key:
1. Obtain a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Either add it to your `.env` file:
   ```env
   GEMINI_API_KEY=your_actual_key_here
   ```
   **OR** enter it directly in the top-right **Gemini AI Commander** input box on the live web dashboard and click **Save**.

### Capabilities of the Gemini AI Agent:
- **Semantic Mission Dispatching**: Type instructions like:
  - *"Rush order: Dispatch AMR-01 to pick up pallet at Inbound Dock A and deliver to Storage Rack C2 immediately."*
  - *"Spill detected in Aisle 2, reroute all robots through perimeter corridor."*
- **Deadlock Diagnosis & Anomaly Resolution**: When an AMR encounters a persistent stall, the full telemetry context (nearby obstacles, battery SOC, sensor scans) is evaluated by Gemini to output root-cause recovery maneuvers.
- **Battery Fleet Optimization**: Gemini analyzes battery discharge curves to recommend optimal inductive charging windows before peak shift hours.
- **Offline Heuristic Fallback**: If no API key is provided, the built-in heuristic expert engine automatically parses commands and runs all autonomous operations locally.

---

## 🎮 Interactive Controls & Features in the 3D Cockpit

- **Camera Switcher**:
  - `🎥 3D Orbit`: Full 360° free rotation, pan (right click / two fingers), and zoom.
  - `🛰️ Top-Down Tactical`: Orthographic 2D/3D overhead view of the entire warehouse.
  - `🤖 AMR Chase Cam`: Follow-cam tracking behind the selected robot.
  - `👁️ LiDAR Depth POV`: First-person forward-facing view from the robot's front bumper.
- **Manual Teleoperation (WASD)**:
  - Select any AMR in the left panel and drive using **W, A, S, D** or arrow keys, or the on-screen D-Pad.
- **Dynamic Obstacle Injection**:
  - Click `+ Spawn Worker` to inject a moving human pedestrian across warehouse aisles.
  - Click `+ Spawn Heavy Forklift` to inject heavy industrial traffic.
  - Watch the AMRs dynamically slow down, reroute, or execute 5-tier recovery behaviors!
- **Emergency Stop (E-STOP)**:
  - Click `🛑 E-STOP FLEET` in the top header to instantly freeze all robot drive systems.

---

## 📂 Project Structure

```
AMR/
├── server.py                        # Centralized Fleet Manager, REST API & Simulation Engine
├── config.py                        # Warehouse, AMR, and Sensor configuration parameters
├── requirements.txt                 # Dependencies (flask, flask-cors, numpy, scipy, requests)
├── run_simulation.py                # Launch script (starts backend & opens 3D Digital Twin)
├── run_simulation.bat               # Windows 1-click batch launcher
├── .env.example                     # Environment template
│
├── core/                            # Core Autonomous Robotics Algorithms
│   ├── kinematics.py                # Differential drive kinematics, wheel odometry & RK4
│   ├── sensor_fusion.py             # EKF (Extended Kalman Filter) & LiDAR raycaster
│   ├── costmap.py                   # Dynamic 2D Occupancy Grid & Obstacle Inflation layer
│   ├── path_planner.py              # Global Path Planning (Cost-aware A* with smoothing)
│   ├── local_planner.py             # Dynamic Window Approach (DWA) dynamic obstacle avoidance
│   ├── fleet_manager.py             # Multi-AMR Task Allocation & Right-of-Way Arbitration
│   ├── recovery_system.py           # 5-tier Deadlock Detection & Behavior Tree Recovery
│   ├── battery_manager.py           # LiFePO4 battery model & Autonomous Charging Station manager
│   ├── material_handler.py          # Pallet pickup, lifter mechanism state machine & RFID
│   ├── gemini_ai_agent.py           # Google Gemini API integration for semantic fleet reasoning
│   └── amr_agent.py                 # Integrated AMR robot agent class
│
├── ros2_nodes/                      # Production-ready ROS 2 / Nav2 nodes
│   ├── amr_navigation_node.py       # ROS 2 node wrapping navigation, costmap & sensor fusion
│   ├── dynamic_obstacle_node.py     # ROS 2 node for LiDAR obstacle detection & tracking
│   ├── fleet_coordination_node.py   # ROS 2 multi-robot fleet communications
│   └── amr_robot.urdf               # Full URDF 3D robot model description
│
└── static/                          # 3D Digital Twin & Centralized Control Web Application
    ├── index.html                   # Centralized Fleet Control Station HTML5 Cockpit
    ├── css/
    │   └── dashboard.css            # Futuristic Industrial HUD styling
    └── js/
        ├── app.js                   # Main application orchestration & UI event handling
        ├── amr_3d_model.js          # Procedural high-detail 3D AMR CAD Model
        ├── warehouse_scene.js       # 3D Warehouse environment (Racks, Pallets, Chargers)
        ├── sensor_visualizer.js     # 3D LiDAR point cloud, laser rays, costmap & path ribbons
        └── gemini_chat.js           # Interactive AI Fleet Commander UI
```

---

## 📜 License
Developed for Industrial Autonomous Logistics Research & Demonstration. Released under the MIT License.

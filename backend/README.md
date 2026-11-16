# ⚙️ Industrial AMR Fleet Management Engine (Backend)

This directory contains the central robotics simulation server, multi-agent fleet orchestrator, and Google Gemini AI Agent integration.

## Folder Contents
- `server.py`: Flask application hosting the 12.5 Hz background simulation loop and REST APIs (`/api/state`, `/api/task/create`, `/api/amr/command`, `/api/ai/command`).
- `config.py`: Warehouse map dimensions, physics constraints, battery specs, and sensor parameters.
- `core/`:
  - `kinematics.py`: Differential drive kinematics & 4th-Order Runge-Kutta numerical integrator.
  - `sensor_fusion.py`: Extended Kalman Filter (EKF) and 360° planar LiDAR raycaster.
  - `costmap.py`: 2D Occupancy Grid with Euclidean Distance Transform (EDT) obstacle inflation.
  - `path_planner.py`: Cost-aware A* global path planner with line-of-sight shortcutting.
  - `local_planner.py`: Dynamic Window Approach (DWA) with dynamic obstacle velocity prediction.
  - `fleet_manager.py`: Auction-based task allocation and right-of-way conflict resolution.
  - `recovery_system.py`: 5-Tier hierarchical deadlock recovery behavior tree.
  - `battery_manager.py`: LiFePO4 battery discharge model and autonomous charging station coordinator.
  - `material_handler.py`: Automated scissor lift mechanism state machine and RFID payload tracker.
  - `gemini_ai_agent.py`: Google Gemini API integration for semantic fleet reasoning.
  - `amr_agent.py`: Integrated AMR robot instance bringing all subsystems together.
- `ros2_nodes/`: Production ROS 2 Humble/Iron/Jazzy compliant nodes and `amr_robot.urdf`.

## Launching Backend
```powershell
python backend/server.py
```
Or from root:
```powershell
python run_simulation.py
```

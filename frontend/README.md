# 🎨 Industrial AMR 3D Digital Twin (Frontend)

This directory contains the standalone WebGL 3D Digital Twin and Fleet Command user interface built with **Three.js**.

## Folder Contents
- `index.html`: Main HTML5 cockpit structure.
- `css/dashboard.css`: Cyber-industrial dark HUD styling, responsive glassmorphism panels.
- `js/app.js`: Master orchestrator, Three.js renderer, telemetry poller, and camera controllers.
- `js/amr_3d_model.js`: CAD-grade procedural 3D AMR model with chassis, wheels, animated scissor lift, spinning LiDAR turret, and halo safety LED ring.
- `js/warehouse_scene.js`: 3D warehouse environment with epoxy floor, pallet storage racks, loading docks A & B, inductive charging bays, dynamic human workers, and forklifts.
- `js/sensor_visualizer.js`: 3D LiDAR point cloud renderer, laser scan rays, global A* path ribbons, and DWA prediction cones.
- `js/gemini_chat.js`: Interactive Google Gemini AI supervisor commander panel.

## Usage
Can be served directly via Flask backend or any standard static web server (e.g. `npx serve frontend` or VS Code Live Server).

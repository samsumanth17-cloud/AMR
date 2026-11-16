"""
Flask REST API and High-Performance Background Simulation Server
Orchestrates Multi-AMR Fleet, Dynamic Obstacles, Costmaps, SQLite Database, and Google Gemini AI Agent.
"""

import os
import sys
import time
import math
import io
import csv
import threading
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS

from config import (
    SERVER_HOST, SERVER_PORT, MAP_WIDTH, MAP_HEIGHT, GRID_RESOLUTION,
    COSTMAP_INFLATION_RADIUS, INFRASTRUCTURE, DEFAULT_FLEET, DYNAMIC_OBSTACLES,
    GEMINI_API_KEY
)
from core import Costmap2D, AMR, Pallet, Task, FleetCoordinator, GeminiFleetAgent
from core.database import WarehouseDatabase

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

class WarehouseSimulationEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = True
        self.dt = 0.08 # ~12.5 Hz simulation loop
        self.sim_time = 0.0
        self.last_db_log_time = 0.0

        # 1. Database
        self.db = WarehouseDatabase()

        # 2. Costmap
        self.costmap = Costmap2D(
            width_m=MAP_WIDTH,
            height_m=MAP_HEIGHT,
            resolution=GRID_RESOLUTION,
            inflation_radius=COSTMAP_INFLATION_RADIUS
        )
        self.costmap.initialize_static_map(INFRASTRUCTURE["storage_racks"])

        # 3. Robots
        self.amrs = {}
        for cfg in DEFAULT_FLEET:
            amr = AMR(
                amr_id=cfg["id"],
                name=cfg["name"],
                color=cfg["color"],
                initial_pose=cfg["initial_pose"],
                battery_soc=cfg["battery"],
                payload_capacity_kg=cfg["payload_capacity_kg"],
                role=cfg["role"],
                costmap=self.costmap
            )
            self.amrs[amr.id] = amr

        # 4. Dynamic Obstacles (Pedestrians, Forklifts)
        self.dynamic_obstacles = []
        for obs in DYNAMIC_OBSTACLES:
            self.dynamic_obstacles.append({
                "id": obs["id"],
                "type": obs["type"],
                "name": obs["name"],
                "x": obs["x"],
                "y": obs["y"],
                "speed": obs["speed"],
                "radius": obs["radius"],
                "waypoints": obs["waypoints"],
                "wp_index": 0,
                "vx": 0.0,
                "vy": 0.0
            })

        # 5. Pallets in Warehouse
        self.pallets = [
            Pallet("PALLET_101", "SKU-ELEC-404", 280, [46.0, 6.0],  [12.0, 6.0],  priority=2),
            Pallet("PALLET_102", "SKU-AUTO-890", 350, [46.0, 6.0],  [26.0, 6.0],  priority=1),
            Pallet("PALLET_103", "SKU-PHAR-112", 120, [7.0, 15.0],  [46.0, 24.0], priority=3),
            Pallet("PALLET_104", "SKU-FOOD-331", 200, [18.0, 18.0], [40.0, 15.0], priority=1),
        ]

        # 6. Fleet Coordinator
        self.fleet_coordinator = FleetCoordinator(list(self.amrs.values()))

        # 7. Gemini AI Agent
        self.gemini_agent = GeminiFleetAgent(api_key=GEMINI_API_KEY)

        # 8. Metrics & Event Log
        self.event_log = []
        self.completed_delivery_count = 0

        # Enqueue initial missions & save to DB
        t1 = Task("TASK-001", self.pallets[0], priority=2)
        t2 = Task("TASK-002", self.pallets[2], priority=3)
        self.fleet_coordinator.add_task(t1)
        self.fleet_coordinator.add_task(t2)
        self.db.upsert_mission(t1)
        self.db.upsert_mission(t2)
        self.log_event("SYSTEM", "Warehouse Engine & SQLite Database initialized successfully.")

    def log_event(self, category, message, amr_id=None, severity="INFO"):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "category": category, # NAV, TASK, BATTERY, AI, SAFETY, MANUAL
            "message": message,
            "amr_id": amr_id
        }
        self.event_log.insert(0, entry)
        if len(self.event_log) > 100:
            self.event_log.pop()
        self.db.log_event(category, amr_id, message, severity)

    def update_dynamic_obstacles(self):
        """Move simulated workers and forklifts along patrol routes."""
        for obs in self.dynamic_obstacles:
            wps = obs["waypoints"]
            target_wp = wps[obs["wp_index"]]
            dx = target_wp[0] - obs["x"]
            dy = target_wp[1] - obs["y"]
            dist = math.hypot(dx, dy)

            if dist < 0.5:
                obs["wp_index"] = (obs["wp_index"] + 1) % len(wps)
                target_wp = wps[obs["wp_index"]]
                dx = target_wp[0] - obs["x"]
                dy = target_wp[1] - obs["y"]
                dist = math.hypot(dx, dy)

            if dist > 0.05:
                speed = obs["speed"]
                vx = (dx / dist) * speed
                vy = (dy / dist) * speed
                obs["x"] += vx * self.dt
                obs["y"] += vy * self.dt
                obs["vx"] = vx
                obs["vy"] = vy
            else:
                obs["vx"] = 0.0
                obs["vy"] = 0.0

    def step(self):
        with self.lock:
            self.sim_time += self.dt

            # 1. Update dynamic obstacles
            self.update_dynamic_obstacles()

            # 2. Update dynamic costmap ONLY with external obstacles (workers, forklifts)
            # AMRs are avoided dynamically by DWA velocity obstacles to prevent self-collision locks!
            dynamic_colliders = []
            for obs in self.dynamic_obstacles:
                dynamic_colliders.append({"x": obs["x"], "y": obs["y"], "radius": obs["radius"]})

            self.costmap.update_dynamic_obstacles(dynamic_colliders)

            # 3. Inter-robot conflict resolution & task allocation
            self.fleet_coordinator.arbitrate_traffic_conflicts()
            self.fleet_coordinator.allocate_pending_tasks()

            # 4. Step each AMR
            for amr_id, amr in self.amrs.items():
                # Filter peer AMRs for local DWA avoidance
                other_obstacles = [o for o in self.dynamic_obstacles]
                for other_id, other_amr in self.amrs.items():
                    if other_id != amr_id:
                        other_obstacles.append({
                            "id": other_id,
                            "type": "amr",
                            "name": other_amr.name,
                            "x": other_amr.pose[0],
                            "y": other_amr.pose[1],
                            "radius": 0.6,
                            "vx": other_amr.velocity[0] * math.cos(other_amr.pose[2]),
                            "vy": other_amr.velocity[0] * math.sin(other_amr.pose[2])
                        })

                prev_status = amr.status
                amr.update(other_obstacles, self.dt)

                # Check state changes for logging
                if prev_status != amr.status:
                    self.log_event("NAV", f"{amr.name} state changed: {prev_status} -> {amr.status}", amr.id)

            # 5. Periodic Database Telemetry Logging (1 Hz)
            if self.sim_time - self.last_db_log_time >= 1.0:
                self.last_db_log_time = self.sim_time
                for amr in self.amrs.values():
                    self.db.log_telemetry(amr.to_telemetry(), self.sim_time)
                for task in self.fleet_coordinator.task_queue:
                    self.db.upsert_mission(task)

    def run_loop(self):
        while self.running:
            start_t = time.time()
            self.step()
            elapsed = time.time() - start_t
            sleep_t = max(0.005, self.dt - elapsed)
            time.sleep(sleep_t)


# Initialize simulation engine
engine = WarehouseSimulationEngine()
sim_thread = threading.Thread(target=engine.run_loop, daemon=True)
sim_thread.start()


# --- HTTP Routes ---

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/state", methods=["GET"])
def get_state():
    with engine.lock:
        telemetry = [amr.to_telemetry() for amr in engine.amrs.values()]
        pallets_data = [p.to_dict() for p in engine.pallets]
        tasks_data = [t.to_dict() for t in engine.fleet_coordinator.task_queue]

        response = {
            "timestamp": round(time.time(), 2),
            "sim_time": round(engine.sim_time, 1),
            "fleet": telemetry,
            "dynamic_obstacles": engine.dynamic_obstacles,
            "pallets": pallets_data,
            "tasks": tasks_data,
            "infrastructure": INFRASTRUCTURE,
            "events": engine.event_log[:25],
            "ai_configured": engine.gemini_agent.is_configured(),
            "ai_model": engine.gemini_agent.model
        }
    return jsonify(response)

@app.route("/api/task/create", methods=["POST"])
def create_task():
    data = request.json or {}
    pickup = data.get("pickup", [46.0, 6.0])
    dropoff = data.get("dropoff", [18.0, 18.0])
    sku = data.get("sku", f"SKU-EXPR-{int(time.time()) % 1000}")
    weight = float(data.get("weight_kg", 250))
    priority = int(data.get("priority", 1))

    with engine.lock:
        new_pallet = Pallet(f"PALLET_{int(time.time()) % 10000}", sku, weight, pickup, dropoff, priority)
        engine.pallets.append(new_pallet)
        new_task = Task(f"TASK-{int(time.time()) % 10000}", new_pallet, priority)
        engine.fleet_coordinator.add_task(new_task)
        engine.db.upsert_mission(new_task)
        engine.log_event("TASK", f"Created Task {new_task.id} (Priority {priority})")

    return jsonify({"success": True, "task_id": new_task.id})

@app.route("/api/amr/command", methods=["POST"])
def amr_command():
    data = request.json or {}
    amr_id = data.get("amr_id")
    cmd_type = data.get("command")

    with engine.lock:
        if amr_id == "ALL":
            target_amrs = list(engine.amrs.values())
        elif amr_id in engine.amrs:
            target_amrs = [engine.amrs[amr_id]]
        else:
            return jsonify({"error": "AMR not found"}), 404

        for amr in target_amrs:
            if cmd_type == "ESTOP":
                amr.status = "ESTOP"
                engine.log_event("SAFETY", f"EMERGENCY STOP issued to {amr.id}", amr.id, "CRITICAL")
            elif cmd_type == "RESUME":
                if amr.status == "ESTOP":
                    amr.status = "IDLE"
                    amr.set_control_mode("AUTONOMOUS")
                    engine.log_event("SAFETY", f"{amr.id} resumed from E-STOP", amr.id)
            elif cmd_type == "CHARGE":
                amr.set_control_mode("AUTONOMOUS")
                amr._route_to_charging_station("Manual charge override")
                engine.log_event("BATTERY", f"{amr.id} routed to charging station", amr.id)
            elif cmd_type == "TELEOP":
                v = float(data.get("v", 0.0))
                w = float(data.get("w", 0.0))
                amr.set_manual_teleop(v, w)
            elif cmd_type == "LIFT":
                action = data.get("action", "RAISE")
                amr.manual_lift(action)
                engine.log_event("MANUAL", f"{amr.id} Scissor lift manual command: {action}", amr.id)
            elif cmd_type == "MODE":
                mode = data.get("mode", "AUTONOMOUS")
                amr.set_control_mode(mode)
                engine.log_event("MANUAL", f"{amr.id} mode switched to {mode}", amr.id)

    return jsonify({"success": True})

@app.route("/api/amr/mode", methods=["POST"])
def set_amr_mode():
    data = request.json or {}
    amr_id = data.get("amr_id")
    mode = data.get("mode", "AUTONOMOUS")

    with engine.lock:
        if amr_id in engine.amrs:
            engine.amrs[amr_id].set_control_mode(mode)
            engine.log_event("MANUAL", f"{amr_id} Mode set to {mode}", amr_id)
            return jsonify({"success": True, "amr_id": amr_id, "mode": mode})
        return jsonify({"error": "AMR not found"}), 404

@app.route("/api/amr/lifter", methods=["POST"])
def set_amr_lifter():
    data = request.json or {}
    amr_id = data.get("amr_id")
    action = data.get("action", "RAISE")

    with engine.lock:
        if amr_id in engine.amrs:
            engine.amrs[amr_id].manual_lift(action)
            engine.log_event("MANUAL", f"{amr_id} Lifter set to {action}", amr_id)
            return jsonify({"success": True, "amr_id": amr_id, "action": action})
        return jsonify({"error": "AMR not found"}), 404

# --- Database API Routes ---

@app.route("/api/db/telemetry", methods=["GET"])
def get_db_telemetry():
    amr_id = request.args.get("amr_id", "ALL")
    limit = int(request.args.get("limit", 60))
    rows = engine.db.get_recent_telemetry(amr_id, limit)
    return jsonify({"success": True, "data": rows})

@app.route("/api/db/missions", methods=["GET"])
def get_db_missions():
    limit = int(request.args.get("limit", 50))
    rows = engine.db.get_missions(limit)
    return jsonify({"success": True, "data": rows})

@app.route("/api/db/events", methods=["GET"])
def get_db_events():
    limit = int(request.args.get("limit", 100))
    cat = request.args.get("category", "ALL")
    rows = engine.db.get_events(limit, cat)
    return jsonify({"success": True, "data": rows})

@app.route("/api/db/analytics", methods=["GET"])
def get_db_analytics():
    stats = engine.db.get_analytics_summary()
    with engine.lock:
        total_dist = sum(a.total_distance_traveled for a in engine.amrs.values())
        avg_battery = sum(a.battery_subsystem.soc for a in engine.amrs.values()) / max(1, len(engine.amrs))
        stats["total_distance_m"] = round(total_dist, 1)
        stats["avg_battery_soc"] = round(avg_battery, 1)
        stats["active_fleet_count"] = len(engine.amrs)
    return jsonify({"success": True, "analytics": stats})

@app.route("/api/db/export", methods=["GET"])
def export_db_table():
    table = request.args.get("table", "telemetry")
    output = io.StringIO()
    writer = csv.writer(output)

    if table == "missions":
        rows = engine.db.get_missions(500)
        if rows:
            writer.writerow(rows[0].keys())
            for r in rows:
                writer.writerow(r.values())
    elif table == "events":
        rows = engine.db.get_events(500)
        if rows:
            writer.writerow(rows[0].keys())
            for r in rows:
                writer.writerow(r.values())
    else:
        rows = engine.db.get_recent_telemetry("ALL", 500)
        if rows:
            writer.writerow(rows[0].keys())
            for r in rows:
                writer.writerow(r.values())

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=amr_{table}_export.csv"}
    )

@app.route("/api/obstacle/spawn", methods=["POST"])
def spawn_obstacle():
    data = request.json or {}
    obs_id = f"DYN_{int(time.time()) % 1000}"
    x = float(data.get("x", 20.0))
    y = float(data.get("y", 15.0))
    obs_type = data.get("type", "worker")
    radius = 1.2 if obs_type == "forklift" else 0.45

    with engine.lock:
        engine.dynamic_obstacles.append({
            "id": obs_id,
            "type": obs_type,
            "name": f"Dynamic {obs_type.title()} {obs_id}",
            "x": x,
            "y": y,
            "speed": 0.8 if obs_type == "forklift" else 0.6,
            "radius": radius,
            "waypoints": [[x, y], [x + 8.0, y], [x, y]],
            "wp_index": 0,
            "vx": 0.0,
            "vy": 0.0
        })
        engine.log_event("SAFETY", f"Dynamic obstacle spawned: {obs_type} at ({x}, {y})")

    return jsonify({"success": True, "id": obs_id})

@app.route("/api/ai/command", methods=["POST"])
def ai_command():
    data = request.json or {}
    user_prompt = data.get("prompt", "")

    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    with engine.lock:
        telemetry = [amr.to_telemetry() for amr in engine.amrs.values()]

    result = engine.gemini_agent.process_supervisor_command(user_prompt, telemetry)

    if result.get("intent") == "NEW_MISSION" and result.get("pickup_location") and result.get("dropoff_location"):
        pickup = result["pickup_location"]
        dropoff = result["dropoff_location"]
        priority = result.get("priority", 1)

        with engine.lock:
            new_pallet = Pallet(
                f"AI_PALLET_{int(time.time()) % 1000}",
                "SKU-AI-LOGIST",
                250,
                pickup,
                dropoff,
                priority
            )
            engine.pallets.append(new_pallet)
            task = Task(f"AI-TASK-{int(time.time()) % 1000}", new_pallet, priority)
            engine.fleet_coordinator.add_task(task)
            engine.db.upsert_mission(task)
            engine.log_event("AI", f"Gemini AI Dispatched Task {task.id}: {result.get('reasoning')}")

    elif result.get("intent") == "ESTOP":
        with engine.lock:
            for amr in engine.amrs.values():
                amr.status = "ESTOP"
            engine.log_event("AI", "Gemini AI triggered EMERGENCY STOP for entire fleet", severity="CRITICAL")

    elif result.get("intent") == "CHARGE_NOW":
        target = result.get("assigned_amr", "AMR-01")
        with engine.lock:
            if target in engine.amrs:
                engine.amrs[target]._route_to_charging_station("Gemini AI Charge Directive")
                engine.log_event("AI", f"Gemini AI routed {target} to charge: {result.get('reasoning')}")

    return jsonify({"success": True, "result": result})

@app.route("/api/ai/configure", methods=["POST"])
def ai_configure():
    data = request.json or {}
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "").strip()

    if api_key:
        engine.gemini_agent.set_api_key(api_key)
    if model:
        engine.gemini_agent.model = model

    engine.log_event("AI", f"Gemini AI key updated. Configured: {engine.gemini_agent.is_configured()}")
    return jsonify({
        "success": True,
        "is_configured": engine.gemini_agent.is_configured(),
        "model": engine.gemini_agent.model
    })

if __name__ == "__main__":
    print(f"============================================================")
    print(f" INDUSTRIAL AMR DIGITAL TWIN & FLEET SIMULATOR")
    print(f" SQLite Database Connected: {engine.db.db_path}")
    print(f" Server starting on http://{SERVER_HOST}:{SERVER_PORT}")
    print(f" Gemini AI Status: {'Configured' if engine.gemini_agent.is_configured() else 'Local Heuristic Mode'}")
    print(f"============================================================")
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, use_reloader=False)

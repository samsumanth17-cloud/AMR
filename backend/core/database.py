"""
SQLite Database and Historical Telemetry Storage Engine for Industrial AMR
Maintains persistent records of AMR telemetry, logistics missions, system events,
charging cycles, and deadlock recovery incidents.
"""

import os
import sqlite3
import time
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "warehouse_amr.db")

class WarehouseDatabase:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Telemetry Log Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    datetime_str TEXT,
                    sim_time REAL,
                    amr_id TEXT,
                    x REAL,
                    y REAL,
                    theta REAL,
                    v REAL,
                    w REAL,
                    battery_soc REAL,
                    voltage REAL,
                    status TEXT,
                    lifter_height REAL,
                    payload_id TEXT,
                    total_distance_m REAL
                )
            """)

            # 2. Logistics Missions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE,
                    pallet_id TEXT,
                    sku TEXT,
                    weight_kg REAL,
                    priority INTEGER,
                    pickup_x REAL,
                    pickup_y REAL,
                    dropoff_x REAL,
                    dropoff_y REAL,
                    assigned_amr TEXT,
                    status TEXT,
                    created_at REAL,
                    completed_at REAL,
                    duration_s REAL
                )
            """)

            # 3. System Events Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    datetime_str TEXT,
                    category TEXT,
                    amr_id TEXT,
                    message TEXT,
                    severity TEXT
                )
            """)

            # 4. Charging Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS charging_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amr_id TEXT,
                    station_id TEXT,
                    start_time REAL,
                    end_time REAL,
                    start_soc REAL,
                    end_soc REAL,
                    energy_wh REAL
                )
            """)

            # 5. Deadlock & Anomaly Incidents Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deadlock_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amr_id TEXT,
                    timestamp REAL,
                    datetime_str TEXT,
                    location_x REAL,
                    location_y REAL,
                    tier_escalated TEXT,
                    resolution TEXT
                )
            """)

            # Create indices for fast querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_amr ON telemetry_logs (amr_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events_log (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_missions_status ON missions (status)")
            conn.commit()

    def log_telemetry(self, amr_data, sim_time):
        """Record AMR telemetry point."""
        try:
            now = time.time()
            dt_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
            pose = amr_data.get("pose", [0.0, 0.0, 0.0])
            vel = amr_data.get("velocity", [0.0, 0.0])
            pallet = amr_data.get("carrying_pallet")
            payload_id = pallet.get("id") if pallet else None

            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO telemetry_logs (
                        timestamp, datetime_str, sim_time, amr_id, x, y, theta,
                        v, w, battery_soc, voltage, status, lifter_height,
                        payload_id, total_distance_m
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now, dt_str, sim_time, amr_data.get("id"),
                    pose[0], pose[1], pose[2], vel[0], vel[1],
                    amr_data.get("battery", 100.0), amr_data.get("voltage", 24.0),
                    amr_data.get("status", "IDLE"), amr_data.get("lifter_height", 0.0),
                    payload_id, amr_data.get("total_distance_m", 0.0)
                ))
                conn.commit()
        except Exception as e:
            pass

    def upsert_mission(self, task):
        """Insert or update mission state."""
        try:
            pallet = task.pallet
            pallet_id = pallet.id if pallet else None
            sku = pallet.sku if pallet else None
            weight_kg = pallet.weight_kg if pallet else 0.0
            pickup_x = pallet.pickup_x if pallet else 0.0
            pickup_y = pallet.pickup_y if pallet else 0.0
            dropoff_x = pallet.dropoff_x if pallet else 0.0
            dropoff_y = pallet.dropoff_y if pallet else 0.0
            
            duration_s = (task.completed_at - task.created_at) if task.completed_at else None

            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO missions (
                        task_id, pallet_id, sku, weight_kg, priority,
                        pickup_x, pickup_y, dropoff_x, dropoff_y,
                        assigned_amr, status, created_at, completed_at, duration_s
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        assigned_amr = excluded.assigned_amr,
                        status = excluded.status,
                        completed_at = excluded.completed_at,
                        duration_s = excluded.duration_s
                """, (
                    task.id, pallet_id, sku, weight_kg, task.priority,
                    pickup_x, pickup_y, dropoff_x, dropoff_y,
                    task.assigned_amr, task.status, task.created_at,
                    task.completed_at, duration_s
                ))
                conn.commit()
        except Exception as e:
            pass

    def log_event(self, category, amr_id, message, severity="INFO"):
        """Record operational event."""
        try:
            now = time.time()
            dt_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO events_log (timestamp, datetime_str, category, amr_id, message, severity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (now, dt_str, category, amr_id, message, severity))
                conn.commit()
        except Exception as e:
            pass

    def log_deadlock_incident(self, amr_id, x, y, tier, resolution):
        """Record deadlock recovery incident."""
        try:
            now = time.time()
            dt_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO deadlock_incidents (amr_id, timestamp, datetime_str, location_x, location_y, tier_escalated, resolution)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (amr_id, now, dt_str, x, y, tier, resolution))
                conn.commit()
        except Exception as e:
            pass

    def get_recent_telemetry(self, amr_id=None, limit=100):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if amr_id and amr_id != "ALL":
                cursor.execute("""
                    SELECT * FROM telemetry_logs WHERE amr_id = ?
                    ORDER BY id DESC LIMIT ?
                """, (amr_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM telemetry_logs ORDER BY id DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_missions(self, limit=50):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM missions ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_events(self, limit=100, category=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category and category != "ALL":
                cursor.execute("SELECT * FROM events_log WHERE category = ? ORDER BY id DESC LIMIT ?", (category, limit))
            else:
                cursor.execute("SELECT * FROM events_log ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_analytics_summary(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Missions count
            cursor.execute("SELECT count(*) as total, sum(case when status='COMPLETED' then 1 else 0 end) as completed FROM missions")
            mission_row = cursor.fetchone()
            total_missions = mission_row["total"] or 0
            completed_missions = mission_row["completed"] or 0

            # Total telemetry count
            cursor.execute("SELECT count(*) as count FROM telemetry_logs")
            telemetry_count = cursor.fetchone()["count"] or 0

            # Deadlocks count
            cursor.execute("SELECT count(*) as count FROM deadlock_incidents")
            deadlock_count = cursor.fetchone()["count"] or 0

            # Events count
            cursor.execute("SELECT count(*) as count FROM events_log")
            event_count = cursor.fetchone()["count"] or 0

            return {
                "total_missions": total_missions,
                "completed_missions": completed_missions,
                "telemetry_records": telemetry_count,
                "deadlock_events": deadlock_count,
                "total_events": event_count,
                "db_status": "ONLINE",
                "db_size_kb": round(os.path.getsize(self.db_path) / 1024.0, 1) if os.path.exists(self.db_path) else 0.0
            }

"""
Battery Dynamics and Autonomous Charging Station Manager for Industrial AMR
Implements real-time SOC tracking, power consumption physics, and automated charging scheduling.
"""

import math
from config import BATTERY_CONFIG, INFRASTRUCTURE

class BatterySubsystem:
    def __init__(self, initial_soc=100.0, capacity_wh=None):
        self.capacity_wh = capacity_wh or BATTERY_CONFIG["capacity_wh"]
        self.nominal_voltage = BATTERY_CONFIG["nominal_voltage"]
        self.soc = float(initial_soc) # Percentage 0 - 100%
        
        self.idle_power = BATTERY_CONFIG["idle_power_w"]
        self.motion_power_coeff = BATTERY_CONFIG["motion_power_per_mps_w"]
        self.payload_power_coeff = BATTERY_CONFIG["payload_power_w_per_kg"]
        self.charging_power = BATTERY_CONFIG["charging_power_w"]

        self.critical_soc = BATTERY_CONFIG["critical_threshold"]
        self.warning_soc = BATTERY_CONFIG["warning_threshold"]
        self.full_soc = BATTERY_CONFIG["full_threshold"]

        self.is_charging = False
        self.assigned_station = None
        self.voltage = self.nominal_voltage

    def update(self, v, w, payload_kg, is_docked_at_charger, dt):
        """
        Calculates power consumption or charging replenishment over dt (seconds).
        Returns current SOC, voltage, and instantaneous power (Watts).
        """
        if is_docked_at_charger:
            self.is_charging = True
            # Charging dynamics (Taper current above 85%)
            effective_power = self.charging_power
            if self.soc > 85.0:
                effective_power *= max(0.2, (100.0 - self.soc) / 15.0)

            energy_added_wh = (effective_power * dt) / 3600.0
            self.soc = min(100.0, self.soc + (energy_added_wh / self.capacity_wh) * 100.0)
            self.voltage = self.nominal_voltage + 2.0 * (self.soc / 100.0)
            return round(self.soc, 2), round(self.voltage, 2), -round(effective_power, 1)

        self.is_charging = False
        # Discharge dynamics
        p_idle = self.idle_power
        p_motion = self.motion_power_coeff * (abs(v) + 0.3 * abs(w))
        p_payload = self.payload_power_coeff * payload_kg * (1.0 if abs(v) > 0.05 else 0.1)

        p_total = p_idle + p_motion + p_payload
        energy_consumed_wh = (p_total * dt) / 3600.0
        self.soc = max(0.0, self.soc - (energy_consumed_wh / self.capacity_wh) * 100.0)

        # Voltage curve based on discharge
        self.voltage = max(20.0, self.nominal_voltage - 2.5 * (1.0 - self.soc / 100.0))
        return round(self.soc, 2), round(self.voltage, 2), round(p_total, 1)

    def is_critical(self):
        return self.soc <= self.critical_soc

    def needs_charge(self):
        return self.soc <= self.warning_soc

    def is_fully_charged(self):
        return self.soc >= self.full_soc


class ChargingStationFleetCoordinator:
    """Manages multi-robot charging queue and bay allocations."""
    def __init__(self, stations=None):
        self.stations = stations or INFRASTRUCTURE["charging_stations"]

    def request_station(self, robot_id):
        """Allocate nearest available charging bay for robot."""
        for station in self.stations:
            if station.get("occupied_by") is None or station.get("occupied_by") == robot_id:
                station["occupied_by"] = robot_id
                return station
        return None

    def release_station(self, robot_id):
        for station in self.stations:
            if station.get("occupied_by") == robot_id:
                station["occupied_by"] = None

    def get_station_coords(self, station_id):
        for station in self.stations:
            if station["id"] == station_id:
                return station["x"], station["y"]
        return None

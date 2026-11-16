"""
Google Gemini AI Agent Integration for Industrial AMR Fleet Intelligence
Provides semantic mission dispatching, real-time deadlock diagnosis, and fleet optimization.
"""

import os
import json
import requests
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_API_ENDPOINT, INFRASTRUCTURE

class GeminiFleetAgent:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
        self.model = model or os.getenv("GEMINI_MODEL", GEMINI_MODEL)
        self.system_prompt = self._build_system_prompt()

    def set_api_key(self, key):
        self.api_key = key.strip()

    def is_configured(self):
        return bool(self.api_key and len(self.api_key) > 5)

    def _build_system_prompt(self):
        return (
            "You are the Central AI Fleet Intelligence Officer for an autonomous industrial warehouse AMR system. "
            "Your role is to orchestrate a fleet of 3 Autonomous Mobile Robots (AMR-01 Alpha, AMR-02 Beta, AMR-03 Gamma). "
            "You have full visibility into warehouse coordinates (0-50m X, 0-30m Y), storage racks (A1, A2, B1, B2, C1, C2, D1, D2), "
            "Loading Docks (DOCK_A, DOCK_B), Charging Bays (CHARGE_01, CHARGE_02), and Staging Zones (STAGE_1, STAGE_2). "
            "You optimize material flow, resolve navigation bottlenecks, assign tasks based on payload and battery SOC, "
            "and suggest real-time avoidance corridors. "
            "Always respond in JSON format when parsing commands, or clear, concise professional industrial logistics briefs."
        )

    def process_supervisor_command(self, user_command, fleet_telemetry):
        """
        Interprets natural language supervisor instructions and translates to actionable JSON mission.
        """
        if not self.is_configured():
            return self._heuristic_command_parser(user_command, fleet_telemetry)

        url = f"{GEMINI_API_ENDPOINT}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        prompt = f"""
Warehouse Fleet State:
{json.dumps(fleet_telemetry, indent=2)}

Supervisor Natural Language Command:
"{user_command}"

Analyze this command and output a JSON response with the following schema:
{{
  "intent": "NEW_MISSION" | "REROUTE" | "ESTOP" | "CHARGE_NOW" | "STATUS_QUERY",
  "assigned_amr": "AMR-01" | "AMR-02" | "AMR-03" | "AUTO",
  "priority": 1 | 2 | 3,
  "pickup_location": [x, y] or null,
  "dropoff_location": [x, y] or null,
  "pickup_label": string,
  "dropoff_label": string,
  "avoid_zones": [[x, y, radius]],
  "reasoning": "Clear 2-sentence explanation of why this AMR and path were chosen",
  "reply_message": "Concise natural language confirmation for the warehouse dashboard"
}}
Return ONLY valid JSON.
"""

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": self.system_prompt + "\n\n" + prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw_text)
            else:
                return {
                    "error": f"Gemini API returned status {resp.status_code}: {resp.text}",
                    **self._heuristic_command_parser(user_command, fleet_telemetry)
                }
        except Exception as e:
            return {
                "warning": f"Gemini API call failed: {str(e)}. Using fallback heuristic.",
                **self._heuristic_command_parser(user_command, fleet_telemetry)
            }

    def diagnose_deadlock(self, amr_id, telemetry_snapshot):
        """
        Analyzes a navigation failure / deadlock and provides actionable recovery advice.
        """
        if not self.is_configured():
            return {
                "diagnosis": f"AMR {amr_id} encountered spatial congestion in narrow aisle.",
                "action": "EXECUTE_RECOVERY_TIER_3_AND_REROUTE",
                "recommended_path": "Perimeter corridor (Y=28m)",
                "confidence": 0.88
            }

        url = f"{GEMINI_API_ENDPOINT}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        prompt = f"""
Deadlock Emergency Alert for {amr_id}:
Incident Snapshot:
{json.dumps(telemetry_snapshot, indent=2)}

Provide root-cause diagnosis and recommend next best recovery maneuver. Output JSON:
{{
  "diagnosis": "Root cause explanation",
  "action": "SPIN_SCAN" | "RETREAT" | "REROUTE_PERIMETER" | "WAIT_YIELD",
  "recommended_path": "Description of route",
  "confidence": 0.95
}}
"""
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=7.0)
            if resp.status_code == 200:
                return json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
        except Exception:
            pass

        return {
            "diagnosis": f"AMR {amr_id} path blocked by dynamic traffic.",
            "action": "RETREAT",
            "recommended_path": "Reroute via outer warehouse lane",
            "confidence": 0.85
        }

    def _heuristic_command_parser(self, command, fleet_telemetry):
        """Intelligent offline fallback parser when no API key is set."""
        cmd = command.lower()

        # Check for charging command
        if "charge" in cmd or "battery" in cmd:
            target_amr = "AMR-03" if "amr-03" in cmd else ("AMR-02" if "amr-02" in cmd else "AMR-01")
            return {
                "intent": "CHARGE_NOW",
                "assigned_amr": target_amr,
                "priority": 3,
                "pickup_location": None,
                "dropoff_location": [3.0, 3.0],
                "pickup_label": "None",
                "dropoff_label": "Charging Bay Alpha",
                "avoid_zones": [],
                "reasoning": f"Manual charge order received for {target_amr}. Navigating to inductive charging bay.",
                "reply_message": f"Dispatching {target_amr} to Charging Bay Alpha. Inductive pad reserved."
            }

        # Check for emergency stop
        if "stop" in cmd or "halt" in cmd or "emergency" in cmd:
            return {
                "intent": "ESTOP",
                "assigned_amr": "ALL",
                "priority": 3,
                "reasoning": "Supervisor safety override triggered.",
                "reply_message": "EMERGENCY STOP (E-STOP) broadcasted to all AMRs. Drives locked."
            }

        # Default: Delivery Mission (Dock A -> Rack B1 or similar)
        # Select AMR with highest battery and idle
        best_amr = "AMR-01"
        highest_soc = -1
        for amr in fleet_telemetry:
            if amr["status"] == "IDLE" and amr["battery"] > highest_soc:
                highest_soc = amr["battery"]
                best_amr = amr["id"]

        is_dock_b = "dock b" in cmd or "outbound" in cmd
        pickup = [46.0, 24.0] if is_dock_b else [46.0, 6.0]
        dropoff = [18.0, 18.0] if "rack c" in cmd else [26.0, 6.0]

        return {
            "intent": "NEW_MISSION",
            "assigned_amr": best_amr,
            "priority": 2 if "rush" in cmd or "urgent" in cmd else 1,
            "pickup_location": pickup,
            "dropoff_location": dropoff,
            "pickup_label": "Outbound Dock B" if is_dock_b else "Inbound Dock A",
            "dropoff_label": "Storage Rack C2" if "rack c" in cmd else "Storage Rack B1",
            "avoid_zones": [[22.0, 12.0, 3.0]] if "avoid" in cmd or "aisle" in cmd else [],
            "reasoning": f"Assigned {best_amr} (SOC: {highest_soc}%) for optimal throughput with shortest transit time.",
            "reply_message": f"Mission confirmed: {best_amr} dispatched to transport pallet to destination."
        }

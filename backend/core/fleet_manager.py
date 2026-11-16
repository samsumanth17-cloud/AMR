"""
Fleet Manager and Multi-Robot Coordination Engine
Implements auction-based task allocation, traffic conflict deconfliction, and right-of-way arbitration.
"""

import math
import time

class Task:
    def __init__(self, task_id, pallet, priority=1):
        self.id = task_id
        self.pallet = pallet
        self.priority = priority
        self.status = "PENDING" # PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED
        self.assigned_amr = None
        self.created_at = time.time()
        self.completed_at = None

    def to_dict(self):
        return {
            "id": self.id,
            "pallet": self.pallet.to_dict() if self.pallet else None,
            "priority": self.priority,
            "status": self.status,
            "assigned_amr": self.assigned_amr,
            "created_at": round(self.created_at, 1),
            "completed_at": round(self.completed_at, 1) if self.completed_at else None
        }


class FleetCoordinator:
    def __init__(self, amrs):
        self.amrs = {amr.id: amr for amr in amrs}
        self.task_queue = []
        self.completed_tasks = []
        self.conflict_resolution_log = []

    def add_task(self, task):
        self.task_queue.append(task)
        self.allocate_pending_tasks()

    def allocate_pending_tasks(self):
        """
        Auction-based assignment: Computes cost matrix between unassigned tasks and idle AMRs.
        Cost = alpha * Distance + beta * (100 - Battery%) - gamma * Priority
        """
        pending = [t for t in self.task_queue if t.status == "PENDING"]
        if not pending:
            return

        for task in pending:
            best_amr = None
            min_cost = float('inf')

            for amr_id, amr in self.amrs.items():
                if amr.status in ["IDLE", "CHARGING_IDLE"] and not amr.battery_subsystem.is_critical():
                    # Distance from AMR current pose to pallet pickup
                    dist = math.hypot(amr.pose[0] - task.pallet.pickup_x, amr.pose[1] - task.pallet.pickup_y)
                    
                    # Capacity check
                    if task.pallet.weight_kg > amr.payload_capacity_kg:
                        continue

                    # Cost function
                    cost = (1.0 * dist) + (0.5 * (100.0 - amr.battery_subsystem.soc)) - (5.0 * task.priority)
                    if cost < min_cost:
                        min_cost = cost
                        best_amr = amr

            if best_amr:
                task.status = "ASSIGNED"
                task.assigned_amr = best_amr.id
                best_amr.assign_mission(task)

    def arbitrate_traffic_conflicts(self):
        """
        Spatial-temporal collision prevention between multiple AMRs.
        Applies industrial right-of-way rules:
        1. Loaded AMR has priority over Empty AMR.
        2. Higher priority mission proceeds first.
        3. Tie-breaker: Lower AMR ID proceeds while the other yields.
        """
        amr_list = list(self.amrs.values())
        for i in range(len(amr_list)):
            for j in range(i + 1, len(amr_list)):
                r1 = amr_list[i]
                r2 = amr_list[j]

                dist = math.hypot(r1.pose[0] - r2.pose[0], r1.pose[1] - r2.pose[1])
                
                # Conflict zone: < 2.5 meters
                if dist < 2.5:
                    # Check if robots are heading toward each other
                    v1_dir = [math.cos(r1.pose[2]), math.sin(r1.pose[2])]
                    rel_p = [r2.pose[0] - r1.pose[0], r2.pose[1] - r1.pose[1]]
                    dot = (v1_dir[0] * rel_p[0] + v1_dir[1] * rel_p[1]) / (dist + 1e-5)

                    if dot > 0.3: # Moving toward collision
                        # Determine winner of right-of-way
                        prio1 = (2 if r1.carrying_pallet else 0) + (r1.active_task.priority if r1.active_task else 0)
                        prio2 = (2 if r2.carrying_pallet else 0) + (r2.active_task.priority if r2.active_task else 0)

                        if prio1 >= prio2:
                            r2.apply_traffic_yield(f"Yielding right-of-way to {r1.id} (Higher Priority)")
                        else:
                            r1.apply_traffic_yield(f"Yielding right-of-way to {r2.id} (Higher Priority)")

"""
Deadlock Detection and Hierarchical Recovery Behavior Tree
Implements multi-tiered recovery maneuvers for navigation failure resolution.
"""

import time
import math
import collections

class RecoveryBehaviorTree:
    TIER_NORMAL = "NORMAL"
    TIER_1_CLEAR_COSTMAP = "CLEAR_LOCAL_COSTMAP"
    TIER_2_SPIN = "ROTATIONAL_SCAN"
    TIER_3_RETREAT = "BACKWARD_RETREAT"
    TIER_4_REPLAN = "GLOBAL_REPLAN"
    TIER_5_YIELD_ESCALATION = "COOPERATIVE_YIELD_OR_OPERATOR"

    def __init__(self, stall_timeout=3.5, stall_distance_thresh=0.20):
        self.stall_timeout = stall_timeout
        self.stall_distance_thresh = stall_distance_thresh

        self.pose_history = collections.deque(maxlen=20) # stores (timestamp, x, y)
        self.current_tier = self.TIER_NORMAL
        self.tier_start_time = 0.0
        self.tier_index = 0
        self.maneuver_progress = 0.0
        self.recovery_event_log = []

    def update(self, current_pose, is_navigating, dt):
        """
        Check for stalls/deadlocks and progress recovery state machine.
        Returns recovery commands: (override_active, v_cmd, w_cmd, status_message)
        """
        now = time.time()
        x, y, th = current_pose

        if not is_navigating:
            self.reset()
            return False, 0.0, 0.0, "IDLE"

        self.pose_history.append((now, x, y))

        # Check for deadlock if in normal mode
        if self.current_tier == self.TIER_NORMAL:
            if len(self.pose_history) >= 15:
                oldest_t, old_x, old_y = self.pose_history[0]
                time_span = now - oldest_t
                if time_span >= self.stall_timeout:
                    dist_moved = math.hypot(x - old_x, y - old_y)
                    if dist_moved < self.stall_distance_thresh:
                        # Deadlock detected! Escalate to Tier 1
                        self._escalate(now, x, y, "Stall detected: < 0.2m progress in 3.5s")

        # Handle active recovery tier
        if self.current_tier != self.TIER_NORMAL:
            return self._execute_recovery_tier(current_pose, now, dt)

        return False, 0.0, 0.0, "CLEAR"

    def _escalate(self, now, x, y, reason):
        self.tier_index += 1
        self.tier_start_time = now
        self.maneuver_progress = 0.0

        tiers = [
            self.TIER_1_CLEAR_COSTMAP,
            self.TIER_2_SPIN,
            self.TIER_3_RETREAT,
            self.TIER_4_REPLAN,
            self.TIER_5_YIELD_ESCALATION
        ]

        if self.tier_index <= len(tiers):
            self.current_tier = tiers[self.tier_index - 1]
        else:
            self.current_tier = self.TIER_5_YIELD_ESCALATION

        log_entry = {
            "time": round(now, 1),
            "tier": self.current_tier,
            "reason": reason,
            "pose": [round(x, 2), round(y, 2)]
        }
        self.recovery_event_log.append(log_entry)

    def _execute_recovery_tier(self, current_pose, now, dt):
        elapsed = now - self.tier_start_time

        if self.current_tier == self.TIER_1_CLEAR_COSTMAP:
            # Step 1: Pause and signal local costmap refresh
            if elapsed > 1.0:
                # Transition to spin recovery
                self._escalate(now, current_pose[0], current_pose[1], "Costmap cleared, starting clearance spin")
            return True, 0.0, 0.0, "Tier 1: Clearing costmap..."

        elif self.current_tier == self.TIER_2_SPIN:
            # Step 2: In-place 360-degree rotation (speed 0.6 rad/s, duration ~4.0s)
            spin_speed = 0.8
            self.maneuver_progress += spin_speed * dt
            if elapsed > 4.5 or self.maneuver_progress >= (2 * math.pi):
                self._escalate(now, current_pose[0], current_pose[1], "Spin complete, initiating backward retreat")
                return True, 0.0, 0.0, "Tier 2: Spin complete"
            return True, 0.0, spin_speed, f"Tier 2: 360° LiDAR Scan ({int(elapsed/4.5*100)}%)"

        elif self.current_tier == self.TIER_3_RETREAT:
            # Step 3: Reverse 0.6 meters at -0.3 m/s (duration ~2.0s)
            reverse_v = -0.3
            self.maneuver_progress += abs(reverse_v) * dt
            if elapsed > 2.2 or self.maneuver_progress >= 0.6:
                self._escalate(now, current_pose[0], current_pose[1], "Retreat complete, requesting global replan")
                return True, 0.0, 0.0, "Tier 3: Retreat done"
            return True, reverse_v, 0.0, f"Tier 3: Reverse Retreat ({round(self.maneuver_progress, 2)}m)"

        elif self.current_tier == self.TIER_4_REPLAN:
            # Step 4: Signal global replan with virtual obstacle
            self.reset()
            return True, 0.0, 0.0, "Tier 4: Global Replan with blocked aisle avoidance"

        elif self.current_tier == self.TIER_5_YIELD_ESCALATION:
            # Step 5: Broadcast cooperative yield / operator alert
            return True, 0.0, 0.0, "Tier 5: Inter-robot deadlock yield broadcast active"

        return False, 0.0, 0.0, "CLEAR"

    def reset(self):
        self.current_tier = self.TIER_NORMAL
        self.tier_index = 0
        self.tier_start_time = 0.0
        self.maneuver_progress = 0.0
        self.pose_history.clear()

"""
Intelligent Material Handling, Lifter Mechanism, and Payload Tracking
Simulates automated pallet pickup, scissor lift docking, RFID verification, and delivery state transitions.
"""

import time
import math

class Pallet:
    def __init__(self, pallet_id, sku, weight_kg, pickup_loc, dropoff_loc, priority=1):
        self.id = pallet_id
        self.sku = sku
        self.weight_kg = weight_kg
        self.pickup_x, self.pickup_y = pickup_loc
        self.dropoff_x, self.dropoff_y = dropoff_loc
        self.current_x = self.pickup_x
        self.current_y = self.pickup_y
        self.priority = priority # 1 (Normal), 2 (Rush), 3 (Critical/Hazmat)

        self.status = "AVAILABLE"  # AVAILABLE, ASSIGNED, PICKING_UP, IN_TRANSIT, DROPPING_OFF, DELIVERED
        self.carried_by = None     # AMR ID
        self.created_at = time.time()
        self.rfid_verified = False

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "weight_kg": self.weight_kg,
            "priority": self.priority,
            "status": self.status,
            "carried_by": self.carried_by,
            "x": round(self.current_x, 2),
            "y": round(self.current_y, 2),
            "pickup": [self.pickup_x, self.pickup_y],
            "dropoff": [self.dropoff_x, self.dropoff_y],
            "rfid_verified": self.rfid_verified
        }


class LifterMechanism:
    """Simulates physical scissor lift / pin hook mechanism on AMR."""
    HEIGHT_DOWN = 0.00
    HEIGHT_UP = 0.12 # 12 cm lift height

    def __init__(self, lift_speed=0.04): # 4 cm/s -> ~3 seconds to full lift
        self.height = self.HEIGHT_DOWN
        self.target_height = self.HEIGHT_DOWN
        self.speed = lift_speed
        self.state = "LOWERED" # LOWERED, RAISING, RAISED, LOWERING

    def update(self, dt):
        if self.state == "RAISING":
            self.height = min(self.HEIGHT_UP, self.height + self.speed * dt)
            if self.height >= self.HEIGHT_UP:
                self.state = "RAISED"
        elif self.state == "LOWERING":
            self.height = max(self.HEIGHT_DOWN, self.height - self.speed * dt)
            if self.height <= self.HEIGHT_DOWN:
                self.state = "LOWERED"
        return self.height, self.state

    def raise_lift(self):
        self.target_height = self.HEIGHT_UP
        self.state = "RAISING"

    def lower_lift(self):
        self.target_height = self.HEIGHT_DOWN
        self.state = "LOWERING"

    def is_raised(self):
        return self.state == "RAISED"

    def is_lowered(self):
        return self.state == "LOWERED"

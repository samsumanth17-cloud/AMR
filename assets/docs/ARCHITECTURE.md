# 🏗️ LogiSwift Industrial AMR System Architecture

## 1. Topological Decomposition

The Autonomous Mobile Robot (AMR) platform is partitioned into discrete layers conforming to modern industrial robotics standards (ROS 2 / Nav2 & ISO 3691-4 industrial AGV/AMR safety regulations).

```
   [ SUPERVISORY LAYER ]      -> Google Gemini AI Agent & Fleet Director
            |
   [ ORCHESTRATION LAYER ]    -> Multi-Robot Conflict Resolution, Auction Dispatcher
            |
   [ PLANNING LAYER ]         -> Cost-Aware A* Global Route, Dynamic Window (DWA) Local
            |
   [ PERCEPTION LAYER ]       -> EKF Sensor Fusion (Odom + IMU), 360° LiDAR Raycaster
            |
   [ ACTUATION LAYER ]        -> Differential Drive Kinematics, Prismatic Scissor Lift
            |
   [ DIGITAL TWIN LAYER ]     -> Three.js WebGL 3D Model, CAD-Grade Assembly, Live HUD
```

## 2. Mathematical Formulations

### 2.1 Sensor Fusion - Extended Kalman Filter (EKF)
State vector: $\mathbf{x} = [x, y, \theta, v, \omega]^T$
- State Transition Matrix $F$:
  $$F = \begin{bmatrix}
  1 & 0 & -v \sin\theta \Delta t & \cos\theta \Delta t & 0 \\
  0 & 1 & v \cos\theta \Delta t & \sin\theta \Delta t & 0 \\
  0 & 0 & 1 & 0 & \Delta t \\
  0 & 0 & 0 & 1 & 0 \\
  0 & 0 & 0 & 0 & 1
  \end{bmatrix}$$
- Measurement Update:
  $$\mathbf{y}_k = \mathbf{z}_k - \mathbf{H} \hat{\mathbf{x}}_k$$
  $$\mathbf{S}_k = \mathbf{H} \mathbf{P}_k \mathbf{H}^T + \mathbf{R}$$
  $$\mathbf{K}_k = \mathbf{P}_k \mathbf{H}^T \mathbf{S}_k^{-1}$$
  $$\hat{\mathbf{x}}_k \leftarrow \hat{\mathbf{x}}_k + \mathbf{K}_k \mathbf{y}_k$$
  $$\mathbf{P}_k \leftarrow (\mathbf{I} - \mathbf{K}_k \mathbf{H}) \mathbf{P}_k$$

### 2.2 Dynamic Window Approach (DWA) Objective Function
$$G(v, \omega) = \alpha \cdot \text{heading}(v, \omega) + \beta \cdot \text{clearance}(v, \omega) + \gamma \cdot \text{velocity}(v, \omega)$$
Dynamic Window Boundaries:
$$V_d = [v - a_{\text{lin}}\Delta t, v + a_{\text{lin}}\Delta t] \cap [-v_{\text{max}}/2, v_{\text{max}}]$$
$$\Omega_d = [\omega - a_{\text{ang}}\Delta t, \omega + a_{\text{ang}}\Delta t] \cap [-\omega_{\text{max}}, \omega_{\text{max}}]$$

### 2.3 5-Tier Deadlock Recovery Tree
1. `CLEAR_LOCAL_COSTMAP`: Invalidate transient dynamic obstacles.
2. `ROTATIONAL_SCAN`: $360^\circ$ scan rotation at $0.8\,\text{rad/s}$ to eliminate LiDAR blind zones.
3. `BACKWARD_RETREAT`: Reverse $0.6\,\text{m}$ along previous trajectory to create passing clearance.
4. `GLOBAL_REPLAN`: Place temporary virtual wall at bottleneck cell and compute alternate aisle route.
5. `INTER_ROBOT_YIELD`: Cooperative multi-robot right-of-way speed reduction or operator alert.

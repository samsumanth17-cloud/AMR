/**
 * 3D Sensor and Navigation Visualizer for Industrial AMR
 * Renders LiDAR Point Clouds, Ray Fan Lines, Costmap Overlays, and Trajectory Ribbons.
 */

window.SensorVisualizer = (function () {
  const THREE = window.THREE;

  class AMRVisualizer {
    constructor(scene, amrId, colorHex) {
      this.scene = scene;
      this.amrId = amrId;
      this.color = new THREE.Color(colorHex || "#00e5ff");

      // 1. LiDAR Hit Points (Point Cloud)
      this.maxPoints = 200;
      const pointGeo = new THREE.BufferGeometry();
      const positions = new Float32Array(this.maxPoints * 3);
      pointGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

      const pointMat = new THREE.PointsMaterial({
        color: 0xff0055,
        size: 0.12,
        transparent: true,
        opacity: 0.85
      });
      this.pointCloud = new THREE.Points(pointGeo, pointMat);
      this.scene.add(this.pointCloud);

      // 2. Global Planned Path Polyline Ribbon
      const pathMat = new THREE.LineBasicMaterial({
        color: this.color,
        linewidth: 3,
        transparent: true,
        opacity: 0.8
      });
      const pathGeo = new THREE.BufferGeometry();
      this.pathLine = new THREE.Line(pathGeo, pathMat);
      this.scene.add(this.pathLine);

      // 3. Local DWA Prediction Arc
      const dwaMat = new THREE.LineBasicMaterial({
        color: 0x76ff03,
        linewidth: 2,
        transparent: true,
        opacity: 0.9
      });
      const dwaGeo = new THREE.BufferGeometry();
      this.dwaLine = new THREE.Line(dwaGeo, dwaMat);
      this.scene.add(this.dwaLine);

      // 4. Breadcrumb History Trail
      const trailMat = new THREE.LineBasicMaterial({
        color: 0x0284c7,
        transparent: true,
        opacity: 0.4
      });
      const trailGeo = new THREE.BufferGeometry();
      this.trailLine = new THREE.Line(trailGeo, trailMat);
      this.scene.add(this.trailLine);

      // Visibility toggles
      this.showLidar = true;
      this.showPaths = true;
    }

    update(telemetry) {
      // 1. Update LiDAR Hit Points
      if (this.showLidar && telemetry.lidar_hits && telemetry.lidar_hits.length > 0) {
        this.pointCloud.visible = true;
        const positions = this.pointCloud.geometry.attributes.position.array;
        const count = Math.min(this.maxPoints, telemetry.lidar_hits.length);

        for (let i = 0; i < count; i++) {
          const pt = telemetry.lidar_hits[i];
          positions[i * 3 + 0] = pt[0];
          positions[i * 3 + 1] = 0.25; // Elevated slightly off floor
          positions[i * 3 + 2] = pt[1];
        }
        for (let i = count; i < this.maxPoints; i++) {
          positions[i * 3 + 0] = 0;
          positions[i * 3 + 1] = -100; // Hide unused
          positions[i * 3 + 2] = 0;
        }
        this.pointCloud.geometry.attributes.position.needsUpdate = true;
      } else {
        this.pointCloud.visible = false;
      }

      // 2. Update Global Planned Path
      if (this.showPaths && telemetry.path && telemetry.path.length > 1) {
        this.pathLine.visible = true;
        const pts = [];
        // Add current robot position as start
        pts.push(new THREE.Vector3(telemetry.pose[0], 0.05, telemetry.pose[1]));
        for (let i = telemetry.path_index || 0; i < telemetry.path.length; i++) {
          pts.push(new THREE.Vector3(telemetry.path[i][0], 0.05, telemetry.path[i][1]));
        }
        this.pathLine.geometry.setFromPoints(pts);
      } else {
        this.pathLine.visible = false;
      }

      // 3. Update Local DWA Arc
      if (this.showPaths && telemetry.local_trajectory && telemetry.local_trajectory.length > 1) {
        this.dwaLine.visible = true;
        const pts = telemetry.local_trajectory.map(p => new THREE.Vector3(p[0], 0.06, p[1]));
        this.dwaLine.geometry.setFromPoints(pts);
      } else {
        this.dwaLine.visible = false;
      }

      // 4. Update Breadcrumb Trail
      if (telemetry.breadcrumbs && telemetry.breadcrumbs.length > 1) {
        const pts = telemetry.breadcrumbs.map(p => new THREE.Vector3(p[0], 0.02, p[1]));
        this.trailLine.geometry.setFromPoints(pts);
      }
    }

    dispose() {
      this.scene.remove(this.pointCloud);
      this.scene.remove(this.pathLine);
      this.scene.remove(this.dwaLine);
      this.scene.remove(this.trailLine);
    }
  }

  return {
    AMRVisualizer
  };
})();

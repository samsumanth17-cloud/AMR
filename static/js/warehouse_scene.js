/**
 * 3D Industrial Warehouse Environment Generator
 * Generates concrete epoxy floor, multi-tier pallet racks, loading docks, charging bays,
 * animated dynamic workers, and forklift traffic.
 */

window.WarehouseScene = (function () {
  const THREE = window.THREE;

  function buildWarehouse(scene, infrastructure) {
    const warehouseGroup = new THREE.Group();

    // 1. Polished Concrete Epoxy Floor (50m x 30m)
    const floorGeo = new THREE.PlaneGeometry(50.0, 30.0);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x1e2638,
      roughness: 0.35,
      metalness: 0.25
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(25.0, 0.0, 15.0); // Center at (25, 15)
    floor.receiveShadow = true;
    warehouseGroup.add(floor);

    // Floor Aisle Grid & Guide Lines
    const grid = new THREE.GridHelper(50, 50, 0x00e5ff, 0x22324c);
    grid.position.set(25.0, 0.005, 15.0);
    warehouseGroup.add(grid);

    // Safety Yellow Lane Markings along Perimeter
    const laneGeo = new THREE.PlaneGeometry(48.0, 0.15);
    const yellowMat = new THREE.MeshBasicMaterial({ color: 0xffd600 });

    const laneN = new THREE.Mesh(laneGeo, yellowMat);
    laneN.rotation.x = -Math.PI / 2;
    laneN.position.set(25.0, 0.01, 1.5);
    warehouseGroup.add(laneN);

    const laneS = new THREE.Mesh(laneGeo, yellowMat);
    laneS.rotation.x = -Math.PI / 2;
    laneS.position.set(25.0, 0.01, 28.5);
    warehouseGroup.add(laneS);

    // 2. Storage Racking Systems
    const steelBlueMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.7, roughness: 0.3 });
    const beamOrangeMat = new THREE.MeshStandardMaterial({ color: 0xf97316, metalness: 0.5, roughness: 0.4 });

    (infrastructure.storage_racks || []).forEach(rack => {
      const rackGroup = new THREE.Group();
      rackGroup.position.set(rack.x, 0, rack.y);

      // Upright steel columns (4 legs, height 4.5m)
      const colGeo = new THREE.BoxGeometry(0.1, 4.5, 0.1);
      const halfW = rack.w / 2.0;
      const halfH = rack.h / 2.0;

      [[-halfW, -halfH], [halfW, -halfH], [-halfW, halfH], [halfW, halfH]].forEach(([cx, cz]) => {
        const col = new THREE.Mesh(colGeo, steelBlueMat);
        col.position.set(cx, 2.25, cz);
        col.castShadow = true;
        rackGroup.add(col);
      });

      // 3 Shelf Levels (at 0.2m, 1.6m, 3.0m)
      [0.2, 1.6, 3.0].forEach(shelfY => {
        // Orange cross beams
        const beamGeo = new THREE.BoxGeometry(rack.w + 0.1, 0.08, rack.h + 0.1);
        const beam = new THREE.Mesh(beamGeo, beamOrangeMat);
        beam.position.set(0, shelfY, 0);
        beam.castShadow = true;
        beam.receiveShadow = true;
        rackGroup.add(beam);

        // Decorative background stored boxes on racks
        [-halfH + 1.2, 0.0, halfH - 1.2].forEach(bz => {
          const storedBoxGeo = new THREE.BoxGeometry(rack.w * 0.75, 0.7, 1.2);
          const boxMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.8 });
          const storedBox = new THREE.Mesh(storedBoxGeo, boxMat);
          storedBox.position.set(0, shelfY + 0.38, bz);
          storedBox.castShadow = true;
          rackGroup.add(storedBox);
        });
      });

      warehouseGroup.add(rackGroup);
    });

    // 3. Autonomous Inductive Fast Charging Stations
    (infrastructure.charging_stations || []).forEach(station => {
      const padGroup = new THREE.Group();
      padGroup.position.set(station.x, 0.015, station.y);

      // Charging base plate
      const padGeo = new THREE.BoxGeometry(1.6, 0.03, 1.6);
      const padMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5 });
      const pad = new THREE.Mesh(padGeo, padMat);
      padGroup.add(pad);

      // Pulsing magnetic flux ring
      const ringGeo = new THREE.RingGeometry(0.3, 0.65, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x10b981,
        side: THREE.DoubleSide
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.02;
      padGroup.add(ring);

      // Charging Totem Pillar
      const totemGeo = new THREE.BoxGeometry(0.35, 1.5, 0.35);
      const totemMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.7 });
      const totem = new THREE.Mesh(totemGeo, totemMat);
      totem.position.set(-0.9, 0.75, 0);
      padGroup.add(totem);

      // Totem LED Indicator
      const ledGeo = new THREE.SphereGeometry(0.08, 16, 16);
      const totemLedMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
      const totemLed = new THREE.Mesh(ledGeo, totemLedMat);
      totemLed.position.set(-0.9, 1.4, 0.18);
      padGroup.add(totemLed);

      warehouseGroup.add(padGroup);
    });

    // 4. Loading Docks A & B
    (infrastructure.loading_docks || []).forEach(dock => {
      const dockGroup = new THREE.Group();
      dockGroup.position.set(dock.x, 0, dock.y);

      // Dock Pit Frame
      const pitGeo = new THREE.BoxGeometry(3.5, 0.1, 4.0);
      const pitMat = new THREE.MeshStandardMaterial({ color: 0x334155 });
      const pit = new THREE.Mesh(pitGeo, pitMat);
      pit.position.y = 0.05;
      dockGroup.add(pit);

      // Roll-up overhead bay door
      const doorGeo = new THREE.BoxGeometry(0.15, 3.5, 3.6);
      const doorMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.8, roughness: 0.3 });
      const door = new THREE.Mesh(doorGeo, doorMat);
      door.position.set(1.6, 1.75, 0);
      dockGroup.add(door);

      // Hazard Warning Stripes
      const stripeGeo = new THREE.PlaneGeometry(3.5, 0.3);
      const stripeMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
      const stripe = new THREE.Mesh(stripeGeo, stripeMat);
      stripe.rotation.x = -Math.PI / 2;
      stripe.position.set(0, 0.11, -2.0);
      dockGroup.add(stripe);

      warehouseGroup.add(dockGroup);
    });

    scene.add(warehouseGroup);
    return warehouseGroup;
  }

  function createDynamicWorkerMesh() {
    const group = new THREE.Group();

    // Humanoid stylized worker with safety vest & hardhat
    const skinMat = new THREE.MeshStandardMaterial({ color: 0xffd1a4, roughness: 0.6 });
    const vestMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.5 }); // Hi-vis safety green
    const hardhatMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.2 }); // Yellow hardhat
    const pantsMat = new THREE.MeshStandardMaterial({ color: 0x1e3a8a, roughness: 0.7 });

    // Torso with Safety Vest
    const torsoGeo = new THREE.BoxGeometry(0.4, 0.6, 0.25);
    const torso = new THREE.Mesh(torsoGeo, vestMat);
    torso.position.y = 1.1;
    torso.castShadow = true;
    group.add(torso);

    // Head & Hardhat
    const headGeo = new THREE.SphereGeometry(0.12, 16, 16);
    const head = new THREE.Mesh(headGeo, skinMat);
    head.position.y = 1.55;
    group.add(head);

    const hardhatGeo = new THREE.SphereGeometry(0.14, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2);
    const hardhat = new THREE.Mesh(hardhatGeo, hardhatMat);
    hardhat.position.y = 1.58;
    group.add(hardhat);

    // Legs
    const legGeo = new THREE.BoxGeometry(0.14, 0.7, 0.14);
    const leftLeg = new THREE.Mesh(legGeo, pantsMat);
    leftLeg.position.set(0.1, 0.45, 0);
    leftLeg.castShadow = true;
    group.add(leftLeg);

    const rightLeg = new THREE.Mesh(legGeo, pantsMat);
    rightLeg.position.set(-0.1, 0.45, 0);
    rightLeg.castShadow = true;
    group.add(rightLeg);

    // Warning halo indicator around worker
    const warningGeo = new THREE.RingGeometry(0.5, 0.55, 24);
    const warningMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, side: THREE.DoubleSide });
    const warningRing = new THREE.Mesh(warningGeo, warningMat);
    warningRing.rotation.x = -Math.PI / 2;
    warningRing.position.y = 0.02;
    group.add(warningRing);

    return group;
  }

  function createDynamicForkliftMesh() {
    const group = new THREE.Group();

    const bodyMat = new THREE.MeshStandardMaterial({ color: 0xf97316, metalness: 0.5, roughness: 0.3 }); // Orange industrial body
    const metalMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8, roughness: 0.2 });
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.9 });

    // Chassis & Counterweight
    const bodyGeo = new THREE.BoxGeometry(1.8, 0.8, 1.1);
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.set(0, 0.6, 0);
    body.castShadow = true;
    group.add(body);

    // Overhead Safety Cage
    const cageGeo = new THREE.BoxGeometry(1.2, 1.2, 1.0);
    const cage = new THREE.Mesh(cageGeo, metalMat);
    cage.position.set(-0.1, 1.5, 0);
    group.add(cage);

    // Front Mast & Forks
    const mastGeo = new THREE.BoxGeometry(0.1, 1.8, 0.8);
    const mast = new THREE.Mesh(mastGeo, metalMat);
    mast.position.set(0.95, 1.0, 0);
    group.add(mast);

    const forkGeo = new THREE.BoxGeometry(0.8, 0.05, 0.12);
    const leftFork = new THREE.Mesh(forkGeo, metalMat);
    leftFork.position.set(1.4, 0.12, 0.25);
    group.add(leftFork);

    const rightFork = new THREE.Mesh(forkGeo, metalMat);
    rightFork.position.set(1.4, 0.12, -0.25);
    group.add(rightFork);

    // Large Industrial Wheels
    const fwGeo = new THREE.CylinderGeometry(0.25, 0.25, 0.15, 24);
    fwGeo.rotateX(Math.PI / 2);
    [[-0.6, 0.25, 0.55], [-0.6, 0.25, -0.55], [0.6, 0.25, 0.55], [0.6, 0.25, -0.55]].forEach(([wx, wy, wz]) => {
      const wh = new THREE.Mesh(fwGeo, wheelMat);
      wh.position.set(wx, wy, wz);
      wh.castShadow = true;
      group.add(wh);
    });

    // Amber Rotating Beacon
    const beaconGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.1, 16);
    const beaconMat = new THREE.MeshBasicMaterial({ color: 0xffea00 });
    const beacon = new THREE.Mesh(beaconGeo, beaconMat);
    beacon.position.set(-0.1, 2.15, 0);
    group.add(beacon);

    return group;
  }

  return {
    buildWarehouse,
    createDynamicWorkerMesh,
    createDynamicForkliftMesh
  };
})();

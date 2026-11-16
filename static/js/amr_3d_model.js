/**
 * Procedural 3D CAD-Grade Model Generator for Industrial AMR
 * Constructs high-detail chassis, differential wheels, scissor lift, LiDAR turret, RGB-D camera, and safety LED ring.
 */

window.AMR3DModel = (function () {
  const THREE = window.THREE;

  function createRobotMesh(config) {
    const group = new THREE.Group();
    group.name = config.id;

    // Materials
    const baseColor = new THREE.Color(config.color || "#00e5ff");
    const chassisMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.6,
      roughness: 0.3
    });

    const accentMat = new THREE.MeshStandardMaterial({
      color: baseColor,
      metalness: 0.4,
      roughness: 0.4
    });

    const bumperMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.9,
      metalness: 0.1
    });

    const metalMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      metalness: 0.85,
      roughness: 0.2
    });

    const wheelMat = new THREE.MeshStandardMaterial({
      color: 0x111827,
      roughness: 0.8
    });

    // 1. Lower Bumper & Skirt (Length 1.0m, Width 0.8m, Height 0.12m)
    const bumperGeo = new THREE.BoxGeometry(1.0, 0.12, 0.8);
    const bumper = new THREE.Mesh(bumperGeo, bumperMat);
    bumper.position.y = 0.10;
    bumper.castShadow = true;
    bumper.receiveShadow = true;
    group.add(bumper);

    // 2. Main Robot Body Upper Shell
    const shellGeo = new THREE.BoxGeometry(0.92, 0.18, 0.72);
    const shell = new THREE.Mesh(shellGeo, chassisMat);
    shell.position.y = 0.22;
    shell.castShadow = true;
    group.add(shell);

    // Top accent cover plate with robot color
    const plateGeo = new THREE.BoxGeometry(0.86, 0.02, 0.66);
    const topPlate = new THREE.Mesh(plateGeo, accentMat);
    topPlate.position.y = 0.315;
    group.add(topPlate);

    // 3. 360-Degree Safety LED Status Light Ring
    const ringGeo = new THREE.BoxGeometry(0.94, 0.025, 0.74);
    const ledMat = new THREE.MeshStandardMaterial({
      color: baseColor,
      emissive: baseColor,
      emissiveIntensity: 0.85,
      roughness: 0.1
    });
    const ledRing = new THREE.Mesh(ringGeo, ledMat);
    ledRing.position.y = 0.17;
    group.add(ledRing);
    group.userData.ledMaterial = ledMat;

    // 4. Wheels: 2 Main Drive Wheels (Left & Right)
    const wheelGeo = new THREE.CylinderGeometry(0.10, 0.10, 0.06, 24);
    wheelGeo.rotateX(Math.PI / 2);

    const leftWheel = new THREE.Mesh(wheelGeo, wheelMat);
    leftWheel.position.set(0.0, 0.10, 0.38);
    leftWheel.castShadow = true;
    group.add(leftWheel);

    const rightWheel = new THREE.Mesh(wheelGeo, wheelMat);
    rightWheel.position.set(0.0, 0.10, -0.38);
    rightWheel.castShadow = true;
    group.add(rightWheel);

    // Omni-Caster Wheels (Front & Rear)
    const casterGeo = new THREE.SphereGeometry(0.05, 16, 16);
    const casterMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7 });
    
    const frontCaster = new THREE.Mesh(casterGeo, casterMat);
    frontCaster.position.set(0.38, 0.05, 0.0);
    group.add(frontCaster);

    const rearCaster = new THREE.Mesh(casterGeo, casterMat);
    rearCaster.position.set(-0.38, 0.05, 0.0);
    group.add(rearCaster);

    // 5. 360-Degree LiDAR Turret (Elevated center)
    const lidarBaseGeo = new THREE.CylinderGeometry(0.07, 0.08, 0.06, 24);
    const lidarBase = new THREE.Mesh(lidarBaseGeo, metalMat);
    lidarBase.position.set(0.20, 0.35, 0.0);
    group.add(lidarBase);

    const lidarRotorGeo = new THREE.CylinderGeometry(0.065, 0.065, 0.04, 24);
    const lidarRotorMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      emissive: 0x0284c7,
      emissiveIntensity: 0.4,
      metalness: 0.9,
      roughness: 0.1
    });
    const lidarRotor = new THREE.Mesh(lidarRotorGeo, lidarRotorMat);
    lidarRotor.position.set(0.20, 0.39, 0.0);
    group.add(lidarRotor);
    group.userData.lidarRotor = lidarRotor;

    // 6. Front Stereoscopic RGB-D Depth Camera Sensor
    const cameraHousingGeo = new THREE.BoxGeometry(0.04, 0.04, 0.14);
    const cameraHousing = new THREE.Mesh(cameraHousingGeo, metalMat);
    cameraHousing.position.set(0.48, 0.20, 0.0);
    group.add(cameraHousing);

    const lensGeo = new THREE.CylinderGeometry(0.012, 0.012, 0.01, 16);
    lensGeo.rotateZ(Math.PI / 2);
    const lensMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });

    const leftLens = new THREE.Mesh(lensGeo, lensMat);
    leftLens.position.set(0.50, 0.20, 0.04);
    group.add(leftLens);

    const rightLens = new THREE.Mesh(lensGeo, lensMat);
    rightLens.position.set(0.50, 0.20, -0.04);
    group.add(rightLens);

    // 7. Scissor Lifter Platform Mechanism
    const lifterGroup = new THREE.Group();
    lifterGroup.position.set(0, 0.33, 0);

    const lifterPlatformGeo = new THREE.BoxGeometry(0.75, 0.02, 0.55);
    const lifterPlatform = new THREE.Mesh(lifterPlatformGeo, metalMat);
    lifterPlatform.castShadow = true;
    lifterPlatform.receiveShadow = true;
    lifterGroup.add(lifterPlatform);

    // Scissor cross-link simulation bars
    const barGeo = new THREE.CylinderGeometry(0.008, 0.008, 0.22);
    barGeo.rotateZ(Math.PI / 4);
    const scissorBar1 = new THREE.Mesh(barGeo, metalMat);
    scissorBar1.position.set(-0.15, -0.05, 0.22);
    lifterGroup.add(scissorBar1);

    const scissorBar2 = new THREE.Mesh(barGeo, metalMat);
    scissorBar2.position.set(0.15, -0.05, -0.22);
    lifterGroup.add(scissorBar2);

    group.add(lifterGroup);
    group.userData.lifterGroup = lifterGroup;

    // 8. Overhead Text Tag (AMR ID)
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "rgba(10, 15, 30, 0.85)";
    if (ctx.roundRect) {
      ctx.roundRect(0, 0, 256, 64, 16);
    } else {
      ctx.fillRect(0, 0, 256, 64);
    }
    ctx.fill();
    ctx.strokeStyle = config.color || "#00e5ff";
    ctx.lineWidth = 4;
    ctx.stroke();
    ctx.font = "bold 28px monospace";
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(config.id, 128, 32);

    const textTexture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: textTexture });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(0, 0.85, 0);
    sprite.scale.set(0.9, 0.25, 1.0);
    group.add(sprite);

    return group;
  }

  function createPalletMesh(palletData) {
    const group = new THREE.Group();
    group.name = palletData.id;

    // Standard Euro-Pallet (1.2m x 0.8m x 0.15m)
    const woodMat = new THREE.MeshStandardMaterial({
      color: 0xc29b62,
      roughness: 0.85,
      metalness: 0.05
    });

    // Top deck boards
    for (let i = -0.35; i <= 0.35; i += 0.175) {
      const boardGeo = new THREE.BoxGeometry(1.2, 0.02, 0.12);
      const board = new THREE.Mesh(boardGeo, woodMat);
      board.position.set(0, 0.13, i);
      board.castShadow = true;
      group.add(board);
    }

    // Wooden blocks and bottom skids
    const blockGeo = new THREE.BoxGeometry(0.15, 0.10, 0.12);
    [-0.5, 0.0, 0.5].forEach(bx => {
      [-0.32, 0.0, 0.32].forEach(bz => {
        const blk = new THREE.Mesh(blockGeo, woodMat);
        blk.position.set(bx, 0.06, bz);
        blk.castShadow = true;
        group.add(blk);
      });
    });

    // Cargo Box on Pallet
    const boxColor = palletData.priority === 3 ? 0xef4444 : (palletData.priority === 2 ? 0xf59e0b : 0x3b82f6);
    const boxGeo = new THREE.BoxGeometry(1.0, 0.65, 0.7);
    const boxMat = new THREE.MeshStandardMaterial({
      color: boxColor,
      roughness: 0.5,
      metalness: 0.1
    });
    const box = new THREE.Mesh(boxGeo, boxMat);
    box.position.set(0, 0.48, 0);
    box.castShadow = true;
    group.add(box);

    return group;
  }

  return {
    createRobotMesh,
    createPalletMesh
  };
})();

/**
 * LogiSwift Industrial AMR Enterprise Suite - Master Application Controller
 * Outlook-Style Multi-View Application, SQLite Telemetry Sync, Manual Teleoperation,
 * and Three.js 3D Digital Twin Engine.
 */

(function () {
  const THREE = window.THREE;
  const OrbitControls = window.OrbitControls || (window.THREE ? window.THREE.OrbitControls : null);

  let scene, camera, renderer, controls;
  let robotMeshes = {};
  let robotVisualizers = {};
  let palletMeshes = {};
  let dynamicObstacleMeshes = {};

  let currentActiveView = "view-3d";
  let selectedAmrId = "AMR-01";
  let cameraMode = "orbit";
  let isEStopActive = false;
  let warehouseBuilt = false;
  let currentDbTab = "telemetry";
  let activeTelemetryCache = [];

  // Key tracking for smooth WASD manual teleoperation
  const activeKeys = {};
  let teleopInterval = null;

  function initApplication() {
    setupNavigationRail();
    setupCameraControls();
    setupTeleoperationControls();
    setupMissionDispatcher();
    setupDatabaseViewer();
    setupSettingsAndObstacles();
    window.GeminiCommander.init();

    init3D();

    // Start background polling loops
    setInterval(fetchWarehouseState, 80);    // 12.5 Hz live state
    setInterval(fetchDatabaseAnalytics, 2000); // 0.5 Hz DB stats
    fetchDatabaseTable(currentDbTab);
  }

  // --- Outlook-Style Navigation Rail ---
  function setupNavigationRail() {
    const railItems = document.querySelectorAll(".nav-rail .rail-item");
    const viewPanels = document.querySelectorAll(".views-container .view-panel");

    railItems.forEach(item => {
      item.addEventListener("click", () => {
        railItems.forEach(r => r.classList.remove("active"));
        item.classList.add("active");

        const targetId = item.dataset.target;
        currentActiveView = targetId;

        viewPanels.forEach(panel => {
          panel.classList.remove("active");
          if (panel.id === targetId) {
            panel.classList.add("active");
          }
        });

        // Trigger resize if switching back to 3D view
        if (targetId === "view-3d") {
          onWindowResize();
        } else if (targetId === "view-database") {
          fetchDatabaseTable(currentDbTab);
        }
      });
    });
  }

  // --- 3D Scene Initialization ---
  function init3D() {
    const container = document.getElementById("canvas-container");
    if (!container) return;
    const width = container.clientWidth || window.innerWidth - 72;
    const height = container.clientHeight || window.innerHeight - 48;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e17);
    scene.fog = new THREE.FogExp2(0x0a0e17, 0.015);

    camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 200);
    camera.position.set(25.0, 32.0, 38.0);

    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    if (OrbitControls) {
      controls = new OrbitControls(camera, renderer.domElement);
      controls.target.set(25.0, 0.0, 15.0);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.maxPolarAngle = Math.PI / 2 - 0.02;
      controls.minDistance = 3.0;
      controls.maxDistance = 80.0;
    }

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.65));
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(25.0, 40.0, 15.0);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    scene.add(dirLight);

    const blueLight = new THREE.PointLight(0x00e5ff, 2.0, 40);
    blueLight.position.set(5.0, 6.0, 5.0);
    scene.add(blueLight);

    const orangeLight = new THREE.PointLight(0xf97316, 2.0, 40);
    orangeLight.position.set(45.0, 6.0, 25.0);
    scene.add(orangeLight);

    window.addEventListener("resize", onWindowResize);
    animate();
  }

  function onWindowResize() {
    const container = document.getElementById("canvas-container");
    if (!container || !renderer || !camera) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }

  function setupCameraControls() {
    const btns = document.querySelectorAll(".camera-bar .hud-btn");
    btns.forEach(btn => {
      btn.addEventListener("click", () => {
        btns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        cameraMode = btn.dataset.view;

        if (cameraMode === "topdown") {
          camera.position.set(25.0, 45.0, 15.0);
          if (controls) controls.target.set(25.0, 0.0, 15.0);
        } else if (cameraMode === "orbit") {
          camera.position.set(25.0, 32.0, 38.0);
          if (controls) controls.target.set(25.0, 0.0, 15.0);
        }
      });
    });
  }

  // --- Manual Teleoperation & Key Handling ---
  function setupTeleoperationControls() {
    // Master E-STOP
    const estopBtn = document.getElementById("btn-estop-main");
    if (estopBtn) {
      estopBtn.addEventListener("click", async () => {
        isEStopActive = !isEStopActive;
        const cmd = isEStopActive ? "ESTOP" : "RESUME";
        await fetch("/api/amr/command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ amr_id: "ALL", command: cmd })
        });
        estopBtn.classList.toggle("active", isEStopActive);
        estopBtn.innerText = isEStopActive ? "⚠️ RESUME FLEET" : "🛑 E-STOP FLEET";
      });
    }

    // Individual Deck E-Stop
    const deckEstop = document.getElementById("deck-btn-estop");
    if (deckEstop) {
      deckEstop.addEventListener("click", () => {
        fetch("/api/amr/command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ amr_id: selectedAmrId, command: "ESTOP" })
        });
      });
    }

    // Individual Deck Route to Charge
    const deckCharge = document.getElementById("deck-btn-charge");
    if (deckCharge) {
      deckCharge.addEventListener("click", () => {
        fetch("/api/amr/command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ amr_id: selectedAmrId, command: "CHARGE" })
        });
      });
    }

    // Mode Toggle Buttons (Autonomous vs Manual)
    const btnAuto = document.getElementById("btn-mode-auto");
    const btnManual = document.getElementById("btn-mode-manual");

    if (btnAuto && btnManual) {
      btnAuto.addEventListener("click", () => setRobotMode(selectedAmrId, "AUTONOMOUS"));
      btnManual.addEventListener("click", () => setRobotMode(selectedAmrId, "MANUAL"));
    }

    // Lifter Buttons
    const bindLifter = (id, action) => {
      const btn = document.getElementById(id);
      if (btn) {
        btn.addEventListener("click", () => {
          fetch("/api/amr/lifter", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amr_id: selectedAmrId, action: action })
          });
        });
      }
    };
    bindLifter("btn-quick-lift-up", "RAISE");
    bindLifter("btn-quick-lift-down", "LOWER");
    bindLifter("deck-btn-lift-up", "RAISE");
    bindLifter("deck-btn-lift-down", "LOWER");

    // D-Pad Buttons binding (supports both click and continuous hold)
    const bindDpad = (id, v, w) => {
      const btn = document.getElementById(id);
      if (btn) {
        const send = () => sendTeleopCommand(selectedAmrId, v, w);
        btn.addEventListener("mousedown", () => {
          send();
          teleopInterval = setInterval(send, 80);
        });
        window.addEventListener("mouseup", () => {
          if (teleopInterval) {
            clearInterval(teleopInterval);
            teleopInterval = null;
          }
        });
      }
    };

    // Quick HUD D-Pad
    bindDpad("dpad-up", 0.9, 0.0);
    bindDpad("dpad-down", -0.5, 0.0);
    bindDpad("dpad-left", 0.0, 1.1);
    bindDpad("dpad-right", 0.0, -1.1);
    const dpadStop = document.getElementById("dpad-stop");
    if (dpadStop) dpadStop.addEventListener("click", () => sendTeleopCommand(selectedAmrId, 0.0, 0.0));

    // Deep-dive Deck D-Pad
    bindDpad("deck-dpad-up", 0.9, 0.0);
    bindDpad("deck-dpad-down", -0.5, 0.0);
    bindDpad("deck-dpad-left", 0.0, 1.1);
    bindDpad("deck-dpad-right", 0.0, -1.1);
    const deckStop = document.getElementById("deck-dpad-stop");
    if (deckStop) deckStop.addEventListener("click", () => sendTeleopCommand(selectedAmrId, 0.0, 0.0));

    // Keyboard WASD / Arrow Keys Listeners
    window.addEventListener("keydown", (e) => {
      if (document.activeElement && document.activeElement.tagName === "INPUT") return;
      activeKeys[e.key.toLowerCase()] = true;
      processKeyboardTeleop();
    });

    window.addEventListener("keyup", (e) => {
      if (document.activeElement && document.activeElement.tagName === "INPUT") return;
      activeKeys[e.key.toLowerCase()] = false;
      processKeyboardTeleop();
    });
  }

  function processKeyboardTeleop() {
    let v = 0.0;
    let w = 0.0;

    if (activeKeys["w"] || activeKeys["arrowup"]) v += 0.9;
    if (activeKeys["s"] || activeKeys["arrowdown"]) v -= 0.5;
    if (activeKeys["a"] || activeKeys["arrowleft"]) w += 1.1;
    if (activeKeys["d"] || activeKeys["arrowright"]) w -= 1.1;

    if (v !== 0.0 || w !== 0.0) {
      sendTeleopCommand(selectedAmrId, v, w);
    }
  }

  async function setRobotMode(amrId, mode) {
    try {
      const resp = await fetch("/api/amr/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amr_id: amrId, mode: mode })
      });
      const data = await resp.json();
      if (data.success) {
        updateModeUI(mode);
      }
    } catch (e) {}
  }

  function updateModeUI(mode) {
    const btnAuto = document.getElementById("btn-mode-auto");
    const btnManual = document.getElementById("btn-mode-manual");
    const quickPill = document.getElementById("quick-mode-pill");

    const isAuto = mode.toUpperCase() === "AUTONOMOUS";
    if (btnAuto) btnAuto.classList.toggle("active", isAuto);
    if (btnManual) btnManual.classList.toggle("active", !isAuto);

    if (quickPill) {
      quickPill.innerText = isAuto ? "AUTO" : "MANUAL";
      quickPill.className = `pill-status ${isAuto ? "pill-nav" : "pill-manual"}`;
    }
  }

  function sendTeleopCommand(amrId, v, w) {
    fetch("/api/amr/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amr_id: amrId, command: "TELEOP", v, w })
    });
  }

  // --- Mission Creation & Queue ---
  function setupMissionDispatcher() {
    const btnSubmit = document.getElementById("btn-submit-mission");
    if (btnSubmit) {
      btnSubmit.addEventListener("click", () => {
        const pickupSelect = document.getElementById("mission-pickup-select");
        const dropoffSelect = document.getElementById("mission-dropoff-select");
        const skuInput = document.getElementById("mission-sku-input");
        const prioSelect = document.getElementById("mission-priority-select");

        const pickup = pickupSelect.value.split(",").map(Number);
        const dropoff = dropoffSelect.value.split(",").map(Number);
        const sku = skuInput.value.trim() || `SKU-AUTO-${Date.now() % 1000}`;
        const priority = parseInt(prioSelect.value);

        fetch("/api/task/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pickup, dropoff, sku, priority, weight_kg: 250 })
        }).then(() => {
          skuInput.value = "";
        });
      });
    }

    const btnQuickNew = document.getElementById("btn-quick-new-task");
    if (btnQuickNew) {
      btnQuickNew.addEventListener("click", () => {
        document.getElementById("mission-sku-input")?.focus();
      });
    }
  }

  // --- Database Analytics & Table Viewer ---
  function setupDatabaseViewer() {
    const tabs = document.querySelectorAll(".db-tabs-bar .db-tab-btn");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        currentDbTab = tab.dataset.dbtab;
        fetchDatabaseTable(currentDbTab);
      });
    });

    const filterAmr = document.getElementById("db-filter-amr");
    if (filterAmr) {
      filterAmr.addEventListener("change", () => fetchDatabaseTable(currentDbTab));
    }

    const btnExport = document.getElementById("btn-db-export");
    if (btnExport) {
      btnExport.addEventListener("click", () => {
        window.location.href = `/api/db/export?table=${currentDbTab}`;
      });
    }
  }

  async function fetchDatabaseAnalytics() {
    try {
      const resp = await fetch("/api/db/analytics");
      const data = await resp.json();
      if (data.success && data.analytics) {
        const a = data.analytics;
        document.getElementById("db-stat-tasks").innerText = a.total_missions;
        document.getElementById("db-stat-dist").innerText = `${a.total_distance_m} m`;
        document.getElementById("db-stat-records").innerText = a.telemetry_records;
        document.getElementById("db-stat-deadlocks").innerText = a.deadlock_events;
      }
    } catch (e) {}
  }

  async function fetchDatabaseTable(tab) {
    const head = document.getElementById("db-table-head");
    const body = document.getElementById("db-table-body");
    const filterAmr = document.getElementById("db-filter-amr")?.value || "ALL";
    if (!head || !body) return;

    try {
      if (tab === "telemetry") {
        head.innerHTML = `
          <tr>
            <th>ID</th><th>Timestamp</th><th>AMR</th><th>Pose [x, y, θ]</th>
            <th>Speed (v)</th><th>Battery</th><th>Status</th><th>Total Dist</th>
          </tr>
        `;
        const res = await fetch(`/api/db/telemetry?amr_id=${filterAmr}&limit=40`);
        const json = await res.json();
        body.innerHTML = (json.data || []).map(r => `
          <tr>
            <td>#${r.id}</td>
            <td>${r.datetime_str ? r.datetime_str.split(" ")[1] : r.timestamp}</td>
            <td style="color:var(--accent-cyan); font-weight:700;">${r.amr_id}</td>
            <td>[${r.x.toFixed(2)}, ${r.y.toFixed(2)}, ${r.theta.toFixed(2)}]</td>
            <td>${r.v.toFixed(2)} m/s</td>
            <td style="color:${r.battery_soc < 25 ? '#ff1744' : '#76ff03'};">${r.battery_soc.toFixed(1)}%</td>
            <td><span class="pill-status pill-nav">${r.status}</span></td>
            <td>${r.total_distance_m.toFixed(1)} m</td>
          </tr>
        `).join("");

      } else if (tab === "missions") {
        head.innerHTML = `
          <tr>
            <th>Task ID</th><th>SKU</th><th>Weight</th><th>Priority</th>
            <th>Pickup</th><th>Dropoff</th><th>Assigned</th><th>Status</th>
          </tr>
        `;
        const res = await fetch("/api/db/missions?limit=40");
        const json = await res.json();
        body.innerHTML = (json.data || []).map(m => `
          <tr>
            <td style="font-weight:700;">${m.task_id}</td>
            <td>${m.sku}</td>
            <td>${m.weight_kg} kg</td>
            <td>P${m.priority}</td>
            <td>[${m.pickup_x}, ${m.pickup_y}]</td>
            <td>[${m.dropoff_x}, ${m.dropoff_y}]</td>
            <td style="color:var(--accent-cyan);">${m.assigned_amr || 'Unassigned'}</td>
            <td><span class="pill-status pill-${m.status.toLowerCase()}">${m.status}</span></td>
          </tr>
        `).join("");

      } else if (tab === "events") {
        head.innerHTML = `
          <tr>
            <th>ID</th><th>Time</th><th>Category</th><th>AMR</th><th>Message</th><th>Severity</th>
          </tr>
        `;
        const res = await fetch("/api/db/events?limit=40");
        const json = await res.json();
        body.innerHTML = (json.data || []).map(e => `
          <tr>
            <td>#${e.id}</td>
            <td>${e.datetime_str ? e.datetime_str.split(" ")[1] : e.timestamp}</td>
            <td style="color:var(--accent-amber); font-weight:700;">${e.category}</td>
            <td>${e.amr_id || 'System'}</td>
            <td>${e.message}</td>
            <td style="color:${e.severity === 'CRITICAL' ? '#ff1744' : '#76ff03'};">${e.severity}</td>
          </tr>
        `).join("");
      }
    } catch (e) {}
  }

  // --- Dynamic Obstacles & Environment ---
  function setupSettingsAndObstacles() {
    const bindSpawn = (id, type, x, y) => {
      const btn = document.getElementById(id);
      if (btn) {
        btn.addEventListener("click", () => {
          fetch("/api/obstacle/spawn", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ type, x, y })
          });
        });
      }
    };
    bindSpawn("btn-spawn-worker-3d", "worker", 22.0, 14.0);
    bindSpawn("btn-spawn-forklift-3d", "forklift", 36.0, 22.0);
    bindSpawn("settings-spawn-worker", "worker", 22.0, 14.0);
    bindSpawn("settings-spawn-forklift", "forklift", 36.0, 22.0);
  }

  // --- Main State Synchronization Loop ---
  async function fetchWarehouseState() {
    try {
      const res = await fetch("/api/state");
      const state = await res.json();

      if (!warehouseBuilt && state.infrastructure) {
        window.WarehouseScene.buildWarehouse(scene, state.infrastructure);
        warehouseBuilt = true;
      }

      activeTelemetryCache = state.fleet;
      sync3DFleet(state.fleet);
      syncPallets(state.pallets);
      syncDynamicObstacles(state.dynamic_obstacles);
      syncQuickCards(state.fleet);
      syncFleetDeepDive(state.fleet);
      syncMissionsTable(state.tasks);

    } catch (err) {}
  }

  function sync3DFleet(fleet) {
    fleet.forEach(amr => {
      if (!robotMeshes[amr.id]) {
        const mesh = window.AMR3DModel.createRobotMesh(amr);
        scene.add(mesh);
        robotMeshes[amr.id] = mesh;

        const visualizer = new window.SensorVisualizer.AMRVisualizer(scene, amr.id, amr.color);
        robotVisualizers[amr.id] = visualizer;
      }

      const mesh = robotMeshes[amr.id];
      mesh.position.x = amr.pose[0];
      mesh.position.z = amr.pose[1];
      mesh.rotation.y = -amr.pose[2];

      if (mesh.userData.lidarRotor) {
        mesh.userData.lidarRotor.rotation.y += 0.25;
      }

      if (mesh.userData.lifterGroup) {
        mesh.userData.lifterGroup.position.y = 0.33 + amr.lifter_height;
      }

      // Safety LED Light Ring Colors
      if (mesh.userData.ledMaterial) {
        let ledColor = 0x00e5ff;
        if (amr.status === "CHARGING") ledColor = 0x10b981;
        else if (amr.status === "RECOVERY") ledColor = 0xf59e0b;
        else if (amr.status === "ESTOP") ledColor = 0xff1744;
        else if (amr.status === "MANUAL") ledColor = 0xff9100;
        else if (amr.status === "LIFTING" || amr.status === "LOWERING") ledColor = 0xd500f9;
        mesh.userData.ledMaterial.color.setHex(ledColor);
        mesh.userData.ledMaterial.emissive.setHex(ledColor);
      }

      if (robotVisualizers[amr.id]) {
        robotVisualizers[amr.id].update(amr);
      }
    });

    updateTrackingCamera(fleet);
  }

  function updateTrackingCamera(fleet) {
    const activeAmr = fleet.find(a => a.id === selectedAmrId);
    if (!activeAmr) return;

    const x = activeAmr.pose[0];
    const z = activeAmr.pose[1];
    const th = activeAmr.pose[2];

    if (cameraMode === "chase") {
      const dist = 4.5;
      const camX = x - Math.cos(th) * dist;
      const camZ = z + Math.sin(th) * dist;
      camera.position.lerp(new THREE.Vector3(camX, 2.5, camZ), 0.1);
      if (controls) controls.target.lerp(new THREE.Vector3(x, 0.5, z), 0.1);
    } else if (cameraMode === "sensor_pov") {
      const camX = x + Math.cos(th) * 0.45;
      const camZ = z - Math.sin(th) * 0.45;
      camera.position.set(camX, 0.45, camZ);
      const lookX = x + Math.cos(th) * 5.0;
      const lookZ = z - Math.sin(th) * 5.0;
      camera.lookAt(lookX, 0.35, lookZ);
    }
  }

  function syncPallets(pallets) {
    pallets.forEach(pallet => {
      if (!palletMeshes[pallet.id]) {
        const mesh = window.AMR3DModel.createPalletMesh(pallet);
        scene.add(mesh);
        palletMeshes[pallet.id] = mesh;
      }
      const mesh = palletMeshes[pallet.id];
      mesh.position.x = pallet.x;
      mesh.position.z = pallet.y;

      if (pallet.carried_by && robotMeshes[pallet.carried_by]) {
        const amrMesh = robotMeshes[pallet.carried_by];
        mesh.position.x = amrMesh.position.x;
        mesh.position.z = amrMesh.position.z;
        mesh.position.y = amrMesh.userData.lifterGroup ? amrMesh.userData.lifterGroup.position.y + 0.05 : 0.45;
        mesh.rotation.y = amrMesh.rotation.y;
      } else {
        mesh.position.y = 0.0;
      }
    });
  }

  function syncDynamicObstacles(obstacles) {
    obstacles.forEach(obs => {
      if (!dynamicObstacleMeshes[obs.id]) {
        let mesh = obs.type === "forklift"
          ? window.WarehouseScene.createDynamicForkliftMesh()
          : window.WarehouseScene.createDynamicWorkerMesh();
        scene.add(mesh);
        dynamicObstacleMeshes[obs.id] = mesh;
      }
      const mesh = dynamicObstacleMeshes[obs.id];
      mesh.position.x = obs.x;
      mesh.position.z = obs.y;
      if (obs.vx !== 0 || obs.vy !== 0) {
        mesh.rotation.y = Math.atan2(-obs.vy, obs.vx);
      }
    });
  }

  // --- Quick 3D HUD Left Cards ---
  function syncQuickCards(fleet) {
    const container = document.getElementById("quick-amr-cards-container");
    if (!container) return;

    container.innerHTML = fleet.map(amr => `
      <div class="amr-card ${amr.id === selectedAmrId ? 'selected' : ''}" onclick="window.selectAmr('${amr.id}')" style="cursor:pointer; padding:8px 10px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; align-items:center; gap:6px; font-weight:700; font-size:0.75rem;">
            <div style="width:8px; height:8px; border-radius:50%; background:${amr.color};"></div>
            <span>${amr.name}</span>
          </div>
          <span class="pill-status pill-${amr.status.toLowerCase().split('_')[0]}">${amr.status}</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.65rem; color:var(--text-muted); margin-top:4px; font-family:var(--font-mono);">
          <span>Bat: <strong style="color:#76ff03;">${amr.battery}%</strong></span>
          <span>Spd: <strong>${Math.abs(amr.velocity[0]).toFixed(2)} m/s</strong></span>
          <span>Mode: <strong style="color:var(--accent-cyan);">${amr.mode || 'AUTO'}</strong></span>
        </div>
      </div>
    `).join("");

    document.getElementById("quick-selected-amr").innerText = selectedAmrId;
    const active = fleet.find(a => a.id === selectedAmrId);
    if (active) {
      updateModeUI(active.mode || "AUTONOMOUS");
    }
  }

  // --- Fleet Monitor View Deep Dive ---
  function syncFleetDeepDive(fleet) {
    const cardsContainer = document.getElementById("fleet-selector-cards");
    if (!cardsContainer) return;

    cardsContainer.innerHTML = fleet.map(amr => `
      <div class="robot-tab-card ${amr.id === selectedAmrId ? 'active' : ''}" onclick="window.selectAmr('${amr.id}')">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div style="display:flex; align-items:center; gap:8px; font-weight:700;">
            <div style="width:10px; height:10px; border-radius:50%; background:${amr.color};"></div>
            <span>${amr.name}</span>
          </div>
          <span class="pill-status pill-${amr.status.toLowerCase().split('_')[0]}">${amr.status}</span>
        </div>
        <div style="font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono); display:flex; justify-content:space-between;">
          <span>SOC: ${amr.battery}%</span>
          <span>Mode: ${amr.mode || 'AUTO'}</span>
        </div>
      </div>
    `).join("");

    const active = fleet.find(a => a.id === selectedAmrId);
    if (!active) return;

    document.getElementById("fleet-selected-name").innerText = `${active.name} (${active.id})`;
    document.getElementById("gauge-speed").innerHTML = `${Math.abs(active.velocity[0]).toFixed(2)} <span style="font-size:0.9rem;">m/s</span>`;
    document.getElementById("gauge-angular").innerText = `ω: ${active.velocity[1].toFixed(2)} rad/s`;
    document.getElementById("gauge-battery").innerText = `${active.battery}%`;
    document.getElementById("gauge-voltage").innerText = `${active.voltage} V (LiFePO4)`;
    document.getElementById("gauge-lifter").innerHTML = `${(active.lifter_height * 100).toFixed(1)} <span style="font-size:0.9rem;">cm</span>`;
    document.getElementById("gauge-lifter-state").innerText = active.lifter_state;
    document.getElementById("gauge-odometer").innerHTML = `${active.total_distance_m} <span style="font-size:0.9rem;">m</span>`;

    document.getElementById("pos-truth").innerText = `[${active.pose[0].toFixed(2)}, ${active.pose[1].toFixed(2)}, ${active.pose[2].toFixed(2)}]`;
    document.getElementById("pos-ekf").innerText = `[${active.estimated_pose[0].toFixed(2)}, ${active.estimated_pose[1].toFixed(2)}, ${active.estimated_pose[2].toFixed(2)}]`;
    document.getElementById("pos-goal").innerText = active.path && active.path.length ? `[${active.path[active.path.length - 1][0]}, ${active.path[active.path.length - 1][1]}]` : 'None';
    document.getElementById("pos-payload").innerText = active.carrying_pallet ? active.carrying_pallet.sku : 'None';
    document.getElementById("pos-recovery").innerText = active.recovery_tier || 'NORMAL';

    updateModeUI(active.mode || "AUTONOMOUS");
  }

  // --- Missions View Synchronization ---
  function syncMissionsTable(tasks) {
    const tbody = document.getElementById("missions-table-body");
    if (!tbody) return;

    if (!tasks || tasks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-dim); padding:16px;">No missions currently in queue.</td></tr>`;
      return;
    }

    tbody.innerHTML = tasks.map(t => `
      <tr>
        <td style="font-weight:700; color:#fff;">${t.id}</td>
        <td>${t.pallet ? t.pallet.sku : 'Cargo Box'}</td>
        <td>${t.pallet ? t.pallet.weight_kg : 250} kg</td>
        <td><strong style="color:${t.priority === 3 ? '#ff1744' : (t.priority === 2 ? '#f59e0b' : '#00e5ff')};">P${t.priority}</strong></td>
        <td>${t.pallet ? `[${t.pallet.pickup[0]}, ${t.pallet.pickup[1]}]` : 'Dock A'}</td>
        <td>${t.pallet ? `[${t.pallet.dropoff[0]}, ${t.pallet.dropoff[1]}]` : 'Rack C2'}</td>
        <td style="color:var(--accent-cyan); font-weight:700;">${t.assigned_amr || 'Searching...'}</td>
        <td><span class="pill-status pill-${t.status.toLowerCase()}">${t.status}</span></td>
      </tr>
    `).join("");
  }

  window.selectAmr = function (amrId) {
    selectedAmrId = amrId;
    if (activeTelemetryCache.length) {
      syncQuickCards(activeTelemetryCache);
      syncFleetDeepDive(activeTelemetryCache);
    }
  };

  function animate() {
    requestAnimationFrame(animate);
    if (controls && (cameraMode === "orbit" || cameraMode === "topdown")) {
      controls.update();
    }
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  window.addEventListener("DOMContentLoaded", initApplication);
})();

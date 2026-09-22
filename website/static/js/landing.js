/**
 * CampusOS Cinematic 3D Scrollytelling Engine
 * Three.js 3D WebGL Universe + Web Audio Haptics + Interactive Playgrounds + Lenis + GSAP
 */

(() => {
  "use strict";

  // Helpers
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let lenisInstance = null;
  let webglWorld = null;
  let audioEngine = null;

  window.addEventListener("DOMContentLoaded", () => {
    initLenisSmoothScroll();
    initThreeJsUniverse();
    initWebAudioEngine();
    initCursorSpotlight();
    initHeaderAndProgress();
    initPipelineTelemetryHUD();
    initRolePerspectiveSwitcher();
    initAgentSimulations();
    initSectionMoodLighting();
    initInteractiveTilts();

    if (typeof gsap !== "undefined" && typeof ScrollTrigger !== "undefined") {
      gsap.registerPlugin(ScrollTrigger);
      initHeroTheater();
      initKineticProblemScrub();
      initPinnedAgentStages();
      initConduitHighways();
      initDayInLifeCards();
      initOrchestrationMatrix();
      initFinalCTA();
    }
  });

  /* ========================================================================= */
  /* 1. LENIS INERTIAL SMOOTH SCROLL                                           */
  /* ========================================================================= */
  function initLenisSmoothScroll() {
    if (typeof Lenis === "undefined" || reduceMotion) return;

    lenisInstance = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: "vertical",
      gestureOrientation: "vertical",
      smoothWheel: true,
      wheelMultiplier: 1.05,
      touchMultiplier: 1.8
    });

    lenisInstance.on("scroll", ScrollTrigger.update);

    gsap.ticker.add((time) => {
      lenisInstance.raf(time * 1000);
    });

    gsap.ticker.lagSmoothing(0);

    // Smooth anchor click handling via Lenis
    $$('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", (e) => {
        const href = anchor.getAttribute("href");
        if (href === "#") return;
        const target = $(href);
        if (target) {
          e.preventDefault();
          lenisInstance.scrollTo(target, { offset: -30, duration: 1.4 });
        }
      });
    });
  }

  /* ========================================================================= */
  /* 2. WEB AUDIO API SYNTHESIZER & HAPTIC SOUND ENGINE                         */
  /* ========================================================================= */
  function initWebAudioEngine() {
    let ctx = null;
    let isMuted = true;
    let droneOsc1 = null, droneOsc2 = null, droneGain = null;

    const audioToggleBtn = $("#audioToggleBtn");
    const audioLabel = $("#audioLabel");

    function getContext() {
      if (!ctx) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) ctx = new AudioCtx();
      }
      if (ctx && ctx.state === "suspended") {
        ctx.resume();
      }
      return ctx;
    }

    function playHapticTick(freq = 440, type = "sine", duration = 0.04) {
      if (isMuted) return;
      const c = getContext();
      if (!c) return;

      const osc = c.createOscillator();
      const gain = c.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, c.currentTime);
      osc.frequency.exponentialRampToValueAtTime(freq * 0.5, c.currentTime + duration);

      gain.gain.setValueAtTime(0.06, c.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + duration);

      osc.connect(gain);
      gain.connect(c.destination);
      osc.start();
      osc.stop(c.currentTime + duration);
    }

    function playLaserHum() {
      if (isMuted) return;
      const c = getContext();
      if (!c) return;

      const osc = c.createOscillator();
      const gain = c.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(880, c.currentTime);
      osc.frequency.exponentialRampToValueAtTime(220, c.currentTime + 0.35);

      gain.gain.setValueAtTime(0.05, c.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + 0.35);

      osc.connect(gain);
      gain.connect(c.destination);
      osc.start();
      osc.stop(c.currentTime + 0.35);
    }

    function playTransitionWhoosh() {
      if (isMuted) return;
      const c = getContext();
      if (!c) return;

      const osc = c.createOscillator();
      const gain = c.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(120, c.currentTime);
      osc.frequency.exponentialRampToValueAtTime(420, c.currentTime + 0.25);
      osc.frequency.exponentialRampToValueAtTime(180, c.currentTime + 0.5);

      gain.gain.setValueAtTime(0.08, c.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + 0.5);

      osc.connect(gain);
      gain.connect(c.destination);
      osc.start();
      osc.stop(c.currentTime + 0.5);
    }

    function startAmbientDrone() {
      const c = getContext();
      if (!c || droneGain) return;

      droneGain = c.createGain();
      droneGain.gain.setValueAtTime(0.02, c.currentTime);

      droneOsc1 = c.createOscillator();
      droneOsc1.type = "sine";
      droneOsc1.frequency.setValueAtTime(55, c.currentTime); // A1 note

      droneOsc2 = c.createOscillator();
      droneOsc2.type = "triangle";
      droneOsc2.frequency.setValueAtTime(82.4, c.currentTime); // E2 fifth

      droneOsc1.connect(droneGain);
      droneOsc2.connect(droneGain);
      droneGain.connect(c.destination);

      droneOsc1.start();
      droneOsc2.start();
    }

    function stopAmbientDrone() {
      if (droneGain && ctx) {
        droneGain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.3);
        setTimeout(() => {
          droneOsc1?.stop();
          droneOsc2?.stop();
          droneOsc1 = null;
          droneOsc2 = null;
          droneGain = null;
        }, 350);
      }
    }

    if (audioToggleBtn) {
      audioToggleBtn.addEventListener("click", () => {
        const c = getContext();
        if (isMuted) {
          isMuted = false;
          audioToggleBtn.classList.add("active");
          if (audioLabel) audioLabel.textContent = "AUDIO: ON";
          startAmbientDrone();
          playHapticTick(660, "sine", 0.08);
        } else {
          isMuted = true;
          audioToggleBtn.classList.remove("active");
          if (audioLabel) audioLabel.textContent = "AUDIO: OFF";
          stopAmbientDrone();
        }
      });
    }

    audioEngine = {
      playHapticTick,
      playLaserHum,
      playTransitionWhoosh
    };
  }

  /* ========================================================================= */
  /* 3. THREE.JS 3D WEBGL UNIVERSE WITH SHOCKWAVE PARTICLE PHYSICS             */
  /* ========================================================================= */
  function initThreeJsUniverse() {
    const canvas = $("#webglCanvas");
    if (!canvas || typeof THREE === "undefined" || reduceMotion) return;

    // --- Scene, Camera, Renderer ---
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x040407, 0.028);

    const camera = new THREE.PerspectiveCamera(
      50,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.set(0, 0, 32);

    const renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance"
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // --- Lighting ---
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const cyanPoint = new THREE.PointLight(0x38bdf8, 3.5, 80);
    cyanPoint.position.set(15, 12, 18);
    scene.add(cyanPoint);

    const violetPoint = new THREE.PointLight(0x818cf8, 3.0, 80);
    violetPoint.position.set(-15, -10, 15);
    scene.add(violetPoint);

    const emeraldPoint = new THREE.PointLight(0x34d399, 2.5, 70);
    emeraldPoint.position.set(0, -18, 10);
    scene.add(emeraldPoint);

    // --- Generate Glowing Particle Texture in Memory ---
    function createGlowSprite() {
      const c = document.createElement("canvas");
      c.width = 64;
      c.height = 64;
      const ctx = c.getContext("2d");
      const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
      gradient.addColorStop(0, "rgba(255, 255, 255, 1)");
      gradient.addColorStop(0.25, "rgba(91, 140, 255, 0.85)");
      gradient.addColorStop(0.55, "rgba(56, 189, 248, 0.35)");
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 64, 64);
      return new THREE.CanvasTexture(c);
    }
    const particleTexture = createGlowSprite();

    // --- 3,600 Morphing Particle Geometries & Velocities ---
    const PARTICLE_COUNT = 3600;
    const geometry = new THREE.BufferGeometry();
    const currentPositions = new Float32Array(PARTICLE_COUNT * 3);
    const targetPositions = new Float32Array(PARTICLE_COUNT * 3);
    const velocities = new Float32Array(PARTICLE_COUNT * 3);
    const colors = new Float32Array(PARTICLE_COUNT * 3);

    // Target Shapes Array Generators
    const targets = {
      hero: new Float32Array(PARTICLE_COUNT * 3),
      problem: new Float32Array(PARTICLE_COUNT * 3),
      agent1: new Float32Array(PARTICLE_COUNT * 3),
      agent2: new Float32Array(PARTICLE_COUNT * 3),
      agent3: new Float32Array(PARTICLE_COUNT * 3),
      orchestration: new Float32Array(PARTICLE_COUNT * 3)
    };

    // Populate Target 0: Torus Knot (Hero)
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const u = (i / PARTICLE_COUNT) * Math.PI * 2 * 3;
      const v = (i / PARTICLE_COUNT) * Math.PI * 2 * 2;
      const r = 4.5 + Math.cos(v) * 2.2 + (Math.random() - 0.5) * 0.8;
      const x = r * Math.cos(u);
      const y = r * Math.sin(u);
      const z = Math.sin(v) * 3.5 + (Math.random() - 0.5) * 1.2;

      targets.hero[i * 3] = x;
      targets.hero[i * 3 + 1] = y;
      targets.hero[i * 3 + 2] = z;

      currentPositions[i * 3] = x;
      currentPositions[i * 3 + 1] = y;
      currentPositions[i * 3 + 2] = z;

      targetPositions[i * 3] = x;
      targetPositions[i * 3 + 1] = y;
      targetPositions[i * 3 + 2] = z;

      colors[i * 3] = 0.22 + Math.random() * 0.2;
      colors[i * 3 + 1] = 0.65 + Math.random() * 0.35;
      colors[i * 3 + 2] = 0.98;
    }

    // Populate Target 1: Problem Fragmented Chaos
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const cluster = i % 3;
      const angle = (i / PARTICLE_COUNT) * Math.PI * 2 + (cluster * Math.PI * 2) / 3;
      const dist = 7 + Math.random() * 16;
      targets.problem[i * 3] = Math.cos(angle) * dist + (Math.random() - 0.5) * 6;
      targets.problem[i * 3 + 1] = Math.sin(angle) * dist * 0.8 + (Math.random() - 0.5) * 6;
      targets.problem[i * 3 + 2] = (Math.random() - 0.5) * 14;
    }

    // Populate Target 2: Agent 1 (AttendMate Biometric Face / Scan Sphere)
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const phi = Math.acos(1 - (2 * (i + 0.5)) / PARTICLE_COUNT);
      const theta = Math.PI * (1 + 5 ** 0.5) * i;
      const radX = 6.2;
      const radY = 8.5;
      const radZ = 5.2;

      const y = radY * Math.cos(phi);
      const taper = y < 0 ? 1 + y * 0.04 : 1;

      targets.agent1[i * 3] = radX * Math.sin(phi) * Math.cos(theta) * taper;
      targets.agent1[i * 3 + 1] = y;
      targets.agent1[i * 3 + 2] = radZ * Math.sin(phi) * Math.sin(theta);
    }

    // Populate Target 3: Agent 2 (Synapse Neural Brain Graph)
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const hemi = i % 2 === 0 ? 1 : -1;
      const u = Math.random() * Math.PI;
      const v = Math.random() * Math.PI * 2;
      const r = 6.8 + Math.sin(u * 5) * 0.8 + Math.cos(v * 4) * 0.6;

      targets.agent2[i * 3] = r * Math.sin(u) * Math.cos(v) + hemi * 1.8;
      targets.agent2[i * 3 + 1] = r * Math.cos(u) * 1.1;
      targets.agent2[i * 3 + 2] = r * Math.sin(u) * Math.sin(v) * 0.9;
    }

    // Populate Target 4: Agent 3 (Resume-IQ 3D Gyroscope & Radar Disk)
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const ring = i % 4;
      const radius = ring === 0 ? 4.0 : ring === 1 ? 7.2 : ring === 2 ? 10.5 : 13.0;
      const angle = (i / PARTICLE_COUNT) * Math.PI * 2 * (ring + 1);
      const tilt = ring * 0.45;

      targets.agent3[i * 3] = Math.cos(angle) * radius;
      targets.agent3[i * 3 + 1] = Math.sin(angle) * radius * Math.cos(tilt) + (Math.random() - 0.5) * 0.6;
      targets.agent3[i * 3 + 2] = Math.sin(angle) * radius * Math.sin(tilt);
    }

    // Populate Target 5: Orchestration (4-Node Satellite Singularity)
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const node = i % 5;
      if (node === 0) {
        const phi = Math.acos(1 - (2 * (i + 0.5)) / (PARTICLE_COUNT / 5));
        const theta = Math.PI * 2.236 * i;
        const r = 2.8 + Math.random() * 0.8;
        targets.orchestration[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        targets.orchestration[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        targets.orchestration[i * 3 + 2] = r * Math.cos(phi);
      } else {
        const satIdx = node - 1;
        const satAngle = (satIdx * Math.PI) / 2;
        const satCenterX = Math.cos(satAngle) * 9.5;
        const satCenterY = Math.sin(satAngle) * 9.5;
        const r = 2.0 + Math.random() * 0.6;
        const subAngle = Math.random() * Math.PI * 2;
        const subZ = (Math.random() - 0.5) * 2.2;

        targets.orchestration[i * 3] = satCenterX + Math.cos(subAngle) * r;
        targets.orchestration[i * 3 + 1] = satCenterY + Math.sin(subAngle) * r;
        targets.orchestration[i * 3 + 2] = subZ;
      }
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(currentPositions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const particleMaterial = new THREE.PointsMaterial({
      size: 0.85,
      map: particleTexture,
      transparent: true,
      vertexColors: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const particleSystem = new THREE.Points(geometry, particleMaterial);
    scene.add(particleSystem);

    // --- 3D Holographic Laser Plane ---
    const laserPlaneGeo = new THREE.PlaneGeometry(16, 0.08);
    const laserPlaneMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0,
      side: THREE.DoubleSide
    });
    const laserPlane = new THREE.Mesh(laserPlaneGeo, laserPlaneMat);
    laserPlane.position.z = 2;
    scene.add(laserPlane);

    // --- 3D Wireframe Reactor Rings ---
    const ringGeo1 = new THREE.TorusGeometry(8.5, 0.04, 16, 100);
    const ringMat1 = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.35, wireframe: true });
    const wireRing1 = new THREE.Mesh(ringGeo1, ringMat1);
    scene.add(wireRing1);

    const ringGeo2 = new THREE.TorusGeometry(12.5, 0.03, 16, 100);
    const ringMat2 = new THREE.MeshBasicMaterial({ color: 0x818cf8, transparent: true, opacity: 0.25, wireframe: true });
    const wireRing2 = new THREE.Mesh(ringGeo2, ringMat2);
    wireRing2.rotation.x = Math.PI * 0.45;
    scene.add(wireRing2);

    // --- Mouse & Dynamic Tilt Control ---
    let mouseX = 0, mouseY = 0;
    let targetCameraRotX = 0, targetCameraRotY = 0;
    let currentCameraZ = 32;
    let targetCameraZ = 32;

    window.addEventListener("pointermove", (e) => {
      mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
      targetCameraRotY = mouseX * 0.18;
      targetCameraRotX = -mouseY * 0.14;
    }, { passive: true });

    // --- 3D Shockwave Impulse on Click / Tap ---
    window.addEventListener("pointerdown", (e) => {
      // Don't trigger shockwave if clicking inside form or inputs
      if (e.target.closest("button, a, input, textarea")) return;

      const clickX = (e.clientX / window.innerWidth - 0.5) * 28;
      const clickY = -(e.clientY / window.innerHeight - 0.5) * 20;

      audioEngine?.playHapticTick(320, "triangle", 0.06);

      const positions = geometry.attributes.position.array;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const px = positions[i * 3];
        const py = positions[i * 3 + 1];
        const pz = positions[i * 3 + 2];

        const dx = px - clickX;
        const dy = py - clickY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 12) {
          const force = (12 - dist) * 0.45;
          velocities[i * 3] += (dx / (dist + 0.1)) * force;
          velocities[i * 3 + 1] += (dy / (dist + 0.1)) * force;
          velocities[i * 3 + 2] += (Math.random() - 0.5) * force * 1.5;
        }
      }
    });

    // Resize handler
    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }, { passive: true });

    // Morph state controller
    let currentTargetArray = targets.hero;
    let morphSpeed = 0.07;
    let activeLaserIntensity = 0;

    function set3DTargetShape(shapeName, cameraZ = 32, laserIntensity = 0) {
      if (targets[shapeName]) {
        currentTargetArray = targets[shapeName];
        targetCameraZ = cameraZ;
        activeLaserIntensity = laserIntensity;
        audioEngine?.playTransitionWhoosh();
      }
    }

    // --- Render Loop (60-120 FPS WebGL with Spring Physics) ---
    let clock = new THREE.Clock();

    function renderLoop() {
      const elapsed = clock.getElapsedTime();

      const positions = geometry.attributes.position.array;
      for (let i = 0; i < PARTICLE_COUNT * 3; i++) {
        // Spring physics: pull toward target + apply velocity damping
        const diff = currentTargetArray[i] - positions[i];
        velocities[i] += diff * 0.05;
        velocities[i] *= 0.88; // Damping
        positions[i] += velocities[i];
      }
      geometry.attributes.position.needsUpdate = true;

      // Rotate particle cloud & rings
      particleSystem.rotation.y = elapsed * 0.08;
      particleSystem.rotation.z = Math.sin(elapsed * 0.05) * 0.05;

      wireRing1.rotation.z = elapsed * 0.12;
      wireRing2.rotation.y = elapsed * 0.09;

      // Laser plane sweep
      if (activeLaserIntensity > 0) {
        laserPlane.material.opacity = activeLaserIntensity * (0.6 + Math.sin(elapsed * 4) * 0.3);
        laserPlane.position.y = Math.sin(elapsed * 2.2) * 5.5;
      } else {
        laserPlane.material.opacity = 0;
      }

      // Smooth Camera Lerp with mouse parallax
      camera.rotation.y += (targetCameraRotY - camera.rotation.y) * 0.05;
      camera.rotation.x += (targetCameraRotX - camera.rotation.x) * 0.05;
      currentCameraZ += (targetCameraZ - currentCameraZ) * 0.06;
      camera.position.z = currentCameraZ;

      renderer.render(scene, camera);
      requestAnimationFrame(renderLoop);
    }
    renderLoop();

    webglWorld = {
      set3DTargetShape,
      scene,
      camera,
      targets
    };
  }

  /* ========================================================================= */
  /* 4. ROLE PERSPECTIVE SWITCHER (STUDENT / FACULTY / ADMIN)                  */
  /* ========================================================================= */
  function initRolePerspectiveSwitcher() {
    const tabBtns = $$(".ps-tab-btn");
    const insightBox = $("#psDynamicInsight");
    const data = window.CAMPUS_OS_DATA?.perspectives;

    if (!tabBtns.length || !insightBox || !data) return;

    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        const pKey = btn.dataset.perspective;
        const pData = data[pKey];
        if (pData) {
          audioEngine?.playHapticTick(520, "sine", 0.05);
          insightBox.innerHTML = `
            <span class="ps-insight-title">${pData.title}:</span>
            <span class="ps-insight-text">${pData.tagline}</span>
          `;
        }
      });
    });
  }

  /* ========================================================================= */
  /* 5. INTERACTIVE AGENT SIMULATIONS (PLAYGROUNDS)                            */
  /* ========================================================================= */
  function initAgentSimulations() {
    const data = window.CAMPUS_OS_DATA?.simulations;

    // --- Agent 1: Live Biometric Scan Simulation ---
    const btnSimulateScan = $("#btnSimulateScan");
    const attendmateScore = $("#attendmateScore");
    const cosineProgressFill = $("#cosineProgressFill");
    const qcInference = $("#qcInference");
    const reticleIdBadge = $("#reticleIdBadge");

    if (btnSimulateScan) {
      btnSimulateScan.addEventListener("click", () => {
        audioEngine?.playLaserHum();
        btnSimulateScan.classList.add("scanning");
        btnSimulateScan.innerHTML = `<span>Scanning Biometric Vectors...</span>`;

        if (reticleIdBadge) reticleIdBadge.textContent = "AUTHENTICATING...";

        setTimeout(() => {
          btnSimulateScan.classList.remove("scanning");
          btnSimulateScan.innerHTML = `<span class="sim-scan-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></span><span>Trigger Live Biometric Scan</span>`;

          const randomScore = (99.4 + Math.random() * 0.55).toFixed(1);
          if (attendmateScore) attendmateScore.textContent = `${randomScore}%`;
          if (cosineProgressFill) cosineProgressFill.style.width = `${randomScore}%`;
          if (qcInference) qcInference.textContent = `0.${Math.floor(22 + Math.random() * 8)}s`;
          if (reticleIdBadge) reticleIdBadge.textContent = "Alex Vance • CS-2026-892 (VERIFIED)";

          audioEngine?.playHapticTick(880, "sine", 0.08);
        }, 1200);
      });
    }

    // --- Agent 2: Synapse AI Topic Switcher ---
    const topicBtns = $$(".topic-chip-btn");
    const synapseTopicSub = $("#synapseTopicSub");
    const synapseQueryText = $("#synapseQueryText");
    const synapseAnalogyText = $("#synapseAnalogyText");
    const synapseMathFormula = $("#synapseMathFormula");
    const synapseCompLift = $("#synapseCompLift");
    const rmStep1 = $("#rmStep1");
    const rmStep2 = $("#rmStep2");
    const rmStep3 = $("#rmStep3");

    if (topicBtns.length && data?.synapseTopics) {
      topicBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          topicBtns.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");

          const topicKey = btn.dataset.topic;
          const topicInfo = data.synapseTopics[topicKey];
          if (topicInfo) {
            audioEngine?.playHapticTick(580, "sine", 0.05);

            if (synapseTopicSub) synapseTopicSub.textContent = `Active Subject: CS402 ${topicKey}`;
            if (synapseQueryText) synapseQueryText.textContent = `"Explain ${topicKey} with a simple intuitive mental model and roadmap."`;
            if (synapseAnalogyText) synapseAnalogyText.innerHTML = `"${topicInfo.analogy}"`;
            if (synapseMathFormula) synapseMathFormula.innerHTML = `<span>${topicInfo.math}</span>`;
            if (synapseCompLift) synapseCompLift.textContent = topicInfo.metric;

            if (rmStep1 && topicInfo.roadmap[0]) rmStep1.textContent = topicInfo.roadmap[0];
            if (rmStep2 && topicInfo.roadmap[1]) rmStep2.textContent = topicInfo.roadmap[1];
            if (rmStep3 && topicInfo.roadmap[2]) rmStep3.textContent = topicInfo.roadmap[2];
          }
        });
      });
    }

    // --- Agent 3: Resume-IQ Before/After ATS Toggle ---
    const atsModeBtns = $$(".abat-btn");
    const atsScoreVal = $("#atsScoreVal");
    const atsRankLbl = $("#atsRankLbl");
    const atsDialMeter = $("#atsDialMeter");
    const atsBulletsList = $("#atsBulletsList");

    if (atsModeBtns.length && data?.resumeATS) {
      atsModeBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          atsModeBtns.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");

          const mode = btn.dataset.atsMode;
          const atsData = data.resumeATS[mode];
          if (atsData) {
            audioEngine?.playHapticTick(mode === "after" ? 720 : 380, "sine", 0.06);

            if (atsScoreVal) atsScoreVal.textContent = `${atsData.score}%`;
            if (atsRankLbl) atsRankLbl.textContent = atsData.rank.toUpperCase();

            if (atsDialMeter) {
              const total = 314;
              const offset = total - (total * (atsData.score / 100));
              atsDialMeter.style.strokeDashoffset = offset;
            }

            if (atsBulletsList) {
              atsBulletsList.innerHTML = atsData.bullets.map(b => `<li>${b}</li>`).join("");
            }
          }
        });
      });
    }

    // --- Agent 4: Campus-Desk Query Inquiries ---
    const promptBtns = $$(".prompt-chip-btn");
    const campusUserQueryText = $("#campusUserQueryText");
    const campusBotAnswerText = $("#campusBotAnswerText");
    const campusDocFileName = $("#campusDocFileName");
    const campusLookupTime = $("#campusLookupTime");

    if (promptBtns.length && data?.campusInquiries) {
      promptBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
          promptBtns.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");

          const inqKey = btn.dataset.inquiry;
          const inqData = data.campusInquiries[inqKey];
          if (inqData) {
            audioEngine?.playHapticTick(640, "sine", 0.05);

            if (campusUserQueryText) campusUserQueryText.textContent = `"How do I access the ${inqKey} details and official documentation?"`;
            if (campusBotAnswerText) campusBotAnswerText.innerHTML = `"${inqData.answer}"`;
            if (campusDocFileName) campusDocFileName.textContent = inqData.doc;
            if (campusLookupTime) campusLookupTime.textContent = inqData.time;
          }
        });
      });
    }
  }

  /* ========================================================================= */
  /* 6. MOUSE SPOTLIGHT FOLLOWER                                               */
  /* ========================================================================= */
  function initCursorSpotlight() {
    const spot = $("#cursorSpotlight");
    if (!spot || reduceMotion) return;

    let mx = window.innerWidth / 2, my = window.innerHeight / 2;
    let cx = mx, cy = my;

    window.addEventListener("pointermove", (e) => {
      mx = e.clientX;
      my = e.clientY;
    }, { passive: true });

    function render() {
      cx += (mx - cx) * 0.1;
      cy += (my - cy) * 0.1;
      spot.style.transform = `translate(${cx}px, ${cy}px)`;
      requestAnimationFrame(render);
    }
    requestAnimationFrame(render);
  }

  /* ========================================================================= */
  /* 7. HEADER & TOP SCROLL PROGRESS BAR                                       */
  /* ========================================================================= */
  function initHeaderAndProgress() {
    const header = $("#cinematicHeader");
    const progressFill = $("#scrollProgressFill");

    window.addEventListener("scroll", () => {
      const scrollY = window.scrollY;
      if (scrollY > 60) {
        header?.classList.add("scrolled");
      } else {
        header?.classList.remove("scrolled");
      }

      if (progressFill) {
        const doc = document.documentElement;
        const total = doc.scrollHeight - doc.clientHeight;
        const p = total > 0 ? scrollY / total : 0;
        progressFill.style.transform = `scaleX(${p})`;
      }
    }, { passive: true });
  }

  /* ========================================================================= */
  /* 8. FLOATING PIPELINE TELEMETRY HUD (EXPAND / CONTRACT & AUTO-COLLAPSE)     */
  /* ========================================================================= */
  function initPipelineTelemetryHUD() {
    const hud = $("#pipelineStatusHud");
    const headerToggle = $("#hudHeaderToggle");
    const collapsedPreview = $("#hudCollapsedPreview");
    const toggleBtn = $("#hudToggleBtn");

    if (!hud) return;

    let isExpanded = true;
    let autoCollapseTimer = null;

    function contractHUD() {
      if (!isExpanded) return;
      hud.classList.remove("expanded");
      hud.classList.add("collapsed");
      isExpanded = false;
    }

    function expandHUD() {
      if (isExpanded) return;
      hud.classList.remove("collapsed");
      hud.classList.add("expanded");
      isExpanded = true;
      audioEngine?.playHapticTick(620, "sine", 0.05);
    }

    // Auto-contract after 2 seconds on page load
    autoCollapseTimer = setTimeout(() => {
      contractHUD();
    }, 2000);

    // Cancel auto-collapse if user hovers or interacts before 2 seconds
    hud.addEventListener("pointerenter", () => {
      if (autoCollapseTimer) {
        clearTimeout(autoCollapseTimer);
        autoCollapseTimer = null;
      }
    });

    if (collapsedPreview) {
      collapsedPreview.addEventListener("click", (e) => {
        e.stopPropagation();
        expandHUD();
      });
    }

    if (headerToggle) {
      headerToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        contractHUD();
      });
    }

    if (toggleBtn) {
      toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        contractHUD();
      });
    }

    hud.addEventListener("click", () => {
      if (hud.classList.contains("collapsed")) {
        expandHUD();
      }
    });
  }

  /* ========================================================================= */
  /* 9. DYNAMIC SECTION MOOD LIGHTING SHIFTER                                  */
  /* ========================================================================= */
  function initSectionMoodLighting() {
    const moodLight = $("#moodLight");
    if (!moodLight || reduceMotion) return;

    const moods = [
      { id: "hero", color: "radial-gradient(circle at 50% 30%, rgba(59, 130, 246, 0.18), transparent 65%)" },
      { id: "problem", color: "radial-gradient(circle at 50% 40%, rgba(239, 68, 68, 0.14), transparent 60%)" },
      { id: "agent-1", color: "radial-gradient(circle at 60% 50%, rgba(56, 189, 248, 0.2), transparent 65%)" },
      { id: "agent-2", color: "radial-gradient(circle at 40% 50%, rgba(129, 140, 248, 0.2), transparent 65%)" },
      { id: "agent-3", color: "radial-gradient(circle at 60% 50%, rgba(56, 189, 248, 0.2), transparent 65%)" },
      { id: "agent-4", color: "radial-gradient(circle at 40% 50%, rgba(52, 211, 153, 0.2), transparent 65%)" },
      { id: "orchestration", color: "radial-gradient(circle at 50% 50%, rgba(129, 140, 248, 0.22), rgba(52, 211, 153, 0.12) 50%, transparent 70%)" }
    ];

    moods.forEach(({ id, color }) => {
      ScrollTrigger.create({
        trigger: `#${id}`,
        start: "top 60%",
        end: "bottom 40%",
        onEnter: () => { moodLight.style.background = color; },
        onEnterBack: () => { moodLight.style.background = color; }
      });
    });
  }

  /* ========================================================================= */
  /* 10. 3D INTERACTIVE TILT ON HUD CARDS                                      */
  /* ========================================================================= */
  function initInteractiveTilts() {
    if (reduceMotion || window.innerWidth < 1080) return;

    const cards = $$(".hologram-hud-monolith, .silo-prism-card, .orch-node-card, .journey-step-card");
    cards.forEach((card) => {
      card.addEventListener("mousemove", (e) => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;

        card.style.transform = `perspective(1000px) rotateX(${-y * 7}deg) rotateY(${x * 7}deg) translateY(-4px)`;
      });

      card.addEventListener("mouseleave", () => {
        card.style.transform = "";
      });
    });
  }

  /* ========================================================================= */
  /* 11. HERO THEATER ENTRANCE & 3D REACTOR TRIGGER                            */
  /* ========================================================================= */
  function initHeroTheater() {
    if (reduceMotion) return;

    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

    tl.fromTo(".hero-tech-badge", { opacity: 0, y: 25 }, { opacity: 1, y: 0, duration: 0.8, delay: 0.2 })
      .fromTo(".hero-title-word", { opacity: 0, y: 40, rotateX: 20 }, { opacity: 1, y: 0, rotateX: 0, duration: 0.85, stagger: 0.08 }, "-=0.5")
      .fromTo(".hero-epic-subheading", { opacity: 0, y: 25 }, { opacity: 1, y: 0, duration: 0.8 }, "-=0.5")
      .fromTo(".perspective-switcher-deck", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.7 }, "-=0.5")
      .fromTo(".hero-actions-dock", { opacity: 0, scale: 0.95 }, { opacity: 1, scale: 1, duration: 0.7 }, "-=0.4")
      .fromTo(".hero-reactor-stage", { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 1 }, "-=0.4");

    gsap.to(".sat-1, .sat-3", { y: "-=10", duration: 3, repeat: -1, yoyo: true, ease: "sine.inOut" });
    gsap.to(".sat-2, .sat-4", { y: "+=10", duration: 3.4, repeat: -1, yoyo: true, ease: "sine.inOut" });

    ScrollTrigger.create({
      trigger: "#hero",
      start: "top center",
      end: "bottom center",
      onEnter: () => webglWorld?.set3DTargetShape("hero", 30, 0),
      onEnterBack: () => webglWorld?.set3DTargetShape("hero", 30, 0)
    });
  }

  /* ========================================================================= */
  /* 12. KINETIC TEXT WORD-BY-WORD SCRUB (THE PROBLEM)                         */
  /* ========================================================================= */
  function initKineticProblemScrub() {
    if (reduceMotion) return;

    const words = $$("#kineticProblem .k-word");
    if (words.length > 0) {
      gsap.to(words, {
        opacity: 1,
        stagger: 0.08,
        ease: "none",
        scrollTrigger: {
          trigger: "#problem",
          start: "top 70%",
          end: "center 40%",
          scrub: 0.6
        }
      });
    }

    gsap.fromTo(".silo-prism-card",
      { opacity: 0, y: 50, scale: 0.94 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.9,
        stagger: 0.2,
        ease: "power3.out",
        scrollTrigger: {
          trigger: ".fractured-silos-grid",
          start: "top 75%",
          toggleActions: "play none none reverse"
        }
      }
    );

    ScrollTrigger.create({
      trigger: "#problem",
      start: "top 60%",
      end: "bottom 30%",
      onEnter: () => webglWorld?.set3DTargetShape("problem", 36, 0),
      onEnterBack: () => webglWorld?.set3DTargetShape("problem", 36, 0)
    });
  }

  /* ========================================================================= */
  /* 13. PINNED AGENT STAGES (CINEMATIC SCROLLYTELLING & 3D MORPHING)          */
  /* ========================================================================= */
  function initPinnedAgentStages() {
    const stages = $$(".pinned-agent-stage");
    const isDesktop = window.innerWidth >= 1080 && !reduceMotion;
    const hudPills = $$(".pipeline-status-hud .agent-pill-state");
    const hudActivePacket = $("#hudActivePacket");
    const navChapters = $$(".chapter-nav .nav-chapter");

    const stage3DMappings = ["agent1", "agent2", "agent3", "orchestration"];
    const stageCameraZs = [26, 28, 30, 32];
    const stageLasers = [1.0, 0.0, 0.3, 0.0];

    stages.forEach((stage, sIdx) => {
      const stepItems = $$(".story-step-item", stage);
      const frames = $$(".monolith-view-frame", stage);

      function setStagePhase(phaseIndex) {
        stepItems.forEach((item, i) => {
          if (i === phaseIndex) item.classList.add("active");
          else item.classList.remove("active");
        });

        frames.forEach((frame, i) => {
          if (i === phaseIndex) frame.classList.add("active");
          else frame.classList.remove("active");
        });

        hudPills.forEach((pill, pIdx) => {
          if (pIdx === sIdx) pill.classList.add("active");
          else pill.classList.remove("active");
        });

        navChapters.forEach((nav) => {
          const chAttr = nav.dataset.chapter;
          if (chAttr === `agent-${sIdx + 1}`) nav.classList.add("active");
          else nav.classList.remove("active");
        });

        if (hudActivePacket) {
          const names = ["Alex_Vance_092.presence", "Alex_Vance_092.mastery", "Alex_Vance_092.ats_profile", "Alex_Vance_092.ecosystem_sync"];
          hudActivePacket.textContent = names[sIdx] || "Alex_Vance_092";
        }

        const collapsedActiveAgent = $("#collapsedActiveAgent");
        if (collapsedActiveAgent) {
          const agentShortNames = ["01 AttendMate", "02 Synapse", "03 Resume-IQ", "04 Campus-Desk"];
          collapsedActiveAgent.textContent = agentShortNames[sIdx] || "01 AttendMate";
        }
      }

      stepItems.forEach((item, i) => {
        item.addEventListener("click", () => setStagePhase(i));
      });

      ScrollTrigger.create({
        trigger: stage,
        start: "top 70%",
        end: "bottom 30%",
        onEnter: () => {
          webglWorld?.set3DTargetShape(
            stage3DMappings[sIdx] || "hero",
            stageCameraZs[sIdx] || 30,
            stageLasers[sIdx] || 0
          );
        },
        onEnterBack: () => {
          webglWorld?.set3DTargetShape(
            stage3DMappings[sIdx] || "hero",
            stageCameraZs[sIdx] || 30,
            stageLasers[sIdx] || 0
          );
        },
        onUpdate: (self) => {
          const p = self.progress;
          if (p < 0.33) {
            setStagePhase(0);
          } else if (p < 0.66) {
            setStagePhase(1);
          } else {
            setStagePhase(2);
          }
        }
      });
    });
  }

  /* ========================================================================= */
  /* 14. HIGHWAY DATA CAPSULES TRAVELING DOWN THE WIRE                         */
  /* ========================================================================= */
  function initConduitHighways() {
    if (reduceMotion) return;

    const conduits = [
      { id: "#conduit1to2", capsule: "#capsule1to2" },
      { id: "#conduit2to3", capsule: "#capsule2to3" },
      { id: "#conduit3to4", capsule: "#capsule3to4" }
    ];

    conduits.forEach(({ id, capsule }) => {
      const section = $(id);
      const capEl = $(capsule);
      if (!section || !capEl) return;

      gsap.fromTo(capEl,
        { top: "0%", opacity: 0.3, scale: 0.85 },
        {
          top: "100%",
          opacity: 1,
          scale: 1.1,
          ease: "none",
          scrollTrigger: {
            trigger: section,
            start: "top 80%",
            end: "bottom 20%",
            scrub: true
          }
        }
      );
    });
  }

  /* ========================================================================= */
  /* 15. "DAY IN THE LIFE" CARDS ANIMATION                                     */
  /* ========================================================================= */
  function initDayInLifeCards() {
    if (reduceMotion) return;

    gsap.fromTo(".journey-step-card",
      { opacity: 0, y: 40, scale: 0.95 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.8,
        stagger: 0.15,
        ease: "power3.out",
        scrollTrigger: {
          trigger: ".day-in-life-theater",
          start: "top 75%",
          toggleActions: "play none none reverse"
        }
      }
    );
  }

  /* ========================================================================= */
  /* 16. ORCHESTRATION MATRIX & 3D SINGULARITY ORCHESTRA                       */
  /* ========================================================================= */
  function initOrchestrationMatrix() {
    if (reduceMotion) return;

    ScrollTrigger.create({
      trigger: "#orchestration",
      start: "top 70%",
      end: "bottom 30%",
      onEnter: () => webglWorld?.set3DTargetShape("orchestration", 34, 0),
      onEnterBack: () => webglWorld?.set3DTargetShape("orchestration", 34, 0)
    });

    gsap.fromTo(".orch-node-card",
      { opacity: 0, y: 40, scale: 0.95 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.8,
        stagger: 0.16,
        ease: "power3.out",
        scrollTrigger: {
          trigger: "#orchMatrixGrid",
          start: "top 75%",
          toggleActions: "play none none reverse"
        }
      }
    );

    const counterEl = $('[data-counter="240000"]');
    if (counterEl) {
      ScrollTrigger.create({
        trigger: ".holistic-impact-hud",
        start: "top 75%",
        onEnter: () => {
          let countObj = { val: 0 };
          gsap.to(countObj, {
            val: 240000,
            duration: 2.2,
            ease: "power2.out",
            onUpdate: () => {
              counterEl.textContent = Math.floor(countObj.val).toLocaleString() + "+";
            }
          });
        }
      });
    }
  }

  /* ========================================================================= */
  /* 17. FINAL CTA ANIMATION                                                   */
  /* ========================================================================= */
  function initFinalCTA() {
    if (reduceMotion) return;

    ScrollTrigger.create({
      trigger: "#cta",
      start: "top 80%",
      onEnter: () => webglWorld?.set3DTargetShape("hero", 24, 0),
      onEnterBack: () => webglWorld?.set3DTargetShape("hero", 24, 0)
    });

    gsap.fromTo(".cta-monolith-card",
      { opacity: 0, y: 45, scale: 0.96 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.9,
        ease: "power3.out",
        scrollTrigger: {
          trigger: "#cta",
          start: "top 80%",
          toggleActions: "play none none reverse"
        }
      }
    );
  }

})();

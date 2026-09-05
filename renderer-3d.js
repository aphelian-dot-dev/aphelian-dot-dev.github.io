/* APHELIAN 3D — read-only presentation adapter; never mutates simulation state.
 * All combat centers share the y=22 plane. Pointer rays intersect that plane.
 * Geometry, lighting, shadows and depth are genuine WebGL, not a skewed 2D canvas.
 */
// A tiny screen-space nudge, independent of simulation time and gameplay RNG.
window.orreryImpactOffset = function orreryImpactOffset(game, time, reducedMotion) {
  const amplitude = reducedMotion || game.mode !== 'playing' || game.shake < .03
    ? 0 : Math.min(3, Math.max(0, game.shake) * .65);
  return { x: Math.sin(time * 87) * amplitude * Math.SQRT1_2,
    y: Math.cos(time * 103) * amplitude * Math.SQRT1_2 };
};

window.createOrrery3D = function createOrrery3D(canvas) {
  'use strict';
  const T = THREE, TAU = Math.PI * 2, ELEVATION = 22;
  const renderer = new T.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
  renderer.setClearColor(0x05050e);
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(40, 1, 1, 10000);
  camera.position.set(0, 1600, 1150);
  camera.lookAt(0, 0, 0);
  scene.add(new T.HemisphereLight(0xa4b2ff, 0x100925, 1.25));
  const key = new T.DirectionalLight(0xffe2b0, 3.8);
  key.position.set(-400, 500, -300);
  scene.add(key);
  const rim = new T.DirectionalLight(0x4433ff, 3);
  rim.position.set(250, 80, 300);
  scene.add(rim);
  const sphere = new T.IcosahedronGeometry(1, 3);
  const rock = new T.IcosahedronGeometry(1, 0);
  const diamond = new T.OctahedronGeometry(1, 0);
  const shard = new T.ConeGeometry(1, 2, 3);
  const ring = new T.TorusGeometry(1, .023, 5, 80);
  const cube = new T.BoxGeometry(1, 1, 1);
  const disc = new T.CircleGeometry(1, 32);
  const mat = (color, emissive = 0x000000, metalness = .35) => new T.MeshStandardMaterial({ color, emissive, roughness: .64, metalness, flatShading: true });
  const paper = mat(0xf1f0e8, 0x101010, .15);
  const ink = mat(0x14122e, 0x06031a, .7);
  const cobalt = mat(0x3223d9, 0x0b033f, .5);
  const ember = mat(0xed9347, 0x441507, .3);
  const luminous = color => new T.MeshBasicMaterial({ color });
  const ivoryLight = luminous(0xe7ddbf), amberLight = luminous(0xe49a56), blueLight = luminous(0x6157ed);
  const shadowMat = new T.MeshBasicMaterial({ color: 0x01010a, transparent: true, opacity: .6, depthWrite: false });
  const mesh = (geometry, material, parent = scene) => { const m = new T.Mesh(geometry, material); parent.add(m); return m; };
  const floor = mesh(cube, mat(0x111022, 0x02010a, .4));
  floor.position.y = -31;
  const architecture = new T.Group(); scene.add(architecture);
  const player = new T.Group(); scene.add(player);
  const body = mesh(diamond, ink, player); body.scale.set(12, 27, 12);
  const heart = mesh(sphere, amberLight, player); heart.scale.setScalar(4); heart.position.y = 12;
  const crown = mesh(ring, ivoryLight, player); crown.scale.setScalar(22); crown.rotation.x = Math.PI / 2;
  const halo = mesh(ring, blueLight, player); halo.scale.setScalar(19); halo.rotation.y = .65;
  const playerShadow = mesh(disc, shadowMat); playerShadow.rotation.x = -Math.PI / 2;
  const moons = Array.from({ length: 3 }, () => {
    const group = new T.Group(); scene.add(group);
    mesh(sphere, paper, group);
    const meridian = mesh(ring, blueLight, group); meridian.scale.setScalar(1.16); meridian.rotation.y = .6;
    return group;
  });
  const moonShadows = moons.map(() => { const s = mesh(disc, shadowMat); s.rotation.x = -Math.PI / 2; return s; });
  const enemies = new Map(), pickups = new Map();
  const lineGeo = new T.BufferGeometry();
  const MAX_VERTICES = 18000;
  const linePositions = new Float32Array(MAX_VERTICES * 3), lineColors = new Float32Array(MAX_VERTICES * 3);
  lineGeo.setAttribute('position', new T.BufferAttribute(linePositions, 3).setUsage(T.DynamicDrawUsage));
  lineGeo.setAttribute('color', new T.BufferAttribute(lineColors, 3).setUsage(T.DynamicDrawUsage));
  const lines = new T.LineSegments(lineGeo, new T.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: .85, depthWrite: false }));
  lines.frustumCulled = false; scene.add(lines);
  const effects = new T.InstancedMesh(rock, new T.MeshBasicMaterial({ color: 0xffffff }), 1000);
  effects.instanceMatrix.setUsage(T.DynamicDrawUsage); effects.frustumCulled = false; scene.add(effects);
  const dummy = new T.Object3D(), color = new T.Color();
  let width = 1, height = 1, lineCount = 0, lastMode = '', lastTime = 0;
  const ray = new T.Raycaster(), pointerNDC = new T.Vector2();
  const combatPlane = new T.Plane(new T.Vector3(0, 1, 0), -ELEVATION);
  const projection = new T.Vector3();
  // A private visual PRNG: rendering must never consume the gameplay generator.
  let seed = 1977;
  const random = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);
  const starsGeo = new T.BufferGeometry(), starPositions = [];
  for (let i = 0; i < 650; i++) starPositions.push((random() - .5) * 3600, -100 - random() * 350, (random() - .5) * 3000);
  starsGeo.setAttribute('position', new T.Float32BufferAttribute(starPositions, 3));
  scene.add(new T.Points(starsGeo, new T.PointsMaterial({ color: 0xaaa3c4, size: 1.3, transparent: true, opacity: .55 })));

  function resize(w, h, scale) {
    width = w; height = h;
    renderer.setPixelRatio(scale); renderer.setSize(w, h, false);
    camera.clearViewOffset();
    camera.aspect = w / h;
    const distance = h / (2 * Math.tan(T.MathUtils.degToRad(20))) * 1.27 + h * .32;
    camera.position.set(0, 1600, 1150).normalize().multiplyScalar(distance);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix(); camera.updateMatrixWorld();
    floor.scale.set(w + 12, 16, h + 12);
    architecture.clear();
    const vertices = [];
    const segment = (ax, az, bx, bz, y = -21.8) => vertices.push(ax, y, az, bx, y, bz);
    const a = w / 2, b = h / 2;
    segment(-a, -b, a, -b); segment(a, -b, a, b); segment(a, b, -a, b); segment(-a, b, -a, -b);
    for (let i = 0; i <= 40; i++) {
      const x = -a + w * i / 40, z = -b + h * i / 40, length = i % 5 === 0 ? 13 : 5;
      segment(x, -b, x, -b + length); segment(x, b, x, b - length);
      segment(-a, z, -a + length, z); segment(a, z, a - length, z);
    }
    const radius = Math.min(w, h) * .46;
    for (const r of [radius, radius * .72, radius * .35]) {
      for (let i = 0; i < 120; i++) {
        const t = i * TAU / 120, u = (i + 1) * TAU / 120;
        segment(Math.cos(t) * r, Math.sin(t) * r, Math.cos(u) * r, Math.sin(u) * r);
      }
    }
    for (let i = 0; i < 12; i++) {
      const t = i * TAU / 12;
      segment(Math.cos(t) * radius * .25, Math.sin(t) * radius * .25, Math.cos(t) * radius, Math.sin(t) * radius);
    }
    if (architecture.userData.geometry) architecture.userData.geometry.dispose();
    const geometry = new T.BufferGeometry(); geometry.setAttribute('position', new T.Float32BufferAttribute(vertices, 3));
    architecture.userData.geometry = geometry;
    if (!architecture.userData.material) architecture.userData.material = new T.LineBasicMaterial({ color: 0x4b4085, transparent: true, opacity: .42 });
    architecture.add(new T.LineSegments(geometry, architecture.userData.material));
    for (const x of [-a, a]) for (const z of [-b, b]) {
      const plinth = mesh(cube, ink, architecture); plinth.position.set(x, -15, z); plinth.scale.set(20, 30, 20);
      const marker = mesh(diamond, ember, architecture); marker.position.set(x, 8, z); marker.scale.set(6, 17, 6);
    }
  }
  function position(object, x, y, r = 1, altitude = ELEVATION) {
    object.position.set(x - width / 2, altitude, y - height / 2); object.scale.setScalar(r);
  }
  function project(x, y, altitude = ELEVATION) {
    projection.set(x - width / 2, altitude, y - height / 2).project(camera);
    // World extents stay logical; projection coordinates are rendered CSS pixels.
    const rect = canvas.getBoundingClientRect();
    return { x: (projection.x + 1) * rect.width / 2, y: (1 - projection.y) * rect.height / 2 };
  }
  function unproject(point) {
    const rect = canvas.getBoundingClientRect();
    pointerNDC.set(point.x / rect.width * 2 - 1, 1 - point.y / rect.height * 2);
    ray.setFromCamera(pointerNDC, camera);
    ray.ray.intersectPlane(combatPlane, projection);
    return { x: projection.x + width / 2, y: projection.z + height / 2 };
  }
  function line(ax, ay, bx, by, tint = 0x5a50c7, altitude = ELEVATION) {
    if (lineCount + 2 > MAX_VERTICES) return;
    color.set(tint);
    for (const [x, y] of [[ax, ay], [bx, by]]) {
      const offset = lineCount++ * 3;
      linePositions.set([x - width / 2, altitude, y - height / 2], offset);
      lineColors.set([color.r, color.g, color.b], offset);
    }
  }
  function circle(x, y, radius, tint, altitude = ELEVATION, segments = 64) {
    for (let i = 0; i < segments; i++) {
      const a = i * TAU / segments, b = (i + 1) * TAU / segments;
      line(x + Math.cos(a) * radius, y + Math.sin(a) * radius, x + Math.cos(b) * radius, y + Math.sin(b) * radius, tint, altitude);
    }
  }
  function makeEnemy(e) {
    const group = new T.Group(); scene.add(group);
    const material = (e.type === 'meteor' ? paper : e.type === 'cinder' ? ember : e.boss ? ink : cobalt).clone();
    const geometry = e.type === 'shard' ? shard : e.type === 'meteor' ? rock : e.boss ? sphere : diamond;
    const hull = mesh(geometry, material, group);
    if (e.type === 'shard') { hull.rotation.z = Math.PI / 2; hull.scale.set(.7, 1.2, .7); }
    if (e.type === 'ram') hull.scale.set(1.35, .6, .85);
    const wire = new T.LineSegments(new T.EdgesGeometry(geometry), new T.LineBasicMaterial({ color: e.type === 'meteor' ? 0xa5a0ff : e.boss ? 0x222044 : 0x9887df, transparent: true, opacity: .5 }));
    hull.add(wire);
    const rings = [];
    if (e.boss || e.type === 'wisp' || e.type === 'cinder') {
      const r = mesh(ring, e.boss ? amberLight : blueLight, group);
      r.scale.setScalar(e.boss ? 1.48 : 1.25); r.rotation.x = 1.18; r.rotation.y = .3; rings.push(r);
      if (e.boss) {
        const r2 = mesh(ring, blueLight, group); r2.scale.setScalar(1.72); r2.rotation.x = .32; r2.rotation.y = -.7; rings.push(r2);
        const spark = mesh(sphere, amberLight, group); spark.position.set(-.27, .45, .79); spark.scale.setScalar(.10);
      }
    }
    const shadow = mesh(disc, shadowMat); shadow.rotation.x = -Math.PI / 2;
    return { group, hull, material, rings, shadow, wire };
  }
  function syncEnemies(game, time) {
    const live = new Set(game.mode === 'title' ? [] : game.enemies.filter(e => !e.dead));
    for (const [e, item] of enemies) if (!live.has(e)) {
      scene.remove(item.group, item.shadow); item.material.dispose(); item.wire.geometry.dispose(); item.wire.material.dispose(); enemies.delete(e);
    }
    for (const e of live) {
      if (!enemies.has(e)) enemies.set(e, makeEnemy(e));
      const item = enemies.get(e);
      position(item.group, e.x, e.y, e.r);
      item.hull.rotation.y = e.angle;
      if (e.type === 'meteor') item.hull.rotation.x = e.angle * .63;
      item.material.emissive.set(e.hitFlash > 0 ? 0xb97739 : e.boss ? 0x06031a : e.type === 'cinder' ? 0x441507 : 0x0b033f);
      item.rings.forEach((r, i) => { r.rotation.z = time * (i ? -.13 : .2); });
      position(item.shadow, e.x + 8, e.y + 9, e.r * 1.25, -21.7);
      if (e.state === 'telegraph') {
        const progress = Math.max(0, 1 - e.stateTimer / (e.boss ? 1.05 : .78));
        line(e.x, e.y, e.lockX, e.lockY, 0xffbb76);
        // Parallel danger rails make the dash lane legible against the floor.
        const a = Math.atan2(e.lockY - e.y, e.lockX - e.x), dx = Math.sin(a) * e.r, dy = -Math.cos(a) * e.r;
        line(e.x + dx, e.y + dy, e.lockX + dx, e.lockY + dy, 0x96532d, -20);
        line(e.x - dx, e.y - dy, e.lockX - dx, e.lockY - dy, 0x96532d, -20);
        circle(e.lockX, e.lockY, 14, 0xffbb76);
        circle(e.x, e.y, e.r + (1 - progress) * (e.boss ? 70 : 35), 0xebad72);
      }
    }
  }
  function syncPickups(game, time) {
    const live = new Set(game.mode === 'title' ? [] : game.pickups.filter(p => p.life > 0));
    for (const [p, object] of pickups) if (!live.has(p)) { scene.remove(object); pickups.delete(p); }
    for (const p of live) {
      if (!pickups.has(p)) {
        const group = new T.Group(); scene.add(group);
        mesh(diamond, p.type !== 'fuel' ? paper : ember, group);
        const r = mesh(ring, p.type !== 'fuel' ? ivoryLight : amberLight, group); r.scale.setScalar(1.5); r.rotation.x = Math.PI / 2;
        pickups.set(p, group);
      }
      const object = pickups.get(p); position(object, p.x, p.y, 7);
      object.rotation.y = time;
      circle(p.x, p.y, 15, p.type !== 'fuel' ? 0x9290be : 0xb37646, -21);
    }
  }
  function render(game, time, reducedMotion, pointer) {
    lastMode = game.mode; lastTime = time; lineCount = 0;
    const shake = window.orreryImpactOffset(game, time, reducedMotion);
    // Keep the logical camera aspect, converting the CSS shake to its view units.
    if (shake.x || shake.y) {
      const rect = canvas.getBoundingClientRect();
      camera.setViewOffset(width, height, -shake.x * width / rect.width, -shake.y * height / rect.height, width, height);
    }
    else if (camera.view?.enabled) camera.clearViewOffset();
    const title = game.mode === 'title';
    let p = game.player;
    if (title) {
      const x = width * (width < 760 ? .5 : .69), y = height * .52, radius = Math.min(width, height) * .23;
      p = { x, y, angle: time * .45, axis: -.3, invuln: 0, charge: 0, burst: 0, orbs: Array.from({ length: 3 }, (_, i) => ({ x: x + Math.cos(time * .45 + i * TAU / 3) * radius, y: y + Math.sin(time * .45 + i * TAU / 3) * radius * .64, r: i === 1 ? 15 : 13, trail: [] })) };
    }
    if (p) {
      position(player, p.x, p.y, title ? 1.8 : 1);
      player.visible = reducedMotion || p.invuln <= 0 || Math.floor(game.time * 12) % 2 === 0;
      body.rotation.y = p.axis || 0; halo.rotation.z = time * .15;
      position(playerShadow, p.x + 8, p.y + 12, 20, -21.6);
      const hot = p.burst > 0 || (p.folding && p.charge >= .36);
      const overheated = p.overheated === true && p.burst > 0;
      for (let i = 0; i < 3; i++) {
        const orb = p.orbs[i], next = p.orbs[(i + 1) % 3];
        position(moons[i], orb.x, orb.y, orb.r);
        moons[i].rotation.y = time * .25 + i;
        position(moonShadows[i], orb.x + 8, orb.y + 9, orb.r, -21.6);
        line(orb.x, orb.y, next.x, next.y, overheated ? 0x5552ff : hot ? 0xffbd79 : title ? 0xaba2db : 0x51465f);
        if (hot) {
          line(orb.x, orb.y, next.x, next.y, overheated ? 0x2924ab : 0xa15d34, ELEVATION - 4);
          circle(orb.x, orb.y, orb.r + 4, overheated ? 0xaaa5ff : 0xffcf94, ELEVATION, 20);
        }
        const trail = orb.trail || [];
        for (let j = 1; j < trail.length; j++) {
          line(trail[j - 1].x, trail[j - 1].y, trail[j].x, trail[j].y, trail[j].hot > .5 ? 0xb7814c : 0x454181, ELEVATION - (1 - j / trail.length) * 10);
        }
      }
      circle(p.x, p.y, 28, p.orbitBoostTime > 0 ? 0xc0bcff : 0x675999, -21.3);
      if (!title && pointer?.active) {
        circle(pointer.x, pointer.y, 6, 0x9d94bb, ELEVATION, 16);
        line(pointer.x - 10, pointer.y, pointer.x + 10, pointer.y, 0x9d94bb);
        line(pointer.x, pointer.y - 10, pointer.x, pointer.y + 10, 0x9d94bb);
      }
    }
    syncEnemies(game, time); syncPickups(game, time);
    if (!title) for (const wave of game.waves) circle(wave.x, wave.y, wave.radius, wave.color, -19.5);
    const particles = title ? [] : game.particles;
    effects.count = Math.min(particles.length, 1000);
    for (let i = 0; i < effects.count; i++) {
      const particle = particles[i];
      dummy.position.set(particle.x - width / 2, ELEVATION + Math.sin(i * 2.4) * 10, particle.y - height / 2);
      dummy.scale.setScalar(Math.max(.5, (particle.size || 2) * Math.min(1, particle.life * 3)));
      dummy.rotation.set(i, time + i, i * .2); dummy.updateMatrix();
      effects.setMatrixAt(i, dummy.matrix); effects.setColorAt(i, color.set(particle.color || 0xf1f0e8));
    }
    effects.instanceMatrix.needsUpdate = true;
    if (effects.instanceColor) effects.instanceColor.needsUpdate = true;
    lineGeo.setDrawRange(0, lineCount);
    lineGeo.attributes.position.needsUpdate = true; lineGeo.attributes.color.needsUpdate = true;
    renderer.render(scene, camera);
  }
  function drawOverlay(ctx, game) {
    if (game.mode === 'title') return;
    ctx.save(); ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
    ctx.font = "700 8px 'Courier New', monospace";
    for (const e of game.enemies) {
      if (e.dead || e.boss) continue;
      const pos = project(e.x, e.y, ELEVATION + e.r + 10);
      if (e.type === 'meteor') {
        ctx.fillStyle = '#ded8f2'; ctx.fillText('◆'.repeat(Math.max(0, e.hitsRemaining)), pos.x, pos.y);
      } else if (e.hp < e.maxHp) {
        ctx.fillStyle = '#181228'; ctx.fillRect(pos.x - 14, pos.y, 28, 3);
        ctx.fillStyle = '#c5b9e0'; ctx.fillRect(pos.x - 14, pos.y, 28 * Math.max(0, e.hp / e.maxHp), 3);
      }
    }
    for (const floater of game.floaters) {
      const pos = project(floater.x, floater.y, ELEVATION + 24);
      ctx.globalAlpha = Math.min(1, floater.life * 2); ctx.fillStyle = floater.color || '#f1f0e8';
      ctx.fillText(floater.text, pos.x, pos.y);
    }
    ctx.globalAlpha = 1;
    for (const p of game.pickups) {
      const pos = project(p.x, p.y, ELEVATION + 15);
      ctx.fillStyle = p.type !== 'fuel' ? '#ece8db' : '#efb177'; ctx.fillText(p.type !== 'fuel' ? '+' : 'F', pos.x, pos.y);
    }
    if (game.player) {
      const p = game.player, pos = project(p.x, p.y, ELEVATION + 45);
      for (const [value, max, label, tint] of [[p.fuelTime, 2, 'FUEL', '#f0aa62'], [p.orbitBoostTime, 5, 'QUICKENED', '#b3aaff']]) {
        if (value <= 0) continue;
        ctx.fillStyle = tint; ctx.fillText(label, pos.x, pos.y - 3); ctx.fillRect(pos.x - 24, pos.y, 48 * value / max, 3); pos.y -= 17;
      }
    }
    ctx.restore();
  }
  return {
    resize, render, drawOverlay, project, unproject,
    info: () => ({ kind: 'webgl3d', camera: camera.type, triangles: renderer.info.render.triangles, calls: renderer.info.render.calls, moons: moons.length, arena: !!floor.parent, mode: lastMode, time: lastTime, geometries: renderer.info.memory.geometries, entities: [...enemies.keys()].reduce((counts, e) => { counts[e.type] = (counts[e.type] || 0) + 1; return counts; }, {}) })
  };
};

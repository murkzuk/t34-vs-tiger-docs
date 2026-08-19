import * as THREE from 'three';
import { OrbitControls } from './OrbitControls.js';

// World is 9000 units square. Rendered 1:1 in metres, Y up in three.js, so
// TvT's (x, y, z) maps to (x, z_height, y). Getting this wrong is the sort of
// silent mirror that cost a day earlier in the project, so it is written once
// here and used everywhere.
const WORLD = 9000;
const toScene = (x, y, z) => new THREE.Vector3(x - WORLD / 2, z, y - WORLD / 2);
const toWorld = (v) => ({ x: v.x + WORLD / 2, y: v.z + WORLD / 2 });

const COL = {
  friend:  0x9aa3a8,   // grey  - German
  enemy:   0x5f9e57,   // green - Soviet
  neutral: 0x6b6f73,
  nav:     0xd8a947,
  sel:     0xe0a33a,
};

let scene, camera, renderer, controls, raycaster;
let terrainMesh, routerOverlay, terrainOverlay, routeLine;
let objectGroup, navGroup, facingGroup;
let data = null, picked = null, dragging = null;
const moves = {};
const meshByName = new Map();

const $ = (id) => document.getElementById(id);
const msg = (t, cls) => { const m = $('msg'); m.textContent = t; m.className = cls || ''; };

init();
loadList();

function init() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x14171a);
  scene.fog = new THREE.Fog(0x14171a, 4000, 11000);

  camera = new THREE.PerspectiveCamera(52, 1, 5, 30000);
  camera.position.set(0, 3200, 3600);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  $('view').appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.maxPolarAngle = Math.PI * 0.492;   // stop under the ground
  controls.screenSpacePanning = false;

  scene.add(new THREE.HemisphereLight(0xbfd4e6, 0x3a3a30, 1.35));
  const sun = new THREE.DirectionalLight(0xffeedd, 1.5);
  sun.position.set(-4000, 5000, 2500);
  scene.add(sun);

  raycaster = new THREE.Raycaster();
  objectGroup = new THREE.Group(); scene.add(objectGroup);
  navGroup    = new THREE.Group(); scene.add(navGroup);
  facingGroup = new THREE.Group(); scene.add(facingGroup);

  addEventListener('resize', resize); resize();
  renderer.domElement.addEventListener('pointerdown', onDown);
  renderer.domElement.addEventListener('pointermove', onMove);
  addEventListener('pointerup', onUp);

  $('pick').onchange = () => loadMission($('pick').value);
  $('reload').onclick = () => loadMission($('pick').value);
  $('save').onclick = save;
  $('check').onclick = validate;
  for (const id of ['cRouter','cTerrain','cRoute','cNav','cScenery','cFacing'])
    $(id).onchange = applyVisibility;

  legend();
  animate();
}

function resize() {
  const v = $('view');
  // Guard against a zero-sized container. A hidden or not-yet-laid-out pane
  // reports 0, which makes the aspect ratio NaN and the canvas 0 high - the
  // scene is then built correctly and renders nothing, which looks like a
  // graphics failure and is not one.
  const w = Math.max(1, v.clientWidth), h = Math.max(1, v.clientHeight);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}

// Re-fit when the pane is first shown or resized by the host, not only on
// window resize - a docked panel can change size without a window event.
if (typeof ResizeObserver !== 'undefined')
  new ResizeObserver(() => resize()).observe(document.getElementById('view'));

function legend() {
  $('legend').innerHTML =
    `<i style="background:#9aa3a8"></i>German &nbsp; <i style="background:#5f9e57"></i>Soviet<br>` +
    `<i style="background:#d8a947"></i>Navpoint &nbsp; <i style="background:#e0a33a"></i>Selected<br>` +
    `<span style="color:#798187">drag a unit to move it &middot; click to select</span>`;
}

async function loadList() {
  const r = await (await fetch('/api/missions')).json();
  $('pick').innerHTML = r.missions.map(m => `<option>${m}</option>`).join('');
  const want = r.missions.includes('Kursk04') ? 'Kursk04' : r.missions[0];
  $('pick').value = want;
  loadMission(want);
}

async function loadMission(name) {
  msg('loading ' + name + ' …');
  const d = await (await fetch('/api/mission/' + name)).json();
  if (d.error) { msg(d.error, 'bad'); return; }
  data = d;
  for (const k in moves) delete moves[k];
  $('save').disabled = true;
  picked = null;
  build();
  msg('');
  $('hud').innerHTML =
    `<b>${d.title || d.name}</b><br>` +
    `${d.objects.length} objects &middot; ${Object.keys(d.groups).length} groups<br>` +
    `${(d.paths[Object.keys(d.paths)[0]] || []).length} advance navpoints`;
}

// ---------------------------------------------------------------- geometry

function build() {
  for (const g of [objectGroup, navGroup, facingGroup]) g.clear();
  meshByName.clear();
  for (const m of [terrainMesh, routerOverlay, terrainOverlay, routeLine])
    if (m) { scene.remove(m); m.geometry?.dispose(); }

  buildTerrain();
  buildZoneOverlays();
  buildObjects();
  buildRoute();
  applyVisibility();
  fillList();
}

function buildTerrain() {
  const n = data.gridN, H = data.heights;
  const geo = new THREE.PlaneGeometry(WORLD, WORLD, n - 1, n - 1);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  // PlaneGeometry after rotateX runs +z downward, but our heights are indexed
  // row 0 = world y=0, so read rows in reverse to keep north where north is.
  for (let iy = 0; iy < n; iy++)
    for (let ix = 0; ix < n; ix++)
      pos.setY(iy * n + ix, H[n - 1 - iy][ix]);
  geo.computeVertexNormals();
  terrainMesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({
    color: 0x6b7355, flatShading: false,
  }));
  terrainMesh.name = '__terrain';
  scene.add(terrainMesh);
}

function zoneTexture(grid, mode) {
  const n = grid.length;
  const buf = new Uint8Array(n * n * 4);
  for (let iy = 0; iy < n; iy++) {
    for (let ix = 0; ix < n; ix++) {
      const v = grid[n - 1 - iy][ix];          // same row flip as the terrain
      const i = (iy * n + ix) * 4;
      let r = 0, g = 0, b = 0, a = 0;
      if (mode === 'router') {
        if (v === 1) { r = 40;  g = 90;  b = 40;  a = 120; }   // forest
        else if (v === 2) { r = 170; g = 50; b = 50; a = 170; } // impassable
        else { a = 0; }                                        // open - show ground
      } else {
        if (v === 1) { r = 30; g = 80; b = 30; a = 150; }
        else if (v === 2) { r = 120; g = 110; b = 90; a = 110; }
        else { r = 150; g = 160; b = 90; a = 70; }
      }
      buf[i] = r; buf[i + 1] = g; buf[i + 2] = b; buf[i + 3] = a;
    }
  }
  const t = new THREE.DataTexture(buf, n, n);
  t.needsUpdate = true;
  return t;
}

function overlayMesh(grid, mode, lift) {
  const n = data.gridN, H = data.heights;
  const geo = new THREE.PlaneGeometry(WORLD, WORLD, n - 1, n - 1);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  for (let iy = 0; iy < n; iy++)
    for (let ix = 0; ix < n; ix++)
      pos.setY(iy * n + ix, H[n - 1 - iy][ix] + lift);
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
    map: zoneTexture(grid, mode), transparent: true, depthWrite: false,
  }));
  scene.add(m);
  return m;
}

function buildZoneOverlays() {
  routerOverlay  = overlayMesh(data.router,  'router',  2.5);
  terrainOverlay = overlayMesh(data.terrain, 'terrain', 1.5);
}

function affiliationColour(o) {
  // Class name is the reliable signal: the payload does not carry the
  // Affiliation property, and German/Soviet is legible from the unit type.
  const c = o.cls;
  if (/German|PzIV|PzVI|Pak40|Hanomag|OpelBlitz|StuG/.test(c)) return COL.friend;
  if (/Soviet|T34|SU85|Zis|SAUSU/.test(c)) return COL.enemy;
  return COL.neutral;
}

const SCENERY = /Barricade|SandBags|DotConcrete|House|Fence|Well|Haystack|Tree/;

function buildObjects() {
  for (const o of data.objects) {
    if (o.kind === 'NavPoint') { buildNav(o); continue; }
    if (o.kind === 'UnitGroup') continue;          // markers, not things on the map
    const [L, W, Hh] = o.dims;
    const geo = new THREE.BoxGeometry(L, Hh, W);
    const mat = new THREE.MeshLambertMaterial({ color: affiliationColour(o) });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.copy(toScene(o.x, o.y, o.z + Hh / 2));
    mesh.rotation.y = -Math.atan2(o.fy, o.fx);
    mesh.userData = o;
    mesh.userData.scenery = SCENERY.test(o.cls) || o.kind === 'InteriorObject';
    objectGroup.add(mesh);
    meshByName.set(o.name, mesh);

    if (!mesh.userData.scenery) {
      const len = Math.max(12, L * 2.2);
      const g = new THREE.BufferGeometry().setFromPoints([
        toScene(o.x, o.y, o.z + Hh),
        toScene(o.x + o.fx * len, o.y + o.fy * len, o.z + Hh),
      ]);
      facingGroup.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xffffff, opacity: .35, transparent: true })));
    }
  }
}

function buildNav(o) {
  const geo = new THREE.ConeGeometry(9, 26, 5);
  const mesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: COL.nav }));
  mesh.position.copy(toScene(o.x, o.y, o.z + 13));
  mesh.userData = o;
  navGroup.add(mesh);
  meshByName.set(o.name, mesh);
}

function routePoints() {
  const key = Object.keys(data.paths)[0];
  if (!key) return [];
  const byName = new Map(data.objects.filter(o => o.kind === 'NavPoint').map(o => [o.name, o]));
  return data.paths[key].map(n => byName.get(n)).filter(Boolean);
}

function buildRoute() {
  const pts = routePoints();
  if (pts.length < 2) { routeLine = null; return; }
  const g = new THREE.BufferGeometry().setFromPoints(
    pts.map(o => toScene(o.x, o.y, o.z + 14)));
  routeLine = new THREE.Line(g, new THREE.LineBasicMaterial({ color: COL.nav }));
  scene.add(routeLine);
}

function applyVisibility() {
  if (routerOverlay)  routerOverlay.visible  = $('cRouter').checked;
  if (terrainOverlay) terrainOverlay.visible = $('cTerrain').checked;
  if (routeLine)      routeLine.visible      = $('cRoute').checked;
  navGroup.visible    = $('cNav').checked;
  facingGroup.visible = $('cFacing').checked;
  const showScenery = $('cScenery').checked;
  for (const m of objectGroup.children)
    m.visible = showScenery || !m.userData.scenery;
}

// ---------------------------------------------------------------- interaction

function pointer(e) {
  const r = renderer.domElement.getBoundingClientRect();
  return new THREE.Vector2(
    ((e.clientX - r.left) / r.width) * 2 - 1,
    -((e.clientY - r.top) / r.height) * 2 + 1);
}

function hit(e, objs) {
  raycaster.setFromCamera(pointer(e), camera);
  return raycaster.intersectObjects(objs, false)[0] || null;
}

function onDown(e) {
  if (e.button !== 0) return;
  const pickable = objectGroup.children.filter(m => m.visible).concat(
    navGroup.visible ? navGroup.children : []);
  const h = hit(e, pickable);
  if (!h) return;
  select(h.object);
  if (e.shiftKey) {                       // shift-drag moves it
    dragging = h.object;
    controls.enabled = false;
  }
}

function onMove(e) {
  if (!dragging || !terrainMesh) return;
  const h = hit(e, [terrainMesh]);
  if (!h) return;
  const w = toWorld(h.point);
  dragging.position.x = h.point.x;
  dragging.position.z = h.point.z;
  const o = dragging.userData;
  o.x = w.x; o.y = w.y;
  moves[o.name] = { x: w.x, y: w.y };
  $('save').disabled = false;
  showSelected(o);
}

function onUp() {
  if (dragging) { dragging = null; controls.enabled = true; rebuildAux(); }
}

function rebuildAux() {
  facingGroup.clear();
  if (routeLine) { scene.remove(routeLine); routeLine.geometry.dispose(); }
  for (const m of objectGroup.children) {
    const o = m.userData;
    if (o.scenery) continue;
    const len = Math.max(12, o.dims[0] * 2.2);
    const g = new THREE.BufferGeometry().setFromPoints([
      toScene(o.x, o.y, o.z + o.dims[2]),
      toScene(o.x + o.fx * len, o.y + o.fy * len, o.z + o.dims[2]),
    ]);
    facingGroup.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xffffff, opacity: .35, transparent: true })));
  }
  buildRoute();
  applyVisibility();
}

function select(mesh) {
  if (picked) picked.material.emissive?.setHex(0x000000);
  picked = mesh;
  mesh.material.emissive?.setHex(0x553300);
  showSelected(mesh.userData);
  for (const el of $('list').children)
    el.classList.toggle('on', el.dataset.name === mesh.userData.name);
}

function showSelected(o) {
  const grp = Object.entries(data.groups).find(([, u]) => u.includes(o.name));
  $('sel').innerHTML =
    `<span>name</span><span>${o.name}</span>` +
    `<span>class</span><span>${o.cls}</span>` +
    `<span>kind</span><span>${o.kind}</span>` +
    `<span>x</span><span class="num">${o.x.toFixed(1)}</span>` +
    `<span>y</span><span class="num">${o.y.toFixed(1)}</span>` +
    `<span>z</span><span class="num">${o.z.toFixed(1)}</span>` +
    (grp ? `<span>group</span><span>${grp[0]}</span>` : '');
}

function fillList() {
  const rows = data.objects
    .filter(o => o.kind === 'GameObject')
    .sort((a, b) => a.name.localeCompare(b.name));
  $('list').innerHTML = rows.map(o =>
    `<div data-name="${o.name}">${o.name.replace(/^[A-Za-z0-9]+_/, '')}</div>`).join('');
  for (const el of $('list').children)
    el.onclick = () => {
      const m = meshByName.get(el.dataset.name);
      if (!m) return;
      select(m);
      controls.target.copy(m.position);
    };
}

// ---------------------------------------------------------------- server

async function save() {
  const n = Object.keys(moves).length;
  if (!n) return;
  msg('saving ' + n + ' …');
  const r = await (await fetch(`/api/mission/${data.name}/save`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ moves }),
  })).json();
  if (r.error) { msg(r.error, 'bad'); return; }
  msg(`saved ${r.saved} object(s); Scripts.cache cleared`, 'good');
  for (const k in moves) delete moves[k];
  $('save').disabled = true;
}

async function validate() {
  msg('checking …');
  const r = await (await fetch(`/api/mission/${data.name}/validate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      route: routePoints().map(o => ({ x: o.x, y: o.y })),
      objects: data.objects.filter(o => o.kind === 'GameObject')
        .map(o => ({ name: o.name, kind: o.kind, x: o.x, y: o.y })),
    }),
  })).json();
  if (r.error) { msg(r.error, 'bad'); return; }
  const bad = r.unroutableLegs.length + r.offMap.length + r.stacked.length;
  const line = (label, arr) =>
    `<div style="color:${arr.length ? 'var(--bad)' : 'var(--ok)'}">${label}: ${arr.length}` +
    (arr.length ? ` — ${arr.slice(0, 3).join(', ')}` : '') + `</div>`;
  $('vout').innerHTML =
    line('unroutable legs', r.unroutableLegs) +
    line('off the map', r.offMap) +
    line('sharing one point', r.stacked) +
    line('on blocked ground', r.onBlocked) +
    `<div style="color:var(--ink3)">worst leg ${r.worstLeg} of ${r.budget} A* steps</div>`;
  msg(bad ? `${bad} problem(s) — see the panel` : 'clean', bad ? 'bad' : 'good');
}

// Debug handle: lets the scene be inspected without a visible canvas, which is
// how this was verified while the preview pane was not compositing.
window.__editor = {
  stats() {
    return {
      mission: data && data.name,
      objects: objectGroup.children.length,
      navpoints: navGroup.children.length,
      facingLines: facingGroup.children.length,
      terrainVerts: terrainMesh ? terrainMesh.geometry.attributes.position.count : 0,
      routePoints: routeLine ? routeLine.geometry.attributes.position.count : 0,
      sceneChildren: scene.children.length,
      pendingMoves: Object.keys(moves).length,
      camera: camera.position.toArray().map(n => Math.round(n)),
    };
  },
  bounds() {
    const b = new THREE.Box3().setFromObject(objectGroup);
    return { min: b.min.toArray().map(Math.round), max: b.max.toArray().map(Math.round) };
  },
  move(name, x, y) {          // exercise the drag path without a pointer
    const m = meshByName.get(name);
    if (!m) return 'no such object';
    const p = toScene(x, y, m.userData.z);
    m.position.x = p.x; m.position.z = p.z;
    m.userData.x = x; m.userData.y = y;
    moves[name] = { x, y };
    $('save').disabled = false;
    return { name, x, y };
  },
  save, validate,
};

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

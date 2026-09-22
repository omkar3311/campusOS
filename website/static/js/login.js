(() => {
  const initThreeScene = () => {
    const canvas = document.querySelector('#loginWebgl');
    if (!canvas || typeof THREE === 'undefined' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, .1, 100);
    camera.position.z = 18;
    const renderer = new THREE.WebGLRenderer({ canvas, alpha:true, antialias:true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75)); renderer.setSize(innerWidth, innerHeight);
    const cluster = new THREE.Group(); scene.add(cluster);
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(1.25, 2), new THREE.MeshBasicMaterial({ color:0x38bdf8, wireframe:true, transparent:true, opacity:.62 })); cluster.add(core);
    const ringMaterial = new THREE.MeshBasicMaterial({ color:0x818cf8, transparent:true, opacity:.28 });
    [[3.2,.018,0],[4.7,.012,.55],[6.2,.01,-.38]].forEach(([radius,tube,tilt]) => { const ring = new THREE.Mesh(new THREE.TorusGeometry(radius,tube,8,100),ringMaterial); ring.rotation.x = Math.PI/2 + tilt; ring.rotation.y = tilt * 1.6; cluster.add(ring); });
    const count = 220, positions = new Float32Array(count * 3), colors = new Float32Array(count * 3), color = new THREE.Color();
    for (let i=0;i<count;i++) { const radius = 2 + Math.random()*6, angle = Math.random()*Math.PI*2; positions[i*3]=Math.cos(angle)*radius; positions[i*3+1]=(Math.random()-.5)*7; positions[i*3+2]=Math.sin(angle)*radius-2; color.setHSL(.54 + Math.random()*.18,.8,.66); colors.set([color.r,color.g,color.b],i*3); }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.BufferAttribute(positions,3)); geo.setAttribute('color',new THREE.BufferAttribute(colors,3));
    const particles = new THREE.Points(geo,new THREE.PointsMaterial({ size:.055, vertexColors:true, transparent:true, opacity:.8, blending:THREE.AdditiveBlending })); cluster.add(particles);
    const target = new THREE.Vector2(); addEventListener('pointermove', event => { target.x=(event.clientX/innerWidth-.5)*1.2; target.y=(event.clientY/innerHeight-.5)*.7; });
    addEventListener('resize',() => { camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth,innerHeight); });
    const render = (time) => { const mobile=innerWidth<850; cluster.position.set(mobile ? 0 : -4.7, mobile ? -7 : .2, 0); cluster.rotation.y=time*.00012 + target.x*.18; cluster.rotation.x=Math.sin(time*.0003)*.12 - target.y*.12; core.rotation.x=time*.00035; core.rotation.y=time*.00022; particles.rotation.y=-time*.00006; renderer.render(scene,camera); requestAnimationFrame(render); }; requestAnimationFrame(render);
  };
  initThreeScene();
  const form = document.querySelector('#authForm');
  const roleInput = document.querySelector('#role');
  const modeInput = document.querySelector('#mode');
  const modeSelector = document.querySelector('#modeBoxes');
  const submitButton = document.querySelector('#submitBtn span');
  const groups = { student: document.querySelector('#studentFields'), teacher: document.querySelector('#teacherFields'), hodLogin: document.querySelector('#hodLoginFields'), hodSignup: document.querySelector('#hodSignupFields') };
  const labels = { student: 'Continue to Dashboard', teacher: 'Continue to Dashboard', hodLogin: 'Login', hodSignup: 'Create College Access' };
  const applyForm = () => {
    const role = roleInput.value, mode = modeInput.value;
    Object.values(groups).forEach(group => { group.classList.add('is-hidden'); group.querySelectorAll('input').forEach(input => input.required = false); });
    const activeKey = role === 'student' ? 'student' : role === 'teacher' ? 'teacher' : mode === 'signup' ? 'hodSignup' : 'hodLogin';
    const active = groups[activeKey]; active.classList.remove('is-hidden'); active.querySelectorAll('input').forEach(input => input.required = true);
    submitButton.textContent = labels[activeKey];
    modeSelector.classList.toggle('is-visible', role === 'hod');
    document.querySelectorAll('[data-role]').forEach(button => { const selected = button.dataset.role === role; button.classList.toggle('is-active', selected); button.setAttribute('aria-selected', String(selected)); });
    document.querySelectorAll('[data-mode]').forEach(button => button.classList.toggle('is-active', button.dataset.mode === mode));
  };
  document.querySelectorAll('[data-role]').forEach(button => button.addEventListener('click', () => { roleInput.value = button.dataset.role; if (button.dataset.role !== 'hod') modeInput.value = 'login'; applyForm(); }));
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => { modeInput.value = button.dataset.mode; applyForm(); }));
  document.querySelectorAll('.notice button').forEach(button => button.addEventListener('click', () => button.parentElement.remove()));
  form.addEventListener('submit', event => { if (!form.checkValidity()) { event.preventDefault(); form.reportValidity(); return; } document.querySelector('.submit-button').classList.add('is-loading'); });
  const card = document.querySelector('[data-tilt]');
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) { card.addEventListener('pointermove', event => { const box = card.getBoundingClientRect(), x = (event.clientX - box.left) / box.width - .5, y = (event.clientY - box.top) / box.height - .5; card.style.transform = `perspective(1100px) rotateX(${-y * 4}deg) rotateY(${x * 5}deg) translateZ(12px)`; }); card.addEventListener('pointerleave', () => card.style.transform = ''); }
  applyForm();
})();

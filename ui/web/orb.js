/* JARVIS Orb v2 — cinematic, stateful, lightweight and audio reactive.
   Canvas 2D keeps the habitat responsive on integrated Radeon GPUs.
   This file also installs the cinematic widget layer and frameless-window drag. */
(function () {
  const TAU = Math.PI * 2;
  const STATES = {
    idle:      { energy: .24, speed: .16, hue: 198, pulse: .14, scatter: .82, turbulence: .42 },
    listening: { energy: .64, speed: .34, hue: 190, pulse: .64, scatter: 1.00, turbulence: .80 },
    thinking:  { energy: .78, speed: .66, hue: 204, pulse: .26, scatter: 1.10, turbulence: 1.02 },
    planning:  { energy: .84, speed: .52, hue: 214, pulse: .22, scatter: 1.18, turbulence: 1.14 },
    executing: { energy: .98, speed: .92, hue: 196, pulse: .38, scatter: 1.30, turbulence: 1.28 },
    observing: { energy: .66, speed: .28, hue: 186, pulse: .18, scatter: 1.12, turbulence: .72 },
    verifying: { energy: .72, speed: .22, hue: 176, pulse: .12, scatter: .74, turbulence: .54 },
    speaking:  { energy: .82, speed: .36, hue: 194, pulse: .74, scatter: 1.04, turbulence: .76 },
    success:   { energy: .76, speed: .20, hue: 164, pulse: .46, scatter: .86, turbulence: .48 },
    error:     { energy: .56, speed: .14, hue: 5,   pulse: .22, scatter: .96, turbulence: .66 },
  };

  class JarvisOrb {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d', { alpha: true });
      this.state = 'idle';
      this.target = STATES.idle;
      this.current = { ...this.target };
      this.audio = 0;
      this.audioTarget = 0;
      this.pointer = { x: 0, y: 0, tx: 0, ty: 0 };
      this.zoom = 1;
      this.dragging = false;
      this.dragX = 0;
      this.phase = Math.random() * 20;
      this.last = performance.now();
      this.reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
      const cores = navigator.hardwareConcurrency || 4;
      this.quality = localStorage.getItem('jarvis-visual-quality') || (cores <= 4 ? 'low' : 'medium');
      this.particleCount = this.quality === 'high' ? 190 : this.quality === 'low' ? 68 : 126;
      this.particles = Array.from({ length: this.particleCount }, (_, i) => ({
        a: Math.random() * TAU,
        r: .42 + Math.random() * .72,
        z: Math.random() * TAU,
        size: .3 + Math.random() * 1.25,
        speed: .3 + Math.random() * .95,
        seed: i * 1.618 + Math.random() * 8,
      }));
      this.resize = this.resize.bind(this);
      this.frame = this.frame.bind(this);
      new ResizeObserver(this.resize).observe(canvas.parentElement);
      this.bindInteraction();
      this.resize();
      requestAnimationFrame(this.frame);
    }

    setState(value) {
      const state = String(value || 'idle').toLowerCase();
      this.state = STATES[state] ? state : 'thinking';
      this.target = STATES[this.state];
      this.canvas.dataset.state = this.state;
    }

    setAudioLevel(value) {
      this.audioTarget = Math.max(0, Math.min(1, Number(value) || 0));
    }

    bindInteraction() {
      const move = event => {
        const rect = this.canvas.getBoundingClientRect();
        this.pointer.tx = ((event.clientX - rect.left) / rect.width - .5) * 2;
        this.pointer.ty = ((event.clientY - rect.top) / rect.height - .5) * 2;
        if (this.dragging) {
          const delta = event.clientX - this.dragX;
          this.phase += delta * .009;
          this.dragX = event.clientX;
        }
      };
      this.canvas.addEventListener('pointerenter', move);
      this.canvas.addEventListener('pointermove', move);
      this.canvas.addEventListener('pointerleave', () => {
        if (!this.dragging) { this.pointer.tx = 0; this.pointer.ty = 0; }
      });
      this.canvas.addEventListener('pointerdown', event => {
        this.dragging = true;
        this.dragX = event.clientX;
        this.canvas.setPointerCapture(event.pointerId);
      });
      this.canvas.addEventListener('pointerup', event => {
        this.dragging = false;
        try { this.canvas.releasePointerCapture(event.pointerId); } catch (_) {}
      });
      this.canvas.addEventListener('wheel', event => {
        event.preventDefault();
        this.zoom = Math.max(.76, Math.min(1.34, this.zoom - event.deltaY * .00045));
      }, { passive: false });
      this.canvas.addEventListener('dblclick', () => {
        this.zoom = 1;
        this.pointer.tx = 0;
        this.pointer.ty = 0;
      });
    }

    resize() {
      const rect = this.canvas.parentElement.getBoundingClientRect();
      const dpr = Math.min(devicePixelRatio || 1, this.quality === 'high' ? 1.75 : 1.35);
      this.canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      this.canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      this.canvas.style.width = `${rect.width}px`;
      this.canvas.style.height = `${rect.height}px`;
      this.dpr = dpr;
    }

    line(points, color, width, blur, close = true) {
      const c = this.ctx;
      c.save();
      c.beginPath();
      points.forEach((p, i) => i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]));
      if (close) c.closePath();
      c.strokeStyle = color;
      c.lineWidth = width;
      c.shadowColor = color;
      c.shadowBlur = blur;
      c.stroke();
      c.restore();
    }

    frame(now) {
      const dt = Math.min(.04, (now - this.last) / 1000);
      this.last = now;
      const lerp = 1 - Math.pow(.002, dt);
      ['energy', 'speed', 'hue', 'pulse', 'scatter', 'turbulence'].forEach(k => {
        this.current[k] += (this.target[k] - this.current[k]) * lerp;
      });
      const motion = this.reduced ? .05 : this.current.speed;
      this.phase += dt * motion;
      this.audio += (this.audioTarget - this.audio) * Math.min(1, dt * (this.audioTarget > this.audio ? 18 : 5));
      this.pointer.x += (this.pointer.tx - this.pointer.x) * Math.min(1, dt * 4.5);
      this.pointer.y += (this.pointer.ty - this.pointer.y) * Math.min(1, dt * 4.5);
      this.draw(now / 1000);
      requestAnimationFrame(this.frame);
    }

    draw(t) {
      const c = this.ctx, w = this.canvas.width, h = this.canvas.height;
      c.clearRect(0, 0, w, h);
      const d = this.dpr || 1;
      const cx = w * .5 + this.pointer.x * w * .018;
      const cy = h * .5 + this.pointer.y * h * .014;
      const base = Math.min(w, h) * .208 * this.zoom;
      const audio = this.audio * .16;
      const speechEnvelope = this.state === 'speaking'
        ? Math.max(0, Math.sin(t * 8.7) * .45 + Math.sin(t * 13.1 + 1.7) * .3 + Math.sin(t * 21.3) * .16) * .11
        : 0;
      const breath = 1 + Math.sin(t * (1.05 + this.current.speed)) * this.current.pulse * .055 + audio + speechEnvelope;
      const r = base * breath;
      const hue = this.current.hue;

      c.save();
      c.globalCompositeOperation = 'lighter';

      // Deep aura.
      const aura = c.createRadialGradient(cx, cy, r * .04, cx, cy, r * 2.05);
      aura.addColorStop(0, `hsla(${hue},100%,94%,${.34 + this.current.energy * .18})`);
      aura.addColorStop(.16, `hsla(${hue},100%,66%,${.17 + this.current.energy * .15})`);
      aura.addColorStop(.5, `hsla(${hue + 8},100%,48%,.065)`);
      aura.addColorStop(1, `hsla(${hue},100%,30%,0)`);
      c.fillStyle = aura;
      c.beginPath();
      c.arc(cx, cy, r * 2.08, 0, TAU);
      c.fill();

      // Energy membranes.
      const membranes = this.quality === 'low' ? 8 : 13;
      for (let layer = 0; layer < membranes; layer++) {
        const pts = [];
        const steps = this.quality === 'high' ? 164 : 104;
        const lr = r * (.40 + layer * .047);
        for (let i = 0; i <= steps; i++) {
          const a = (i / steps) * TAU;
          const turb = this.current.turbulence;
          const warp =
            Math.sin(a * (3 + layer % 4) + this.phase * (1.2 + layer * .06) + layer) * .057 * turb +
            Math.cos(a * (7 + layer % 3) - this.phase * .72 + layer * .83) * .029 * turb +
            Math.sin(a * 13 + this.phase * 1.7 + layer * 2.1) * .013;
          const rr = lr * (1 + warp * this.current.scatter);
          const squash = .90 + layer * .006;
          pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr * squash]);
        }
        const alpha = .042 + (layer % 3) * .024 + this.current.energy * .038;
        this.line(pts, `hsla(${hue + layer * 1.6},100%,${65 + layer * .6}%,${alpha})`, (.42 + layer % 2 * .24) * d, 4 * d);
      }

      // Latitude/longitude energy lattice creates a volumetric feeling.
      const latCount = this.quality === 'low' ? 3 : 5;
      for (let lat = 0; lat < latCount; lat++) {
        const q = (lat + 1) / (latCount + 1);
        const yy = cy + (q - .5) * r * 1.25;
        const rx = r * Math.sqrt(Math.max(.1, 1 - Math.pow((yy - cy) / (r * .72), 2))) * .76;
        c.beginPath();
        c.ellipse(cx, yy, rx, rx * .23, this.phase * .08, 0, TAU);
        c.strokeStyle = `hsla(${hue + 7},100%,76%,${.035 + this.current.energy * .04})`;
        c.lineWidth = .45 * d;
        c.stroke();
      }

      // Orbital paths.
      for (let ring = 0; ring < 4; ring++) {
        c.save();
        c.translate(cx, cy);
        c.rotate(this.phase * (.12 + ring * .03) * (ring % 2 ? -1 : 1) + ring * .78);
        c.scale(1, .32 + ring * .11);
        c.beginPath();
        c.arc(0, 0, r * (1.02 + ring * .16), 0, TAU);
        c.strokeStyle = `hsla(${hue + 12},100%,72%,${.075 + this.current.energy * .06})`;
        c.lineWidth = .5 * d;
        c.setLineDash([r * (.07 + ring * .01), r * .16]);
        c.lineDashOffset = -this.phase * r * (ring + 1);
        c.stroke();
        c.restore();
      }

      // Dynamic surface arcs.
      const arcCount = this.quality === 'low' ? 4 : 8;
      for (let arc = 0; arc < arcCount; arc++) {
        const start = this.phase * (.27 + arc * .03) + arc * 1.41 + Math.sin(t * .19 + arc) * .4;
        const length = .18 + (Math.sin(t * .68 + arc * 2.3) + 1) * .18;
        c.beginPath();
        c.arc(cx, cy, r * (.61 + arc * .07), start, start + length);
        c.strokeStyle = `hsla(${hue - 8 + arc * 3.4},100%,82%,${.07 + this.current.energy * .12})`;
        c.lineWidth = (.5 + (arc % 2) * .45) * d;
        c.shadowColor = `hsla(${hue},100%,70%,.8)`;
        c.shadowBlur = 9 * d;
        c.stroke();
      }

      // Depth-sorted particle cloud.
      const cloud = this.particles.map(p => {
        const a = p.a + this.phase * p.speed * .34;
        const z = Math.sin(p.z + this.phase * p.speed * .22);
        const rr = r * p.r * this.current.scatter;
        return { p, z, x: cx + Math.cos(a) * rr, y: cy + Math.sin(a) * rr * (.78 + z * .12) };
      }).sort((a, b) => a.z - b.z);
      cloud.forEach(({ p, z, x, y }) => {
        const alpha = (.11 + (z + 1) * .18) * this.current.energy;
        c.fillStyle = `hsla(${hue + p.seed * 2},100%,78%,${alpha})`;
        c.beginPath();
        c.arc(x, y, p.size * d * (.72 + (z + 1) * .2), 0, TAU);
        c.fill();
      });

      // Bright reactive core.
      const core = c.createRadialGradient(cx - r * .12, cy - r * .16, 0, cx, cy, r * .61);
      core.addColorStop(0, 'rgba(247,253,255,.99)');
      core.addColorStop(.11, `hsla(${hue - 8},100%,90%,.96)`);
      core.addColorStop(.36, `hsla(${hue},100%,62%,${.74 + this.current.energy * .2})`);
      core.addColorStop(.70, `hsla(${hue + 14},100%,42%,.24)`);
      core.addColorStop(1, `hsla(${hue},100%,35%,0)`);
      c.fillStyle = core;
      c.shadowColor = `hsla(${hue},100%,65%,.8)`;
      c.shadowBlur = 34 * d;
      c.beginPath();
      c.arc(cx, cy, r * .61, 0, TAU);
      c.fill();

      // Tiny nucleus shimmer.
      const spark = .55 + Math.sin(t * 6.2) * .12 + this.audio * .3;
      c.fillStyle = `rgba(255,255,255,${spark})`;
      c.shadowColor = 'rgba(168,237,255,.95)';
      c.shadowBlur = 18 * d;
      c.beginPath();
      c.arc(cx - r * .07, cy - r * .09, Math.max(1.2 * d, r * .025), 0, TAU);
      c.fill();
      c.restore();
    }
  }

  window.JarvisOrb = JarvisOrb;
})();

/* Cinematic assistant layer: no biometrics, no camera scan, only runtime context. */
(function () {
  const STATE_ORDER = ['listening', 'thinking', 'planning', 'executing', 'observing', 'verifying', 'speaking'];
  const STATE_NAMES = {
    idle: 'Disponível', listening: 'Ouvindo', thinking: 'Analisando', planning: 'Planejando',
    executing: 'Executando', observing: 'Observando', verifying: 'Verificando', speaking: 'Respondendo',
    success: 'Concluído', error: 'Atenção'
  };

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }

  function injectStyles() {
    if (document.querySelector('link[data-jarvis-cinematic]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'jarvis-cinematic-v2.css';
    link.dataset.jarvisCinematic = '1';
    document.head.appendChild(link);
  }

  function ensureHud() {
    if (!document.getElementById('jarvisWidgetDeck')) {
      const deck = document.createElement('div');
      deck.id = 'jarvisWidgetDeck';
      deck.className = 'jarvis-widget-deck';
      deck.innerHTML = '<div class="jarvis-widget-column left" id="jarvisWidgetsLeft"></div><div class="jarvis-widget-column right" id="jarvisWidgetsRight"></div>';
      document.body.appendChild(deck);
    }
    if (!document.getElementById('jarvisStateRail')) {
      const rail = document.createElement('div');
      rail.id = 'jarvisStateRail';
      rail.className = 'jarvis-state-rail';
      rail.innerHTML = STATE_ORDER.map(x => `<i data-step="${x}" title="${STATE_NAMES[x]}"></i>`).join('');
      document.body.appendChild(rail);
    }
    if (!document.querySelector('.jarvis-voice-halo')) {
      const halo = document.createElement('div');
      halo.className = 'jarvis-voice-halo';
      document.body.appendChild(halo);
    }
  }

  function stateNow() {
    return String(document.body.dataset.agentState || 'idle').toLowerCase();
  }

  function activeDetail() {
    const node = document.getElementById('orbActivityLabel');
    return node ? String(node.textContent || '').trim() : '';
  }

  function updateRail() {
    const state = stateNow();
    const rail = document.getElementById('jarvisStateRail');
    if (!rail) return;
    const current = STATE_ORDER.indexOf(state);
    rail.querySelectorAll('i').forEach((dot, i) => {
      dot.classList.toggle('active', i === current);
      dot.classList.toggle('done', current > i && current >= 0);
    });
    rail.style.opacity = ['idle','success','error'].includes(state) ? '.48' : '.92';
  }

  function widget(label, title, body, extra = '', stateClass = '') {
    return `<section class="jarvis-widget ${stateClass}"><small>${escapeHtml(label)}</small><b>${escapeHtml(title)}</b><span>${escapeHtml(body)}</span>${extra}</section>`;
  }

  function renderHud() {
    const left = document.getElementById('jarvisWidgetsLeft');
    const right = document.getElementById('jarvisWidgetsRight');
    if (!left || !right) return;

    const state = stateNow();
    const detail = activeDetail() || STATE_NAMES[state] || 'Sistema online';
    const snap = (typeof snapshot !== 'undefined' && snapshot) ? snapshot : {};
    const task = snap.active_task || null;
    const project = snap.projects?.current || null;
    const hw = snap.hardware || {};
    const model = String(snap.model || 'local core');
    const conv = snap.cognitive?.conversations || {};
    const learning = snap.cognitive?.learning || {};
    const jobs = snap.long_horizon?.stats || {};

    const stateClass = state === 'success' ? 'state-success' : state === 'error' ? 'state-error' : state === 'listening' ? 'state-listening' : '';
    const activityExtra = `<div class="jc-row"><i class="jc-dot"></i><small>${escapeHtml((STATE_NAMES[state] || state).toUpperCase())}</small></div>${['thinking','planning','executing','observing','verifying','speaking','listening'].includes(state) ? '<div class="jc-meter"><i></i></div>' : ''}`;

    const leftItems = [widget('LIVE PROCESS', detail.slice(0, 54) || 'Jarvis', task?.goal ? String(task.goal).slice(0, 92) : 'Contexto e ferramentas são ativados sob demanda.', activityExtra, stateClass)];
    if (project) leftItems.push(widget('ACTIVE PROJECT', project.name || 'Projeto', project.description || 'Contexto persistente ligado a esta conversa.'));
    else if ((jobs.active || 0) > 0) leftItems.push(widget('LONG HORIZON', `${jobs.active} job(s) ativo(s)`, 'Tarefas persistentes continuam sendo acompanhadas pelo runtime.'));

    const systemBody = hw.tier
      ? `${hw.tier} • ${hw.ram_gb || '?'} GB RAM • ${hw.cpu_threads || '?'} threads`
      : 'Processamento local e execução supervisionada';
    const rightItems = [widget('LOCAL CORE', model.toUpperCase(), systemBody)];
    const memoryText = `${conv.sessions || 0} sessões • ${learning.active_lessons || 0} lições ativas`;
    rightItems.push(widget('CONTEXT MEMORY', 'Memória persistente', memoryText));

    left.innerHTML = leftItems.join('');
    right.innerHTML = rightItems.join('');
    updateRail();
  }

  function installWindowDrag() {
    // The Python bridge already exposes beginMove()->QWindow.startSystemMove().
    // The original web UI did not call it. Binding the real drag zones here
    // enables native Windows dragging, including crossing monitor boundaries.
    document.addEventListener('pointerdown', event => {
      if (event.button !== 0) return;
      const zone = event.target?.closest?.('.drag-zone');
      if (!zone) return;
      if (event.target.closest('button,input,textarea,select,a,[contenteditable="true"],.no-drag')) return;
      try {
        if (typeof bridge !== 'undefined' && bridge?.beginMove) {
          event.preventDefault();
          bridge.beginMove();
        }
      } catch (_) {}
    }, true);
  }

  function boot() {
    injectStyles();
    ensureHud();
    installWindowDrag();
    renderHud();
    const observer = new MutationObserver(renderHud);
    observer.observe(document.body, { attributes: true, attributeFilter: ['data-agent-state'] });
    setInterval(renderHud, 1500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();

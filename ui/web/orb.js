/* Lightweight procedural JARVIS orb. Canvas 2D is intentional: it keeps the
   habitat responsive on integrated Radeon GPUs while still reacting to real
   runtime states delivered through QWebChannel. */
(function () {
  const TAU = Math.PI * 2;
  const STATES = {
    idle:      { energy: .26, speed: .18, hue: 198, pulse: .16, scatter: .82 },
    listening: { energy: .58, speed: .34, hue: 192, pulse: .52, scatter: 1.02 },
    thinking:  { energy: .72, speed: .72, hue: 205, pulse: .24, scatter: 1.10 },
    planning:  { energy: .78, speed: .56, hue: 214, pulse: .20, scatter: 1.18 },
    executing: { energy: .94, speed: .92, hue: 197, pulse: .36, scatter: 1.28 },
    observing: { energy: .62, speed: .30, hue: 187, pulse: .18, scatter: 1.12 },
    verifying: { energy: .68, speed: .24, hue: 178, pulse: .12, scatter: .72 },
    speaking:  { energy: .78, speed: .38, hue: 195, pulse: .68, scatter: 1.04 },
    success:   { energy: .74, speed: .22, hue: 166, pulse: .44, scatter: .88 },
    error:     { energy: .52, speed: .16, hue: 8, pulse: .20, scatter: .96 },
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
      this.particleCount = this.quality === 'high' ? 170 : this.quality === 'low' ? 64 : 110;
      this.particles = Array.from({ length: this.particleCount }, (_, i) => ({
        a: Math.random() * TAU,
        r: .46 + Math.random() * .64,
        z: Math.random() * TAU,
        size: .35 + Math.random() * 1.15,
        speed: .35 + Math.random() * .9,
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
        this.dragging = true; this.dragX = event.clientX;
        this.canvas.setPointerCapture(event.pointerId);
      });
      this.canvas.addEventListener('pointerup', event => {
        this.dragging = false; this.canvas.releasePointerCapture(event.pointerId);
      });
      this.canvas.addEventListener('wheel', event => {
        event.preventDefault();
        this.zoom = Math.max(.76, Math.min(1.28, this.zoom - event.deltaY * .00045));
      }, { passive: false });
      this.canvas.addEventListener('dblclick', () => {
        this.zoom = 1; this.pointer.tx = 0; this.pointer.ty = 0;
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

    line(points, color, width, blur) {
      const c = this.ctx;
      c.save();
      c.beginPath();
      points.forEach((p, i) => i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]));
      c.closePath();
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
      ['energy', 'speed', 'hue', 'pulse', 'scatter'].forEach(k => {
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
      const cx = w * .5 + this.pointer.x * w * .018, cy = h * .5 + this.pointer.y * h * .014;
      const base = Math.min(w, h) * .205 * this.zoom;
      const audio = this.audio * .14;
      const speechEnvelope = this.state === 'speaking'
        ? Math.max(0, Math.sin(t * 8.7) * .45 + Math.sin(t * 13.1 + 1.7) * .3 + Math.sin(t * 21.3) * .16) * .105
        : 0;
      const breath = 1 + Math.sin(t * (1.1 + this.current.speed)) * this.current.pulse * .055 + audio + speechEnvelope;
      const r = base * breath;
      const hue = this.current.hue;

      c.save();
      c.globalCompositeOperation = 'lighter';
      const aura = c.createRadialGradient(cx, cy, r * .05, cx, cy, r * 1.85);
      aura.addColorStop(0, `hsla(${hue},100%,92%,${.32 + this.current.energy * .18})`);
      aura.addColorStop(.18, `hsla(${hue},100%,62%,${.14 + this.current.energy * .14})`);
      aura.addColorStop(.55, `hsla(${hue + 8},100%,48%,.055)`);
      aura.addColorStop(1, `hsla(${hue},100%,30%,0)`);
      c.fillStyle = aura;c.beginPath();c.arc(cx, cy, r * 1.9, 0, TAU);c.fill();

      // Irregular energy membranes: each layer uses different frequencies so
      // the motion never reads as one repeating spinner.
      const membranes = this.quality === 'low' ? 7 : 11;
      for (let layer = 0; layer < membranes; layer++) {
        const pts = [];
        const steps = this.quality === 'high' ? 150 : 96;
        const lr = r * (.44 + layer * .055);
        for (let i = 0; i <= steps; i++) {
          const a = (i / steps) * TAU;
          const warp =
            Math.sin(a * (3 + layer % 4) + this.phase * (1.3 + layer * .07) + layer) * .055 +
            Math.cos(a * (7 + layer % 3) - this.phase * .7 + layer * .83) * .028 +
            Math.sin(a * 13 + this.phase * 1.8 + layer * 2.1) * .012;
          const rr = lr * (1 + warp * this.current.scatter);
          const squash = .91 + layer * .006;
          pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr * squash]);
        }
        const alpha = .045 + (layer % 3) * .025 + this.current.energy * .035;
        this.line(pts, `hsla(${hue + layer * 1.8},100%,${64 + layer}%,${alpha})`, (.42 + layer % 2 * .24) * d, 4 * d);
      }

      // Three tilted orbital paths with moving highlights.
      for (let ring = 0; ring < 3; ring++) {
        c.save();c.translate(cx, cy);c.rotate(this.phase * (.13 + ring * .035) * (ring === 1 ? -1 : 1) + ring * .9);
        c.scale(1, .36 + ring * .13);
        c.beginPath();c.arc(0, 0, r * (1.07 + ring * .18), 0, TAU);
        c.strokeStyle = `hsla(${hue + 12},100%,72%,${.10 + this.current.energy * .08})`;
        c.lineWidth = .55 * d;c.setLineDash([r * .1, r * .18]);c.lineDashOffset = -this.phase * r * (ring + 1);
        c.stroke();c.restore();
      }

      // Short-lived energy arcs travel across the surface. Their changing
      // start/end angles keep the core feeling active even while idle.
      const arcCount = this.quality === 'low' ? 3 : 6;
      for (let arc = 0; arc < arcCount; arc++) {
        const start = this.phase * (.28 + arc * .035) + arc * 1.73 + Math.sin(t * .17 + arc) * .4;
        const length = .24 + (Math.sin(t * .7 + arc * 2.4) + 1) * .18;
        c.beginPath();
        c.arc(cx, cy, r * (.7 + arc * .075), start, start + length);
        c.strokeStyle = `hsla(${hue - 8 + arc * 4},100%,82%,${.08 + this.current.energy * .13})`;
        c.lineWidth = (.55 + (arc % 2) * .45) * d;
        c.shadowColor = `hsla(${hue},100%,70%,.8)`;c.shadowBlur = 9 * d;c.stroke();
      }

      // Depth-sorted particle cloud.
      const cloud = this.particles.map(p => {
        const a = p.a + this.phase * p.speed * .34;
        const z = Math.sin(p.z + this.phase * p.speed * .22);
        const rr = r * p.r * this.current.scatter;
        return { p, z, x: cx + Math.cos(a) * rr, y: cy + Math.sin(a) * rr * (.78 + z * .12) };
      }).sort((a, b) => a.z - b.z);
      cloud.forEach(({ p, z, x, y }) => {
        const alpha = (.12 + (z + 1) * .17) * this.current.energy;
        c.fillStyle = `hsla(${hue + p.seed * 2},100%,78%,${alpha})`;
        c.beginPath();c.arc(x, y, p.size * d * (.72 + (z + 1) * .2), 0, TAU);c.fill();
      });

      const core = c.createRadialGradient(cx - r * .12, cy - r * .16, 0, cx, cy, r * .58);
      core.addColorStop(0, 'rgba(242,252,255,.98)');
      core.addColorStop(.12, `hsla(${hue - 8},100%,88%,.95)`);
      core.addColorStop(.38, `hsla(${hue},100%,61%,${.72 + this.current.energy * .2})`);
      core.addColorStop(.72, `hsla(${hue + 14},100%,42%,.22)`);
      core.addColorStop(1, `hsla(${hue},100%,35%,0)`);
      c.fillStyle = core;c.shadowColor = `hsla(${hue},100%,65%,.75)`;c.shadowBlur = 30 * d;
      c.beginPath();c.arc(cx, cy, r * .59, 0, TAU);c.fill();
      c.restore();
    }
  }

  window.JarvisOrb = JarvisOrb;
})();

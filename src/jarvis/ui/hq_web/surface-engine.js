/*
 * Adaptive Interface Engine
 *
 * This is deliberately a registry of trusted renderers, rather than an HTML
 * execution channel. Chat/runtime may describe an intent, but only the
 * registered surface types below can be materialised in the workspace.
 */
(function () {
  const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
  const icons = { weather:'☀', agents:'◌', system:'◇', research:'⌕', mission:'◈', approval:'✓', briefing:'☼', discovery:'✦', improvement:'↟' };

  class UIRegistry {
    constructor() { this.items = new Map(); }
    register(type, renderer) { this.items.set(type, renderer); }
    render(intent) { return this.items.get(intent.surface)?.(intent) || null; }
  }

  class SurfaceManager {
    constructor(root, registry) {
      this.root = root; this.registry = registry; this.surfaces = new Map(); this.counter = 0;
    }
    spawn(intent) {
      const content = this.registry.render(intent);
      if (!content) return null;
      const id = intent.surface_id || `surface-${++this.counter}`;
      this.close(id);
      const el = document.createElement('article');
      el.className = `contextual-surface ${intent.priority || 'contextual'}`;
      el.dataset.surfaceId = id; el.dataset.type = intent.surface;
      el.innerHTML = `<div class="surface-connection"></div><header><span class="surface-icon">${icons[intent.surface] || '◈'}</span><div><small>${safe(intent.surface)}</small><strong>${safe(intent.title || intent.surface)}</strong></div><div class="surface-actions"><button data-minimize aria-label="Minimizar">−</button><button data-close aria-label="Fechar">×</button></div></header><div class="surface-content">${content}</div>`;
      el.querySelector('[data-close]').onclick = () => this.close(id);
      el.querySelector('[data-minimize]').onclick = () => this.minimize(id);
      this.root.appendChild(el); this.surfaces.set(id, { ...intent, surface_id:id, el, state:'open', created_at:Date.now(), updated_at:Date.now() });
      requestAnimationFrame(() => el.classList.add('is-open'));
      return id;
    }
    open(id) { const item=this.surfaces.get(id); if(item){item.el.classList.remove('is-minimized');item.state='open';} }
    close(id) { const item=this.surfaces.get(id); if(!item)return; item.el.classList.remove('is-open'); setTimeout(()=>item.el.remove(),180); this.surfaces.delete(id); }
    minimize(id) { const item=this.surfaces.get(id); if(!item)return; item.el.classList.toggle('is-minimized'); item.state=item.el.classList.contains('is-minimized')?'minimized':'open'; }
    focus(id) { const item=this.surfaces.get(id); if(item){item.el.scrollIntoView({behavior:'smooth',block:'nearest'}); item.el.classList.add('is-focused');setTimeout(()=>item.el.classList.remove('is-focused'),500);} }
    replace(id, intent) { this.close(id); return this.spawn({...intent,surface_id:id}); }
    // Kept explicit for the runtime contract; freeform dragging is deliberately
    // not enabled in the Home radial layout yet.
    move() {} resize() {} dock() {} stack() {} collapse(id) { this.minimize(id); } restore(id) { this.open(id); }
  }

  const registry = new UIRegistry();
  registry.register('weather', intent => `<div class="surface-status unavailable"><b>Waiting for weather connector</b><span>Não conectado</span></div><p>Esta superfície está pronta para exibir condições, previsão e alertas quando uma fonte de clima for configurada.</p>`);
  registry.register('agents', intent => {
    const a=intent.data?.agents || [];
    return a.length ? `<div class="agent-surface-list">${a.slice(0,4).map(x=>`<div><i class="status-light ${safe(x.status||'idle')}"></i><span><b>${safe(x.name)}</b><small>${safe(x.activity||x.status||'Disponível')}</small></span></div>`).join('')}</div>` : `<div class="surface-status unavailable"><b>Waiting for runtime</b><span>Sem agentes ativos</span></div>`;
  });
  registry.register('system', intent => `<div class="system-surface">${Object.entries(intent.data||{}).slice(0,4).map(([k,v])=>`<div><small>${safe(k)}</small><b>${safe(v?.status || v || '—')}</b></div>`).join('') || '<span>Waiting for runtime</span>'}</div>`);
  registry.register('research', intent => `<div class="surface-status"><b>Research workspace</b><span>Pronto para uma missão</span></div><p>Inicie uma pesquisa pelo Companion. Resultados verificados aparecerão aqui.</p>`);
  registry.register('mission', intent => `<div class="surface-status"><b>${safe(intent.data?.title || 'Nenhuma missão ativa')}</b><span>${safe(intent.data?.status || 'Waiting for runtime')}</span></div>`);
  registry.register('approval', intent => `<div class="surface-status attention"><b>${safe(intent.data?.action || 'Ação requer aprovação')}</b><span>${safe(intent.data?.risk || 'External operation')}</span></div>`);
  registry.register('briefing', intent => {
    const d=intent.data||{}, news=(d.news||[]).slice(0,3);
    return `<div class="surface-status"><b>${safe(d.weather?.summary || 'Briefing diário')}</b><span>${safe(d.location || '')}</span></div>${news.length?`<div class="surface-mini-list">${news.map(x=>`<span>${safe(x.title||x)}</span>`).join('')}</div>`:''}`;
  });
  registry.register('discovery', intent => {
    const d=intent.data||{};
    return `<div class="surface-status"><b>${safe(d.title || 'Nova descoberta')}</b><span>${safe(d.attention_level || 'ambient')}</span></div><p>${safe(d.summary || d.topic || '')}</p>`;
  });
  registry.register('improvement', intent => {
    const d=intent.data||{};
    return `<div class="surface-status attention"><b>${safe(d.title || 'Melhoria proposta')}</b><span>${safe(d.risk || 'low')} · ${safe(d.status || 'pending')}</span></div><p>${safe(d.summary || '')}</p>`;
  });
  for (const type of ['browser','project','files','document','analytics','chart','comparison','verification','terminal','code','media','search_results']) registry.register(type, intent => `<div class="surface-status unavailable"><b>${safe(intent.title || type)}</b><span>Waiting for runtime</span></div><p>Superfície registrada. Será preenchida somente quando a fonte de dados correspondente estiver conectada.</p>`);

  window.JarvisUI = { UIRegistry, SurfaceManager, registry, create(root) { return new SurfaceManager(root, registry); } };
})();

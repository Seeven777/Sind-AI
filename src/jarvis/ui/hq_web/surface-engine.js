/*
 * Jarvis Generative Surface Engine v11
 *
 * Runtime answers may describe structured data, but they never provide HTML.
 * Only renderers registered here can materialise UI. This preserves the feeling
 * of a generative workspace without creating an arbitrary-code execution path.
 */
(function(){
  const safe=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
  const icons={weather:'◌',news:'⌁',research:'⌕',agenda:'◫',inbox:'▤',agents:'◇',system:'⌘',mission:'◈',comparison:'⇄',analytics:'⌁',approval:'✓',briefing:'☼',discovery:'✦',improvement:'↟',generic:'◇'};
  const safeUrl=value=>{try{const u=new URL(String(value||''),location.href);return ['http:','https:'].includes(u.protocol)?u.href:''}catch{return ''}};

  function sourcesBlock(data){
    const rows=(data?.sources||[]).filter(x=>safeUrl(x?.url)).slice(0,8);
    if(!rows.length)return '';
    return `<section class="surface-section surface-sources"><div class="surface-section-title">FONTES <span>${rows.length}</span></div><div class="source-grid">${rows.map(x=>`<a href="${safe(safeUrl(x.url))}" target="_blank" rel="noopener noreferrer"><span>${safe(x.domain||'fonte')}</span><b>${safe(x.title||x.domain||'Abrir fonte')}</b><i>↗</i></a>`).join('')}</div></section>`;
  }
  function summaryBlock(data){return data?.summary?`<p class="surface-summary">${safe(data.summary)}</p>`:''}
  function itemsBlock(data,label='DESTAQUES'){
    const rows=(data?.items||[]).slice(0,8);if(!rows.length)return '';
    return `<section class="surface-section"><div class="surface-section-title">${safe(label)} <span>${rows.length}</span></div><div class="surface-list">${rows.map((x,i)=>{const url=safeUrl(x?.url);const body=`<span class="surface-index">${String(i+1).padStart(2,'0')}</span><span class="surface-item-copy"><b>${safe(x?.title||x)}</b>${x?.source?`<small>${safe(x.source)}</small>`:''}</span>${url?'<i>↗</i>':''}`;return url?`<a href="${safe(url)}" target="_blank" rel="noopener noreferrer">${body}</a>`:`<div>${body}</div>`}).join('')}</div></section>`;
  }
  function metaBlock(data){const rows=Object.entries(data?.meta||{}).slice(0,4);return rows.length?`<div class="surface-meta-grid">${rows.map(([k,v])=>`<div><small>${safe(k)}</small><b>${safe(v)}</b></div>`).join('')}</div>`:''}

  class UIRegistry{
    constructor(){this.items=new Map()}
    register(type,renderer){this.items.set(type,renderer)}
    render(intent){return this.items.get(intent.surface)?.(intent)||this.items.get('generic')?.(intent)||null}
  }

  class SurfaceManager{
    constructor(root,registry,options={}){
      this.root=root;this.registry=registry;this.options=options;this.surfaces=new Map();this.counter=0;this.max=options.max||1;
    }
    present(intents){
      const list=(Array.isArray(intents)?intents:[]).filter(Boolean).slice(0,this.max);
      if(!list.length){this.clear();return []}
      this.clear();
      return list.map(x=>this.spawn(x)).filter(Boolean);
    }
    spawn(intent){
      const content=this.registry.render(intent);if(!content)return null;
      const id=intent.surface_id||`surface-${++this.counter}`;
      const el=document.createElement('article');
      const expanded=!!intent.default_expanded;
      el.className=`contextual-surface surface-${safe(intent.surface||'generic')} ${expanded?'is-expanded':''}`;
      el.dataset.surfaceId=id;el.dataset.type=intent.surface||'generic';
      const subtitle=intent.subtitle?`<span class="surface-subtitle">${safe(intent.subtitle)}</span>`:'';
      el.innerHTML=`<div class="surface-beam" aria-hidden="true"></div><div class="surface-glow" aria-hidden="true"></div><header class="surface-header"><div class="surface-heading"><span class="surface-icon">${icons[intent.surface]||icons.generic}</span><div><small>${safe(String(intent.surface||'context').toUpperCase())}</small><strong>${safe(intent.title||'Contexto')}</strong>${subtitle}</div></div><div class="surface-actions"><button data-expand aria-label="Expandir ou recolher">${expanded?'↙':'↗'}</button><button data-close aria-label="Fechar">×</button></div></header><div class="surface-content">${content}</div><footer><span>materializado por Jarvis</span><button data-expand-footer>${expanded?'Recolher':'Expandir'}</button></footer>`;
      const toggle=()=>this.expand(id);
      el.querySelector('[data-close]').onclick=()=>this.close(id);
      el.querySelector('[data-expand]').onclick=toggle;
      el.querySelector('[data-expand-footer]').onclick=toggle;
      this.root.appendChild(el);
      this.surfaces.set(id,{...intent,surface_id:id,el,state:expanded?'expanded':'compact'});
      requestAnimationFrame(()=>el.classList.add('is-open'));
      this._notify();return id;
    }
    expand(id){const item=this.surfaces.get(id);if(!item)return;const expanded=item.el.classList.toggle('is-expanded');item.state=expanded?'expanded':'compact';item.el.querySelector('[data-expand]').textContent=expanded?'↙':'↗';item.el.querySelector('[data-expand-footer]').textContent=expanded?'Recolher':'Expandir';this._notify()}
    close(id){const item=this.surfaces.get(id);if(!item)return;item.el.classList.remove('is-open');setTimeout(()=>item.el.remove(),240);this.surfaces.delete(id);this._notify()}
    clear(){for(const id of [...this.surfaces.keys()])this.close(id)}
    focus(id){const item=this.surfaces.get(id);if(item){item.el.classList.add('is-focused');setTimeout(()=>item.el.classList.remove('is-focused'),620)}}
    _notify(){this.options.onChange?.({count:this.surfaces.size,items:[...this.surfaces.values()]})}
  }

  const registry=new UIRegistry();
  registry.register('weather',intent=>{const d=intent.data||{},metrics=(d.metrics||[]).slice(0,4);return `${metrics.length?`<div class="weather-metrics">${metrics.map((m,i)=>`<div class="weather-metric ${i===0?'primary':''}"><small>${safe(m.label)}</small><b>${safe(m.value)}</b></div>`).join('')}</div>`:''}${summaryBlock(d)}${sourcesBlock(d)}`});
  registry.register('news',intent=>{const d=intent.data||{};return `${summaryBlock(d)}${itemsBlock(d,'MANCHETES')}${sourcesBlock(d)}`});
  registry.register('research',intent=>{const d=intent.data||{};return `${summaryBlock(d)}${itemsBlock(d,'PONTOS-CHAVE')}${sourcesBlock(d)}`});
  registry.register('agenda',intent=>{const d=intent.data||{};return `${metaBlock(d)}${summaryBlock(d)}${itemsBlock(d,'AGENDA')}${sourcesBlock(d)}`});
  registry.register('inbox',intent=>{const d=intent.data||{};return `${metaBlock(d)}${summaryBlock(d)}${itemsBlock(d,'PRIORIDADES')}${sourcesBlock(d)}`});
  registry.register('agents',intent=>{const d=intent.data||{};return `${metaBlock(d)}${summaryBlock(d)}${itemsBlock(d,'ATIVIDADE')}`});
  registry.register('system',intent=>{const d=intent.data||{};return `${metaBlock(d)}${summaryBlock(d)}${itemsBlock(d,'SINAIS')}`});
  registry.register('comparison',intent=>{const d=intent.data||{};return `${summaryBlock(d)}${itemsBlock(d,'DIFERENÇAS')}${sourcesBlock(d)}`});
  registry.register('analytics',intent=>{const d=intent.data||{};return `${metaBlock(d)}${summaryBlock(d)}${itemsBlock(d,'INSIGHTS')}${sourcesBlock(d)}`});
  registry.register('mission',intent=>{const d=intent.data||{};return `${summaryBlock(d)}${itemsBlock(d,'ETAPAS')}${sourcesBlock(d)}`});
  registry.register('generic',intent=>{const d=intent.data||{};return `${metaBlock(d)}${summaryBlock(d)}${itemsBlock(d)}${sourcesBlock(d)}`});

  window.JarvisUI={UIRegistry,SurfaceManager,registry,create(root,options={}){return new SurfaceManager(root,registry,options)}};
})();

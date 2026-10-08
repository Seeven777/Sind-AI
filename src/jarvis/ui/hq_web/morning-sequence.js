/* Jarvis Morning Sequence v12.2 — cache-safe interactive boot + live briefing surfaces. */
(function(){
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
  const safeUrl=v=>{try{const u=new URL(String(v||''),location.href);return ['http:','https:'].includes(u.protocol)?u.href:''}catch{return ''}};
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const speechMs=t=>Math.max(1900,Math.min(8800,String(t||'').trim().split(/\s+/).length*335+700));
  const dayKey=()=>new Date().toISOString().slice(0,10);
  const weatherGlyph=code=>{code=Number(code);if(code===0)return 'sun';if([1,2].includes(code))return 'partly';if([3,45,48].includes(code))return 'cloud';if([51,53,55,56,57,61,63,65,66,67,80,81,82].includes(code))return 'rain';if([95,96,99].includes(code))return 'storm';return 'cloud'};
  function iconSvg(type){
    const sun='<circle cx="32" cy="32" r="10" fill="#ffd86b"/><g stroke="#ffd86b" stroke-width="2" stroke-linecap="round"><path d="M32 9v7M32 48v7M9 32h7M48 32h7M15.5 15.5l5 5M43.5 43.5l5 5M48.5 15.5l-5 5M20.5 43.5l-5 5"/></g>';
    const cloud='<path d="M19 43h27c7 0 11-4 11-10 0-5-4-9-9-10-2-8-8-12-16-12-9 0-16 6-17 15-6 1-9 5-9 9 0 5 5 8 13 8z" fill="#e8f7ff" opacity=".95"/>';
    const rain='<g stroke="#74d8ff" stroke-width="2.3" stroke-linecap="round"><path d="M20 49l-3 6M31 49l-3 6M42 49l-3 6"/></g>';
    const lightning='<path d="M33 43h9l-8 8h6L28 62l3-10h-7z" fill="#ffd35b"/>';
    let inner=cloud;if(type==='sun')inner=sun;else if(type==='partly')inner='<g transform="translate(-8 -8) scale(.72)">'+sun+'</g>'+cloud;else if(type==='rain')inner=cloud+rain;else if(type==='storm')inner=cloud+rain+lightning;
    return `<svg viewBox="0 0 64 64" aria-hidden="true">${inner}</svg>`;
  }
  function hourLabel(t){try{return new Date(t).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}catch{return String(t||'').slice(-5)}}
  function dueLabel(t){if(!t)return '';try{const d=new Date(t),n=new Date();const same=d.toDateString()===n.toDateString();return same?'HOJE '+d.toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}):d.toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit'})}catch{return ''}}

  class MorningSequence{
    constructor(options={}){this.options=options;this.layer=null;this.skipped=false;this.boot=null;this._buildBoot();}
    _buildBoot(){
      if(document.querySelector('.boot-sequence')){this.boot=document.querySelector('.boot-sequence');return}
      document.body.classList.add('jarvis-booting');
      const el=document.createElement('section');el.className='boot-sequence';el.innerHTML=`<div class="boot-grid"></div><div class="boot-content"><div class="boot-core"><i class="boot-ring"></i></div><div class="boot-copy"><small>JARVIS / INITIALIZATION</small><h1>Acordando o núcleo</h1><p>Verificando infraestrutura local antes de assumir presença.</p><div class="boot-checks"><div class="boot-check" data-check="runtime"><i></i><span>Runtime principal</span><b>aguardando</b></div><div class="boot-check" data-check="memory"><i></i><span>Memória persistente</span><b>aguardando</b></div><div class="boot-check" data-check="models"><i></i><span>Model mesh</span><b>aguardando</b></div><div class="boot-check" data-check="connectors"><i></i><span>Conectores e rede</span><b>aguardando</b></div><div class="boot-check" data-check="voice"><i></i><span>Voz e presença</span><b>aguardando</b></div></div></div><button class="boot-skip">Pular abertura</button>`;
      document.body.appendChild(el);this.boot=el;el.querySelector('.boot-skip').onclick=()=>this.finishBoot(true);
    }
    async bootProgress(){
      const rows=[...this.boot.querySelectorAll('.boot-check')];
      for(const row of rows){if(this.skipped)break;row.classList.add('active');row.querySelector('b').textContent='verificando';await sleep(210+Math.random()*170);row.classList.remove('active');row.classList.add('done');row.querySelector('b').textContent='online'}
    }
    finishBoot(skip=false){if(skip)this.skipped=true;document.body.classList.remove('jarvis-booting');this.boot?.classList.add('is-leaving');setTimeout(()=>this.boot?.remove(),900);this.options.onWake?.();}
    _ensureLayer(){if(this.layer)return this.layer;const l=document.createElement('section');l.className='morning-layer hidden';l.innerHTML='<button class="morning-skip">Encerrar briefing</button><div class="morning-beam"></div><div class="morning-caption">MORNING BRIEFING</div><div class="morning-stage"></div>';document.querySelector(this.options.hostSelector||'#presence, .stage')?.appendChild(l);l.querySelector('.morning-skip').onclick=()=>this.finish();this.layer=l;return l}
    async initialize(){await this.bootProgress();if(!this.skipped){await sleep(220);this.finishBoot(false)}return !this.skipped}
    shouldRun(force=false){if(force)return true;const now=new Date();if(now.getHours()<5||now.getHours()>=13)return false;return localStorage.getItem('jarvis.morning.sequence.'+dayKey())!=='1'}
    beginPreparing(){
      const l=this._ensureLayer(),stage=l.querySelector('.morning-stage'),host=document.querySelector(this.options.hostSelector||'#presence, .stage');
      this.skipped=false;l.classList.remove('hidden');requestAnimationFrame(()=>l.classList.add('active'));host?.classList.add('morning-active');
      stage.innerHTML='<div class="morning-preparing"><i></i><small>JARVIS / MORNING BRIEFING</small><b>Sincronizando o seu dia</b><span>clima · notícias · responsabilidades</span></div>';
      requestAnimationFrame(()=>stage.firstElementChild?.classList.add('enter'));
    }
    preparingStage(text){const el=this.layer?.querySelector('.morning-preparing b');if(el)el.textContent=text}
    async prepare(force=false){
      this.preparingStage('Atualizando fontes em tempo real');
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),235000);
      try{
        const r=await fetch('/api/morning/prepare',{method:'POST',headers:{'Content-Type':'application/json','Cache-Control':'no-cache'},cache:'no-store',body:JSON.stringify({force}),signal:controller.signal});
        if(!r.ok){let detail='';try{detail=(await r.json()).error||''}catch{}throw new Error(detail||('HTTP '+r.status))}
        const x=await r.json(),seq=x.sequence||x;
        if(!seq||seq.schema!=='jarvis.morning.v1')throw new Error('Sequência de briefing inválida.');
        return seq;
      }catch(e){if(e?.name==='AbortError')throw new Error('O briefing excedeu o tempo de sincronização.');throw e}finally{clearTimeout(timer)}
    }
    async start(sequence,{force=false}={}){
      if(!sequence||!this.shouldRun(force))return false;const l=this._ensureLayer(),host=document.querySelector(this.options.hostSelector||'#presence, .stage'),stage=l.querySelector('.morning-stage');this.skipped=false;l.classList.remove('hidden');requestAnimationFrame(()=>l.classList.add('active'));host?.classList.add('morning-active','morning-awake');l.querySelector('.morning-caption').classList.add('show');
      const prep=stage.querySelector('.morning-preparing');if(prep){prep.classList.add('exit');await sleep(280);prep.remove()}
      await sleep(420);host?.classList.remove('morning-awake');
      await this._say(sequence.greeting||'Bom dia, senhor.');if(this.skipped)return false;
      if(sequence.weather)await this.weather(sequence.weather);if(this.skipped)return false;
      if(sequence.news?.length)await this.news(sequence.news);if(this.skipped)return false;
      await this.tasks(sequence.tasks||[]);if(this.skipped)return false;
      if(sequence.improvements_pending>0)await this._say(`Há ${sequence.improvements_pending} melhoria${sequence.improvements_pending===1?'':'s'} minha${sequence.improvements_pending===1?'':'s'} aguardando sua aprovação.`);
      await this.closing(sequence.closing||'O que faremos hoje?');
      localStorage.setItem('jarvis.morning.sequence.'+dayKey(),'1');return true;
    }
    async _say(text){if(this.skipped||!text)return;this.options.setState?.('SPEAKING');try{this.options.speak?.(text,{force:true})}catch{}await sleep(speechMs(text));if(!this.skipped)this.options.setState?.('IDLE')}
    materialize(el){const l=this._ensureLayer(),stage=l.querySelector('.morning-stage'),host=document.querySelector(this.options.hostSelector||'#presence, .stage');host?.classList.add('morning-showing-gadget');l.classList.add('materialize');stage.innerHTML='';stage.appendChild(el);requestAnimationFrame(()=>{el.classList.add('enter');if(el.classList.contains('news-constellation'))el.classList.add('enter')});setTimeout(()=>l.classList.remove('materialize'),900)}
    async dismiss(el,delay=580){if(!el)return;el.classList.add('exit');el.classList.remove('enter');await sleep(delay);el.remove();document.querySelector(this.options.hostSelector||'#presence, .stage')?.classList.remove('morning-showing-gadget')}
    async weather(w){
      const c=w.current||{},d=w.today||{},u=w.units||{},hourly=w.hourly||[];const el=document.createElement('article');el.className='morning-gadget weather-gadget';const code=c.weather_code;el.innerHTML=`<div class="weather-main"><div class="weather-location"><b>${esc(w.location||'Previsão')}</b><span>HOJE · TEMPO REAL</span></div><div class="weather-temp">${c.temperature!=null?Math.round(c.temperature)+'°':'—'}</div><div class="weather-icon">${iconSvg(weatherGlyph(code))}</div><div class="weather-condition"><strong>${esc((c.condition||'Condição variável').replace(/^./,m=>m.toUpperCase()))}</strong><span>Máx. ${d.temperature_max!=null?Math.round(d.temperature_max)+'°':'—'} · mín. ${d.temperature_min!=null?Math.round(d.temperature_min)+'°':'—'}</span></div></div><div class="weather-metrics-v12"><div><small>Sensação</small><b>${c.apparent_temperature!=null?Math.round(c.apparent_temperature)+'°':'—'}</b></div><div><small>Umidade</small><b>${c.humidity!=null?Math.round(c.humidity)+(u.humidity||'%'):'—'}</b></div><div><small>Chuva</small><b>${d.precipitation_probability_max!=null?Math.round(d.precipitation_probability_max)+(u.probability||'%'):'—'}</b></div><div><small>Vento</small><b>${c.wind_speed!=null?Math.round(c.wind_speed)+' '+(u.wind_speed||'km/h'):'—'}</b></div></div>${hourly.length?`<div class="hourly-strip">${hourly.slice(0,8).map(h=>`<div class="hourly-item"><small>${esc(hourLabel(h.time))}</small><i>${weatherGlyph(h.weather_code)==='sun'?'●':weatherGlyph(h.weather_code)==='rain'?'⌇':weatherGlyph(h.weather_code)==='storm'?'ϟ':'◌'}</i><b>${h.temperature!=null?Math.round(h.temperature)+'°':'—'}</b></div>`).join('')}</div>`:''}<span class="weather-source">Open-Meteo · dados estruturados</span>`;this.materialize(el);await sleep(650);await this._say(w.summary||'Esta é a previsão para hoje.');await sleep(2500);await this.dismiss(el)
    }
    async news(items){
      const el=document.createElement('section');el.className='news-constellation';el.innerHTML=`<div class="news-title">JARVIS / LIVE NEWS<b>O que merece atenção</b></div>${items.slice(0,8).map((n,i)=>{const url=safeUrl(n.url);return `<a class="news-card" style="transition-delay:${i*70}ms" ${url?`href="${esc(url)}" target="_blank" rel="noopener noreferrer"`:''}><div class="news-meta"><span>${String(i+1).padStart(2,'0')} · ${esc(n.source||'fonte')}</span><i>AGORA</i></div><h3>${esc(n.title)}</h3><p>${esc(n.summary||'')}</p><span class="open-source">${url?'↗':'•'}</span></a>`}).join('')}`;this.materialize(el);const top=items.slice(0,3).map(x=>x.title).filter(Boolean);const voice=top.length?`Estas são as notícias mais relevantes desta manhã. ${top.join('. ')}.`:`Separei as principais notícias desta manhã.`;await sleep(750);await this._say(voice);await sleep(4200);await this.dismiss(el,700)
    }
    async tasks(items){
      const el=document.createElement('article');el.className='morning-gadget tasks-gadget';el.innerHTML=`<div class="tasks-head"><div><small>RESPONSABILIDADES / HOJE</small><h3>${items.length?'Pendências em foco':'Agenda de trabalho'}</h3></div><b>${items.length}</b></div>${items.length?`<div class="task-list">${items.slice(0,10).map(t=>{const url=safeUrl(t.url);return `<${url?'a':'div'} class="task-row ${Number(t.priority)>=80?'high':''}" ${url?`href="${esc(url)}" target="_blank" rel="noopener noreferrer"`:''}><span class="task-dot"></span><span class="task-copy"><b>${esc(t.title)}</b><small>${esc(t.status||t.detail||'pendente')}</small></span><span class="task-due">${esc(dueLabel(t.due_at))}</span></${url?'a':'div'}>`}).join('')}</div>`:'<div class="tasks-empty">Nenhuma tarefa pendente foi encontrada no organizador conectado.</div>'}`;this.materialize(el);await sleep(600);let voice=items.length?`Encontrei ${items.length} tarefa${items.length===1?'':'s'} pendente${items.length===1?'':'s'} no seu organizador.`:'Não encontrei tarefas pendentes no seu organizador.';if(items[0])voice+=` A primeira é: ${items[0].title}.`;await this._say(voice);await sleep(2300);await this.dismiss(el)
    }
    async closing(text){const stage=this._ensureLayer().querySelector('.morning-stage');stage.innerHTML='<div class="morning-closing"></div>';const el=stage.firstElementChild;el.textContent=text;requestAnimationFrame(()=>el.classList.add('enter'));await this._say(text);await sleep(900);this.finish();this.options.focusInput?.()}
    finish(){this.skipped=true;const l=this.layer,host=document.querySelector(this.options.hostSelector||'#presence, .stage');if(l){l.classList.remove('active');setTimeout(()=>{l.classList.add('hidden');l.querySelector('.morning-stage').innerHTML=''},500)}host?.classList.remove('morning-active','morning-showing-gadget','morning-awake');this.options.setState?.('IDLE');this.options.focusInput?.()}
  }
  window.JarvisMorning={MorningSequence,create:opts=>new MorningSequence(opts)};
})();

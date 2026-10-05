(() => {
  'use strict';
  const $ = (q) => document.querySelector(q);
  const canvas = $('#office-canvas'), stage = $('#stage'), labels = $('#room-labels');
  const ctx = canvas.getContext('2d');
  const rooms = [
    { id:'command', name:'Command', sub:'Nucleo de operacoes', x:0, z:-3.2, hue:'#d58a50' },
    { id:'research', name:'Research', sub:'Pesquisa e contexto', x:-8.5, z:1.2, hue:'#55a7d7' },
    { id:'engineering', name:'Engineering', sub:'Construcao e entrega', x:0, z:3.7, hue:'#6bc390' },
    { id:'creative', name:'Creative', sub:'Ideias e conteudo', x:8.5, z:1.2, hue:'#d782c7' },
    { id:'operations', name:'Operations', sub:'Fluxos e execucao', x:-4.9, z:8.4, hue:'#e0ad57' },
    { id:'review', name:'Review', sub:'Qualidade e aprovacao', x:4.9, z:8.4, hue:'#a48be1' }
  ];
  const names = ['Luna','Theo','Maya','Nico','Iris','Caio','Sofia','Noah','Eva','Leo'];
  let data = { agents:[], missions:[], attention:[] }, dpr = 1, size = { w:1, h:1 };
  let view = { scale:1, ox:0, oy:0, labels:true, auto:true, selected:'command', dragging:false, px:0, py:0 };
  let clock = 0;

  function esc(v){ return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function resize(){ const r=stage.getBoundingClientRect(); dpr=Math.min(devicePixelRatio||1,2); size={w:r.width,h:r.height}; canvas.width=r.width*dpr; canvas.height=r.height*dpr; canvas.style.width=r.width+'px'; canvas.style.height=r.height+'px'; ctx.setTransform(dpr,0,0,dpr,0,0); }
  function p(x,z,y=0){ const s=Math.min(size.w/118,size.h/82)*view.scale; return { x:size.w*.5+view.ox+(x-z)*s, y:size.h*.44+view.oy+(x+z)*s*.51-y*s }; }
  function poly(points, fill, stroke, lw=1){ ctx.beginPath(); points.forEach((v,i)=>i?ctx.lineTo(v.x,v.y):ctx.moveTo(v.x,v.y)); ctx.closePath(); if(fill){ctx.fillStyle=fill;ctx.fill();} if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lw;ctx.stroke();} }
  function shade(hex, n){ const c=hex.replace('#',''); const v=(i)=>Math.max(0,Math.min(255,parseInt(c.slice(i,i+2),16)+n)).toString(16).padStart(2,'0'); return '#'+v(0)+v(2)+v(4); }
  function tile(x,z,w,h,color='#b78258'){ poly([p(x-w/2,z-h/2),p(x+w/2,z-h/2),p(x+w/2,z+h/2),p(x-w/2,z+h/2)],color,'rgba(61,35,25,.22)'); }
  function block(x,z,w,h,depth,color,top=0){ const a=p(x-w/2,z-depth/2,top),b=p(x+w/2,z-depth/2,top),c=p(x+w/2,z+depth/2,top),d=p(x-w/2,z+depth/2,top); const A=p(x-w/2,z-depth/2,top-h),B=p(x+w/2,z-depth/2,top-h),C=p(x+w/2,z+depth/2,top-h),D=p(x-w/2,z+depth/2,top-h); poly([a,b,c,d],color,'rgba(53,28,19,.2)'); poly([d,c,C,D],shade(color,-45)); poly([b,c,C,B],shade(color,-25)); }
  function text(text,x,y,color='#fff',font='10px system-ui',align='center'){ ctx.fillStyle=color;ctx.font=font;ctx.textAlign=align;ctx.fillText(text,x,y); }
  function rr(x,y,w,h,r,fill,stroke){ ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.stroke()} }

  function background(){
    const g=ctx.createLinearGradient(0,0,0,size.h);g.addColorStop(0,'#172535');g.addColorStop(.55,'#382d35');g.addColorStop(1,'#171a25');ctx.fillStyle=g;ctx.fillRect(0,0,size.w,size.h);
    const glow=ctx.createRadialGradient(size.w*.5,size.h*.5,20,size.w*.5,size.h*.5,Math.max(size.w,size.h)*.58);glow.addColorStop(0,'rgba(255,191,113,.20)');glow.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,size.w,size.h);
  }
  function roomFloor(room){
    const {x,z,hue}=room; tile(x,z,17,12,shade(hue,-70));
    for(let ix=-7;ix<=7;ix+=2) for(let iz=-4;iz<=4;iz+=2) tile(x+ix,z+iz,1.9,1.9,(ix+iz)%4?'#c99a6f':'#d6aa7b');
    const q=p(x,z+.6); ctx.save();ctx.globalAlpha=.3;ctx.beginPath();ctx.ellipse(q.x,q.y,78*view.scale,24*view.scale,0,0,Math.PI*2);ctx.fillStyle=hue;ctx.fill();ctx.restore();
  }
  function wall(x,z,w,side){ block(x,z,w,4,.35,side?'#6c4638':'#825745',3.8); }
  function plant(x,z){ block(x,z,.9,1.4,.9,'#9b623c',1.3); const a=p(x,z,2.0);ctx.fillStyle='#466943';ctx.beginPath();ctx.arc(a.x-5,a.y,7,0,7);ctx.arc(a.x+5,a.y-4,7,0,7);ctx.arc(a.x,a.y-8,7,0,7);ctx.fill(); }
  function shelf(x,z){ block(x,z,1.1,4.5,3.4,'#7f4f32',1.8);[-1,0,1].forEach((v,i)=>{const q=p(x,z+v,2.8);ctx.fillStyle=['#d7684d','#e2b85e','#6ba08f'][i];ctx.fillRect(q.x-4,q.y-3,8,5)}); }
  function desk(x,z,color){ block(x,z,4.3,.65,2.45,shade(color,-25),1.35); const m=p(x,z-.12,2.05);rr(m.x-11,m.y-10,22,15,2,'#2b3743','#d5c7ae');ctx.fillStyle='#79b6d0';ctx.fillRect(m.x-8,m.y-7,16,9); const k=p(x,z+.68,1.55);ctx.fillStyle='#e8d9bd';ctx.fillRect(k.x-8,k.y-4,16,5); }
  function chair(x,z,color){ block(x,z,1.5,.8,1.5,shade(color,-22),.8);const q=p(x,z,.75);ctx.fillStyle=color;ctx.fillRect(q.x-6,q.y-9,12,11); }
  function person(x,z,agent,idx){
    const bob=Math.sin(clock*2.2+idx)*1.5, q=p(x,z,2.12+bob); const work=(agent.status||'').toLowerCase().includes('work')||idx%3===0;
    ctx.save();ctx.translate(q.x,q.y);ctx.fillStyle='rgba(0,0,0,.20)';ctx.beginPath();ctx.ellipse(0,13,9,3,0,0,7);ctx.fill();ctx.fillStyle=['#5d8bc0','#bc7556','#6ea680','#a47bc0','#d3a348'][idx%5];ctx.beginPath();ctx.roundRect(-6,0,12,14,4);ctx.fill();ctx.fillStyle=['#f6c7a6','#8b5b43','#e6af81'][idx%3];ctx.beginPath();ctx.arc(0,-5,6,0,7);ctx.fill();ctx.fillStyle='#332a2c';ctx.beginPath();ctx.arc(0,-8,6,Math.PI,0);ctx.fill(); if(work){ctx.strokeStyle='#e8c98c';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(-4,5);ctx.lineTo(-11,9+Math.sin(clock*8+idx)*2);ctx.moveTo(4,5);ctx.lineTo(11,9+Math.sin(clock*8+idx)*2);ctx.stroke();}ctx.restore();
  }
  function workstation(room, index){ const row=index>1?1:0, col=index%2; const x=room.x+(col?3.1:-3.1), z=room.z+(row?2.2:-1.3); desk(x,z,room.hue);chair(x,z+1.8,'#5c5869'); const agent=data.agents.filter(a=>(a.department||a.team||'').toLowerCase().includes(room.id))[index] || {name:names[(rooms.indexOf(room)*2+index)%names.length],status:index?'idle':'working'}; person(x,z+1.15,agent,index+rooms.indexOf(room)*3); }
  function commandCore(){ const r=rooms[0]; const q=p(r.x,r.z,1.1);ctx.save();ctx.translate(q.x,q.y);ctx.fillStyle='#553b50';ctx.beginPath();ctx.ellipse(0,0,49,18,0,0,7);ctx.fill();ctx.strokeStyle='#f3bd70';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(0,-2,37,12,0,0,7);ctx.stroke();ctx.fillStyle='#d5a75b';ctx.beginPath();ctx.arc(0,-5,8,0,7);ctx.fill();ctx.fillStyle='#fff0b1';ctx.beginPath();ctx.arc(0,-5,3,0,7);ctx.fill();ctx.restore(); }
  function bubble(room){ if(!view.labels)return; const q=p(room.x,room.z-5.5,5.4);const el=document.getElementById('room-'+room.id);if(el){el.style.left=q.x+'px';el.style.top=q.y+'px';el.classList.toggle('active',view.selected===room.id);} }
  function draw(){
    ctx.clearRect(0,0,size.w,size.h);background();
    rooms.forEach(roomFloor); wall(-10,-9,36,0);wall(10,12,36,1); shelf(-16,-7);shelf(15,8);plant(-14,9);plant(14,-6);
    rooms.slice().sort((a,b)=>a.x+a.z-b.x-b.z).forEach(r=>{ if(r.id==='command') commandCore(); else {workstation(r,0);workstation(r,1);} bubble(r); });
    const sel=rooms.find(r=>r.id===view.selected);if(sel){const q=p(sel.x,sel.z,0);ctx.save();ctx.strokeStyle=sel.hue;ctx.lineWidth=2;ctx.setLineDash([5,5]);ctx.beginPath();ctx.ellipse(q.x,q.y,88*view.scale,29*view.scale,0,0,7);ctx.stroke();ctx.restore();}
  }
  function createLabels(){ labels.innerHTML=rooms.map(r=>`<div id="room-${r.id}" class="room-label"><b style="color:${r.hue}">${r.name}</b><span>${r.sub}</span></div>`).join(''); }
  function select(id){ const r=rooms.find(x=>x.id===id)||rooms[0];view.selected=r.id;$('#selected-title').textContent=r.name;$('#selected-subtitle').textContent=r.sub;$('#selected-status').textContent='ONLINE';$('#selected-detail').textContent=`${r.name} está ativo. Clique em outro setor para acompanhar a equipe e suas atividades.`;document.querySelectorAll('.dept-btn').forEach(b=>b.classList.toggle('active',b.dataset.room===r.id)); }
  function render(){
    const agents=data.agents||[], missions=data.missions||[], attention=data.attention||[];
    $('#summary').innerHTML=[[agents.length,'agentes'],[missions.length,'missoes'],[agents.filter(a=>(a.status||'').toLowerCase().includes('work')).length,'trabalhando'],[attention.length,'atencao']].map(x=>`<div class="metric"><strong>${x[0]}</strong><span>${x[1]}</span></div>`).join('');
    $('#mission-total').textContent=missions.length; $('#missions').innerHTML=missions.slice(0,5).map(m=>`<div class="mission-item"><strong>${esc(m.title||m.objective||'Missao')}</strong><small>${esc(m.status||'em andamento')}</small><div class="progress-bar"><i style="width:${Number(m.progress||45)}%"></i></div></div>`).join('')||'<small class="muted-count">Nenhuma missao ativa.</small>';
    $('#attention-count').textContent=attention.length; $('#attention').innerHTML=attention.slice(0,4).map(a=>`<div class="attention-item"><strong>${esc(a.title||'Ponto de atencao')}</strong><small>${esc(a.risk||a.kind||'revisar')}</small>${a.kind==='approval'?`<button data-approve="${esc(a.id)}">Aprovar</button>`:''}</div>`).join('')||'<small class="muted-count">Tudo tranquilo.</small>';
    $('#department-nav').innerHTML=rooms.map(r=>`<button class="dept-btn" data-room="${r.id}"><b>${r.name}</b><span>${r.sub}</span></button>`).join('');document.querySelectorAll('[data-room]').forEach(b=>b.onclick=()=>select(b.dataset.room));document.querySelectorAll('[data-approve]').forEach(b=>b.onclick=()=>approve(b.dataset.approve));select(view.selected);
  }
  async function approve(id){ try{ await fetch('/api/attention/'+encodeURIComponent(id)+'/approve',{method:'POST'}); load(); }catch(_){} }
  async function load(){ try{ const res=await fetch('/api/hq',{cache:'no-store'}); if(!res.ok)throw 0;data=await res.json(); $('#connection').textContent='LIVE';$('#version').textContent='SYNCED';render(); }catch(_){$('#connection').textContent='OFFLINE';render();} }
  function reset(){view.scale=1;view.ox=0;view.oy=0;select('command');}
  function hit(x,y){ let best=null,dist=1e9;rooms.forEach(r=>{const q=p(r.x,r.z);const k=Math.hypot(q.x-x,(q.y-y)*2);if(k<dist){dist=k;best=r;}});if(dist<120*view.scale)return best; }
  function bind(){
    canvas.addEventListener('pointerdown',e=>{view.dragging=true;view.px=e.clientX;view.py=e.clientY;canvas.classList.add('dragging');canvas.setPointerCapture(e.pointerId)});
    canvas.addEventListener('pointermove',e=>{if(!view.dragging)return;view.ox+=e.clientX-view.px;view.oy+=e.clientY-view.py;view.px=e.clientX;view.py=e.clientY;view.auto=false;});
    canvas.addEventListener('pointerup',e=>{const moved=Math.hypot(e.clientX-view.px,e.clientY-view.py);view.dragging=false;canvas.classList.remove('dragging');if(moved<6){const r=hit(e.offsetX,e.offsetY);if(r)select(r.id);}});
    canvas.addEventListener('wheel',e=>{e.preventDefault();view.scale=Math.max(.68,Math.min(1.7,view.scale*(e.deltaY>0?.92:1.08)));},{passive:false});
    $('#zoom-in').onclick=()=>view.scale=Math.min(1.7,view.scale*1.12);$('#zoom-out').onclick=()=>view.scale=Math.max(.68,view.scale*.88);$('#reset-view').onclick=reset;$('#focus-selected').onclick=()=>{view.ox=0;view.oy=0;};$('#toggle-labels').onclick=e=>{view.labels=!view.labels;labels.style.display=view.labels?'block':'none';e.currentTarget.classList.toggle('active',view.labels)};
    $('#auto-rotate').onclick=e=>{view.auto=!view.auto;e.currentTarget.classList.toggle('active',view.auto)};$('#preset-overview').onclick=reset;$('#preset-command').onclick=()=>select('command');$('#preset-floor').onclick=()=>{view.scale=.84;view.ox=0;view.oy=20;};
  }
  function animate(t){ clock=t/1000;if(view.auto&&!view.dragging)view.oy=Math.sin(clock*.45)*4;draw();requestAnimationFrame(animate); }
  try{resize();createLabels();bind();select('command');load();setInterval(load,3000);addEventListener('resize',resize);requestAnimationFrame(animate);}catch(err){$('#fallback').classList.remove('hidden');console.error(err);}
})();

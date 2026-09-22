let bridge=null,snapshot=null,busy=false,lastUserPrompt='',pendingAttachments=[];
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

function safeUrl(raw){
  try{
    const u=new URL(String(raw));
    return ['http:','https:'].includes(u.protocol)?u.href:'#';
  }catch{return '#'}
}
function mdInline(s){
  let x=esc(s);
  x=x.replace(/`([^`]+)`/g,'<code>$1</code>');
  x=x.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  x=x.replace(/__([^_]+)__/g,'<strong>$1</strong>');
  x=x.replace(/(^|[\s(])\*([^*\n]+)\*/g,'$1<em>$2</em>');
  x=x.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,(m,label,url)=>`<a href="${safeUrl(url)}" target="_blank">${label}</a>`);
  x=x.replace(/(^|[\s>])(https?:\/\/[^\s<]+)/g,(m,prefix,url)=>`${prefix}<a href="${safeUrl(url)}" target="_blank">${esc(url)}</a>`);
  return x;
}
function renderMarkdown(text){
  const raw=String(text??'').replace(/\r\n/g,'\n');
  const codeBlocks=[];
  let s=raw.replace(/```([a-zA-Z0-9_-]*)\n?([\s\S]*?)```/g,(m,lang,code)=>{
    const token=`@@CODEBLOCK_${codeBlocks.length}@@`;
    codeBlocks.push(`<pre><code>${esc(code.trim())}</code></pre>`);
    return token;
  });
  const lines=s.split('\n');
  const out=[];let list=null;
  const closeList=()=>{if(list){out.push(`</${list}>`);list=null}};
  for(const line of lines){
    const trimmed=line.trim();
    const codeToken=trimmed.match(/^@@CODEBLOCK_(\d+)@@$/);
    if(codeToken){closeList();out.push(codeBlocks[Number(codeToken[1])]||'');continue}
    if(!trimmed){closeList();out.push('<div class="md-gap"></div>');continue}
    let m=trimmed.match(/^(#{1,3})\s+(.+)$/);
    if(m){closeList();out.push(`<h${m[1].length}>${mdInline(m[2])}</h${m[1].length}>`);continue}
    m=trimmed.match(/^[-*]\s+(.+)$/);
    if(m){if(list!=='ul'){closeList();list='ul';out.push('<ul>')}out.push(`<li>${mdInline(m[1])}</li>`);continue}
    m=trimmed.match(/^\d+\.\s+(.+)$/);
    if(m){if(list!=='ol'){closeList();list='ol';out.push('<ol>')}out.push(`<li>${mdInline(m[1])}</li>`);continue}
    if(trimmed.startsWith('> ')){closeList();out.push(`<blockquote>${mdInline(trimmed.slice(2))}</blockquote>`);continue}
    if(/^---+$/.test(trimmed)){closeList();out.push('<hr>');continue}
    closeList();out.push(`<p>${mdInline(line)}</p>`);
  }
  closeList();
  return out.join('').replace(/<div class="md-gap"><\/div>(?=<div class="md-gap"><\/div>)/g,'<div class="md-gap"></div>');
}
function copyText(text){
  const value=String(text??'');
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(value).catch(()=>fallbackCopy(value));}
  else fallbackCopy(value);
}
function fallbackCopy(value){
  const ta=document.createElement('textarea');ta.value=value;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();
}
function flashButton(btn,label='Copiado'){
  const old=btn.textContent;btn.textContent=label;setTimeout(()=>btn.textContent=old,900);
}

function setBusy(value,detail=''){
  busy=!!value;document.body.classList.toggle('busy',busy);
  $('sendBtn').disabled=busy;$('promptInput').disabled=busy;$('cancelBtn').classList.toggle('visible',busy);
  if(detail)$('statusText').textContent=detail;
  if(!busy)$('statusText').textContent='pronto';
}
function hideWelcome(){const w=$('welcome');if(w)w.style.display='none'}
function addMessage(role,text,ok=true,time=null,meta={}){
  hideWelcome();
  const el=document.createElement('div');el.className=`message ${role}`;
  const main=document.createElement('div');main.className='message-main';
  const raw=String(text??'');
  const sources=Array.isArray(meta?.sources)?meta.sources:[];
  const sourceHtml=sources.length?`<div class="message-sources">${sources.slice(0,5).map((s,i)=>{
    const url=s.url||s.link||'';const label=s.title||s.name||(()=>{try{return new URL(url).hostname}catch{return `Fonte ${i+1}`}})();
    return url?`<a href="${safeUrl(url)}" target="_blank">${esc(label)}</a>`:`<span>${esc(label)}</span>`;
  }).join('')}</div>`:'';
  main.innerHTML=`
    <div class="message-head">${role==='user'?'Você':'Jarvis'}${meta.model?`<span class="message-model">${esc(meta.model)}</span>`:''}${meta.grounded?'<span class="message-model">• grounded</span>':''}</div>
    <div class="message-body ${ok?'':'error'}">${role==='assistant'?renderMarkdown(raw):`<p>${esc(raw).replace(/\n/g,'<br>')}</p>`}</div>
    ${sourceHtml}
    <div class="message-meta">${esc(time||new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}))}</div>
    <div class="message-actions"></div>`;
  const avatar=document.createElement('div');avatar.className='avatar';avatar.textContent=role==='user'?'V':'✦';
  el.appendChild(avatar);el.appendChild(main);
  const actions=main.querySelector('.message-actions');

  const copy=document.createElement('button');copy.className='message-action';copy.textContent='Copiar';copy.onclick=()=>{copyText(raw);flashButton(copy)};
  actions.appendChild(copy);

  if(role==='assistant'){
    const regen=document.createElement('button');regen.className='message-action';regen.textContent='Regenerar';regen.onclick=()=>{if(lastUserPrompt&&!busy)sendPrompt(lastUserPrompt)};
    actions.appendChild(regen);
  }else{
    lastUserPrompt=raw;
    const edit=document.createElement('button');edit.className='message-action';edit.textContent='Editar';edit.onclick=()=>{
      $('promptInput').value=raw;resizeInput();$('promptInput').focus();
    };
    actions.appendChild(edit);
  }

  $('conversation').appendChild(el);
  $('chatScroll').scrollTop=$('chatScroll').scrollHeight;
}
function showThinking(text='Processando'){
  removeThinking();const el=document.createElement('div');el.id='thinking';el.className='thinking';el.textContent=text;
  $('conversation').appendChild(el);$('chatScroll').scrollTop=$('chatScroll').scrollHeight;
}
function removeThinking(){const x=$('thinking');if(x)x.remove()}

function sendPrompt(value){
  const prompt=String(value||'').trim();if(!prompt||!bridge||busy)return;
  lastUserPrompt=prompt;
  addMessage('user',prompt);$('promptInput').value='';resizeInput();
  setBusy(true,'decidindo');showThinking('Jarvis está decidindo se deve conversar, lembrar, pesquisar ou agir…');
  bridge.sendCommand(prompt);
}
function resizeInput(){const i=$('promptInput');i.style.height='auto';i.style.height=Math.min(150,i.scrollHeight)+'px'}
function fetchSnapshot(){if(bridge)bridge.getSnapshot(raw=>{try{renderSnapshot(JSON.parse(raw))}catch(e){console.error(e)}})}

function renderSnapshot(data){
  snapshot=data||{};
  $('footerModel').textContent=snapshot.model||'adaptive local';
  const hw=snapshot.hardware||{};$('hardwareLabel').textContent=hw.tier?`${hw.tier} • ${hw.ram_gb||'?'} GB • ${hw.cpu_threads||'?'} threads`:'local • CPU';
  renderSessions();renderContext();renderSources();renderActivity();renderProjects();renderAttachments();renderControlCenter();
}
function renderSessions(){
  const info=snapshot?.cognitive?.sessions||{};const items=info.items||[];const current=info.current;
  const q=($('conversationSearch').value||'').trim().toLowerCase();
  const filtered=q?items.filter(s=>String(s.title||'').toLowerCase().includes(q)):items;
  $('conversationList').innerHTML=filtered.map(s=>`<button class="conversation-item ${Number(s.id)===Number(current)?'active':''}" data-session="${s.id}" title="${esc(s.title)}">${esc(s.title||'Nova conversa')}</button>`).join('')||'<div class="conversation-item">Nenhuma conversa</div>';
  document.querySelectorAll('[data-session]').forEach(btn=>btn.onclick=()=>openConversation(Number(btn.dataset.session)));
}
function openConversation(id){
  if(!bridge)return;
  bridge.openConversation(id,raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!d.ok)return;
    $('conversation').innerHTML='';
    (d.messages||[]).forEach(m=>{
      let metadata=m.metadata||{};
      if(typeof metadata==='string'){try{metadata=JSON.parse(metadata)}catch{metadata={}}}
      addMessage(m.role==='assistant'?'assistant':'user',m.content,!metadata?.error,(m.created_at||'').slice(11,16),metadata);
    });
    if(!(d.messages||[]).length)showWelcome();
    fetchSnapshot();
  });
}
function showWelcome(){
  $('conversation').innerHTML=`<div class="welcome" id="welcome"><div class="welcome-orb">✦</div><h1>O que você precisa?</h1><p>Converse normalmente. O Jarvis lembra contexto, consulta dados, pesquisa e usa ferramentas quando isso realmente ajuda.</p><div class="welcome-hints"><button data-prompt="Quero começar um novo projeto. Me ajude a organizar o contexto.">Novo projeto</button><button data-prompt="Pesquise fontes oficiais sobre um assunto que eu indicar.">Pesquisar</button><button data-prompt="O que você lembra das nossas conversas recentes?">Lembrar</button></div></div>`;
  bindPromptButtons();
}

function renderContext(){
  const active=snapshot?.active_task;const conv=snapshot?.cognitive?.conversations||{};const learning=snapshot?.cognitive?.learning||{};const kb=snapshot?.knowledge||{};
  const reflections=snapshot?.cognitive?.reflections||{};const proj=snapshot?.projects?.current;
  $('taskCard').innerHTML=active?`<strong>${esc(active.goal||'Tarefa ativa')}</strong><span>${esc(active.status||'running')}</span>`:`<strong>Nenhuma tarefa ativa</strong><span>Jarvis está disponível para conversar ou agir.</span>`;
  $('projectContext').innerHTML=proj?`<strong>${esc(proj.name)}</strong><span>${esc(proj.description||'Projeto ativo nesta conversa.')}</span>`:`<strong>Sem projeto ativo</strong><span>Você pode agrupar conversas e documentos em um projeto quando quiser.</span>`;
  $('cognitiveStats').innerHTML=`
    <div class="mini"><small>CONVERSAS</small><b>${conv.sessions||0}</b></div>
    <div class="mini"><small>KNOWLEDGE</small><b>${kb.documents||0}</b></div>
    <div class="mini"><small>LIÇÕES</small><b>${learning.active_lessons||0}</b></div>
    <div class="mini"><small>REFLEXÕES</small><b>${reflections.active||0}</b></div>`;
  const lessons=snapshot?.cognitive?.lessons||[];
  $('lessonList').innerHTML=lessons.slice(0,7).map(x=>`<div class="simple-item"><b>${esc(x.kind||'lesson')}</b><span>${esc(x.lesson||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhuma preferência/correção aprendida ainda.</span></div>';
  const refl=snapshot?.cognitive?.reflection_items||[];
  $('reflectionList').innerHTML=refl.slice(0,7).map(x=>`<div class="simple-item"><b>${esc(x.kind||'reflection')}</b><span>${esc(x.insight||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhuma reflexão relevante ainda.</span></div>';
  const at=snapshot?.attachments?.items||[];
  $('attachmentList').innerHTML=at.slice(0,8).map(x=>`<div class="simple-item"><b>${esc(x.name)}</b><span>${esc(x.status||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhum anexo nesta conversa/projeto.</span></div>';
}
function renderSources(){
  const pd=snapshot?.public_data||{};const stats=pd.stats||{};const sources=pd.sources||[];
  $('sourceStats').innerHTML=`<span class="pill">${stats.sources||0} fontes</span><span class="pill">${stats.official||0} oficiais</span><span class="pill">${snapshot?.institutional_services?.stats?.services||0} serviços do sindicato</span>`;
  $('sourceList').innerHTML=sources.slice(0,14).map(x=>`<div class="simple-item"><b>${esc(x.name)}</b><span>${esc((x.topics||[]).slice(0,4).join(' • '))}</span></div>`).join('');
}
function renderActivity(){
  const tasks=snapshot?.recent_tasks||[];const alerts=snapshot?.notifications?.unread||[];const improvements=snapshot?.improvements?.items||[];
  $('activityList').innerHTML=tasks.slice(0,8).map(x=>`<div class="simple-item"><b>#${x.id} • ${esc((x.status||'').toUpperCase())}</b><span>${esc(x.goal||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhuma atividade recente.</span></div>';
  $('alertList').innerHTML=alerts.slice(0,8).map(x=>`<div class="simple-item"><b>${esc(x.title||'Alerta')}</b><span>${esc(x.message||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhum alerta pendente.</span></div>';
  $('improvementList').innerHTML=improvements.slice(0,8).map(x=>`<div class="simple-item"><b>${esc(x.title||x.kind)}</b><span>${esc(x.description||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhuma melhoria sugerida pendente.</span></div>';
}
function renderProjects(){
  const data=snapshot?.projects||{};const current=data.current;const items=data.items||[];
  const label=current?.name||'Sem projeto';$('projectLabel').textContent=label;$('projectChip').textContent=label;
  $('projectList').innerHTML=`
    <div class="project-row ${!current?'active':''}"><div><b>Sem projeto</b><span>Conversa geral</span></div><button data-project-id="0">Usar</button></div>
    ${items.map(x=>`<div class="project-row ${current&&Number(current.id)===Number(x.id)?'active':''}"><div><b>${esc(x.name)}</b><span>${esc(x.description||'')}</span></div><button data-project-id="${x.id}">${current&&Number(current.id)===Number(x.id)?'Ativo':'Usar'}</button></div>`).join('')}`;
  document.querySelectorAll('[data-project-id]').forEach(btn=>btn.onclick=()=>setProject(Number(btn.dataset.projectId)));
}
function setProject(id){
  if(!bridge)return;bridge.setCurrentProject(id,raw=>{let d={};try{d=JSON.parse(raw)}catch{};if(d.ok){fetchSnapshot();$('projectOverlay').classList.add('hidden')}})
}
function createProject(){
  const name=$('projectName').value.trim(),desc=$('projectDescription').value.trim();if(!name||!bridge)return;
  bridge.createProject(name,desc,raw=>{let d={};try{d=JSON.parse(raw)}catch{};if(d.ok){$('projectName').value='';$('projectDescription').value='';fetchSnapshot()}else alert(d.error||'Não foi possível criar o projeto.')})
}
function renderAttachments(){
  const items=snapshot?.attachments?.items||[];
  $('attachmentStrip').innerHTML=items.slice(0,5).map(x=>`<div class="attachment-chip ${x.status==='failed'?'failed':''}" title="${esc(x.path||'')}">${esc(x.name||'anexo')}</div>`).join('');
}
function pickAttachments(){
  if(!bridge||busy)return;
  bridge.pickAttachments(raw=>{let d={};try{d=JSON.parse(raw)}catch{};if(!d.ok&&d.error)alert(d.error);fetchSnapshot()})
}

function renderControlCenter(){
  if(!snapshot)return;
  const a=snapshot.actions||{},w=snapshot.workflows||{},c=snapshot.capabilities||{},p=snapshot.public_data?.stats||{},k=snapshot.knowledge||{},auto=snapshot.automations?.stats||{},con=snapshot.connectors?.stats||{},r=snapshot.cognitive?.reflections||{},proj=snapshot.projects?.stats||{};
  const tiles=[
    ['CONVERSATION',snapshot.cognitive?.conversations?.messages||0,'mensagens persistentes'],
    ['PROJECTS',proj.projects||0,'contextos ativos'],
    ['KNOWLEDGE',k.documents||0,'documentos indexados'],
    ['PUBLIC DATA',p.sources||0,'fontes catalogadas'],
    ['ACTIONS',a.actions||0,'ferramentas internas'],
    ['WORKFLOWS',w.workflows||0,'fluxos compostos'],
    ['AUTONOMY',auto.jobs||0,'automações'],
    ['REFLECTION',r.active||0,'aprendizados em análise'],
  ];
  $('controlGrid').innerHTML=tiles.map(x=>`<div class="control-tile"><small>${x[0]}</small><b>${x[1]}</b><span>${x[2]}</span></div>`).join('');
}
function searchSources(){
  const q=$('sourceQuery').value.trim();if(!q||!bridge)return;
  $('sourceSearchResults').innerHTML='<div class="advanced-note">Pesquisando catálogo…</div>';
  bridge.searchPublicSources(q,raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    const items=d.items||[];
    $('sourceSearchResults').innerHTML=items.map(x=>`<div class="source-card"><b>${esc(x.name)}</b><span>${esc(x.access||'')} • ${esc(x.authority||'')}</span><span>${esc((x.topics||[]).slice(0,5).join(' • '))}</span></div>`).join('')||'<div class="advanced-note">Nenhuma fonte correspondente.</div>';
  });
}
function bindPromptButtons(){document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>sendPrompt(b.dataset.prompt))}
function setInspectorTab(name){
  document.querySelectorAll('.inspector-tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id===`panel-${name}`));
}
function toggleInspector(force=null){
  const inspector=$('inspector'),app=$('app');
  const show=force===null?inspector.classList.contains('hidden'):!!force;
  inspector.classList.toggle('hidden',!show);app.classList.toggle('no-inspector',!show);
}
function openOverlay(id){$(id)?.classList.remove('hidden')}
function closeOverlay(id){$(id)?.classList.add('hidden')}

function initBridge(){
  if(typeof QWebChannel==='undefined'||typeof qt==='undefined'){setTimeout(initBridge,250);return}
  new QWebChannel(qt.webChannelTransport,channel=>{
    bridge=channel.objects.jarvisBridge;
    bridge.statusChanged.connect((state,detail)=>{
      setBusy(true,detail||state);
      const d=String(detail||state||'').toLowerCase();
      let msg='Jarvis está trabalhando…';
      if(d.includes('pesquis'))msg='Pesquisando fontes…';
      else if(d.includes('execut'))msg='Executando…';
      else if(d.includes('consult'))msg='Consultando contexto…';
      else if(d.includes('convers'))msg='Preparando resposta…';
      showThinking(msg);
    });
    bridge.commandFinished.connect((prompt,result,ok,metaRaw)=>{
      let meta={};try{meta=JSON.parse(metaRaw||'{}')}catch{}
      removeThinking();addMessage('assistant',result,ok,null,meta);setBusy(false);fetchSnapshot();
    });
    bridge.snapshotChanged.connect(raw=>{try{renderSnapshot(JSON.parse(raw))}catch(e){console.error(e)}});
    fetchSnapshot();
  });
}

$('sendBtn').onclick=()=>sendPrompt($('promptInput').value);
$('promptInput').addEventListener('input',resizeInput);
$('promptInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendPrompt(e.target.value)}});
$('cancelBtn').onclick=()=>bridge&&bridge.cancelTask();
$('attachBtn').onclick=pickAttachments;
$('newChatBtn').onclick=()=>{if(bridge)bridge.newChat();showWelcome();fetchSnapshot()};
$('conversationSearch').addEventListener('input',renderSessions);
$('projectBtn').onclick=()=>openOverlay('projectOverlay');$('projectChip').onclick=()=>openOverlay('projectOverlay');
$('createProjectBtn').onclick=createProject;
$('controlBtn').onclick=()=>{openOverlay('controlOverlay');renderControlCenter()};
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>closeOverlay(b.dataset.close));
document.querySelectorAll('.overlay').forEach(x=>x.onclick=e=>{if(e.target===x)x.classList.add('hidden')});
$('sourceSearchBtn').onclick=searchSources;$('sourceQuery').addEventListener('keydown',e=>{if(e.key==='Enter')searchSources()});
$('contextToggle').onclick=()=>toggleInspector();$('closeInspector').onclick=()=>toggleInspector(false);
$('compactBtn').onclick=()=>{document.body.classList.toggle('compact');if(bridge)bridge.setMode(document.body.classList.contains('compact')?'compact':'habitat')};
document.querySelectorAll('[data-window]').forEach(b=>b.onclick=()=>bridge&&bridge.windowAction(b.dataset.window));
document.querySelectorAll('.inspector-tab').forEach(b=>b.onclick=()=>setInspectorTab(b.dataset.tab));
document.addEventListener('keydown',e=>{
  if(e.ctrlKey&&e.key.toLowerCase()==='k'){e.preventDefault();openOverlay('controlOverlay');renderControlCenter()}
  if(e.ctrlKey&&e.key.toLowerCase()==='n'){e.preventDefault();$('newChatBtn').click()}
  if(e.key==='Escape'){document.querySelectorAll('.overlay').forEach(x=>x.classList.add('hidden'))}
});
bindPromptButtons();toggleInspector(false);initBridge();

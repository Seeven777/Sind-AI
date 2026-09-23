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
function cleanAssistantText(value){
  let s=String(value??'');
  if(!s)return '';
  const lower=s.toLowerCase();
  const close='</think>';
  const idx=lower.lastIndexOf(close);
  if(idx>=0)s=s.slice(idx+close.length);
  s=s.replace(/<think\b[^>]*>[\s\S]*?<\/think>/gi,'');
  s=s.replace(/<\/?think\b[^>]*>/gi,'');
  if(/^\s*<think\b/i.test(String(value??''))&&!lower.includes(close)){
    return 'O modelo ainda estava processando internamente e não produziu uma resposta final válida.';
  }
  return s.trim();
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
function chatEl(){return $('chatScroll')}
function distanceFromBottom(){
  const c=chatEl();if(!c)return 0;
  return Math.max(0,c.scrollHeight-c.scrollTop-c.clientHeight);
}
function nearBottom(threshold=180){return distanceFromBottom()<=threshold}
function scrollChatToBottom(smooth=true){
  const c=chatEl();if(!c)return;
  c.scrollTo({top:c.scrollHeight,behavior:smooth?'smooth':'auto'});
}
function updateJumpBottom(){
  const btn=$('jumpBottomBtn');if(!btn)return;
  btn.classList.toggle('hidden',nearBottom(120));
}
function addMessage(role,text,ok=true,time=null,meta={}){
  const shouldFollow=role==='user'||nearBottom();
  hideWelcome();
  const el=document.createElement('div');el.className=`message ${role}`;
  const main=document.createElement('div');main.className='message-main';
  const raw=role==='assistant'?cleanAssistantText(text):String(text??'');
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
  if(shouldFollow)requestAnimationFrame(()=>scrollChatToBottom(false));
  else updateJumpBottom();
}
function showThinking(text='Processando'){
  const shouldFollow=nearBottom();
  removeThinking();const el=document.createElement('div');el.id='thinking';el.className='thinking';el.textContent=text;
  $('conversation').appendChild(el);
  if(shouldFollow)requestAnimationFrame(()=>scrollChatToBottom(false));
  else updateJumpBottom();
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
  renderSessions();renderContext();renderSources();renderActivity();renderProjects();renderAttachments();renderMobile();renderUpdates();renderControlCenter();
}
function renderSessions(){
  const info=snapshot?.cognitive?.sessions||{};const items=info.items||[];const current=info.current;
  const q=($('conversationSearch').value||'').trim().toLowerCase();
  const filtered=q?items.filter(s=>String(s.title||'').toLowerCase().includes(q)):items;
  $('conversationList').innerHTML=filtered.map(s=>`
    <div class="conversation-row ${Number(s.id)===Number(current)?'active':''}">
      <button class="conversation-item ${Number(s.id)===Number(current)?'active':''}" data-session="${s.id}" title="${esc(s.title)}">
        <span>${esc(s.title||'Nova conversa')}</span><small>${s.message_count||0}</small>
      </button>
      <button class="conversation-delete" data-delete-session="${s.id}" data-delete-title="${esc(s.title||'Nova conversa')}" title="Excluir conversa">×</button>
    </div>`).join('')||'<div class="conversation-item empty">Nenhuma conversa</div>';
  document.querySelectorAll('[data-session]').forEach(btn=>btn.onclick=()=>openConversation(Number(btn.dataset.session)));
  document.querySelectorAll('[data-delete-session]').forEach(btn=>btn.onclick=e=>{
    e.stopPropagation();
    deleteConversation(Number(btn.dataset.deleteSession),btn.dataset.deleteTitle||'esta conversa');
  });
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
    requestAnimationFrame(()=>scrollChatToBottom(false));
    fetchSnapshot();
  });
}
function deleteConversation(id,title){
  if(!bridge||busy)return;
  const ok=confirm(`Excluir permanentemente “${title}”?\\n\\nAs mensagens serão removidas do histórico. Anexos exclusivos desta conversa também serão removidos da Knowledge Base. Anexos ligados a um projeto serão preservados.`);
  if(!ok)return;
  bridge.deleteConversation(id,raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!d.ok){alert(d.error||'Não foi possível excluir a conversa.');return}
    if(d.deleted_was_current){
      $('conversation').innerHTML='';
      (d.messages||[]).forEach(m=>{
        let metadata=m.metadata||{};
        if(typeof metadata==='string'){try{metadata=JSON.parse(metadata)}catch{metadata={}}}
        addMessage(m.role==='assistant'?'assistant':'user',m.content,!metadata?.error,(m.created_at||'').slice(11,16),metadata);
      });
      if(!(d.messages||[]).length)showWelcome();
      requestAnimationFrame(()=>scrollChatToBottom(false));
    }
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
  const swarm=snapshot?.swarm?.stats||{};const apprenticeship=snapshot?.apprenticeship||{};
  $('taskCard').innerHTML=active?`<strong>${esc(active.goal||'Tarefa ativa')}</strong><span>${esc(active.status||'running')}</span>`:`<strong>Nenhuma tarefa ativa</strong><span>Jarvis está disponível para conversar ou agir.</span>`;
  $('projectContext').innerHTML=proj?`<strong>${esc(proj.name)}</strong><span>${esc(proj.description||'Projeto ativo nesta conversa.')}</span>`:`<strong>Sem projeto ativo</strong><span>Você pode agrupar conversas e documentos em um projeto quando quiser.</span>`;
  $('cognitiveStats').innerHTML=`
    <div class="mini"><small>CONVERSAS</small><b>${conv.sessions||0}</b></div>
    <div class="mini"><small>KNOWLEDGE</small><b>${kb.documents||0}</b></div>
    <div class="mini"><small>LIÇÕES</small><b>${learning.active_lessons||0}</b></div>
    <div class="mini"><small>REFLEXÕES</small><b>${reflections.active||0}</b></div>
    <div class="mini"><small>AGENTES</small><b>${swarm.agents||0}</b></div>
    <div class="mini"><small>ROTINAS</small><b>${apprenticeship.procedures||0}</b></div>`;
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
  const tasks=snapshot?.recent_tasks||[];const alerts=snapshot?.notifications?.unread||[];const improvements=snapshot?.improvements?.items||[];const jobs=snapshot?.long_horizon?.items||[];
  $('activityList').innerHTML=tasks.slice(0,8).map(x=>`<div class="simple-item"><b>#${x.id} • ${esc((x.status||'').toUpperCase())}</b><span>${esc(x.goal||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhuma atividade recente.</span></div>';
  $('longJobList').innerHTML=jobs.slice(0,8).map(x=>{
    const p=x.progress||{};
    const controls=x.status==='paused'?`<button data-long-job="${x.id}" data-long-action="resume">Retomar</button>`:
      x.status==='waiting_user'?`<button data-long-job="${x.id}" data-long-action="resume">Revisar/retomar</button>`:
      ['completed','cancelled','failed'].includes(x.status)?'':
      `<button data-long-job="${x.id}" data-long-action="pause">Pausar</button>`;
    const cancel=!['completed','cancelled'].includes(x.status)?`<button data-long-job="${x.id}" data-long-action="cancel">Cancelar</button>`:'';
    return `<div class="simple-item long-job-item"><b>#${x.id} • ${esc((x.status||'').toUpperCase())} • ${p.percent||0}%</b><span>${esc(x.goal||'')}</span><div class="long-job-progress"><i style="width:${Math.max(0,Math.min(100,p.percent||0))}%"></i></div><div class="long-job-actions">${controls}${cancel}</div></div>`;
  }).join('')||'<div class="simple-item"><span>Nenhum job persistente.</span></div>';
  document.querySelectorAll('[data-long-job]').forEach(btn=>btn.onclick=()=>longJobAction(Number(btn.dataset.longJob),btn.dataset.longAction));
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

function renderMobile(){
  const m=snapshot?.mobile||{};
  const running=!!m.running;
  const side=$('mobileSideStatus');if(side)side.textContent=running?'ativo • mesma rede':'desligado';
  const dot=$('mobileStateDot');if(dot)dot.classList.toggle('on',running);
  const label=$('mobileStateLabel');if(label)label.textContent=running?'Acesso mobile ativo':'Acesso mobile desligado';
  const hint=$('mobileStateHint');if(hint)hint.textContent=running?'Use o endereço abaixo no celular.':'Ative para usar na mesma rede Wi‑Fi.';
  const url=$('mobileUrl');if(url)url.textContent=running?(m.url||'—'):'—';
  const pin=$('mobilePin');if(pin)pin.textContent=running?(m.pin||'———'):'———';
  const alt=$('mobileAltUrls');if(alt)alt.innerHTML=running?(m.urls||[]).filter(x=>x!==m.url).map(x=>`<code>${esc(x)}</code>`).join(''):'';
  const toggle=$('mobileToggleBtn');if(toggle)toggle.textContent=running?'Desativar acesso mobile':'Ativar acesso mobile';
}
function toggleMobile(){
  if(!bridge)return;
  const btn=$('mobileToggleBtn');if(btn)btn.disabled=true;
  bridge.mobileToggle(raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!d.ok&&d.error)alert(d.error);
    if(btn)btn.disabled=false;
    fetchSnapshot();
  });
}
function resetMobilePin(){
  if(!bridge)return;
  bridge.mobileResetPin(raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!d.ok&&d.error)alert(d.error);
    fetchSnapshot();
  });
}



function diagnoseMobile(){
  if(!bridge)return;
  const box=$('mobileDiagnostic');const text=$('mobileDiagnosticText');
  if(box){box.classList.remove('hidden','ok','warn');box.classList.add('warn')}
  if(text)text.textContent='Verificando servidor, rede e Firewall do Windows…';
  bridge.mobileDiagnostics(raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!box||!text)return;
    box.classList.remove('ok','warn');box.classList.add(d.ok?'ok':'warn');
    const details=[];
    if(d.running)details.push('Servidor mobile: ativo');if(d.index_exists===false)details.push('Interface mobile: AUSENTE');else if(d.index_exists===true)details.push('Interface mobile: OK');
    if(d.loopback_ok)details.push('Teste local: OK');
    if(d.network_profile)details.push(`Perfil da rede: ${d.network_profile}`);
    details.push(`Firewall Jarvis: ${d.firewall_rule?'liberado':'não detectado'}`);
    const privateBtn=$('mobilePrivateBtn');
    if(privateBtn)privateBtn.classList.toggle('hidden',String(d.network_profile||'').toLowerCase()!=='public');
    if((d.urls||[]).length)details.push(`Endereços: ${(d.urls||[]).join(' • ')}`);
    if((d.issues||[]).length)details.push(`Problemas: ${(d.issues||[]).join(' ')}`);
    text.textContent=details.join('\\n');
  });
}
function makeMobileNetworkPrivate(){
  if(!bridge)return;
  bridge.mobileMakeNetworkPrivate(raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!d.ok)alert(d.error||'Não foi possível alterar o perfil da rede.');
    else setTimeout(diagnoseMobile,3000);
  });
}

function enableMobileFirewall(){
  if(!bridge)return;
  bridge.mobileEnableFirewall(raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!d.ok)alert(d.error||'Não foi possível abrir a configuração de firewall.');
    else setTimeout(diagnoseMobile,2500);
  });
}

function renderUpdates(){
  const u=snapshot?.updates||{};
  const available=!!u.available;
  const checking=!!u.checking;
  const side=$('updateSideStatus');
  if(side)side.textContent=checking?'verificando…':available?'nova versão disponível':u.error?'não foi possível verificar':'atualizado';
  const badge=$('updateBadge');if(badge)badge.classList.toggle('available',available);
  const current=$('updateCurrentVersion');if(current)current.textContent=u.current_version||'—';
  const channel=$('updateChannelLabel');if(channel)channel.textContent=u.channel||'main';
  const remote=$('updateRemoteVersion');if(remote)remote.textContent=u.remote_version||((u.remote_sha||'').slice(0,8))||'—';
  const date=$('updateRemoteDate');if(date)date.textContent=u.remote_date||u.last_checked_at||'ainda não consultado';
  const summary=$('updateSummary');
  if(summary){
    summary.textContent=checking?'Consultando o GitHub…':
      available?'Existe uma versão nova pronta para instalar.':
      u.error?'A verificação encontrou um problema.':'Este computador está atualizado.';
  }
  const msg=$('updateMessage');if(msg)msg.textContent=u.error||u.remote_message||'Nenhuma observação remota.';
  const install=$('updateInstallBtn');if(install){install.disabled=!available||checking;install.textContent=available?'Atualizar agora':'Atualizado'}
  document.querySelectorAll('input[name="updateChannel"]').forEach(r=>r.checked=r.value===(u.channel||'main'));
}
function checkUpdate(){
  if(!bridge)return;
  const btn=$('updateCheckBtn');if(btn)btn.disabled=true;
  bridge.checkUpdate(()=>{setTimeout(()=>{fetchSnapshot();if(btn)btn.disabled=false},1400)});
}
function installUpdate(){
  if(!bridge)return;
  const u=snapshot?.updates||{};
  if(!u.available)return;
  if(!confirm('O Jarvis será fechado, atualizado e reiniciado. O runtime atual será salvo como backup antes da troca. Continuar?'))return;
  const btn=$('updateInstallBtn');if(btn){btn.disabled=true;btn.textContent='Preparando…'}
  bridge.installUpdate(raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!d.ok){
      alert(d.error||'Não foi possível iniciar a atualização.');
      if(btn){btn.disabled=false;btn.textContent='Atualizar agora'}
    }
  });
}
function changeUpdateChannel(value){
  if(!bridge)return;
  bridge.setUpdateChannel(value,()=>setTimeout(fetchSnapshot,800));
}

function longJobAction(id,action){
  if(!bridge)return;
  bridge.longJobAction(id,action,raw=>{
    let d={};try{d=JSON.parse(raw)}catch{}
    if(!d.ok&&d.error)alert(d.error);
    fetchSnapshot();
  });
}

function renderControlCenter(){
  if(!snapshot)return;
  const a=snapshot.actions||{},w=snapshot.workflows||{},c=snapshot.capabilities||{},p=snapshot.public_data?.stats||{},k=snapshot.knowledge||{},auto=snapshot.automations?.stats||{},lh=snapshot.long_horizon?.stats||{},con=snapshot.connectors?.stats||{},r=snapshot.cognitive?.reflections||{},proj=snapshot.projects?.stats||{},acq=snapshot.acquisition?.stats||{};
  const tiles=[
    ['CONVERSATION',snapshot.cognitive?.conversations?.messages||0,'mensagens persistentes'],
    ['PROJECTS',proj.projects||0,'contextos ativos'],
    ['KNOWLEDGE',k.documents||0,'documentos indexados'],
    ['PUBLIC DATA',p.sources||0,'fontes catalogadas'],
    ['ACTIONS',a.actions||0,'ferramentas internas'],
    ['WORKFLOWS',w.workflows||0,'fluxos compostos'],
    ['AUTONOMY',auto.jobs||0,'automações'],
    ['LONG HORIZON',lh.active||0,'jobs ativos'],
    ['ACQUISITION',(acq.candidates?.installed||0),'competências adquiridas'],
    ['GAPS',Object.values(acq.gaps||{}).reduce((a,b)=>a+b,0),'lacunas registradas'],
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

function bindChatScrolling(){
  const c=chatEl();if(!c)return;

  c.addEventListener('scroll',updateJumpBottom,{passive:true});

  // Qt WebEngine normally handles wheel scrolling, but this fallback makes
  // the conversation panel reliable even when focus is inside nested content.
  c.addEventListener('wheel',e=>{
    if(Math.abs(e.deltaY)<=Math.abs(e.deltaX))return;
    if(c.scrollHeight<=c.clientHeight)return;
    e.preventDefault();
    c.scrollTop+=e.deltaY;
  },{passive:false});

  c.addEventListener('click',()=>c.focus({preventScroll:true}));

  c.addEventListener('keydown',e=>{
    const page=Math.max(220,c.clientHeight*0.82);
    if(e.key==='PageDown'){e.preventDefault();c.scrollBy({top:page,behavior:'smooth'})}
    else if(e.key==='PageUp'){e.preventDefault();c.scrollBy({top:-page,behavior:'smooth'})}
    else if(e.key==='Home'&&e.ctrlKey){e.preventDefault();c.scrollTo({top:0,behavior:'smooth'})}
    else if(e.key==='End'&&e.ctrlKey){e.preventDefault();scrollChatToBottom(true)}
  });

  $('jumpBottomBtn').onclick=()=>scrollChatToBottom(true);
  updateJumpBottom();
}

function initBridge(){
  if(typeof QWebChannel==='undefined'||typeof qt==='undefined'){setTimeout(initBridge,250);return}
  new QWebChannel(qt.webChannelTransport,channel=>{
    bridge=channel.objects.jarvisBridge;
    bridge.statusChanged.connect((state,detail)=>{
      const raw=String(detail||state||'Jarvis está trabalhando…');
      setBusy(true,raw);
      // Exibe o estágio real + tempo decorrido vindo do runtime.
      // Não reduz mais tarefas longas a uma mensagem genérica.
      showThinking(raw);
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
$('mobileBtn').onclick=()=>{openOverlay('mobileOverlay');renderMobile()};
$('mobileToggleBtn').onclick=toggleMobile;
$('mobileResetBtn').onclick=resetMobilePin;
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
bindPromptButtons();bindChatScrolling();toggleInspector(false);initBridge();

$('updateCheckBtn').onclick=checkUpdate;
$('updateInstallBtn').onclick=installUpdate;
document.querySelectorAll('input[name="updateChannel"]').forEach(r=>r.addEventListener('change',e=>changeUpdateChannel(e.target.value)));

setInterval(()=>{if(bridge&&!busy)fetchSnapshot()},15000);

$('mobileDiagBtn').onclick=diagnoseMobile;
$('mobileFirewallBtn').onclick=enableMobileFirewall;

$('mobilePrivateBtn').onclick=makeMobileNetworkPrivate;

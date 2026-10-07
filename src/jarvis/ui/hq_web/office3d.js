import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const canvas = $('#office-canvas');
const stage = $('#stage');
const fallback = $('#fallback');
const labelsEl = $('#room-labels');

const ROOM_LAYOUT = {
  Research:[-11,-7], Intelligence:[0,-7], Creative:[11,-7],
  Engineering:[-11,7], Command:[0,7], Operations:[11,7],
  Review:[-11,21], Administration:[0,21], Memory:[11,21],
};
const PALETTE = {
  room:0x0b1219, glass:0x5f87a7, desk:0x30241d, wood:0x5b4030,
  metal:0x74818c, screen:0x69bfff, green:0x62dfac, amber:0xe6b66b,
  red:0xef6674, floor:0x10171e, accent:0x4cb7f3, wall:0x18232d,
  muted:0x49687e,
};
const AGENT_COLORS = [0x607b8f,0x5f6f87,0x735f78,0x58766c,0x756b58,0x63708a,0x58777b,0x6b657d];

let renderer, scene, camera, controls, raycaster, pointer;
let state = null, selected = null, autoRotate = true, lastFrame = performance.now();
let lastTimelineKey = '', coreMode = 'IDLE';
const roomMap = new Map(), agentObjects = new Map(), dataFlows = new Map();
const clickables = [], animations = [], transient = [];
let core = null;

function material(color, roughness=.7, metalness=.1, emissive=0, transparent=false, opacity=1){
  const m = new THREE.MeshStandardMaterial({color,roughness,metalness,transparent,opacity});
  if(emissive){m.emissive=new THREE.Color(color);m.emissiveIntensity=emissive;}
  return m;
}
function box(w,h,d,color,r=.72,m=.1,e=0){return new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material(color,r,m,e));}
function cyl(r,h,color,segments=24){return new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,segments),material(color,.62,.18));}
function sphere(r,color,e=0,segments=20){return new THREE.Mesh(new THREE.SphereGeometry(r,segments,Math.max(10,segments>>1)),material(color,.5,.14,e));}
function pointLight(color,intensity=1,distance=10){return new THREE.PointLight(color,intensity,distance,2);}
function statusColor(s){return s==='working'?PALETTE.screen:s==='error'?PALETTE.red:s==='needs_input'?PALETTE.amber:PALETTE.green;}
function agentById(id){return Object.values(state?.departments||{}).flat().find(a=>a.id===id);}
function worldOfRoom(name){const p=ROOM_LAYOUT[name]||[0,7];return new THREE.Vector3(p[0],0,p[1]);}
function roomForAgent(id){return agentById(id)?.department || 'Command';}

function makeScreen(parent,x,y,z,w=.86,h=.5,color=PALETTE.screen){
  const frame=box(w+.1,h+.1,.06,0x0d141b,.36,.5); frame.position.set(x,y,z); parent.add(frame);
  const screen=box(w,h,.022,color,.25,.3,1.2); screen.position.set(x,y,z-.043); parent.add(screen);
  animations.push({type:'screen',obj:screen,phase:Math.random()*7});
}
function makeDesk(parent,x,z,accent=PALETTE.screen){
  const d=new THREE.Group(); d.position.set(x,.34,z);
  const top=box(2.05,.12,.92,PALETTE.wood,.76,.08); top.position.y=.45; d.add(top);
  for(const dx of[-.78,.78]) for(const dz of[-.31,.31]){const leg=box(.075,.67,.075,PALETTE.metal,.48,.62);leg.position.set(dx,.02,dz);d.add(leg);}
  makeScreen(d,0,1.08,-.24,.92,.52,accent);
  const keyboard=box(.50,.024,.18,0x161e25,.82,.28); keyboard.position.set(0,.54,.17); d.add(keyboard);
  const chair=cyl(.35,.075,0x19232b); chair.position.set(0,.25,.86); d.add(chair);
  const back=box(.57,.54,.075,0x182129,.78,.18);back.position.set(0,.55,1.06);back.rotation.x=-.08;d.add(back);
  const stem=box(.05,.30,.05,PALETTE.metal,.4,.7);stem.position.set(0,.10,.86);d.add(stem);
  const foot=cyl(.22,.035,0x313d46,18);foot.position.set(0,-.05,.86);d.add(foot);
  parent.add(d);
  return {group:d,seat:new THREE.Vector3(x,0,z+.86)};
}
function makePlant(parent,x,z){
  const pot=cyl(.17,.29,0x45362b);pot.position.set(x,.20,z);parent.add(pot);
  for(let i=0;i<5;i++){const leaf=sphere(.14,0x285d49,.22,12);leaf.scale.set(.42,1.65,.42);leaf.position.set(x+Math.cos(i*1.26)*.11,.49,z+Math.sin(i*1.26)*.11);leaf.rotation.z=Math.cos(i)*.62;parent.add(leaf);}
}
function glassWalls(parent){
  const glass=material(0x6f9ab4,.16,.4,0,true,.17);
  for(const x of[-4.7,4.7]){const w=box(.055,2.1,7.55,0x6f9ab4);w.material=glass.clone();w.position.set(x,1.05,0);parent.add(w);}
  for(const z of[-3.8,3.8]){const w=box(9.4,2.1,.055,0x6f9ab4);w.material=glass.clone();w.position.set(0,1.05,z);parent.add(w);}
}
function roomAccent(name){return ({Research:0x5fc7ff,Intelligence:0x84a8ff,Creative:0xc78bc4,Engineering:0x6d91ff,Operations:0x6ce0ba,Review:0xf0be78,Administration:0x8fb7d4,Memory:0x6ec8c5,Command:0x67d7ff})[name]||PALETTE.screen;}
function makeRoom(name,pos){
  const accent=roomAccent(name),g=new THREE.Group(); g.position.set(pos[0],0,pos[1]); g.userData={type:'room',room:name,seats:[]}; roomMap.set(name,g); clickables.push(g);
  const floor=box(9.4,.08,7.8,PALETTE.room,.95,.04); floor.position.y=.05; g.add(floor);
  const rug=box(7.55,.022,5.72,0x101923,.98,.02); rug.position.y=.105; g.add(rug);
  const back=box(9.35,2.08,.1,PALETTE.wall,.82,.28); back.position.set(0,1.04,-3.78);g.add(back);
  if(name!=='Command'){
    const panel=box(4.8,.95,.045,0x0b151e,.42,.42);panel.position.set(0,1.16,-3.69);g.add(panel);
    for(const x of[-1.55,0,1.55])makeScreen(g,x,1.16,-3.655,.68,.37,accent);
    for(const x of[0,-2.35,2.35]){const station=makeDesk(g,x,.58,accent);g.userData.seats.push(station.seat);}
  }
  makePlant(g,-3.9,2.75);makePlant(g,3.9,2.75);glassWalls(g);
  const strip=box(7.6,.024,.06,accent,.28,.34,.65);strip.position.set(0,.13,-3.42);g.add(strip);
  const statusLamp=pointLight(accent,1.05,7);statusLamp.position.set(0,2.15,.3);g.add(statusLamp);
  g.userData.statusLamp=statusLamp;g.userData.strip=strip;g.userData.energy=0;g.userData.accent=accent;
  scene.add(g);
  return g;
}

function randomSpherePoints(count,inner=.64,outer=1){
  const arr=new Float32Array(count*3);
  for(let i=0;i<count;i++){
    const u=Math.random(),v=Math.random(),theta=2*Math.PI*u,phi=Math.acos(2*v-1),r=inner+(outer-inner)*Math.pow(Math.random(),.62);
    arr[i*3]=r*Math.sin(phi)*Math.cos(theta);arr[i*3+1]=r*Math.cos(phi);arr[i*3+2]=r*Math.sin(phi)*Math.sin(theta);
  }
  return arr;
}
function makeOrbit(group,rx,rz,tilt,color,opacity=.35){
  const points=[];for(let i=0;i<130;i++){const a=(i/129)*Math.PI*2;points.push(new THREE.Vector3(Math.cos(a)*rx,Math.sin(a)*tilt,Math.sin(a)*rz));}
  const geo=new THREE.BufferGeometry().setFromPoints(points);const mat=new THREE.LineBasicMaterial({color,transparent:true,opacity,blending:THREE.AdditiveBlending,depthWrite:false});const line=new THREE.Line(geo,mat);group.add(line);return line;
}
function buildCore(command){
  const g=new THREE.Group();g.position.set(0,.75,0);command.add(g);
  const dais=cyl(3.75,.32,0x0c161f,64);dais.position.y=-.55;g.add(dais);
  const inset=cyl(2.75,.07,0x12293a,64);inset.position.y=-.35;g.add(inset);
  for(let r=1.55;r<=3.05;r+=.75){const ring=new THREE.Mesh(new THREE.TorusGeometry(r,.022,7,96),material(r>2.8?0x55bdf8:0x325f7f,.35,.4,1));ring.rotation.x=Math.PI/2;ring.position.y=-.26;g.add(ring);animations.push({type:'ring',obj:ring,dir:r%1.5?1:-1});}
  const shellGeo=new THREE.BufferGeometry();shellGeo.setAttribute('position',new THREE.BufferAttribute(randomSpherePoints(1300,.78,1.26),3));
  const shellMat=new THREE.PointsMaterial({color:0x65ceff,size:.033,transparent:true,opacity:.82,blending:THREE.AdditiveBlending,depthWrite:false,sizeAttenuation:true});
  const shell=new THREE.Points(shellGeo,shellMat);shell.scale.set(1.65,1.65,1.65);shell.position.y=.58;g.add(shell);
  const innerGeo=new THREE.BufferGeometry();innerGeo.setAttribute('position',new THREE.BufferAttribute(randomSpherePoints(520,.08,.88),3));
  const innerMat=new THREE.PointsMaterial({color:0xc7f3ff,size:.042,transparent:true,opacity:.66,blending:THREE.AdditiveBlending,depthWrite:false,sizeAttenuation:true});
  const inner=new THREE.Points(innerGeo,innerMat);inner.scale.set(1.06,1.06,1.06);inner.position.y=.58;g.add(inner);
  const nucleus=sphere(.42,0x79ddff,4.2,28);nucleus.position.y=.58;g.add(nucleus);
  const halo=sphere(1.58,0x1777bb,.8,32);halo.position.y=.58;halo.material.transparent=true;halo.material.opacity=.055;halo.material.side=THREE.BackSide;g.add(halo);
  const orbits=[makeOrbit(g,2.15,1.25,.62,0x4dbbf8,.34),makeOrbit(g,1.68,2.2,.44,0x67d6ff,.27),makeOrbit(g,2.35,1.85,.31,0x397fc7,.22)];orbits.forEach(o=>o.position.y=.58);
  const light=pointLight(0x54bfff,12,20);light.position.y=1.35;g.add(light);
  core={group:g,shell,inner,nucleus,halo,orbits,light,targetEnergy:.5,energy:.5};
  animations.push({type:'core',obj:g});
}

function buildFlow(roomName){
  if(roomName==='Command')return;
  const from=worldOfRoom(roomName).add(new THREE.Vector3(0,.17,0));
  const to=worldOfRoom('Command').add(new THREE.Vector3(0,.17,0));
  const mid=from.clone().lerp(to,.5);mid.y=.22+Math.min(1.2,from.distanceTo(to)*.035);
  const curve=new THREE.CatmullRomCurve3([from,mid,to]);
  const geo=new THREE.BufferGeometry().setFromPoints(curve.getPoints(45));
  const mat=new THREE.LineBasicMaterial({color:0x24516d,transparent:true,opacity:.16,blending:THREE.AdditiveBlending,depthWrite:false});
  const line=new THREE.Line(geo,mat);scene.add(line);
  const packets=[];
  for(let i=0;i<3;i++){const p=sphere(.075,0x65d7ff,2.2,10);p.visible=false;scene.add(p);packets.push({obj:p,offset:i/3});}
  dataFlows.set(roomName,{curve,line,packets,activity:0,target:0});
}
function buildFlows(){for(const room of Object.keys(ROOM_LAYOUT))buildFlow(room);}

function makeAgentVisual(color){
  const g=new THREE.Group();g.userData={type:'agent',visualState:'idle'};
  const jacket=material(0x273642,.68,.18);jacket.emissive=new THREE.Color(color);jacket.emissiveIntensity=.08;
  const torso=new THREE.Mesh(new THREE.CapsuleGeometry(.19,.34,5,12),jacket);torso.position.set(0,1.04,0);torso.rotation.x=.05;g.add(torso);
  const accent=box(.33,.045,.055,color,.42,.2,1.0);accent.position.set(0,1.08,-.19);g.add(accent);
  const head=sphere(.19,0xd7b497,0,18);head.position.set(0,1.48,-.02);g.add(head);
  const hair=sphere(.198,0x1d252c,0,16);hair.scale.set(1.02,.48,1.0);hair.position.set(0,1.60,-.005);g.add(hair);
  // Seated pose: thighs point toward the desk (-Z), shins drop to the floor.
  for(const x of[-.115,.115]){
    const thigh=box(.09,.10,.36,0x202a32,.74,.12);thigh.position.set(x,.73,-.16);thigh.rotation.x=.08;g.add(thigh);
    const shin=box(.085,.33,.09,0x1b242b,.74,.12);shin.position.set(x,.50,-.34);g.add(shin);
    const foot=box(.095,.055,.18,0x11181e,.78,.10);foot.position.set(x,.31,-.40);g.add(foot);
    const arm=box(.07,.34,.075,0xd0ad92,.66,.04);arm.position.set(x*1.75,1.00,-.22);arm.rotation.x=.78;g.add(arm);
  }
  const ring=new THREE.Mesh(new THREE.TorusGeometry(.34,.022,8,30),material(PALETTE.green,.3,.25,1.2));ring.rotation.x=Math.PI/2;ring.position.y=.16;g.add(ring);g.userData.statusRing=ring;
  const beacon=sphere(.035,PALETTE.screen,2,8);beacon.position.set(0,1.82,0);beacon.visible=false;g.add(beacon);g.userData.beacon=beacon;
  scene.add(g);animations.push({type:'agent',obj:g,phase:Math.random()*7});return g;
}
function agentSlot(index){const slots=[[0,1.44],[-2.35,1.44],[2.35,1.44],[0,-1.0],[-2.35,-1.0],[2.35,-1.0]];return slots[index%slots.length];}
function buildAgents(){
  let colorIndex=0;
  for(const [roomName,agents] of Object.entries(state?.departments||{})){
    agents.forEach((a,i)=>{
      if(agentObjects.has(a.id))return;
      const obj=makeAgentVisual(AGENT_COLORS[colorIndex++%AGENT_COLORS.length]);
      const roomObj=roomMap.get(roomName),room=worldOfRoom(roomName),seat=roomObj?.userData?.seats?.[i],slot=seat?[seat.x,seat.z]:agentSlot(i);const home=new THREE.Vector3(room.x+slot[0],0,room.z+slot[1]);
      obj.position.copy(home);obj.userData.agentId=a.id;obj.userData.home=home.clone();obj.userData.target=home.clone();obj.userData.room=roomName;clickables.push(obj);agentObjects.set(a.id,obj);
    });
  }
}

function buildScene(){
  scene.background=new THREE.Color(0x05090e);scene.fog=new THREE.FogExp2(0x05090e,.017);
  scene.add(new THREE.HemisphereLight(0xb8d5eb,0x0d1013,1.38));
  const key=new THREE.DirectionalLight(0xe8f5ff,2.35);key.position.set(7,27,-3);key.castShadow=true;key.shadow.mapSize.set(2048,2048);scene.add(key);
  const warm=pointLight(0xffb66d,22,62);warm.position.set(-8,7,15);scene.add(warm);
  const cool=pointLight(0x4faeff,18,56);cool.position.set(10,9,-9);scene.add(cool);
  const floor=box(36,.52,42,PALETTE.floor,.96,.18);floor.position.set(0,-.31,7);floor.receiveShadow=true;scene.add(floor);
  for(let x=-18;x<=18;x+=2){const l=box(.012,.01,42,0x22313c,.99,.1);l.position.set(x,-.02,7);scene.add(l);}
  for(let z=-14;z<=28;z+=2){const l=box(36,.01,.012,0x22313c,.99,.1);l.position.set(0,-.018,z);scene.add(l);}
  for(const [name,pos] of Object.entries(ROOM_LAYOUT))makeRoom(name,pos);
  buildCore(roomMap.get('Command'));buildFlows();
  const edgeMat=material(0x101922,.85,.25);for(const z of[-13.7,27.7]){const wall=box(36,4.8,.15,0x101922,.84,.3);wall.position.set(0,2.4,z);scene.add(wall);}for(const x of[-17.9,17.9]){const wall=box(.15,4.8,41.4,0x101922,.84,.3);wall.position.set(x,2.4,7);scene.add(wall);}
  for(let x=-15;x<=15;x+=5){const light=box(2.4,.025,.07,0x3a6781,.3,.35,1.2);light.position.set(x,4.35,-13.55);scene.add(light);}
  void edgeMat;
}

function addLabels(){
  labelsEl.innerHTML='';
  for(const room of Object.keys(ROOM_LAYOUT)){const d=document.createElement('div');d.className='room-label';d.dataset.room=room;d.innerHTML=`<b>${esc(room)}</b><span>carregando</span>`;labelsEl.appendChild(d);}
}
function projectLabels(){
  for(const el of labelsEl.children){const obj=roomMap.get(el.dataset.room);if(!obj)continue;const p=obj.getWorldPosition(new THREE.Vector3(0,2.75,0));p.project(camera);el.style.left=`${(p.x*.5+.5)*stage.clientWidth}px`;el.style.top=`${(-p.y*.5+.5)*stage.clientHeight}px`;el.style.opacity=(p.z>1||p.z<-1)?'0':'1';}
}
function setCamera(pos,target){camera.position.set(...pos);controls.target.set(...target);controls.update();}
function focusRoom(name){const p=worldOfRoom(name);setCamera([p.x+8.5,9.5,p.z+10.5],[p.x,1,p.z]);}

function selectCommand(){
  selected=null;$('#selected-title').textContent='Command Core';$('#selected-subtitle').textContent='central orchestration';$('#selected-status').textContent=coreMode;
  $('#selected-detail').innerHTML='<b>Jarvis Core</b><br><br>O núcleo reage ao estado real do runtime. Fluxos luminosos representam atividade e handoffs; presença visual auxiliar é diferenciada de execução real.<br><br><span>Fonte: /api/hq · telemetry-first</span>';
}
function selectAgentObject(id){
  const a=agentById(id),obj=agentObjects.get(id);if(!a||!obj)return;selected=obj;
  $('#selected-title').textContent=a.name;$('#selected-subtitle').textContent=`${a.department} · ${a.id}`;$('#selected-status').textContent=String(obj.userData.visualState||a.status||'idle').toUpperCase();
  const progress=a.status==='working'?Math.round((a.progress||0)*100)+'%':'—';$('#selected-detail').innerHTML=`<b>${esc(a.activity||'Disponível')}</b><br><br>Execução: ${esc(a.status||'idle')}<br>Presença visual: ${esc(obj.userData.visualState||'idle')}<br>Saúde: ${esc(a.health||'healthy')}<br>Modelo: ${esc(a.model||'—')}<br>Progresso atual: ${progress}<br>Task: ${esc(a.task_id||'—')}<br><br>${esc(a.mission||'')}`;
}
function selectRoom(name){
  const agents=state?.departments?.[name]||[],visual=agents.map(a=>agentObjects.get(a.id)?.userData.visualState).filter(Boolean);
  $('#selected-title').textContent=name;$('#selected-subtitle').textContent=`${agents.length} agente(s)`;$('#selected-status').textContent=visual.includes('executing')?'EXECUTING':visual.includes('assisting')?'ASSISTING':'READY';
  $('#selected-detail').innerHTML=agents.map(a=>{const v=agentObjects.get(a.id)?.userData.visualState||a.status;return `<b>${esc(a.name)}</b> · ${esc(v)}<br><span>${esc(a.activity||'Disponível')}</span>`;}).join('<br><br>')||'Nenhum agente';
}
function handleClick(e){
  const r=canvas.getBoundingClientRect();pointer.x=((e.clientX-r.left)/r.width)*2-1;pointer.y=-((e.clientY-r.top)/r.height)*2+1;raycaster.setFromCamera(pointer,camera);
  const hit=raycaster.intersectObjects(clickables,true)[0];if(!hit)return;let o=hit.object;while(o.parent&&!o.userData?.type)o=o.parent;
  if(o.userData?.type==='agent')selectAgentObject(o.userData.agentId);else if(o.userData?.room==='Command'||o.userData?.type==='command')selectCommand();else if(o.userData?.type==='room')selectRoom(o.userData.room);
}

function stageStateFromSnapshot(data){
  const agents=Object.values(data?.departments||{}).flat();
  if(agents.some(a=>a.status==='error'))return 'ERROR';
  if((data?.attention||[]).some(x=>['critical','high'].includes(String(x.risk))))return 'ATTENTION';
  if(agents.some(a=>a.id==='review.verifier'&&a.status==='working'))return 'VERIFYING';
  if(agents.some(a=>a.id==='research.general'&&a.status==='working'))return 'RESEARCHING';
  if(agents.some(a=>a.status==='working'))return 'EXECUTING';
  return 'IDLE';
}
function corePalette(mode){
  if(mode==='ERROR')return {color:0xff5268,energy:1.15};if(mode==='ATTENTION')return {color:0xffb44b,energy:1.05};if(mode==='VERIFYING')return {color:0x73e0ff,energy:.9};if(mode==='EXECUTING'||mode==='RESEARCHING')return {color:0x52c9ff,energy:1};return {color:0x4a9bd3,energy:.5};
}
function syncCore(){
  if(!core)return;coreMode=stageStateFromSnapshot(state);const p=corePalette(coreMode);core.targetEnergy=p.energy;core.shell.material.color.setHex(p.color);core.inner.material.color.setHex(coreMode==='ERROR'?0xffc1c9:0xc6f4ff);core.light.color.setHex(p.color);$('#core-live-state') && ($('#core-live-state').textContent=coreMode);
}
function activeMissionAgentIds(){
  const ids=new Set();for(const m of state?.missions||[]){if(['completed','failed','cancelled'].includes(m.status))continue;for(const step of m.steps||[]){if(['running','waiting'].includes(step.status))ids.add(step.agent_id);}}return ids;
}
function syncAgents(){
  const missionAgents=activeMissionAgentIds();
  for(const [id,obj] of agentObjects){
    const a=agentById(id);if(!a)continue;const executing=a.status==='working',assisting=!executing&&missionAgents.has(id);const visual=executing?'executing':assisting?'assisting':a.status==='error'?'error':'idle';obj.userData.visualState=visual;
    const ring=obj.userData.statusRing, color=visual==='executing'?PALETTE.screen:visual==='assisting'?PALETTE.amber:visual==='error'?PALETTE.red:PALETTE.green;ring.material.color.setHex(color);ring.material.emissive.setHex(color);ring.material.emissiveIntensity=visual==='executing'?2.8:visual==='assisting'?1.8:1.0;obj.userData.beacon.visible=visual==='executing'||visual==='assisting';obj.userData.beacon.material.color.setHex(color);obj.userData.beacon.material.emissive.setHex(color);
    const home=obj.userData.home,room=worldOfRoom(obj.userData.room);const towardCore=worldOfRoom('Command').clone().sub(room).normalize();const target=home.clone();if(executing)target.add(towardCore.multiplyScalar(.06));else if(assisting)target.add(towardCore.multiplyScalar(.025));obj.userData.target.copy(target);
  }
}
function syncRoomsAndFlows(){
  for(const [name,room] of roomMap){
    const agents=state?.departments?.[name]||[],executing=agents.some(a=>a.status==='working'),assisting=agents.some(a=>agentObjects.get(a.id)?.userData.visualState==='assisting');
    const target=executing?1:(assisting ? .58 : 0);room.userData.energyTarget=Number(target)||0;
    if(name!=='Command'){const flow=dataFlows.get(name);flow.target=executing?1:(assisting ? .48 : 0);}
  }
}
function syncLabels(){
  for(const el of labelsEl.children){const room=el.dataset.room,agents=state?.departments?.[room]||[],executing=agents.filter(a=>a.status==='working').length,assisting=agents.filter(a=>agentObjects.get(a.id)?.userData.visualState==='assisting').length;el.classList.toggle('working',executing>0);el.classList.toggle('assisting',!executing&&assisting>0);el.querySelector('span').textContent=executing?`${executing} executando`:assisting?`${assisting} em assistência`:`${agents.length} estação(ões)`;}
}
function timelineKey(event){return `${event?.timestamp||''}:${event?.type||''}:${event?.agent_id||''}`;}
function agentDepartmentFromId(id){return agentById(id)?.department || null;}
function spawnHandoff(fromRoom,toRoom,color=0x6ad6ff){
  if(!fromRoom||!toRoom||fromRoom===toRoom)return;const a=worldOfRoom(fromRoom).add(new THREE.Vector3(0,.45,0)),b=worldOfRoom(toRoom).add(new THREE.Vector3(0,.45,0)),mid=a.clone().lerp(b,.5);mid.y=2.1;const curve=new THREE.CatmullRomCurve3([a,mid,b]);const dot=sphere(.12,color,3.1,12);scene.add(dot);transient.push({type:'handoff',obj:dot,curve,t:0,speed:.38});
}
function syncTimeline(){
  const events=state?.timeline||[];if(!events.length)return;const newest=events[0],key=timelineKey(newest);if(!lastTimelineKey){lastTimelineKey=key;return;}if(key===lastTimelineKey)return;lastTimelineKey=key;
  const p=newest.payload||{};if(newest.type==='mission.handoff'){spawnHandoff(agentDepartmentFromId(p.from_agent||newest.agent_id),agentDepartmentFromId(p.to_agent),0x65d6ff);}else if(newest.type==='tool.started'){spawnHandoff(agentDepartmentFromId(newest.agent_id)||'Operations','Command',0xffb85c);}else if(newest.type==='verification.passed'||newest.type==='mission.completed'){pulseCore('success');}
  const label=$('#live-activity');if(label){label.textContent=humanEvent(newest);label.classList.remove('flash');requestAnimationFrame(()=>label.classList.add('flash'));}
}
function humanEvent(e){const p=e?.payload||{},type=e?.type||'';if(type==='mission.handoff')return `${p.from_agent||'Agente'} → ${p.to_agent||'próximo estágio'}`;if(type==='mission.completed')return 'Missão concluída e verificada';if(type==='verification.passed')return 'Verificação aprovada';if(type==='verification.failed')return 'Verificação exige revisão';if(type==='tool.started')return 'Ferramenta em execução';if(type==='agent.started')return `${e.agent_id||'Agente'} iniciou trabalho`;return type.replaceAll('.',' · ')||'runtime conectado';}
function pulseCore(kind='activity'){if(!core)return;core.energy=Math.max(core.energy,kind==='success'?1.25:1.05);core.nucleus.scale.setScalar(1.18);}

function renderState(data){
  state=data;if(!scene.userData.agentsBuilt){buildAgents();scene.userData.agentsBuilt=true;}
  const m=data.metrics||{};$('#summary').innerHTML=`<div class="metric"><strong>${m.agents_available||0}</strong><span>disponíveis</span></div><div class="metric"><strong>${m.agents_working||0}</strong><span>executando</span></div><div class="metric"><strong>${m.missions_active||0}</strong><span>missões</span></div><div class="metric"><strong>${m.needs_you||0}</strong><span>atenções</span></div>`;
  $('#mission-total').textContent=String((data.missions||[]).filter(x=>!['completed','failed','cancelled'].includes(x.status)).length);
  $('#attention-count').textContent=String((data.attention||[]).length);
  $('#missions').innerHTML=(data.missions||[]).filter(x=>!['completed','failed','cancelled'].includes(x.status)).slice(0,5).map(x=>{const steps=x.steps||[],done=steps.filter(s=>s.status==='completed').length,pct=Math.round(done/Math.max(1,steps.length)*100);return `<div class="mission-item"><strong>${esc(x.title)}</strong><small>${esc(x.status)} · ${done}/${steps.length} etapas</small><div class="progress-bar"><i style="width:${pct}%"></i></div></div>`;}).join('')||'<div class="muted-count">Nenhuma missão ativa.</div>';
  $('#attention').innerHTML=(data.attention||[]).slice(0,5).map(x=>`<div class="attention-item"><strong>${esc(x.title)}</strong><small>${esc(x.kind)} · ${esc(x.risk)}</small>${x.kind==='approval'?`<button data-approve="${esc(x.id)}">Aprovar</button>`:''}</div>`).join('')||'<div class="muted-count">Nada pendente.</div>';
  $('#attention').querySelectorAll('[data-approve]').forEach(b=>b.onclick=approve);
  $('#department-nav').innerHTML=Object.entries(data.departments||{}).map(([name,agents])=>{const working=agents.filter(a=>a.status==='working').length;return `<button class="dept-btn ${working?'active':''}" data-dept="${esc(name)}"><b>${esc(name)}</b><span>${working?working+' executando':agents.length+' estação(ões)'}</span></button>`;}).join('');
  $('#department-nav').querySelectorAll('[data-dept]').forEach(b=>b.onclick=()=>{selectRoom(b.dataset.dept);focusRoom(b.dataset.dept);});
  $('#connection').textContent='ONLINE';$('#version').textContent=data.schema||'LIVE';
  syncAgents();syncRoomsAndFlows();syncLabels();syncCore();syncTimeline();window.JarvisVisual?.snapshot?.(data);
}

async function approve(e){const id=e.currentTarget?.dataset?.approve||e.dataset?.approve;try{const r=await fetch('/api/approval/'+encodeURIComponent(id)+'/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});if(!r.ok)throw new Error('approval failed');await load();}catch{}}
async function load(){try{const r=await fetch('/api/hq',{cache:'no-store'});if(!r.ok)throw new Error();renderState(await r.json());}catch{$('#connection').textContent='OFFLINE';}}
function resize(){const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
function bind(){
  stage.addEventListener('pointerdown',handleClick);window.addEventListener('resize',resize);
  $('#auto-rotate').onclick=e=>{autoRotate=!autoRotate;e.currentTarget.classList.toggle('active',autoRotate);};
  $('#reset-view').onclick=()=>setCamera([29,25,34],[0,2,7]);$('#preset-overview').onclick=()=>setCamera([29,25,34],[0,2,7]);$('#preset-command').onclick=()=>setCamera([13,9,17],[0,1.1,7]);$('#preset-floor').onclick=()=>setCamera([0,33,10],[0,0,7]);$('#zoom-in').onclick=()=>controls.dollyIn(1.18);$('#zoom-out').onclick=()=>controls.dollyOut(1.18);
}

function animate(now=performance.now()){
  const dt=Math.min(.05,(now-lastFrame)/1000);lastFrame=now;
  if(autoRotate&&!controls._dragging){camera.position.applyAxisAngle(new THREE.Vector3(0,1,0),dt*.022);}
  if(core){
    core.energy+=(core.targetEnergy-core.energy)*Math.min(1,dt*3.2);core.shell.rotation.y+=dt*(.085+.10*core.energy);core.shell.rotation.x=Math.sin(now*.00018)*.16;core.inner.rotation.y-=dt*(.12+.11*core.energy);core.inner.rotation.z+=dt*.055;core.nucleus.scale.lerp(new THREE.Vector3(1+core.energy*.06,1+core.energy*.06,1+core.energy*.06),.05);core.shell.material.opacity=.58+core.energy*.27+Math.sin(now*.0022)*.045;core.inner.material.opacity=.48+core.energy*.27;core.light.intensity=7+core.energy*8;core.orbits.forEach((o,i)=>o.rotation.y+=dt*(.035+i*.012)*(i%2?1:-1));
  }
  for(const a of animations){if(a.type==='screen')a.obj.material.emissiveIntensity=1.08+Math.sin(now*.0018+a.phase)*.14;else if(a.type==='ring')a.obj.rotation.z+=dt*.075*a.dir;else if(a.type==='agent'){const target=a.obj.userData.target;if(target)a.obj.position.lerp(target,Math.min(1,dt*2.1));a.obj.position.y=.006+Math.sin(now*.0015+a.phase)*.010;a.obj.rotation.x+=( (a.obj.userData.visualState==='executing'?.045:a.obj.userData.visualState==='assisting'?.020:0)-a.obj.rotation.x)*Math.min(1,dt*2.6);const r=a.obj.userData.statusRing;r.rotation.z+=dt*(a.obj.userData.visualState==='executing'?1.45:a.obj.userData.visualState==='assisting'?.75:.24);if(a.obj.userData.beacon.visible)a.obj.userData.beacon.position.y=1.82+Math.sin(now*.004+a.phase)*.04;}}
  for(const [name,room] of roomMap){const target=room.userData.energyTarget||0;room.userData.energy+=(target-room.userData.energy)*Math.min(1,dt*3);const e=room.userData.energy;room.userData.statusLamp.intensity=1.1+e*3.2;room.userData.statusLamp.color.setHex(e>.72?PALETTE.screen:e>.18?PALETTE.amber:PALETTE.green);room.userData.strip.material.emissiveIntensity=.35+e*2;room.userData.strip.material.color.setHex(e>.72?PALETTE.screen:e>.18?PALETTE.amber:PALETTE.muted);room.userData.strip.material.emissive.setHex(e>.72?PALETTE.screen:e>.18?PALETTE.amber:PALETTE.muted);}
  for(const flow of dataFlows.values()){flow.activity+=(flow.target-flow.activity)*Math.min(1,dt*2.4);flow.line.material.opacity=.10+flow.activity*.45;flow.line.material.color.setHex(flow.activity>.7?0x5bcaff:flow.activity>.15?0xd19a4c:0x24516d);flow.packets.forEach((p,i)=>{p.obj.visible=flow.activity>.08;if(!p.obj.visible)return;const t=(now*.00012*(.65+flow.activity*1.6)+p.offset)%1;p.obj.position.copy(flow.curve.getPoint(t));p.obj.scale.setScalar(.58+flow.activity*.65);});}
  for(let i=transient.length-1;i>=0;i--){const x=transient[i];x.t+=dt*x.speed;if(x.t>=1){scene.remove(x.obj);x.obj.geometry?.dispose?.();x.obj.material?.dispose?.();transient.splice(i,1);continue;}x.obj.position.copy(x.curve.getPoint(x.t));x.obj.scale.setScalar(.72+Math.sin(x.t*Math.PI)*1.2);}
  controls.update();renderer.render(scene,camera);projectLabels();requestAnimationFrame(animate);
}

try{
  renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false,powerPreference:'high-performance'});renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.75));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(42,1,.1,170);controls=new OrbitControls(camera,canvas);controls.enableDamping=true;controls.dampingFactor=.055;controls.minDistance=12;controls.maxDistance=72;controls.maxPolarAngle=Math.PI/2.03;controls.target.set(0,2,7);raycaster=new THREE.Raycaster();pointer=new THREE.Vector2();
  buildScene();addLabels();bind();setCamera([29,25,34],[0,2,7]);resize();selectCommand();load();setInterval(load,2200);requestAnimationFrame(animate);
}catch(err){console.error('Jarvis Office renderer failed',err);fallback.classList.remove('hidden');}

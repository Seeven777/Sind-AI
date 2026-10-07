/* Runtime-to-visual adapter.
   Visual events are derived from runtime telemetry only. They never create
   tasks, approvals or execution claims. */
(function(){
  const listeners=new Map(),seenTimeline=new Set();
  const motion=Object.freeze({fast:140,normal:220,surface:360,scene:650,ease:'cubic-bezier(.2,.75,.2,1)'});
  function on(type,fn){const set=listeners.get(type)||new Set();set.add(fn);listeners.set(type,set);return()=>set.delete(fn)}
  function emit(type,detail={}){for(const fn of listeners.get(type)||[])fn(detail);for(const fn of listeners.get('*')||[])fn({type,detail});}
  function snapshot(hq){
    const agents=Object.values(hq?.departments||{}).flat();
    if(agents.some(a=>a.status==='error'))emit('system.error',{snapshot:hq});
    else if(agents.some(a=>a.id==='review.verifier'&&a.status==='working'))emit('verification.started',{snapshot:hq});
    else if(agents.some(a=>a.id==='research.general'&&a.status==='working'))emit('agent.researching',{snapshot:hq});
    else if(agents.some(a=>a.status==='working'))emit('agent.executing',{snapshot:hq});
    else emit('system.idle',{snapshot:hq});
    for(const a of hq?.attention||[])emit('approval.required',{attention:a});
    for(const e of (hq?.timeline||[]).slice(0,12).reverse()){
      const key=`${e.timestamp||''}:${e.type||''}:${e.agent_id||''}:${e.task_id||''}`;if(seenTimeline.has(key))continue;seenTimeline.add(key);if(seenTimeline.size>180){const first=seenTimeline.values().next().value;seenTimeline.delete(first);}
      if(['mission.started','mission.completed','mission.failed','mission.handoff','tool.started','tool.completed','verification.started','verification.completed','verification.passed','verification.failed','agent.started','agent.completed','autonomy.curiosity.started','autonomy.curiosity.completed','autonomy.agent_life.started','autonomy.agent_life.completed','autonomy.improvement.proposed'].includes(e.type))emit(e.type,{event:e,snapshot:hq});
    }
  }
  window.JarvisVisual={on,emit,snapshot,motion};
})();

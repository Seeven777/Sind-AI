/* Development-only visual state exerciser. Activate explicitly with
   ?visual-demo=idle|simple_task|medium_task|complex_task|research|coding|
   creative|handoff|tool_use|verification|approval|success|error. */
(function(){
  const mode=new URLSearchParams(location.search).get('visual-demo');
  if(!mode||!window.JarvisVisual)return;
  document.documentElement.dataset.visualDemo=mode;
  const map={idle:'system.idle',simple_task:'agent.executing',medium_task:'agent.assisting',complex_task:'mission.started',research:'agent.researching',coding:'tool.started',creative:'agent.assisting',handoff:'agent.handoff',tool_use:'tool.started',verification:'verification.started',approval:'approval.required',success:'mission.completed',error:'system.error'};
  window.JarvisVisual.emit(map[mode]||'system.idle',{demo:true,mode});
})();

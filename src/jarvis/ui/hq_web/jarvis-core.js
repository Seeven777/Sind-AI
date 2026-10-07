/*
 * Jarvis Living Core v3 — Particle Membrane
 * Visual language shared with the HQ Command Core: a dark, breathing particle
 * sphere wrapped by a restrained electric membrane. Motion reflects runtime
 * state; no decorative HUD geometry is required.
 */
(function(){
  const STATE={
    IDLE:{speed:.20,energy:.62,turbulence:.25,pulse:.09,hue:0.00,points:1.00,filament:.64},
    LISTENING:{speed:.33,energy:.76,turbulence:.38,pulse:.20,hue:-.01,points:1.10,filament:.78},
    THINKING:{speed:.47,energy:.86,turbulence:.54,pulse:.22,hue:.02,points:1.16,filament:.88},
    RESEARCHING:{speed:.39,energy:.82,turbulence:.46,pulse:.18,hue:-.035,points:1.13,filament:.84},
    EXECUTING:{speed:.55,energy:.94,turbulence:.60,pulse:.25,hue:.045,points:1.22,filament:.96},
    VERIFYING:{speed:.30,energy:.78,turbulence:.31,pulse:.14,hue:-.055,points:1.08,filament:.76},
    SPEAKING:{speed:.38,energy:.96,turbulence:.44,pulse:.38,hue:.005,points:1.24,filament:.98},
    SUCCESS:{speed:.23,energy:.80,turbulence:.24,pulse:.13,hue:-.08,points:1.08,filament:.74},
    ATTENTION:{speed:.39,energy:.88,turbulence:.44,pulse:.27,hue:.18,points:1.08,filament:.92},
    ERROR:{speed:.47,energy:.92,turbulence:.58,pulse:.30,hue:.42,points:1.10,filament:.96},
  };

  const QUAD_VERT=`#version 300 es
  in vec2 a_position;
  void main(){gl_Position=vec4(a_position,0.0,1.0);}`;

  const MEMBRANE_FRAG=`#version 300 es
  precision highp float;
  uniform vec2 u_resolution;
  uniform vec2 u_pointer;
  uniform float u_time;
  uniform float u_speed;
  uniform float u_energy;
  uniform float u_turb;
  uniform float u_pulse;
  uniform float u_hue;
  uniform float u_audio;
  uniform float u_filament;
  out vec4 outColor;

  float hash(float n){return fract(sin(n)*43758.5453123);}
  float n1(float x){float i=floor(x),f=fract(x);f=f*f*(3.0-2.0*f);return mix(hash(i),hash(i+1.0),f);}
  mat2 rot(float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}
  vec3 palette(float amount){
    vec3 blue=vec3(.025,.34,.72), cyan=vec3(.16,.78,1.0), white=vec3(.82,.96,1.0);
    if(u_hue>.34){blue=mix(blue,vec3(.78,.025,.07),.78);cyan=mix(cyan,vec3(1.,.20,.13),.72);}
    else if(u_hue>.10){blue=mix(blue,vec3(.78,.26,.015),.56);cyan=mix(cyan,vec3(1.,.65,.10),.45);}
    else if(u_hue<-.05){blue=mix(blue,vec3(.01,.45,.39),.25);cyan=mix(cyan,vec3(.30,1.,.77),.22);}
    return mix(blue,mix(cyan,white,smoothstep(.68,1.,amount)),smoothstep(.05,.88,amount));
  }
  void main(){
    float minDim=min(u_resolution.x,u_resolution.y);
    vec2 uv=(gl_FragCoord.xy-.5*u_resolution.xy)/minDim;
    float r=length(uv),a=atan(uv.y,uv.x),t=u_time*u_speed;
    vec2 pointer=(u_pointer-.5)*vec2(u_resolution.x/u_resolution.y,1.0);
    float proximity=exp(-11.0*length(uv-pointer));

    float breathe=sin(t*1.65)*(.0025+u_pulse*.0045)+u_audio*.0075;
    float wobble=(n1(a*3.2+t*.42)-.5)*.010*u_turb;
    wobble+=(n1(a*8.0-t*.31)-.5)*.0045*(.35+u_turb);
    wobble+=sin(a*5.0+t*.72)*.0024*u_turb;
    float radius=.306+breathe+wobble+proximity*.0022;

    // Three thin energy paths form a living membrane instead of a solid glow.
    float d0=abs(r-radius);
    float r1=radius+sin(a*3.0-t*.48)*(.006+.004*u_turb)+(n1(a*5.4+t*.34)-.5)*.006;
    float r2=radius+sin(a*2.0+t*.36+1.7)*(.010+.003*u_turb)+(n1(a*7.0-t*.22)-.5)*.004;
    float line0=exp(-pow(d0/(.0029+.0014*u_energy),2.0));
    float line1=exp(-pow(abs(r-r1)/(.0020+.0011*u_energy),2.0));
    float line2=exp(-pow(abs(r-r2)/(.0017+.0009*u_energy),2.0));
    float broken=.58+.42*smoothstep(.18,.92,n1(a*13.0+t*.24));
    float fil=(line0*.66+line1*.48+line2*.34)*broken*u_filament;

    float outer=exp(-pow(max(0.0,r-radius)/.052,2.0))*.12*u_energy;
    float inner=exp(-pow(max(0.0,radius-r)/.13,2.0))*.040*u_energy;
    float spark=pow(max(0.0,sin(a*11.0-t*1.15+n1(a*17.0)*3.0)),18.0)*line0*(.28+.60*u_energy);

    // A restrained luminous nucleus makes the Core readable even in IDLE.
    float nucleus=exp(-pow(r/(.082+u_audio*.012),2.0))*(.32+.42*u_energy+u_audio*.30);
    float plasma=exp(-pow(r/.245,4.0))*(.030+.055*u_energy)*( .78+.22*sin(t*.82+a*3.0) );
    float innerHalo=exp(-pow((r-.205)/.090,2.0))*.026*u_energy;

    // Two subtle orbital traces borrow the visual language of the Office Core.
    vec2 q1=rot(t*.055)*uv;
    vec2 q2=rot(-t*.041+1.25)*uv;
    float orbit1=exp(-pow(abs(length(vec2(q1.x*.74,q1.y*1.48))-.365)/.0024,2.0))*.105*u_energy;
    float orbit2=exp(-pow(abs(length(vec2(q2.x*1.42,q2.y*.78))-.382)/.0021,2.0))*.075*u_energy;
    float orbitFade=smoothstep(.22,.35,r)*(1.0-smoothstep(.47,.56,r));
    float orbits=(orbit1+orbit2)*orbitFade;

    float intensity=fil+outer+inner+spark+proximity*(line0*.34+nucleus*.10)+nucleus+plasma+innerHalo+orbits;
    vec3 col=palette(clamp(.20+intensity*.86,0.,1.));
    vec3 coreWhite=mix(col,vec3(.86,.98,1.0),clamp(nucleus*1.35,0.,.72));
    float alpha=clamp(fil+outer+inner+spark+nucleus+plasma+innerHalo+orbits+proximity*.05,0.,.96)*(1.0-smoothstep(.48,.60,r));
    outColor=vec4(coreWhite,alpha);
  }`;

  const POINT_VERT=`#version 300 es
  precision highp float;
  in vec3 a_position;
  in float a_seed;
  in float a_layer;
  uniform float u_time;
  uniform float u_speed;
  uniform float u_energy;
  uniform float u_turb;
  uniform float u_pulse;
  uniform float u_audio;
  uniform float u_points;
  uniform vec2 u_pointer;
  uniform float u_dpr;
  out float v_depth;
  out float v_seed;
  out float v_layer;
  out float v_energy;

  mat3 rotX(float a){float c=cos(a),s=sin(a);return mat3(1.,0.,0.,0.,c,-s,0.,s,c);}
  mat3 rotY(float a){float c=cos(a),s=sin(a);return mat3(c,0.,s,0.,1.,0.,-s,0.,c);}
  mat3 rotZ(float a){float c=cos(a),s=sin(a);return mat3(c,-s,0.,s,c,0.,0.,0.,1.);}

  void main(){
    float t=u_time*u_speed;
    vec3 p=a_position;
    float wave=sin(p.x*7.0+p.y*4.0+t*.82+a_seed*5.1)*.5+
               sin(p.z*8.0-p.x*3.0-t*.57+a_seed*2.3)*.5;
    float breathing=1.0+sin(t*1.55+a_seed*.35)*(.003+.004*u_pulse)+u_audio*.008;
    float displacement=wave*.012*u_turb*(.45+a_layer*.55);
    p*=breathing+displacement;

    float mx=(u_pointer.x-.5)*.30;
    float my=(u_pointer.y-.5)*.22;
    vec2 mouse=(u_pointer-.5)*2.0;
    float local=exp(-3.4*length(p.xy-mouse*.68));
    vec2 away=normalize(p.xy-mouse*.68+vec2(.0001));
    p.xy+=away*local*(.012+.025*u_turb);
    p=rotZ(sin(t*.11)*.052)*rotX(-.20+t*.043+my)*rotY(t*.115+mx)*p;

    float depth=clamp(p.z*.5+.5,0.,1.);
    float perspective=1.0/(1.18-p.z*.12);
    vec2 xy=p.xy*.645*perspective;
    gl_Position=vec4(xy,0.,1.);

    float baseSize=mix(1.30,2.05,a_layer);
    float depthSize=mix(.66,1.28,depth);
    gl_PointSize=baseSize*depthSize*u_dpr*u_points*(1.0+u_energy*.28+u_audio*.38);
    v_depth=depth;v_seed=a_seed;v_layer=a_layer;v_energy=u_energy;
  }`;

  const POINT_FRAG=`#version 300 es
  precision highp float;
  uniform float u_hue;
  uniform float u_audio;
  in float v_depth;
  in float v_seed;
  in float v_layer;
  in float v_energy;
  out vec4 outColor;
  vec3 palette(float k){
    vec3 deep=vec3(.02,.22,.43),cyan=vec3(.24,.83,1.0),white=vec3(.86,.98,1.0);
    if(u_hue>.34){deep=mix(deep,vec3(.70,.03,.06),.80);cyan=mix(cyan,vec3(1.,.21,.16),.72);}
    else if(u_hue>.10){deep=mix(deep,vec3(.70,.28,.02),.54);cyan=mix(cyan,vec3(1.,.72,.18),.42);}
    else if(u_hue<-.05){deep=mix(deep,vec3(.01,.42,.37),.24);cyan=mix(cyan,vec3(.35,1.,.82),.20);}
    return mix(deep,mix(cyan,white,smoothstep(.72,1.,k)),smoothstep(.02,.92,k));
  }
  void main(){
    vec2 q=gl_PointCoord-.5;float d=length(q);if(d>.5)discard;
    float soft=smoothstep(.5,.12,d);
    float twinkle=.78+.22*sin(v_seed*41.0+v_depth*8.0);
    float brightness=clamp(.20+v_depth*.72+v_layer*.10+u_audio*.13,0.,1.);
    vec3 col=palette(brightness);
    float alpha=soft*twinkle*mix(.28,.88,v_depth)*mix(.62,1.,v_layer)*( .76+v_energy*.24 );
    outColor=vec4(col,alpha);
  }`;

  function makeShader(gl,type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s)||'shader compile');return s;}
  function makeProgram(gl,vs,fs){const p=gl.createProgram();gl.attachShader(p,makeShader(gl,gl.VERTEX_SHADER,vs));gl.attachShader(p,makeShader(gl,gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p)||'program link');return p;}
  function uniformMap(gl,p,names){const out={};for(const n of names)out[n]=gl.getUniformLocation(p,n);return out;}

  function sphereCloud(shellCount=3600,innerCount=980){
    const total=shellCount+innerCount,pos=new Float32Array(total*3),seed=new Float32Array(total),layer=new Float32Array(total);
    const golden=Math.PI*(3-Math.sqrt(5));
    for(let i=0;i<shellCount;i++){
      const y=1-(i/(shellCount-1))*2,rad=Math.sqrt(Math.max(0,1-y*y)),theta=golden*i;
      const jitter=(Math.sin(i*12.9898)*43758.5453)%1;
      const r=1+(jitter-Math.floor(jitter)-.5)*.012;
      pos[i*3]=Math.cos(theta)*rad*r;pos[i*3+1]=y*r;pos[i*3+2]=Math.sin(theta)*rad*r;
      seed[i]=(i*0.61803398875)%1;layer[i]=1;
    }
    for(let j=0;j<innerCount;j++){
      const i=shellCount+j,u=(j*.754877666)%1,v=(j*.569840291)%1,theta=2*Math.PI*u,phi=Math.acos(2*v-1);
      const r=.20+.73*Math.pow(((j*.414213562)%1),.58);
      pos[i*3]=r*Math.sin(phi)*Math.cos(theta);pos[i*3+1]=r*Math.cos(phi);pos[i*3+2]=r*Math.sin(phi)*Math.sin(theta);
      seed[i]=(j*.381966011)%1;layer[i]=.18+.50*(j%7)/6;
    }
    return {pos,seed,layer,total};
  }

  class LivingCore{
    constructor(canvas,options={}){this.canvas=canvas;this.options=options||{};this.state='IDLE';this.target={...STATE.IDLE};this.current={...STATE.IDLE};this.audio=0;this.pointer={x:.5,y:.5};this.running=true;this.started=performance.now();this.raf=0;this.resizeObserver=null;this.gl=null;this.ctx=null;this._bound=[];this._quality=this._resolveQuality();this._hidden=document.hidden;this._visibility=()=>{this._hidden=document.hidden;if(!this._hidden&&this.running&&!this.raf){this.started=performance.now();this.gl?this._frameGL():this._frame2D();}};document.addEventListener('visibilitychange',this._visibility);this._init();}
    _resolveQuality(){const requested=this.options.quality||'auto';if(requested==='mobile')return {shell:2200,inner:560,dpr:1.55};if(requested==='low')return {shell:1500,inner:360,dpr:1.25};if(requested==='high')return {shell:3600,inner:980,dpr:2};const mobile=matchMedia('(max-width:700px)').matches,mem=Number(navigator.deviceMemory||4),cores=Number(navigator.hardwareConcurrency||4);return mobile||mem<=3||cores<=4?{shell:2200,inner:560,dpr:1.55}:{shell:3600,inner:980,dpr:2};}
    _init(){try{this.gl=this.canvas.getContext('webgl2',{alpha:true,antialias:true,premultipliedAlpha:false,powerPreference:'high-performance'});if(!this.gl)throw new Error('WebGL2 unavailable');this._initGL();}catch(err){console.warn('Jarvis Core WebGL fallback',err);this.gl=null;this.ctx=this.canvas.getContext('2d');this._init2D();}}
    _resize(){const r=this.canvas.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,this._quality.dpr);const w=Math.max(2,Math.round(r.width*d)),h=Math.max(2,Math.round(r.height*d));if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h;}if(this.gl)this.gl.viewport(0,0,w,h);}
    _listen(type,fn){this.canvas.addEventListener(type,fn,{passive:type!=='pointerdown'});this._bound.push([type,fn]);}
    _events(){this._listen('pointermove',e=>{const r=this.canvas.getBoundingClientRect();this.pointer.x=(e.clientX-r.left)/Math.max(1,r.width);this.pointer.y=1-(e.clientY-r.top)/Math.max(1,r.height);this.audio=Math.max(this.audio,.10);});this._listen('pointerleave',()=>{this.pointer.x=.5;this.pointer.y=.5});this._listen('pointerdown',()=>{this.audio=Math.max(this.audio,.62)});}
    _initGL(){
      const gl=this.gl;this.membraneProgram=makeProgram(gl,QUAD_VERT,MEMBRANE_FRAG);this.pointProgram=makeProgram(gl,POINT_VERT,POINT_FRAG);
      this.membraneU=uniformMap(gl,this.membraneProgram,['u_resolution','u_pointer','u_time','u_speed','u_energy','u_turb','u_pulse','u_hue','u_audio','u_filament']);
      this.pointU=uniformMap(gl,this.pointProgram,['u_time','u_speed','u_energy','u_turb','u_pulse','u_hue','u_audio','u_points','u_pointer','u_dpr']);
      this.quad=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.quad);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
      const cloud=sphereCloud(this._quality.shell,this._quality.inner);this.pointCount=cloud.total;this.pointBuffers={};
      this.pointBuffers.pos=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.pointBuffers.pos);gl.bufferData(gl.ARRAY_BUFFER,cloud.pos,gl.STATIC_DRAW);
      this.pointBuffers.seed=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.pointBuffers.seed);gl.bufferData(gl.ARRAY_BUFFER,cloud.seed,gl.STATIC_DRAW);
      this.pointBuffers.layer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.pointBuffers.layer);gl.bufferData(gl.ARRAY_BUFFER,cloud.layer,gl.STATIC_DRAW);
      gl.disable(gl.DEPTH_TEST);gl.enable(gl.BLEND);this._events();this.resizeObserver=new ResizeObserver(()=>this._resize());this.resizeObserver.observe(this.canvas);this._resize();this._frameGL();
    }
    _lerp(){for(const k of ['speed','energy','turbulence','pulse','hue','points','filament'])this.current[k]+=(this.target[k]-this.current[k])*.032;this.audio*=.91;}
    _commonUniforms(program,u,t){const gl=this.gl;gl.useProgram(program);if(u.u_time)gl.uniform1f(u.u_time,t);if(u.u_speed)gl.uniform1f(u.u_speed,this.current.speed);if(u.u_energy)gl.uniform1f(u.u_energy,this.current.energy);if(u.u_turb)gl.uniform1f(u.u_turb,this.current.turbulence);if(u.u_pulse)gl.uniform1f(u.u_pulse,this.current.pulse);if(u.u_hue)gl.uniform1f(u.u_hue,this.current.hue);if(u.u_audio)gl.uniform1f(u.u_audio,this.audio);if(u.u_pointer)gl.uniform2f(u.u_pointer,this.pointer.x,this.pointer.y);}
    _frameGL=()=>{
      if(!this.running)return;if(this._hidden){this.raf=0;return;}this._resize();this._lerp();const gl=this.gl,t=(performance.now()-this.started)/1000;
      gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
      // restrained membrane first
      this._commonUniforms(this.membraneProgram,this.membraneU,t);gl.uniform2f(this.membraneU.u_resolution,this.canvas.width,this.canvas.height);gl.uniform1f(this.membraneU.u_filament,this.current.filament);gl.bindBuffer(gl.ARRAY_BUFFER,this.quad);const q=gl.getAttribLocation(this.membraneProgram,'a_position');gl.enableVertexAttribArray(q);gl.vertexAttribPointer(q,2,gl.FLOAT,false,0,0);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.drawArrays(gl.TRIANGLES,0,6);
      // point-cloud body, sharing the HQ visual language
      this._commonUniforms(this.pointProgram,this.pointU,t);gl.uniform1f(this.pointU.u_points,this.current.points);gl.uniform1f(this.pointU.u_dpr,Math.min(devicePixelRatio||1,2));
      const bind=(name,buffer,size)=>{const loc=gl.getAttribLocation(this.pointProgram,name);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,0,0)};
      bind('a_position',this.pointBuffers.pos,3);bind('a_seed',this.pointBuffers.seed,1);bind('a_layer',this.pointBuffers.layer,1);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.drawArrays(gl.POINTS,0,this.pointCount);
      this.raf=requestAnimationFrame(this._frameGL);
    }
    _init2D(){
      this._events();this.resizeObserver=new ResizeObserver(()=>this._resize());this.resizeObserver.observe(this.canvas);this._resize();
      const cloud=sphereCloud(1700,420);this.fallbackPoints=[];for(let i=0;i<cloud.total;i++)this.fallbackPoints.push({x:cloud.pos[i*3],y:cloud.pos[i*3+1],z:cloud.pos[i*3+2],seed:cloud.seed[i],layer:cloud.layer[i]});this._frame2D();
    }
    _frame2D=()=>{
      if(!this.running)return;if(this._hidden){this.raf=0;return;}this._resize();this._lerp();const c=this.ctx,w=this.canvas.width,h=this.canvas.height,d=Math.min(w,h),cx=w/2,cy=h/2,t=(performance.now()-this.started)/1000*this.current.speed,scale=d*.325;c.clearRect(0,0,w,h);c.save();c.globalCompositeOperation='lighter';
      const col=this.current.hue>.34?'255,70,70':this.current.hue>.10?'255,180,70':this.current.hue<-.05?'80,235,205':'80,195,255';
      const ring=(phase,width,alpha)=>{c.beginPath();for(let i=0;i<=220;i++){const a=i/220*Math.PI*2,r=scale*(1+Math.sin(a*3-t*.6+phase)*.018*this.current.turbulence+Math.sin(a*7+t*.31+phase)*.008);const x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r;if(i)c.lineTo(x,y);else c.moveTo(x,y)}c.strokeStyle=`rgba(${col},${alpha})`;c.lineWidth=width;c.stroke()};ring(0,1.3*this.current.filament,.42);ring(1.7,.7*this.current.filament,.24);
      const ax=t*.10+(this.pointer.y-.5)*.12,ay=t*.18+(this.pointer.x-.5)*.18,ca=Math.cos(ax),sa=Math.sin(ax),cb=Math.cos(ay),sb=Math.sin(ay);for(const p of this.fallbackPoints){let x=p.x,y=p.y,z=p.z;const y1=y*ca-z*sa,z1=y*sa+z*ca,x2=x*cb+z1*sb,z2=-x*sb+z1*cb;const depth=z2*.5+.5,px=cx+x2*scale,py=cy+y1*scale,rad=(.58+p.layer*.52)*(devicePixelRatio||1)*(1+depth*.45);c.fillStyle=`rgba(${col},${(.14+.66*depth)*(.62+p.layer*.38)})`;c.beginPath();c.arc(px,py,rad,0,Math.PI*2);c.fill()}c.restore();this.audio*=.91;this.raf=requestAnimationFrame(this._frame2D);
    }
    setState(name){name=String(name||'IDLE').toUpperCase();if(!STATE[name])name='IDLE';this.state=name;this.target={...STATE[name]};if(name==='ATTENTION'||name==='ERROR')this.audio=Math.max(this.audio,.34);}
    setAudio(level){this.audio=Math.max(this.audio,Math.max(0,Math.min(1,Number(level)||0)));}
    destroy(){this.running=false;if(this.raf)cancelAnimationFrame(this.raf);this.resizeObserver?.disconnect();document.removeEventListener('visibilitychange',this._visibility);for(const [t,fn] of this._bound)this.canvas.removeEventListener(t,fn);this._bound=[];}
  }

  window.JarvisCore={create:(canvas,options={})=>new LivingCore(canvas,options),states:Object.keys(STATE)};
})();

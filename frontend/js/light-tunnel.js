/* Vanilla adaptation of the React Bits LightTunnel shader for CyberShield's static landing page. */
const vertexSource = `#version 300 es
in vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }`;

const fragmentSource = `#version 300 es
precision highp float;
uniform vec2 iResolution, uMouseOffset;
uniform float iTime;
uniform vec3 uCableColor, uPulseColor, uTunnelColor;
out vec4 fragColor;
void main() {
  vec2 res=iResolution; vec2 uv=(gl_FragCoord.xy-.5*res)/min(res.y,res.x);
  uv-=(uMouseOffset); uv/=2.0001;
  float r=length(uv), angle=atan(uv.y,uv.x), depth=-log(r+.0001);
  float time=iTime*.4, swing=sin(iTime*.15)*.25;
  float waveOffset=sin(depth*1.2-time*.1)*.045;
  float finalAngle=fract(angle/6.2831853+.5+waveOffset+swing);
  float cableID=floor(finalAngle*20.), wireX=abs(fract(finalAngle*20.)-.5);
  float random=fract(sin(cableID*12.9898)*43758.5453);
  float thickness=.1725*(.6+random*.4), wireMask=smoothstep(thickness,thickness-.05,wireX);
  float rimGlow=smoothstep(.0325,0.,abs(wireX-thickness));
  float pulseMask=smoothstep(thickness,thickness-.05,wireX);
  float pulseDist=abs(fract(depth-time*(.4+random*.6)*-.4*2.)-.5);
  float pulse=1.-smoothstep(0.,.28,pulseDist);
  vec3 cable=mix(uCableColor,uPulseColor,random*.25);
  vec3 fiber=cable*rimGlow*1.3+uPulseColor*pulse*3.*pulseMask;
  float distanceFade=smoothstep(0.,.5,r)*smoothstep(2.,1.1,r);
  float intensity=clamp(rimGlow+clamp(pulse*pulseMask,0.,1.),0.,1.)*distanceFade;
  float grain=(fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233))+iTime)*43758.5453)-.5)*.05;
  float alpha=clamp(intensity+grain,0.,1.);
  fragColor=vec4(fiber*alpha,alpha);
}`;

const toRgb = color => color.match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16) / 255);
function shader(gl, type, source) {
  const value=gl.createShader(type); gl.shaderSource(value,source); gl.compileShader(value);
  if (!gl.getShaderParameter(value,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(value));
  return value;
}

function mountLightTunnel(container) {
  const canvas=document.createElement('canvas'); canvas.setAttribute('aria-hidden','true'); container.appendChild(canvas);
  const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:true,antialias:false});
  if (!gl) { canvas.remove(); return; }
  let program;
  try {
    program=gl.createProgram(); gl.attachShader(program,shader(gl,gl.VERTEX_SHADER,vertexSource)); gl.attachShader(program,shader(gl,gl.FRAGMENT_SHADER,fragmentSource)); gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
  } catch (error) { console.warn('Light Tunnel background could not start.',error); canvas.remove(); return; }
  const vao=gl.createVertexArray(); gl.bindVertexArray(vao);
  const buffer=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,buffer); gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
  const position=gl.getAttribLocation(program,'position'); gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
  const uniform=name=>gl.getUniformLocation(program,name);
  const u={ resolution:uniform('iResolution'), time:uniform('iTime'), mouse:uniform('uMouseOffset'), cable:uniform('uCableColor'), pulse:uniform('uPulseColor'), tunnel:uniform('uTunnelColor') };
  const target=[0,0], mouse=[0,0]; let frame=0, running=true;
  const resize=()=>{ const rect=container.getBoundingClientRect(), ratio=Math.min(devicePixelRatio||1,2); canvas.width=Math.max(1,Math.floor(rect.width*ratio)); canvas.height=Math.max(1,Math.floor(rect.height*ratio)); gl.viewport(0,0,canvas.width,canvas.height); };
  const move=event=>{ const rect=canvas.getBoundingClientRect(); target[0]=((event.clientX-rect.left)/rect.width-.5)*.1; target[1]=((event.clientY-rect.top)/rect.height-.5)*.1; };
  const leave=()=>{ target[0]=0; target[1]=0; }; canvas.addEventListener('pointermove',move); canvas.addEventListener('pointerleave',leave);
  const observer=new ResizeObserver(resize); observer.observe(container); resize();
  const start=performance.now();
  const render=now=>{ if (!running) return; mouse[0]+=(target[0]-mouse[0])*.05; mouse[1]+=(target[1]-mouse[1])*.05;
    gl.useProgram(program); gl.bindVertexArray(vao); gl.uniform2f(u.resolution,canvas.width,canvas.height); gl.uniform1f(u.time,(now-start)/1000); gl.uniform2f(u.mouse,mouse[0],mouse[1]);
    gl.uniform3fv(u.cable,toRgb('#0891B2')); gl.uniform3fv(u.pulse,toRgb('#00C8FF')); gl.uniform3fv(u.tunnel,toRgb('#0B1E3D')); gl.drawArrays(gl.TRIANGLES,0,3); frame=requestAnimationFrame(render); };
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { render(start); running=false; } else frame=requestAnimationFrame(render);
  document.addEventListener('visibilitychange',()=>{ if (document.hidden && frame) { cancelAnimationFrame(frame); frame=0; } else if (!document.hidden && !frame && running) frame=requestAnimationFrame(render); });
}
document.querySelectorAll('[data-light-tunnel]').forEach(mountLightTunnel);

const FENCE_START = "```show-widget";
const FENCE_END = "```";
const heightCache = new Map<string, number>();

export type WidgetParseResult = {
  textBefore: string;
  widgetCode: string;
  isClosed: boolean;
};

export function parseShowWidget(input: string): WidgetParseResult {
  const start = input.indexOf(FENCE_START);
  if (start === -1) {
    return { textBefore: input, widgetCode: "", isClosed: false };
  }
  const textBefore = input.slice(0, start);
  const afterStart = input.slice(start + FENCE_START.length).replace(/^\s*\n/, "");
  const end = afterStart.indexOf(FENCE_END);
  if (end === -1) {
    return { textBefore, widgetCode: extractWidgetCode(afterStart), isClosed: false };
  }
  return { textBefore, widgetCode: extractWidgetCode(afterStart.slice(0, end)), isClosed: true };
}

export function extractWidgetCode(raw: string): string {
  const widgetKey = raw.indexOf('"widget_code"');
  if (widgetKey >= 0) {
    const colon = raw.indexOf(":", widgetKey);
    const firstQuote = raw.indexOf('"', colon + 1);
    if (firstQuote >= 0) {
      let output = "";
      for (let index = firstQuote + 1; index < raw.length; index += 1) {
        const char = raw[index];
        if (char === '"' && raw[index - 1] !== "\\") break;
        output += char;
      }
      return output.replace(/\\"/g, '"').replace(/\\n/g, "\n");
    }
  }
  return raw.trim();
}

export function sanitizePreview(html: string): string {
  return truncateOpenScript(html)
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/\s(href|src)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, (match, attr: string, value: string) => {
      const unquoted = value.replace(/^['"]|['"]$/g, "").trim();
      if (/^(javascript:|https?:\/\/)/i.test(unquoted)) {
        return ` ${attr}="#"`;
      }
      return match;
    })
    .replace(/url\(\s*(['"]?)(?:javascript:|https?:\/\/)[^)]+\)/gi, "none");
}

function escapeHtmlText(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
}

function stripHtml(value: string): string {
  return value
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\{\{[^}]+\}\}/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractDemoTitle(source: string, fallback = "动态可视化实验室"): string {
  const titleMatch = source.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i) ?? source.match(/<h2[^>]*>([\s\S]*?)<\/h2>/i) ?? source.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const rawTitle = stripHtml(titleMatch?.[1] ?? source).slice(0, 28);
  return escapeHtmlText(rawTitle || fallback);
}

function quadraticRescueHtml(): string {
  return `
<section class="lfq-rescue" data-learnforge-widget="quadratic-demo">
  <style>
    .lfq-rescue{--ink:#f8fafc;--muted:#a7b2c7;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--green:#86efac;--amber:#f59e0b;--rose:#fb7185;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 15% 10%,rgba(34,211,238,.20),transparent 28%),radial-gradient(circle at 82% 8%,rgba(251,113,133,.14),transparent 24%),linear-gradient(135deg,#07111f,#111827 58%,#06151c);border:1px solid rgba(148,163,184,.25);padding:18px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfq-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:end;margin-bottom:14px}.lfq-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfq-head h2{margin:5px 0 8px;font-size:34px;line-height:1.03}.lfq-head p{margin:0;color:var(--muted);font-size:13px;line-height:1.7;max-width:780px}.lfq-equation{border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.08);padding:12px 14px;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:18px;font-weight:900;white-space:nowrap}
    .lfq-grid{display:grid;grid-template-columns:280px minmax(0,1fr);gap:14px;min-height:0}.lfq-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);backdrop-filter:blur(10px);padding:14px;overflow:auto}.lfq-control{display:grid;gap:6px;margin-bottom:12px}.lfq-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lfq-control input{width:100%;accent-color:var(--cyan)}.lfq-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}.lfq-actions button{min-height:38px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lfq-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lfq-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.lfq-metric{border:1px solid rgba(255,255,255,.11);border-radius:12px;background:rgba(255,255,255,.06);padding:10px}.lfq-metric small{display:block;color:var(--muted);font-size:11px}.lfq-metric strong{font-size:17px}
    .lfq-stage{position:relative;min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.68),rgba(3,7,18,.94));overflow:hidden}.lfq-svg{display:block;width:100%;height:100%}.lfq-axis{stroke:rgba(226,232,240,.55);stroke-width:1.2}.lfq-gridline{stroke:rgba(148,163,184,.14);stroke-width:1}.lfq-curve{fill:none;stroke:var(--rose);stroke-width:4;stroke-linecap:round}.lfq-guide{stroke:var(--green);stroke-dasharray:6 6;stroke-width:1.4}.lfq-focus{fill:var(--cyan);stroke:#06111c;stroke-width:4}.lfq-vertex{fill:var(--green);stroke:#06111c;stroke-width:4}.lfq-root{fill:var(--amber);stroke:#06111c;stroke-width:3}.lfq-label{font-family:"SFMono-Regular",ui-monospace,monospace;font-size:12px;fill:#e5e7eb;font-weight:800}.lfq-callout{position:absolute;right:14px;top:14px;max-width:260px;border:1px solid rgba(255,255,255,.14);border-radius:13px;background:rgba(2,6,23,.76);padding:12px}.lfq-callout strong{display:block;margin-bottom:5px}.lfq-callout p{margin:0;color:var(--muted);font-size:12px;line-height:1.55}
    @media(max-width:840px){.lfq-rescue{height:auto;max-height:none;overflow:visible}.lfq-head,.lfq-grid{grid-template-columns:1fr}.lfq-svg{height:430px}.lfq-stage{min-height:430px}.lfq-equation{white-space:normal}}
  </style>
  <div class="lfq-head"><div><div class="lfq-kicker">Function Motion Studio</div><h2>二次函数参数动态演示实验室</h2><p>拖动 a、b、c 或直接拖拽图面观察点，实时看开口方向、顶点、对称轴、根和函数值如何变化。</p></div><div class="lfq-equation" data-role="equation">y = x²</div></div>
  <div class="lfq-grid">
    <aside class="lfq-panel">
      <div class="lfq-control"><label>参数 a <span data-value="a">1.00</span></label><input data-param="a" type="range" min="-3" max="3" step="0.05" value="1"></div>
      <div class="lfq-control"><label>参数 b <span data-value="b">0.00</span></label><input data-param="b" type="range" min="-6" max="6" step="0.1" value="0"></div>
      <div class="lfq-control"><label>参数 c <span data-value="c">0.00</span></label><input data-param="c" type="range" min="-8" max="8" step="0.1" value="0"></div>
      <div class="lfq-control"><label>观察点 x <span data-value="x">1.50</span></label><input data-param="x" type="range" min="-6" max="6" step="0.05" value="1.5"></div>
      <div class="lfq-actions"><button type="button" data-action="play">播放变形</button><button class="secondary" type="button" data-action="reset">重置</button></div>
      <div class="lfq-metrics"><div class="lfq-metric"><small>顶点</small><strong data-metric="vertex">(0,0)</strong></div><div class="lfq-metric"><small>对称轴</small><strong data-metric="axis">x=0</strong></div><div class="lfq-metric"><small>判别式</small><strong data-metric="disc">0</strong></div><div class="lfq-metric"><small>当前 y</small><strong data-metric="y">2.25</strong></div></div>
    </aside>
    <div class="lfq-stage"><svg class="lfq-svg" data-role="svg" viewBox="0 0 760 520"></svg><div class="lfq-callout"><strong data-role="state-title">开口向上，有最小值</strong><p data-role="state-copy">a 控制开口方向和宽窄，顶点是几何结构的锚点。</p></div></div>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lfq-rescue');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const svg = root.querySelector('[data-role="svg"]');
      const inputs = Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map((input) => [input.dataset.param, input]));
      const valueNodes = Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map((node) => [node.dataset.value, node]));
      const metrics = Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map((node) => [node.dataset.metric, node]));
      const equation = root.querySelector('[data-role="equation"]');
      const title = root.querySelector('[data-role="state-title"]');
      const copy = root.querySelector('[data-role="state-copy"]');
      const W=760,H=520,xMin=-6,xMax=6,yMin=-10,yMax=10;
      let raf=0,start=0,drag=false;
      const sx=x=>((x-xMin)/(xMax-xMin))*W, sy=y=>H-((y-yMin)/(yMax-yMin))*H, fmt=n=>Number(n).toFixed(2).replace(/-0\\.00|\\.00$/g,'0');
      const f=(x,a,b,c)=>a*x*x+b*x+c;
      const xFromClient=clientX=>{const r=svg.getBoundingClientRect();return Math.max(xMin,Math.min(xMax,xMin+((clientX-r.left)/r.width)*(xMax-xMin)));};
      function state(){let a=Number(inputs.a.value); if(Math.abs(a)<.05)a=.05; return {a,b:Number(inputs.b.value),c:Number(inputs.c.value),x:Number(inputs.x.value)};}
      function roots(a,b,c){const d=b*b-4*a*c;if(d<0)return[];const s=Math.sqrt(d);return[(-b-s)/(2*a),(-b+s)/(2*a)].filter(x=>x>=xMin&&x<=xMax);}
      function render(){const {a,b,c,x}=state(),vx=-b/(2*a),vy=f(vx,a,b,c),y=f(x,a,b,c),d=b*b-4*a*c; inputs.a.value=a; valueNodes.a.textContent=fmt(a); valueNodes.b.textContent=fmt(b); valueNodes.c.textContent=fmt(c); valueNodes.x.textContent=fmt(x); equation.textContent='y = '+fmt(a)+'x² '+(b>=0?'+':'-')+' '+fmt(Math.abs(b))+'x '+(c>=0?'+':'-')+' '+fmt(Math.abs(c)); metrics.vertex.textContent='('+fmt(vx)+', '+fmt(vy)+')'; metrics.axis.textContent='x='+fmt(vx); metrics.disc.textContent=fmt(d); metrics.y.textContent=fmt(y); title.textContent=a>0?'开口向上，有最小值':'开口向下，有最大值'; copy.textContent=d>0?'有两个实根，金色点是与 x 轴的交点。':d===0?'顶点刚好贴住 x 轴，是重根。':'没有穿过 x 轴，因此无实数根。'; let g=''; for(let xx=xMin;xx<=xMax;xx++)g+='<line class="lfq-gridline" x1="'+sx(xx)+'" y1="0" x2="'+sx(xx)+'" y2="'+H+'"/>'; for(let yy=yMin;yy<=yMax;yy+=2)g+='<line class="lfq-gridline" x1="0" y1="'+sy(yy)+'" x2="'+W+'" y2="'+sy(yy)+'"/>'; g+='<line class="lfq-axis" x1="0" y1="'+sy(0)+'" x2="'+W+'" y2="'+sy(0)+'"/><line class="lfq-axis" x1="'+sx(0)+'" y1="0" x2="'+sx(0)+'" y2="'+H+'"/>'; const pts=[]; for(let i=0;i<=180;i++){const px=xMin+i/180*(xMax-xMin);pts.push(sx(px).toFixed(1)+','+sy(Math.max(yMin,Math.min(yMax,f(px,a,b,c)))).toFixed(1));} const rs=roots(a,b,c).map(rx=>'<circle class="lfq-root" cx="'+sx(rx)+'" cy="'+sy(0)+'" r="7"/>').join(''); svg.innerHTML=g+'<line class="lfq-guide" x1="'+sx(vx)+'" y1="0" x2="'+sx(vx)+'" y2="'+H+'"/><polyline class="lfq-curve" points="'+pts.join(' ')+'"/>'+rs+'<circle class="lfq-vertex" cx="'+sx(vx)+'" cy="'+sy(Math.max(yMin,Math.min(yMax,vy)))+'" r="8"/><circle class="lfq-focus" cx="'+sx(x)+'" cy="'+sy(Math.max(yMin,Math.min(yMax,y)))+'" r="9"/><line class="lfq-guide" x1="'+sx(x)+'" y1="'+sy(0)+'" x2="'+sx(x)+'" y2="'+sy(Math.max(yMin,Math.min(yMax,y)))+'"/><text class="lfq-label" x="'+(sx(x)+10)+'" y="'+(sy(Math.max(yMin,Math.min(yMax,y)))-12)+'">('+fmt(x)+', '+fmt(y)+')</text>'; }
      function stop(){if(raf)cancelAnimationFrame(raf);raf=0;start=0;root.querySelector('[data-action="play"]').textContent='播放变形';}
      function play(t=performance.now()){if(!start)start=t;const s=(t-start)/1000;inputs.a.value=(1.45*Math.sin(s*.72)+.25).toFixed(2);inputs.b.value=(4.2*Math.sin(s*.48+1.3)).toFixed(2);inputs.c.value=(4.8*Math.cos(s*.64)).toFixed(2);inputs.x.value=(5.2*Math.sin(s*.95)).toFixed(2);render();raf=requestAnimationFrame(play);}
      root.addEventListener('input',()=>{stop();render();}); root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:''; if(a==='play'){ if(raf)stop(); else {e.target.textContent='停止动画'; raf=requestAnimationFrame(play);} } if(a==='reset'){stop();Object.assign(inputs.a,{value:1});Object.assign(inputs.b,{value:0});Object.assign(inputs.c,{value:0});Object.assign(inputs.x,{value:1.5});render();}});
      svg.addEventListener('pointerdown',e=>{stop();drag=true;inputs.x.value=xFromClient(e.clientX).toFixed(2);render();svg.setPointerCapture(e.pointerId);}); svg.addEventListener('pointermove',e=>{if(!drag)return;inputs.x.value=xFromClient(e.clientX).toFixed(2);render();}); svg.addEventListener('pointerup',()=>drag=false); svg.addEventListener('pointercancel',()=>drag=false);
      render();
    })();
  </script>
</section>`;
}

function sortingRescueHtml(): string {
  return `
<section class="lfs-rescue" data-learnforge-widget="sorting-demo">
  <style>
    .lfs-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--amber:#f59e0b;--rose:#fb7185;--green:#86efac;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 18% 8%,rgba(34,211,238,.18),transparent 28%),radial-gradient(circle at 82% 10%,rgba(251,113,133,.12),transparent 26%),linear-gradient(135deg,#07111f,#111827 60%,#06151c);border:1px solid rgba(148,163,184,.25);padding:16px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfs-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:end;margin-bottom:14px}.lfs-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfs-head h2{margin:5px 0 8px;font-size:34px;line-height:1.03}.lfs-head p{margin:0;color:var(--muted);font-size:13px;line-height:1.7;max-width:780px}
    .lfs-stats{display:grid;grid-template-columns:repeat(3,92px);gap:8px}.lfs-stat{border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.07);padding:10px}.lfs-stat small{display:block;color:var(--muted);font-size:11px}.lfs-stat strong{font-size:22px}
    .lfs-grid{display:grid;grid-template-columns:280px minmax(0,1fr) 280px;gap:12px;min-height:0}.lfs-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);backdrop-filter:blur(10px);padding:13px;overflow:auto}.lfs-panel h3{margin:0 0 10px;font-size:15px}.lfs-field{display:grid;gap:6px;margin-bottom:11px}.lfs-field label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lfs-field input,.lfs-field select{width:100%;accent-color:var(--cyan)}.lfs-field select{height:36px;border:1px solid var(--line);border-radius:10px;background:#111827;color:var(--ink);font-weight:900;padding:0 10px}
    .lfs-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}.lfs-actions button{min-height:38px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lfs-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}.lfs-actions button.warn{background:linear-gradient(135deg,var(--amber),var(--rose));color:#21080f}
    .lfs-stage{min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.94));overflow:hidden;position:relative}.lfs-canvas{display:block;width:100%;height:100%}.lfs-overlay{position:absolute;left:14px;right:14px;bottom:12px;display:flex;justify-content:space-between;gap:10px}.lfs-pill{border:1px solid var(--line);background:rgba(0,0,0,.30);border-radius:999px;padding:7px 10px;color:var(--muted);font-size:12px}
    .lfs-code{min-height:180px;white-space:pre-wrap;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:12px;line-height:1.55;color:#c7d2fe;background:#050a13;border:1px solid rgba(148,163,184,.18);border-radius:12px;padding:12px}.lfs-log{margin-top:10px;min-height:72px;border-left:3px solid var(--cyan);background:rgba(34,211,238,.08);border-radius:10px;padding:10px;color:#dbeafe;font-weight:850;line-height:1.55;font-size:13px}
    @media(max-width:980px){.lfs-rescue{height:auto;max-height:none;overflow:visible}.lfs-head,.lfs-grid{grid-template-columns:1fr}.lfs-stats{grid-template-columns:repeat(3,1fr)}.lfs-canvas{height:440px}.lfs-stage{min-height:440px}}
  </style>
  <div class="lfs-head"><div><div class="lfs-kicker">Algorithm Motion Lab</div><h2>高级排序算法动态可视化沙盒</h2><p>逐帧观察比较、交换、插入、选择和快速分区。这里使用 Canvas 状态机驱动动画，不展示静态表单。</p></div><div class="lfs-stats"><div class="lfs-stat"><small>比较</small><strong data-metric="compare">0</strong></div><div class="lfs-stat"><small>交换</small><strong data-metric="swap">0</strong></div><div class="lfs-stat"><small>步骤</small><strong data-metric="step">0</strong></div></div></div>
  <div class="lfs-grid">
    <aside class="lfs-panel"><h3>控制台</h3><div class="lfs-field"><label>算法 <span data-role="algo-label">冒泡排序</span></label><select data-role="algo"><option value="bubble">冒泡排序</option><option value="insertion">插入排序</option><option value="selection">选择排序</option><option value="quick">快速排序分区</option></select></div><div class="lfs-field"><label>数据规模 <span data-role="size-label">22</span></label><input data-role="size" type="range" min="8" max="42" value="22"></div><div class="lfs-field"><label>速度 <span data-role="speed-label">中速</span></label><input data-role="speed" type="range" min="1" max="5" value="3"></div><div class="lfs-actions"><button type="button" data-action="play">播放</button><button class="secondary" type="button" data-action="step">单步</button><button class="secondary" type="button" data-action="shuffle">刷新</button><button class="warn" type="button" data-action="stop">停止</button></div></aside>
    <div class="lfs-stage"><canvas class="lfs-canvas" data-role="canvas"></canvas><div class="lfs-overlay"><span class="lfs-pill" data-role="phase">等待执行</span><span class="lfs-pill">蓝=待处理 橙=比较 红=交换 绿=已确定</span></div></div>
    <aside class="lfs-panel"><h3>当前步骤</h3><div class="lfs-code" data-role="code">选择算法后开始执行。</div><div class="lfs-log" data-role="log">已生成初始数据。</div></aside>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lfs-rescue');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
      const n={algo:root.querySelector('[data-role="algo"]'),size:root.querySelector('[data-role="size"]'),speed:root.querySelector('[data-role="speed"]'),algoLabel:root.querySelector('[data-role="algo-label"]'),sizeLabel:root.querySelector('[data-role="size-label"]'),speedLabel:root.querySelector('[data-role="speed-label"]'),compare:root.querySelector('[data-metric="compare"]'),swap:root.querySelector('[data-metric="swap"]'),step:root.querySelector('[data-metric="step"]'),phase:root.querySelector('[data-role="phase"]'),code:root.querySelector('[data-role="code"]'),log:root.querySelector('[data-role="log"]')};
      const labels={bubble:'冒泡排序',insertion:'插入排序',selection:'选择排序',quick:'快速排序分区'},speedText=['很慢','慢速','中速','快速','高速'];
      let values=[],steps=[],cursor=0,playing=false,raf=0,last=0,metrics={compare:0,swap:0,step:0},current={};
      const range=(a,b)=>Array.from({length:Math.max(0,b-a)},(_,i)=>a+i);
      function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(640,Math.floor(r.width*devicePixelRatio));canvas.height=Math.floor(r.height*devicePixelRatio);draw();}
      function shuffle(){const count=Number(n.size.value);values=Array.from({length:count},(_,i)=>({id:i,v:12+Math.floor(Math.random()*88)}));metrics={compare:0,swap:0,step:0};cursor=0;steps=build(n.algo.value,values.map(x=>x.v));current={note:'新数据已就绪',active:[],moved:[],sorted:[]};update();draw();}
      function build(kind,arr){return kind==='insertion'?insertion(arr):kind==='selection'?selection(arr):kind==='quick'?quick(arr):bubble(arr);}
      function bubble(a){const arr=a.slice(),out=[];for(let end=arr.length-1;end>0;end--){for(let i=0;i<end;i++){out.push({t:'compare',active:[i,i+1],sorted:range(end+1,arr.length),code:'if a['+i+'] > a['+(i+1)+']',note:'比较相邻元素'});if(arr[i]>arr[i+1]){[arr[i],arr[i+1]]=[arr[i+1],arr[i]];out.push({t:'swap',values:arr.slice(),active:[i,i+1],moved:[i,i+1],sorted:range(end+1,arr.length),code:'swap(a['+i+'], a['+(i+1)+'])',note:'交换，较大元素向右冒泡'});}}out.push({t:'mark',sorted:range(end,arr.length),code:'mark sorted boundary',note:'本轮最大值归位'});}out.push({t:'done',sorted:range(0,arr.length),code:'done',note:'排序完成'});return out;}
      function insertion(a){const arr=a.slice(),out=[];for(let i=1;i<arr.length;i++){const key=arr[i];let j=i-1;out.push({t:'compare',active:[i,j],sorted:range(0,i),code:'key = a['+i+']',note:'取出 key 插入左侧有序区'});while(j>=0&&arr[j]>key){arr[j+1]=arr[j];out.push({t:'swap',values:arr.slice(),active:[j,j+1],moved:[j+1],sorted:range(0,i),code:'a['+(j+1)+'] = a['+j+']',note:'元素右移'});j--;}arr[j+1]=key;out.push({t:'swap',values:arr.slice(),active:[j+1],moved:[j+1],sorted:range(0,i+1),code:'insert key',note:'key 插入完成'});}out.push({t:'done',sorted:range(0,arr.length),code:'done',note:'排序完成'});return out;}
      function selection(a){const arr=a.slice(),out=[];for(let i=0;i<arr.length-1;i++){let min=i;for(let j=i+1;j<arr.length;j++){out.push({t:'compare',active:[min,j],sorted:range(0,i),code:'scan min from unsorted area',note:'扫描未排序区最小值'});if(arr[j]<arr[min])min=j;}if(min!==i){[arr[i],arr[min]]=[arr[min],arr[i]];out.push({t:'swap',values:arr.slice(),active:[i,min],moved:[i,min],sorted:range(0,i+1),code:'swap min to boundary',note:'把最小值放到边界'});}}out.push({t:'done',sorted:range(0,arr.length),code:'done',note:'排序完成'});return out;}
      function quick(a){const arr=a.slice(),out=[];function part(lo,hi){if(lo>=hi)return;const pivot=arr[hi];let i=lo;out.push({t:'mark',active:[hi],code:'pivot = a['+hi+']',note:'选择基准点'});for(let j=lo;j<hi;j++){out.push({t:'compare',active:[j,hi],moved:range(lo,i),code:'if a['+j+'] < pivot',note:'和基准比较，扩展左分区'});if(arr[j]<pivot){[arr[i],arr[j]]=[arr[j],arr[i]];out.push({t:'swap',values:arr.slice(),active:[i,j],moved:[i,j],code:'swap into left partition',note:'进入小于基准分区'});i++;}}[arr[i],arr[hi]]=[arr[hi],arr[i]];out.push({t:'swap',values:arr.slice(),active:[i,hi],sorted:[i],code:'place pivot',note:'基准落到最终位置'});part(lo,i-1);part(i+1,hi);}part(0,arr.length-1);out.push({t:'done',sorted:range(0,arr.length),code:'done',note:'快速分区完成'});return out;}
      function apply(s){if(!s)return;current=s;if(s.values)values=s.values.map((v,i)=>values[i]?{...values[i],v}:{id:i,v});if(s.t==='compare')metrics.compare++;if(s.t==='swap')metrics.swap++;metrics.step++;update();draw();}
      function update(){n.algoLabel.textContent=labels[n.algo.value];n.sizeLabel.textContent=n.size.value;n.speedLabel.textContent=speedText[Number(n.speed.value)-1];n.compare.textContent=metrics.compare;n.swap.textContent=metrics.swap;n.step.textContent=metrics.step;n.phase.textContent=current.note||'等待执行';n.code.textContent=current.code||'选择算法后开始执行。';n.log.textContent=current.note||'已生成初始数据。';}
      function rect(x,y,w,h,r){ctx.beginPath();if(ctx.roundRect){ctx.roundRect(x,y,w,h,r);}else{ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();}}
      function draw(){const w=canvas.width,h=canvas.height,p=42*devicePixelRatio,base=h-p,max=Math.max(1,...values.map(x=>x.v)),gap=4*devicePixelRatio,bw=(w-p*2-gap*(values.length-1))/values.length;ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);ctx.strokeStyle='rgba(148,163,184,.15)';for(let y=p;y<base;y+=42*devicePixelRatio){ctx.beginPath();ctx.moveTo(p,y);ctx.lineTo(w-p,y);ctx.stroke();}values.forEach((item,i)=>{const x=p+i*(bw+gap),bh=(item.v/max)*(h-p*2),active=(current.active||[]).includes(i),moved=(current.moved||[]).includes(i),sorted=(current.sorted||[]).includes(i),g=ctx.createLinearGradient(0,base-bh,0,base);g.addColorStop(0,sorted?'#86efac':moved?'#fb7185':active?'#f59e0b':'#38bdf8');g.addColorStop(1,sorted?'#15803d':moved?'#be123c':active?'#b45309':'#1d4ed8');ctx.fillStyle=g;rect(x,base-bh,bw,bh,Math.min(12*devicePixelRatio,bw/3));ctx.fill();});}
      function loop(t){if(!playing)return;const delay=760-Number(n.speed.value)*115;if(t-last>delay){last=t;if(cursor>=steps.length){playing=false;return;}apply(steps[cursor++]);}raf=requestAnimationFrame(loop);}
      function stop(){playing=false;cancelAnimationFrame(raf);}
      root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='play'&&!playing){playing=true;last=0;raf=requestAnimationFrame(loop);}if(a==='stop')stop();if(a==='shuffle'){stop();shuffle();}if(a==='step'){stop();if(cursor<steps.length)apply(steps[cursor++]);}});
      root.addEventListener('input',e=>{if(e.target===n.size||e.target===n.algo){stop();shuffle();}else update();});
      window.addEventListener('resize',resize);resize();shuffle();
    })();
  </script>
</section>`;
}

function trigRescueHtml(): string {
  return `
<section class="lft-rescue" data-learnforge-widget="trig-demo">
  <style>
    .lft-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--amber:#f59e0b;--rose:#fb7185;--green:#86efac;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 16% 8%,rgba(34,211,238,.18),transparent 28%),radial-gradient(circle at 82% 8%,rgba(245,158,11,.14),transparent 24%),linear-gradient(135deg,#07111f,#111827 58%,#06151c);border:1px solid rgba(148,163,184,.25);padding:16px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lft-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:end;margin-bottom:12px}.lft-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lft-head h2{margin:4px 0 6px;font-size:30px;line-height:1.04}.lft-head p{margin:0;color:var(--muted);font-size:13px;line-height:1.6;max-width:760px}.lft-equation{border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.07);padding:10px 12px;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:16px;font-weight:900;white-space:nowrap}
    .lft-grid{display:grid;grid-template-columns:270px minmax(0,1fr);gap:12px;min-height:0}.lft-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);backdrop-filter:blur(10px);padding:12px;box-sizing:border-box;overflow:auto}.lft-control{display:grid;gap:5px;margin-bottom:10px}.lft-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lft-control input,.lft-control select{width:100%;accent-color:var(--cyan)}.lft-control select{height:34px;border:1px solid var(--line);border-radius:10px;background:#111827;color:var(--ink);font-weight:900;padding:0 10px}
    .lft-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}.lft-actions button{min-height:36px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lft-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lft-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.lft-metric{border:1px solid rgba(255,255,255,.11);border-radius:11px;background:rgba(255,255,255,.06);padding:8px}.lft-metric small{display:block;color:var(--muted);font-size:11px}.lft-metric strong{font-size:16px}
    .lft-stage{position:relative;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.94));overflow:hidden;min-height:0}.lft-svg{display:block;width:100%;height:100%}.lft-axis{stroke:rgba(226,232,240,.55);stroke-width:1.2}.lft-gridline{stroke:rgba(148,163,184,.14);stroke-width:1}.lft-wave{fill:none;stroke:var(--cyan);stroke-width:4;stroke-linecap:round}.lft-wave.sin{stroke:var(--cyan)}.lft-wave.cos{stroke:var(--amber)}.lft-wave.tan{stroke:var(--rose)}.lft-guide{stroke:var(--green);stroke-dasharray:6 6;stroke-width:1.4}.lft-point{fill:var(--green);stroke:#06111c;stroke-width:4}.lft-label{font-family:"SFMono-Regular",ui-monospace,monospace;font-size:12px;fill:#e5e7eb;font-weight:800}.lft-callout{position:absolute;right:12px;top:12px;max-width:260px;border:1px solid rgba(255,255,255,.14);border-radius:13px;background:rgba(2,6,23,.76);padding:11px}.lft-callout strong{display:block;margin-bottom:4px}.lft-callout p{margin:0;color:var(--muted);font-size:12px;line-height:1.5}
    @media(max-width:840px){.lft-rescue{height:auto;max-height:none;overflow:visible}.lft-head,.lft-grid{grid-template-columns:1fr;height:auto}.lft-stage,.lft-svg{height:430px}.lft-equation{white-space:normal}}
  </style>
  <div class="lft-head"><div><div class="lft-kicker">Wave Motion Studio</div><h2>常见三角函数动态可视化</h2><p>调节振幅、角频率、初相位和观察点，实时理解波峰、周期、平移和函数值变化。</p></div><div class="lft-equation" data-role="equation">y = sin(x)</div></div>
  <div class="lft-grid">
    <aside class="lft-panel">
      <div class="lft-control"><label>函数 <span data-value="type">sin</span></label><select data-param="type"><option value="sin">sin 正弦</option><option value="cos">cos 余弦</option><option value="tan">tan 正切</option></select></div>
      <div class="lft-control"><label>振幅 A <span data-value="A">1.0</span></label><input data-param="A" type="range" min="0.2" max="3" step="0.1" value="1"></div>
      <div class="lft-control"><label>角频率 omega <span data-value="omega">1.0</span></label><input data-param="omega" type="range" min="0.2" max="3" step="0.1" value="1"></div>
      <div class="lft-control"><label>初相位 phi <span data-value="phi">0.00</span></label><input data-param="phi" type="range" min="-3.14" max="3.14" step="0.05" value="0"></div>
      <div class="lft-control"><label>观察点 x <span data-value="x">1.00</span></label><input data-param="x" type="range" min="-6.28" max="6.28" step="0.05" value="1"></div>
      <div class="lft-actions"><button type="button" data-action="play">播放波动</button><button class="secondary" type="button" data-action="reset">重置</button></div>
      <div class="lft-metrics"><div class="lft-metric"><small>周期</small><strong data-metric="period">2pi</strong></div><div class="lft-metric"><small>当前 y</small><strong data-metric="y">0.84</strong></div><div class="lft-metric"><small>相位</small><strong data-metric="phase">1.00</strong></div><div class="lft-metric"><small>波形</small><strong data-metric="shape">正弦</strong></div></div>
    </aside>
    <div class="lft-stage"><svg class="lft-svg" data-role="svg" viewBox="0 0 760 612"></svg><div class="lft-callout"><strong data-role="state-title">正弦波</strong><p data-role="state-copy">A 控制高度，omega 控制周期密度，phi 控制水平平移。</p></div></div>
  </div>
  <script>
    (() => {
      const root=document.currentScript.closest('.lft-rescue'); if(!root||root.dataset.ready==='1')return; root.dataset.ready='1';
      const svg=root.querySelector('[data-role="svg"]'), inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i])), values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n])), metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n])), eq=root.querySelector('[data-role="equation"]'), title=root.querySelector('[data-role="state-title"]'), copy=root.querySelector('[data-role="state-copy"]');
      const W=760,H=612,xMin=-6.28,xMax=6.28,yMin=-3.4,yMax=3.4; let raf=0,start=0,drag=false;
      const sx=x=>((x-xMin)/(xMax-xMin))*W, sy=y=>H-((y-yMin)/(yMax-yMin))*H, fmt=(n,d=2)=>Number(n).toFixed(d).replace(/-0\\.00|\\.00$/g,'0'), xFromClient=c=>{const r=svg.getBoundingClientRect();return Math.max(xMin,Math.min(xMax,xMin+((c-r.left)/r.width)*(xMax-xMin)));};
      function calc(type,z){ if(type==='cos')return Math.cos(z); if(type==='tan'){const v=Math.tan(z); return Math.abs(v)>3.2?NaN:v;} return Math.sin(z); }
      function state(){return{type:inputs.type.value,A:Number(inputs.A.value),omega:Number(inputs.omega.value),phi:Number(inputs.phi.value),x:Number(inputs.x.value)};}
      function render(){const s=state(), phase=s.omega*s.x+s.phi, y=s.A*calc(s.type,phase); values.type.textContent=s.type; values.A.textContent=fmt(s.A,1); values.omega.textContent=fmt(s.omega,1); values.phi.textContent=fmt(s.phi); values.x.textContent=fmt(s.x); metrics.period.textContent=fmt((Math.PI*2)/s.omega); metrics.y.textContent=Number.isFinite(y)?fmt(y):'渐近'; metrics.phase.textContent=fmt(phase); metrics.shape.textContent=s.type==='sin'?'正弦':s.type==='cos'?'余弦':'正切'; eq.textContent='y = '+fmt(s.A,1)+' '+s.type+'('+fmt(s.omega,1)+'x '+(s.phi>=0?'+ ':'- ')+fmt(Math.abs(s.phi))+')'; title.textContent=metrics.shape.textContent+'波'; copy.textContent=s.type==='tan'?'正切函数在奇数个 pi/2 附近出现竖直渐近线。':'A 改变波峰高度，omega 改变周期，phi 让波形水平平移。'; let g=''; for(let x=-6;x<=6;x++)g+='<line class="lft-gridline" x1="'+sx(x)+'" y1="0" x2="'+sx(x)+'" y2="'+H+'"/>'; for(let yy=-3;yy<=3;yy++)g+='<line class="lft-gridline" x1="0" y1="'+sy(yy)+'" x2="'+W+'" y2="'+sy(yy)+'"/>'; g+='<line class="lft-axis" x1="0" y1="'+sy(0)+'" x2="'+W+'" y2="'+sy(0)+'"/><line class="lft-axis" x1="'+sx(0)+'" y1="0" x2="'+sx(0)+'" y2="'+H+'"/>'; const segs=[]; let pts=[]; for(let i=0;i<=360;i++){const px=xMin+i/360*(xMax-xMin), py=s.A*calc(s.type,s.omega*px+s.phi); if(!Number.isFinite(py)){ if(pts.length)segs.push(pts); pts=[]; continue;} pts.push(sx(px).toFixed(1)+','+sy(Math.max(yMin,Math.min(yMax,py))).toFixed(1));} if(pts.length)segs.push(pts); const waves=segs.map(p=>'<polyline class="lft-wave '+s.type+'" points="'+p.join(' ')+'"/>').join(''); const point=Number.isFinite(y)?'<line class="lft-guide" x1="'+sx(s.x)+'" y1="'+sy(0)+'" x2="'+sx(s.x)+'" y2="'+sy(y)+'"/><circle class="lft-point" cx="'+sx(s.x)+'" cy="'+sy(y)+'" r="9"/><text class="lft-label" x="'+(sx(s.x)+10)+'" y="'+(sy(y)-12)+'">('+fmt(s.x)+', '+fmt(y)+')</text>':''; svg.innerHTML=g+waves+point; }
      function stop(){if(raf)cancelAnimationFrame(raf);raf=0;start=0;root.querySelector('[data-action="play"]').textContent='播放波动';}
      function play(t=performance.now()){if(!start)start=t;const dt=(t-start)/1000;inputs.phi.value=((dt*1.4)%6.28-3.14).toFixed(2);inputs.x.value=(5.6*Math.sin(dt*.75)).toFixed(2);render();raf=requestAnimationFrame(play);}
      root.addEventListener('input',()=>{stop();render();}); root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:''; if(a==='play'){if(raf)stop();else{e.target.textContent='停止波动';raf=requestAnimationFrame(play);}} if(a==='reset'){stop();inputs.type.value='sin';inputs.A.value=1;inputs.omega.value=1;inputs.phi.value=0;inputs.x.value=1;render();}});
      svg.addEventListener('pointerdown',e=>{stop();drag=true;inputs.x.value=xFromClient(e.clientX).toFixed(2);render();svg.setPointerCapture(e.pointerId);}); svg.addEventListener('pointermove',e=>{if(!drag)return;inputs.x.value=xFromClient(e.clientX).toFixed(2);render();}); svg.addEventListener('pointerup',()=>drag=false); svg.addEventListener('pointercancel',()=>drag=false);
      render();
    })();
  </script>
</section>`;
}

function momentumRescueHtml(): string {
  return `
<section class="lfm-rescue" data-learnforge-widget="momentum-demo">
  <style>
    .lfm-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--amber:#f59e0b;--rose:#fb7185;--green:#86efac;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 18% 10%,rgba(34,211,238,.18),transparent 30%),radial-gradient(circle at 86% 6%,rgba(134,239,172,.14),transparent 24%),linear-gradient(135deg,#07111f,#111827 60%,#06151c);border:1px solid rgba(148,163,184,.25);padding:16px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfm-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:end;margin-bottom:12px}.lfm-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfm-head h2{margin:4px 0 6px;font-size:30px;line-height:1.04}.lfm-head p{margin:0;color:var(--muted);font-size:13px;line-height:1.6;max-width:780px}.lfm-formula{border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.07);padding:10px 12px;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:15px;font-weight:900;white-space:nowrap}
    .lfm-grid{display:grid;grid-template-columns:280px minmax(0,1fr) 260px;gap:12px;min-height:0}.lfm-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);backdrop-filter:blur(10px);padding:12px;box-sizing:border-box;overflow:auto}.lfm-panel h3{margin:0 0 10px;font-size:15px}.lfm-control{display:grid;gap:5px;margin-bottom:10px}.lfm-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lfm-control input{width:100%;accent-color:var(--cyan)}
    .lfm-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.lfm-actions button{min-height:36px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lfm-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lfm-stage{position:relative;min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}.lfm-canvas{display:block;width:100%;height:100%}.lfm-overlay{position:absolute;left:14px;right:14px;bottom:12px;display:flex;justify-content:space-between;gap:10px;pointer-events:none}.lfm-pill{border:1px solid var(--line);background:rgba(0,0,0,.34);border-radius:999px;padding:7px 10px;color:var(--muted);font-size:12px}
    .lfm-metrics{display:grid;grid-template-columns:1fr;gap:8px}.lfm-metric{border:1px solid rgba(255,255,255,.11);border-radius:11px;background:rgba(255,255,255,.06);padding:9px}.lfm-metric small{display:block;color:var(--muted);font-size:11px}.lfm-metric strong{font-size:18px}.lfm-note{margin-top:10px;border-left:3px solid var(--green);background:rgba(134,239,172,.08);border-radius:10px;padding:10px;color:#dbeafe;font-size:12px;line-height:1.55}
    @media(max-width:980px){.lfm-rescue{height:auto;max-height:none;overflow:visible}.lfm-head,.lfm-grid{grid-template-columns:1fr}.lfm-formula{white-space:normal}.lfm-canvas{height:440px}.lfm-stage{min-height:440px}}
  </style>
  <div class="lfm-head"><div><div class="lfm-kicker">Collision Momentum Lab</div><h2>一维动量守恒与碰撞动态实验室</h2><p>改变质量、初速度和恢复系数，观察碰撞前后速度箭头、总动量和动能损失如何变化。</p></div><div class="lfm-formula" data-role="formula">m1v1 + m2v2 = 常量</div></div>
  <div class="lfm-grid">
    <aside class="lfm-panel">
      <h3>碰撞参数</h3>
      <div class="lfm-control"><label>方块 A 质量 m1 <span data-value="m1">2.0 kg</span></label><input data-param="m1" type="range" min="0.5" max="6" step="0.1" value="2"></div>
      <div class="lfm-control"><label>A 初速度 v1 <span data-value="v1">4.0 m/s</span></label><input data-param="v1" type="range" min="-6" max="6" step="0.1" value="4"></div>
      <div class="lfm-control"><label>方块 B 质量 m2 <span data-value="m2">3.0 kg</span></label><input data-param="m2" type="range" min="0.5" max="6" step="0.1" value="3"></div>
      <div class="lfm-control"><label>B 初速度 v2 <span data-value="v2">-2.0 m/s</span></label><input data-param="v2" type="range" min="-6" max="6" step="0.1" value="-2"></div>
      <div class="lfm-control"><label>恢复系数 e <span data-value="e">1.00</span></label><input data-param="e" type="range" min="0" max="1" step="0.05" value="1"></div>
      <div class="lfm-actions"><button type="button" data-action="play">播放碰撞</button><button class="secondary" type="button" data-action="reset">场景重置</button></div>
    </aside>
    <div class="lfm-stage"><canvas class="lfm-canvas" data-role="canvas"></canvas><div class="lfm-overlay"><span class="lfm-pill" data-role="phase">碰撞前：两物体相向运动</span><span class="lfm-pill">拖动画布中的方块可改初始位置</span></div></div>
    <aside class="lfm-panel">
      <h3>守恒读数</h3>
      <div class="lfm-metrics"><div class="lfm-metric"><small>碰撞后速度</small><strong data-metric="after">v1'=0, v2'=0</strong></div><div class="lfm-metric"><small>总动量前/后</small><strong data-metric="momentum">0 / 0</strong></div><div class="lfm-metric"><small>动能前/后</small><strong data-metric="energy">0 / 0</strong></div><div class="lfm-metric"><small>碰撞类型</small><strong data-metric="type">完全弹性</strong></div></div>
      <div class="lfm-note" data-role="note">e=1 时动能守恒；e 变小，碰撞后相对速度变小，损失的动能转化为形变和热。</div>
    </aside>
  </div>
  <script>
    (() => {
      const root=document.currentScript.closest('.lfm-rescue'); if(!root||root.dataset.ready==='1')return; root.dataset.ready='1';
      const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
      const inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i]));
      const values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n]));
      const metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n]));
      const phase=root.querySelector('[data-role="phase"]'), formula=root.querySelector('[data-role="formula"]');
      let raf=0,last=0,running=false,collided=false,drag=null,boxA={x:-3.9,v:4},boxB={x:3.2,v:-2};
      const fmt=(n,d=2)=>Number(n).toFixed(d).replace(/-0\\.00|\\.00$/g,'0');
      function params(){return{m1:Number(inputs.m1.value),v1:Number(inputs.v1.value),m2:Number(inputs.m2.value),v2:Number(inputs.v2.value),e:Number(inputs.e.value)};}
      function post(p=params()){const v1=(p.m1*p.v1+p.m2*p.v2-p.m2*p.e*(p.v1-p.v2))/(p.m1+p.m2);const v2=(p.m1*p.v1+p.m2*p.v2+p.m1*p.e*(p.v1-p.v2))/(p.m1+p.m2);return{v1,v2};}
      function energy(m,v){return .5*m*v*v;} function momentum(m,v){return m*v;}
      function resetScene(){const p=params();boxA={x:-3.9,v:p.v1};boxB={x:3.2,v:p.v2};collided=false;last=0;update();draw();}
      function update(){const p=params(),q=post(p),p0=momentum(p.m1,p.v1)+momentum(p.m2,p.v2),p1=momentum(p.m1,q.v1)+momentum(p.m2,q.v2),k0=energy(p.m1,p.v1)+energy(p.m2,p.v2),k1=energy(p.m1,q.v1)+energy(p.m2,q.v2);values.m1.textContent=fmt(p.m1,1)+' kg';values.v1.textContent=fmt(p.v1,1)+' m/s';values.m2.textContent=fmt(p.m2,1)+' kg';values.v2.textContent=fmt(p.v2,1)+' m/s';values.e.textContent=fmt(p.e);metrics.after.textContent="v1'="+fmt(q.v1,2)+", v2'="+fmt(q.v2,2);metrics.momentum.textContent=fmt(p0,2)+' / '+fmt(p1,2);metrics.energy.textContent=fmt(k0,2)+' / '+fmt(k1,2)+' J';metrics.type.textContent=p.e===1?'完全弹性':p.e===0?'完全非弹性近似':'部分弹性';formula.textContent='p = '+fmt(p0,2)+' kg·m/s，碰撞后仍为 '+fmt(p1,2);phase.textContent=collided?'碰撞后：速度由动量守恒和恢复系数决定':(p.v1<=p.v2?'当前速度不会相遇，可拖动物体或调速度':'碰撞前：两物体相向运动');}
      function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(640,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(360,Math.floor(r.height*devicePixelRatio));draw();}
      function toScreen(x){const w=canvas.width,p=70*devicePixelRatio;return p+((x+6)/12)*(w-p*2);} function fromScreen(px){const r=canvas.getBoundingClientRect();return ((px-r.left)/r.width)*12-6;}
      function widths(){const p=params();return{a:(54+p.m1*11)*devicePixelRatio,b:(54+p.m2*11)*devicePixelRatio};}
      function rect(x,y,w,h,r){ctx.beginPath();if(ctx.roundRect)ctx.roundRect(x,y,w,h,r);else{ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();}}
      function arrow(cx,cy,v,color){const len=Math.max(18,Math.min(120,Math.abs(v)*22))*devicePixelRatio,dir=v>=0?1:-1;ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=4*devicePixelRatio;ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx+dir*len,cy);ctx.stroke();ctx.beginPath();ctx.moveTo(cx+dir*len,cy);ctx.lineTo(cx+dir*(len-12*devicePixelRatio),cy-7*devicePixelRatio);ctx.lineTo(cx+dir*(len-12*devicePixelRatio),cy+7*devicePixelRatio);ctx.closePath();ctx.fill();}
      function draw(){const w=canvas.width,h=canvas.height,y=h*.55,wh=widths();ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);ctx.strokeStyle='rgba(148,163,184,.14)';for(let x=70*devicePixelRatio;x<w-70*devicePixelRatio;x+=52*devicePixelRatio){ctx.beginPath();ctx.moveTo(x,42*devicePixelRatio);ctx.lineTo(x,h-42*devicePixelRatio);ctx.stroke();}ctx.strokeStyle='rgba(226,232,240,.46)';ctx.lineWidth=2*devicePixelRatio;ctx.beginPath();ctx.moveTo(50*devicePixelRatio,y+62*devicePixelRatio);ctx.lineTo(w-50*devicePixelRatio,y+62*devicePixelRatio);ctx.stroke();const ax=toScreen(boxA.x)-wh.a/2,bx=toScreen(boxB.x)-wh.b/2,bh=64*devicePixelRatio;const gradA=ctx.createLinearGradient(0,y-bh,0,y);gradA.addColorStop(0,'#67e8f9');gradA.addColorStop(1,'#2563eb');const gradB=ctx.createLinearGradient(0,y-bh,0,y);gradB.addColorStop(0,'#86efac');gradB.addColorStop(1,'#15803d');ctx.fillStyle=gradA;rect(ax,y-bh,wh.a,bh,14*devicePixelRatio);ctx.fill();ctx.fillStyle=gradB;rect(bx,y-bh,wh.b,bh,14*devicePixelRatio);ctx.fill();ctx.fillStyle='#06111c';ctx.font=(16*devicePixelRatio)+'px Avenir Next, sans-serif';ctx.textAlign='center';ctx.fillText('A',ax+wh.a/2,y-bh/2+5*devicePixelRatio);ctx.fillText('B',bx+wh.b/2,y-bh/2+5*devicePixelRatio);arrow(ax+wh.a/2,y-bh-24*devicePixelRatio,boxA.v,'#22d3ee');arrow(bx+wh.b/2,y-bh-24*devicePixelRatio,boxB.v,'#86efac');if(collided){ctx.strokeStyle='#f59e0b';ctx.lineWidth=3*devicePixelRatio;ctx.beginPath();ctx.arc((ax+wh.a+bx)/2,y-bh/2,38*devicePixelRatio,0,Math.PI*2);ctx.stroke();}ctx.fillStyle='rgba(226,232,240,.85)';ctx.font=(13*devicePixelRatio)+'px SFMono-Regular, monospace';ctx.fillText('x 方向一维碰撞轨道',w/2,h-26*devicePixelRatio);}
      function step(t){if(!running)return;if(!last)last=t;const dt=Math.min(.035,(t-last)/1000);last=t;const p=params(),wh=widths(),scale=12/(canvas.width-140*devicePixelRatio);boxA.x+=boxA.v*dt*.62;boxB.x+=boxB.v*dt*.62;const gap=(wh.a/2+wh.b/2)*scale;if(!collided&&boxA.x+gap>=boxB.x&&boxA.v>boxB.v){const q=post(p);boxA.v=q.v1;boxB.v=q.v2;boxA.x=boxB.x-gap;collided=true;update();}if(Math.abs(boxA.x)>5.8||Math.abs(boxB.x)>5.8){boxA.v*=.35;boxB.v*=.35;}draw();raf=requestAnimationFrame(step);}
      function play(){if(running){running=false;cancelAnimationFrame(raf);root.querySelector('[data-action="play"]').textContent='播放碰撞';return;}running=true;root.querySelector('[data-action="play"]').textContent='暂停';raf=requestAnimationFrame(step);}
      root.addEventListener('input',()=>{running=false;cancelAnimationFrame(raf);root.querySelector('[data-action="play"]').textContent='播放碰撞';resetScene();});
      root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='play')play();if(a==='reset'){running=false;cancelAnimationFrame(raf);root.querySelector('[data-action="play"]').textContent='播放碰撞';resetScene();}});
      canvas.addEventListener('pointerdown',e=>{running=false;cancelAnimationFrame(raf);const wh=widths(),mx=e.clientX,my=e.clientY,r=canvas.getBoundingClientRect(),sy=canvas.height*.55/devicePixelRatio-64;const ax=toScreen(boxA.x)/devicePixelRatio-wh.a/devicePixelRatio/2,bx=toScreen(boxB.x)/devicePixelRatio-wh.b/devicePixelRatio/2;if(my-r.top>sy-18&&my-r.top<sy+92){if(mx-r.left>ax&&mx-r.left<ax+wh.a/devicePixelRatio)drag='a';else if(mx-r.left>bx&&mx-r.left<bx+wh.b/devicePixelRatio)drag='b';}if(drag)canvas.setPointerCapture(e.pointerId);});
      canvas.addEventListener('pointermove',e=>{if(!drag)return;const x=Math.max(-5.4,Math.min(5.4,fromScreen(e.clientX)));if(drag==='a')boxA.x=Math.min(x,boxB.x-.55);else boxB.x=Math.max(x,boxA.x+.55);collided=false;update();draw();});
      canvas.addEventListener('pointerup',()=>{drag=null;});canvas.addEventListener('pointercancel',()=>{drag=null;});
      window.addEventListener('resize',resize);resize();resetScene();
    })();
  </script>
</section>`;
}

function genericInteractiveRescueHtml(source: string): string {
  const title = extractDemoTitle(source);
  return `
<section class="lfg-rescue" data-learnforge-widget="generic-dynamic-demo">
  <style>
    .lfg-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--amber:#f59e0b;--rose:#fb7185;--green:#86efac;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 18% 8%,rgba(34,211,238,.18),transparent 28%),radial-gradient(circle at 82% 12%,rgba(251,113,133,.12),transparent 25%),linear-gradient(135deg,#07111f,#111827 60%,#06151c);border:0;padding:16px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfg-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:end;margin-bottom:8px}.lfg-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfg-head h2{margin:4px 0 4px;font-size:26px;line-height:1.08}.lfg-head p{margin:0;color:var(--muted);font-size:13px;line-height:1.6;max-width:780px}.lfg-status{border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.07);padding:10px 12px;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:14px;font-weight:900;white-space:nowrap}
    .lfg-grid{display:grid;grid-template-columns:250px minmax(0,1fr) 220px;gap:10px;min-height:0}.lfg-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);backdrop-filter:blur(10px);padding:12px;box-sizing:border-box;overflow:auto}.lfg-panel h3{margin:0 0 10px;font-size:14px}.lfg-control{display:grid;gap:4px;margin-bottom:8px}.lfg-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lfg-control input{width:100%;accent-color:var(--cyan)}
    .lfg-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}.lfg-actions button{min-height:34px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lfg-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lfg-stage{position:relative;min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}.lfg-canvas{display:block;width:100%;height:100%}.lfg-metrics{display:grid;grid-template-columns:1fr;gap:6px}.lfg-metric{border:1px solid rgba(255,255,255,.11);border-radius:11px;background:rgba(255,255,255,.06);padding:8px}.lfg-metric small{display:block;color:var(--muted);font-size:11px}.lfg-metric strong{font-size:17px}.lfg-note{margin-top:8px;border-left:3px solid var(--cyan);background:rgba(34,211,238,.08);border-radius:10px;padding:10px;color:#dbeafe;font-size:12px;line-height:1.5}
    @media(max-width:980px){.lfg-rescue{height:auto;overflow:visible}.lfg-head,.lfg-grid{grid-template-columns:1fr}.lfg-status{white-space:normal}.lfg-canvas{height:400px}.lfg-stage{min-height:400px}}
  </style>
  <div class="lfg-head"><div><div class="lfg-kicker">Interactive Demo Lab</div><h2>${title}</h2><p>拖动画布中的实体，调节参数滑块，实时观察系统变化和数值反馈。</p></div><div class="lfg-status" data-role="status">t = 0.00 s</div></div>
  <div class="lfg-grid">
    <aside class="lfg-panel"><h3>实验控制</h3><div class="lfg-control"><label>运动强度 <span data-value="force">1.00</span></label><input data-param="force" type="range" min="0.2" max="3" step="0.05" value="1"></div><div class="lfg-control"><label>对象数量 <span data-value="count">6</span></label><input data-param="count" type="range" min="2" max="14" step="1" value="6"></div><div class="lfg-control"><label>弹性恢复 <span data-value="restitution">0.75</span></label><input data-param="restitution" type="range" min="0.1" max="1" step="0.05" value="0.75"></div><div class="lfg-actions"><button type="button" data-action="play">暂停/播放</button><button class="secondary" type="button" data-action="reset">重置场景</button></div></aside>
    <div class="lfg-stage"><canvas class="lfg-canvas" data-role="canvas"></canvas></div>
    <aside class="lfg-panel"><h3>状态读数</h3><div class="lfg-metrics"><div class="lfg-metric"><small>总动能</small><strong data-metric="energy">0.00</strong></div><div class="lfg-metric"><small>碰撞次数</small><strong data-metric="collisions">0</strong></div><div class="lfg-metric"><small>活跃对象</small><strong data-metric="active">0</strong></div></div><div class="lfg-note">拖动画布中的任意实体来施加力。滑块实时调节系统参数。</div></aside>
  </div>
  <script>
    (() => {
      const root=document.currentScript.closest('.lfg-rescue'); if(!root||root.dataset.ready==='1')return; root.dataset.ready='1';
      const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
      const inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i]));
      const values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n]));
      const metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n]));
      const status=root.querySelector('[data-role="status"]');
      let raf=0,last=0,t=0,running=true,drag=null,dragIdx=-1;
      let balls=[],collisionCount=0;
      const fmt=(n,d=2)=>Number(n).toFixed(d).replace(/-0\\.00|\\.00$/g,'0');
      function init(){
        const n=Math.max(2,Number(inputs.count.value)||6);
        balls=Array.from({length:n},(_,i)=>({
          x:(Math.random()-.5)*.7, y:(Math.random()-.5)*.55,
          vx:(Math.random()-.5)*1.2, vy:(Math.random()-.5)*1.2,
          r:.04+Math.random()*.06, color:i%4
        }));
        collisionCount=0;
      }
      function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(500,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(300,Math.floor(r.height*devicePixelRatio));draw();}
      function updateLabels(){const p=params();values.force.textContent=fmt(p.force);values.count.textContent=p.count;values.restitution.textContent=fmt(p.restitution);}
      function params(){return{force:Number(inputs.force.value),count:Number(inputs.count.value),restitution:Number(inputs.restitution.value)};}
      function step(dt){const p=params(),f=p.force*dt*.8; balls.forEach(b=>{b.vx*=0.999;b.vy*=0.999;b.x+=b.vx*dt;b.y+=b.vy*dt;
        if(Math.abs(b.x)>0.92){b.x=Math.sign(b.x)*0.92;b.vx*=-p.restitution;collisionCount++;}
        if(Math.abs(b.y)>0.88){b.y=Math.sign(b.y)*0.88;b.vy*=-p.restitution;collisionCount++;}
      });
      for(let i=0;i<balls.length;i++){for(let j=i+1;j<balls.length;j++){
        const dx=balls[j].x-balls[i].x,dy=balls[j].y-balls[i].y,dist=Math.hypot(dx,dy),minDist=balls[i].r+balls[j].r;
        if(dist<minDist&&dist>0.001){const nx=dx/dist,ny=dy/dist,overlap=minDist-dist;balls[i].x-=nx*overlap/2;balls[i].y-=ny*overlap/2;balls[j].x+=nx*overlap/2;balls[j].y+=ny*overlap/2;
          const dvx=balls[j].vx-balls[i].vx,dvy=balls[j].vy-balls[i].vy,dvn=dvx*nx+dvy*ny;
          if(dvn<0){const imp=dvn*(1+p.restitution)/(1/1+1/1)*f;balls[i].vx+=imp*nx;balls[i].vy+=imp*ny;balls[j].vx-=imp*nx;balls[j].vy-=imp*ny;collisionCount++;}
      }}}}
      function draw(){const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);
        ctx.strokeStyle='rgba(148,163,184,.12)';ctx.lineWidth=1*devicePixelRatio;
        const gw=48*devicePixelRatio;for(let x=gw;x<w;x+=gw){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
        for(let y=gw;y<h;y+=gw){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
        ctx.strokeStyle='rgba(226,232,240,.38)';ctx.lineWidth=2*devicePixelRatio;ctx.strokeRect(16*devicePixelRatio,16*devicePixelRatio,w-32*devicePixelRatio,h-32*devicePixelRatio);
        const colors=['#22d3ee','#86efac','#f59e0b','#fb7185'];
        balls.forEach(b=>{const x=w/2+b.x*w*.48,y=h/2+b.y*h*.46,r=Math.max(8*devicePixelRatio,b.r*Math.min(w,h)*.5);
          const g=ctx.createRadialGradient(x-r*.3,y-r*.3,r*.1,x,y,r);g.addColorStop(0,'#ffffff');g.addColorStop(.4,colors[b.color]);g.addColorStop(1,'#0f172a');
          ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
          ctx.strokeStyle='rgba(255,255,255,.3)';ctx.lineWidth=1.5*devicePixelRatio;ctx.stroke();
          if(r>16*devicePixelRatio){ctx.fillStyle='#04111d';ctx.font=(r*.7)+'px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(b.color+1,x,y);}
        });
        let totalKE=0;balls.forEach(b=>{totalKE+=b.vx*b.vx+b.vy*b.vy;});
        metrics.energy.textContent=fmt(totalKE*50);metrics.collisions.textContent=collisionCount;metrics.active.textContent=balls.length;
        status.textContent='t = '+fmt(t)+' s';
      }
      function loop(now){if(!last)last=now;const dt=Math.min(.025,(now-last)/1000);last=now;if(running){t+=dt;step(dt);}draw();raf=requestAnimationFrame(loop);}
      root.addEventListener('input',()=>{updateLabels();const n=Number(inputs.count.value)||6;if(n!==balls.length)init();});
      root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='play')running=!running;if(a==='reset'){init();t=0;}});
      canvas.addEventListener('pointerdown',e=>{const r=canvas.getBoundingClientRect();const mx=(e.clientX-r.left)*devicePixelRatio/canvas.width-0.5,my=(e.clientY-r.top)*devicePixelRatio/canvas.height-0.5;
        dragIdx=-1;let best=-1,dist=Infinity;balls.forEach((b,i)=>{const d=Math.hypot(mx-b.x,my-b.y);if(d<dist){dist=d;best=i;}});if(best>=0&&dist<0.15){dragIdx=best;drag=balls[best];canvas.setPointerCapture(e.pointerId);}});
      canvas.addEventListener('pointermove',e=>{if(!drag||dragIdx<0)return;const r=canvas.getBoundingClientRect();drag.x=Math.max(-0.94,Math.min(0.94,(e.clientX-r.left)*devicePixelRatio/canvas.width-0.5));drag.y=Math.max(-0.89,Math.min(0.89,(e.clientY-r.top)*devicePixelRatio/canvas.height-0.5));drag.vx=0;drag.vy=0;});
      canvas.addEventListener('pointerup',()=>{drag=null;dragIdx=-1;});
      window.addEventListener('resize',resize);init();resize();updateLabels();raf=requestAnimationFrame(loop);
    })();
  </script>
</section>`;
}

function fluidRescueHtml(): string {
  return `
<section class="lffl-rescue" data-learnforge-widget="fluid-demo">
  <style>
    .lffl-rescue{--ink:#e8eefc;--muted:#9fb0cc;--line:rgba(255,255,255,.12);--cyan:#38bdf8;--amber:#fbbf24;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:#0a0e17;border:0;padding:18px 22px;box-sizing:border-box;overflow:auto;display:flex;flex-direction:column;gap:12px}
    .lffl-title{text-align:center;font-size:30px;font-weight:900;letter-spacing:.04em;color:#5b8cff;text-shadow:0 0 18px rgba(91,140,255,.45);margin:2px 0 0}
    .lffl-sub{text-align:center;color:var(--muted);font-size:14px;margin:0}
    .lffl-card{border:1px solid var(--line);border-radius:18px;background:#0d1320;padding:16px;display:flex;flex-direction:column;gap:14px;flex:1;min-height:0}
    .lffl-stage{position:relative;border:1px solid rgba(56,189,248,.18);border-radius:12px;background:#070b13;overflow:hidden;flex:1;min-height:300px}
    .lffl-canvas{display:block;width:100%;height:100%}
    .lffl-sliders{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
    .lffl-slider{border:1px solid var(--line);border-radius:14px;background:#0b1220;padding:12px 14px}
    .lffl-slider .row{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}
    .lffl-slider label{color:var(--muted);font-size:13px;font-weight:700}
    .lffl-slider b{color:#7aa2ff;font-size:18px;font-weight:900;font-variant-numeric:tabular-nums}
    .lffl-slider input{width:100%;accent-color:#5b8cff}
    .lffl-eq{border:1px solid var(--line);border-radius:14px;background:#0b1220;padding:14px;text-align:center}
    .lffl-eq strong{color:var(--amber);font-size:18px;font-weight:900}
    .lffl-eq small{display:block;margin-top:6px;color:var(--muted);font-size:13px}
    @media(max-width:760px){.lffl-sliders{grid-template-columns:1fr}.lffl-stage{min-height:260px}}
  </style>
  <h2 class="lffl-title">交互式伯努利定律演示</h2>
  <p class="lffl-sub">拖动下方滑块，实时观察公式参数变化对流场压强的影响。</p>
  <div class="lffl-card">
    <div class="lffl-stage"><canvas class="lffl-canvas" data-role="canvas"></canvas></div>
    <div class="lffl-sliders">
      <div class="lffl-slider"><div class="row"><label>中间管道半高度 (截面积)</label><b><span data-value="throat">29</span> px</b></div><input data-param="throat" type="range" min="14" max="60" step="1" value="29"></div>
      <div class="lffl-slider"><div class="row"><label>初始流速 (v1)</label><b><span data-value="v1">3.0</span> m/s</b></div><input data-param="v1" type="range" min="0.5" max="8" step="0.1" value="3"></div>
      <div class="lffl-slider"><div class="row"><label>流体相对密度 (ρ)</label><b><span data-value="rho">0.9</span></b></div><input data-param="rho" type="range" min="0.3" max="2" step="0.05" value="0.9"></div>
    </div>
    <div class="lffl-eq"><strong>伯努利方程: P₁ + ½ρv₁² = P₂ + ½ρv₂²</strong><small>(连续性方程: v₁A₁ = v₂A₂ =&gt; 截面积越小，流速越大，压强越低)</small></div>
  </div>
  <script>
    (()=>{const root=document.currentScript.closest('.lffl-rescue');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';
    const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
    const inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i]));
    const values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n]));
    let raf=0,particles=[];
    function params(){return{throat:Number(inputs.throat.value),v1:Number(inputs.v1.value),rho:Number(inputs.rho.value)};}
    function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(560,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(300,Math.floor(r.height*devicePixelRatio));draw();}
    function init(){particles=Array.from({length:220},()=>({x:Math.random(),y:Math.random()*2-1}));}
    // half-height (in device px) of the pipe at normalized x (0..1)
    function halfH(xn,wideH,throatH){const a=0.34,b=0.46,c=0.54,d=0.66;if(xn<a||xn>d)return wideH;if(xn>=b&&xn<=c)return throatH;if(xn<b)return wideH+(throatH-wideH)*((xn-a)/(b-a));return throatH+(wideH-throatH)*((xn-c)/(d-c));}
    function draw(){const w=canvas.width,h=canvas.height,p=params();ctx.clearRect(0,0,w,h);ctx.fillStyle='#070b13';ctx.fillRect(0,0,w,h);
      const padX=40*devicePixelRatio,inW=w-padX*2,cy=h*0.62,wideH=h*0.16,throatH=Math.max(8*devicePixelRatio,p.throat*devicePixelRatio*(h/620));
      const xpx=xn=>padX+xn*inW;
      // velocities via continuity (A ∝ half-height); pressure via Bernoulli (display scale)
      const vAt=xn=>p.v1*(wideH/Math.max(2,halfH(xn,wideH,throatH)));
      const Pbase=140, kP=1.8;
      const Pat=xn=>{const v=vAt(xn);return Pbase - kP*p.rho/0.9*(v*v - p.v1*p.v1);};
      // pipe fill (water gradient)
      const grad=ctx.createLinearGradient(0,cy-wideH,0,cy+wideH);grad.addColorStop(0,'rgba(37,99,235,.55)');grad.addColorStop(1,'rgba(8,40,90,.85)');
      ctx.fillStyle=grad;ctx.beginPath();for(let i=0;i<=120;i++){const xn=i/120;ctx.lineTo(xpx(xn),cy-halfH(xn,wideH,throatH));}for(let i=120;i>=0;i--){const xn=i/120;ctx.lineTo(xpx(xn),cy+halfH(xn,wideH,throatH));}ctx.closePath();ctx.fill();
      // pipe walls
      ctx.strokeStyle='rgba(226,232,240,.92)';ctx.lineWidth=3*devicePixelRatio;ctx.lineJoin='round';
      ctx.beginPath();for(let i=0;i<=120;i++){const xn=i/120,y=cy-halfH(xn,wideH,throatH);i?ctx.lineTo(xpx(xn),y):ctx.moveTo(xpx(xn),y);}ctx.stroke();
      ctx.beginPath();for(let i=0;i<=120;i++){const xn=i/120,y=cy+halfH(xn,wideH,throatH);i?ctx.lineTo(xpx(xn),y):ctx.moveTo(xpx(xn),y);}ctx.stroke();
      // particles
      ctx.fillStyle='#67e8f9';particles.forEach(pt=>{const hh=halfH(pt.x,wideH,throatH),x=xpx(pt.x),y=cy+pt.y*hh*0.92;ctx.beginPath();ctx.arc(x,y,1.9*devicePixelRatio,0,Math.PI*2);ctx.fill();});
      // standpipe pressure gauges at inlet / throat / outlet
      const gauges=[{xn:0.18},{xn:0.5},{xn:0.82}];
      gauges.forEach(g=>{const gx=xpx(g.xn),pipeTop=cy-halfH(g.xn,wideH,throatH),P=Pat(g.xn);
        const tubeW=22*devicePixelRatio,top=18*devicePixelRatio,colH=Math.max(6*devicePixelRatio,Math.min(pipeTop-top-4*devicePixelRatio,(P/Pbase)*(pipeTop-top)));
        // tube outline
        ctx.strokeStyle='rgba(226,232,240,.55)';ctx.lineWidth=2*devicePixelRatio;ctx.strokeRect(gx-tubeW/2,top,tubeW,pipeTop-top);
        // liquid column rises from pipe up to colH
        ctx.fillStyle='#3b82f6';ctx.fillRect(gx-tubeW/2+2*devicePixelRatio,pipeTop-colH,tubeW-4*devicePixelRatio,colH);
        // label
        ctx.fillStyle='#fbbf24';ctx.font='900 '+(15*devicePixelRatio)+'px ui-monospace,monospace';ctx.textAlign='center';ctx.fillText('P='+Math.round(P),gx,pipeTop-colH-8*devicePixelRatio);
      });
      // velocity labels under sections
      ctx.fillStyle='#7aa2ff';ctx.font='900 '+(15*devicePixelRatio)+'px ui-monospace,monospace';ctx.textAlign='center';
      [{xn:0.18},{xn:0.5},{xn:0.82}].forEach(s=>{ctx.fillText('v='+vAt(s.xn).toFixed(1),xpx(s.xn),cy+halfH(s.xn,wideH,throatH)+24*devicePixelRatio);});
      values.throat.textContent=p.throat;values.v1.textContent=p.v1.toFixed(1);values.rho.textContent=p.rho.toFixed(1);
    }
    function step(){const p=params(),wideH=canvas.height*0.16,throatH=Math.max(8*devicePixelRatio,p.throat*devicePixelRatio*(canvas.height/620));particles.forEach(pt=>{const hh=halfH(pt.x,wideH,throatH),speed=p.v1*(wideH/Math.max(2,hh));pt.x+=speed*0.0014;if(pt.x>1){pt.x-=1;pt.y=Math.random()*2-1;}});}
    function loop(){step();draw();raf=requestAnimationFrame(loop);}
    root.addEventListener('input',draw);
    window.addEventListener('resize',resize);init();resize();raf=requestAnimationFrame(loop);
  })();
  </script>
</section>`;
}

function wavesRescueHtml(): string {
  return `
<section class="lfw-rescue" data-learnforge-widget="waves-demo">
  <style>
    .lfw-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--amber:#f59e0b;--green:#86efac;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 20% 10%,rgba(34,211,238,.16),transparent 30%),radial-gradient(circle at 80% 8%,rgba(134,239,172,.10),transparent 26%),linear-gradient(135deg,#07111f,#111827 58%,#06151c);border:0;padding:14px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfw-head{margin-bottom:8px}.lfw-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfw-head h2{margin:4px 0 4px;font-size:26px}.lfw-head p{margin:0;color:var(--muted);font-size:13px;line-height:1.6}
    .lfw-grid{display:grid;grid-template-columns:250px minmax(0,1fr);gap:10px;min-height:0}.lfw-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);padding:12px;overflow:auto}.lfw-control{display:grid;gap:4px;margin-bottom:8px}.lfw-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lfw-control input{width:100%;accent-color:var(--cyan)}
    .lfw-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px}.lfw-actions button{min-height:34px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lfw-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lfw-stage{min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}.lfw-canvas{display:block;width:100%;height:100%}
    .lfw-readouts{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}.lfw-metric{border:1px solid rgba(255,255,255,.11);border-radius:10px;background:rgba(255,255,255,.06);padding:8px}.lfw-metric small{display:block;color:var(--muted);font-size:11px}.lfw-metric strong{font-size:16px}
    @media(max-width:840px){.lfw-rescue{height:auto;overflow:visible}.lfw-grid{grid-template-columns:1fr}.lfw-canvas{height:380px}.lfw-stage{min-height:380px}}
  </style>
  <div class="lfw-head"><div class="lfw-kicker">Wave Motion Lab</div><h2>波动与振动动态演示</h2><p>调节振幅、频率、波长和阻尼，观察波的传播、叠加和衰减。拖动画布改变观察点。</p></div>
  <div class="lfw-grid">
    <aside class="lfw-panel"><h3>波形参数</h3><div class="lfw-control"><label>振幅 <span data-value="amp">1.0</span></label><input data-param="amp" type="range" min="0.2" max="2.5" step="0.1" value="1"></div><div class="lfw-control"><label>频率 <span data-value="freq">1.0</span></label><input data-param="freq" type="range" min="0.3" max="3" step="0.1" value="1"></div><div class="lfw-control"><label>阻尼 <span data-value="damp">0.02</span></label><input data-param="damp" type="range" min="0" max="0.15" step="0.005" value="0.02"></div><div class="lfw-actions"><button type="button" data-action="play">暂停/播放</button><button class="secondary" type="button" data-action="reset">重置</button></div><div class="lfw-readouts"><div class="lfw-metric"><small>波长</small><strong data-metric="wavelength">2pi</strong></div><div class="lfw-metric"><small>周期</small><strong data-metric="period">2pi</strong></div><div class="lfw-metric"><small>观察点 y</small><strong data-metric="y">0.00</strong></div><div class="lfw-metric"><small>相位</small><strong data-metric="phase">0.00</strong></div></div></aside>
    <div class="lfw-stage"><canvas class="lfw-canvas" data-role="canvas"></canvas></div>
  </div>
  <script>
    (()=>{const root=document.currentScript.closest('.lfw-rescue');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';
    const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
    const inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i]));
    const values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n]));
    const metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n]));
    let raf=0,t=0,last=0,running=true,observeX=0;
    const fmt=(n,d=2)=>Number(n).toFixed(d).replace(/-0\\.00|\\.00$/g,'0');
    function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(500,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(300,Math.floor(r.height*devicePixelRatio));draw();}
    function draw(){const w=canvas.width,h=canvas.height,p=params();values.amp.textContent=fmt(p.amp,1);values.freq.textContent=fmt(p.freq,1);values.damp.textContent=fmt(p.damp,3);
      metrics.wavelength.textContent=fmt((2*Math.PI)/p.freq);metrics.period.textContent=fmt((2*Math.PI)/p.freq);
      const yAtObserve=p.amp*Math.sin(p.freq*observeX-t)*Math.exp(-p.damp*Math.abs(observeX));
      metrics.y.textContent=fmt(yAtObserve);metrics.phase.textContent=fmt(t%(2*Math.PI));
      ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);
      const cx=w/2,cy=h/2,xScale=w/14,xMin=-7,xMax=7,toX=v=>cx+v*xScale,toY=v=>cy-v*(h*.14);
      ctx.strokeStyle='rgba(148,163,184,.14)';ctx.lineWidth=1*devicePixelRatio;
      for(let y=cy-h*.14*2.5;y<=cy+h*.14*2.5;y+=h*.14){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
      ctx.strokeStyle='rgba(226,232,240,.45)';ctx.lineWidth=2*devicePixelRatio;ctx.beginPath();ctx.moveTo(0,cy);ctx.lineTo(w,cy);ctx.stroke();ctx.beginPath();ctx.moveTo(cx,0);ctx.lineTo(cx,h);ctx.stroke();
      ctx.strokeStyle='#22d3ee';ctx.lineWidth=3.5*devicePixelRatio;ctx.lineCap='round';ctx.beginPath();
      for(let i=0;i<=w;i+=2){const worldX=(i-cx)/xScale,wave=p.amp*Math.sin(p.freq*worldX-t)*Math.exp(-p.damp*Math.abs(worldX));const y=toY(wave);if(i===0)ctx.moveTo(i,y);else ctx.lineTo(i,y);}ctx.stroke();
      ctx.fillStyle='#86efac';ctx.beginPath();const ox=cx+observeX*xScale,oy=toY(yAtObserve);ctx.arc(ox,oy,8*devicePixelRatio,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle='#86efac';ctx.setLineDash([4,6]);ctx.lineWidth=1.5*devicePixelRatio;ctx.beginPath();ctx.moveTo(ox,oy);ctx.lineTo(ox,cy);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#e5e7eb';ctx.font=(13*devicePixelRatio)+'px monospace';ctx.fillText('('+fmt(observeX)+', '+fmt(yAtObserve)+')',ox+10,oy-10);
    }
    function params(){return{amp:Number(inputs.amp.value),freq:Number(inputs.freq.value),damp:Number(inputs.damp.value)};}
    function loop(now){if(!last)last=now;const dt=Math.min(.03,(now-last)/1000);last=now;if(running)t+=dt*2.5;draw();raf=requestAnimationFrame(loop);}
    root.addEventListener('input',()=>draw());
    root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='play')running=!running;if(a==='reset'){t=0;observeX=0;draw();}});
    canvas.addEventListener('pointerdown',e=>{const r=canvas.getBoundingClientRect();observeX=((e.clientX-r.left)*devicePixelRatio/canvas.width)*14-7;draw();});
    canvas.addEventListener('pointermove',e=>{if(e.buttons!==1)return;const r=canvas.getBoundingClientRect();observeX=((e.clientX-r.left)*devicePixelRatio/canvas.width)*14-7;draw();});
    window.addEventListener('resize',resize);resize();raf=requestAnimationFrame(loop);
  })();
  </script>
</section>`;
}

function forcesRescueHtml(): string {
  return `
<section class="lff-rescue" data-learnforge-widget="forces-demo">
  <style>
    .lff-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--green:#86efac;--amber:#f59e0b;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 20% 10%,rgba(34,211,238,.16),transparent 28%),linear-gradient(135deg,#07111f,#111827 58%,#06151c);border:0;padding:14px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lff-head{margin-bottom:8px}.lff-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lff-head h2{margin:4px 0 4px;font-size:26px}.lff-head p{margin:0;color:var(--muted);font-size:13px}
    .lff-grid{display:grid;grid-template-columns:260px minmax(0,1fr);gap:10px;min-height:0}.lff-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);padding:12px;overflow:auto}.lff-control{display:grid;gap:4px;margin-bottom:8px}.lff-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lff-control input{width:100%;accent-color:var(--cyan)}
    .lff-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px}.lff-actions button{min-height:34px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lff-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lff-stage{min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}.lff-canvas{display:block;width:100%;height:100%}
    .lff-readouts{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}.lff-metric{border:1px solid rgba(255,255,255,.11);border-radius:10px;background:rgba(255,255,255,.06);padding:8px}.lff-metric small{display:block;color:var(--muted);font-size:11px}.lff-metric strong{font-size:16px}
    @media(max-width:840px){.lff-rescue{height:auto;overflow:visible}.lff-grid{grid-template-columns:1fr}.lff-canvas{height:380px}.lff-stage{min-height:380px}}
  </style>
  <div class="lff-head"><div class="lff-kicker">Newtonian Mechanics Lab</div><h2>力与运动动态演示</h2><p>对物体施加水平力，观察速度、位移和加速度的实时变化。拖动物体可改变初始位置。</p></div>
  <div class="lff-grid">
    <aside class="lff-panel"><h3>力学参数</h3><div class="lff-control"><label>质量 m <span data-value="mass">2.0 kg</span></label><input data-param="mass" type="range" min="0.5" max="8" step="0.1" value="2"></div><div class="lff-control"><label>施加力 F <span data-value="force">5.0 N</span></label><input data-param="force" type="range" min="-10" max="10" step="0.1" value="5"></div><div class="lff-control"><label>摩擦力系数 <span data-value="friction">0.15</span></label><input data-param="friction" type="range" min="0" max="0.6" step="0.01" value="0.15"></div><div class="lff-actions"><button type="button" data-action="play">暂停/播放</button><button class="secondary" type="button" data-action="reset">重置</button></div><div class="lff-readouts"><div class="lff-metric"><small>加速度</small><strong data-metric="accel">0.00</strong></div><div class="lff-metric"><small>速度</small><strong data-metric="velocity">0.00</strong></div><div class="lff-metric"><small>位移</small><strong data-metric="pos">0.00</strong></div><div class="lff-metric"><small>时间</small><strong data-metric="time">0.00</strong></div></div></aside>
    <div class="lff-stage"><canvas class="lff-canvas" data-role="canvas"></canvas></div>
  </div>
  <script>
    (()=>{const root=document.currentScript.closest('.lff-rescue');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';
    const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
    const inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i]));
    const values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n]));
    const metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n]));
    let raf=0,t=0,last=0,running=true,pos=0,vel=0,accel=0;
    const fmt=(n,d=2)=>Number(n).toFixed(d).replace(/-0\\.00|\\.00$/g,'0');
    function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(500,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(300,Math.floor(r.height*devicePixelRatio));draw();}
    function draw(){const w=canvas.width,h=canvas.height,p=params();values.mass.textContent=fmt(p.mass,1)+' kg';values.force.textContent=fmt(p.force,1)+' N';values.friction.textContent=fmt(p.friction);
      const frictionForce=-Math.sign(vel||p.force)*p.friction*9.8*p.mass*(Math.abs(vel)>0.01?1:Math.min(1,Math.abs(p.force)/(p.friction*9.8*p.mass+0.001)));
      accel=(p.force+frictionForce)/p.mass;metrics.accel.textContent=fmt(accel)+' m/s²';metrics.velocity.textContent=fmt(vel)+' m/s';metrics.pos.textContent=fmt(pos)+' m';metrics.time.textContent=fmt(t)+' s';
      ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);
      const groundY=h*.62,groundW=w-100*devicePixelRatio,startX=80*devicePixelRatio,blockW=60*devicePixelRatio,blockH=48*devicePixelRatio;
      const blockX=startX+pos*((groundW-blockW)/8);
      ctx.fillStyle='rgba(148,163,184,.18)';ctx.fillRect(startX,groundY,groundW,6*devicePixelRatio);
      ctx.fillStyle='rgba(148,163,184,.08)';for(let x=startX;x<startX+groundW;x+=60*devicePixelRatio){ctx.fillRect(x,groundY+10*devicePixelRatio,1,14*devicePixelRatio);}
      const g=ctx.createLinearGradient(0,groundY-blockH,0,groundY);g.addColorStop(0,'#67e8f9');g.addColorStop(1,'#2563eb');
      ctx.fillStyle=g;ctx.beginPath();const r=10*devicePixelRatio;ctx.moveTo(blockX+r,groundY-blockH);ctx.lineTo(blockX+blockW-r,groundY-blockH);ctx.arcTo(blockX+blockW,groundY-blockH,blockX+blockW,groundY,r);ctx.lineTo(blockX+blockW,groundY);ctx.lineTo(blockX,groundY);ctx.lineTo(blockX,groundY-blockH+r);ctx.arcTo(blockX,groundY-blockH,blockX+r,groundY-blockH,r);ctx.closePath();ctx.fill();
      ctx.fillStyle='#04111d';ctx.font=(16*devicePixelRatio)+'px sans-serif';ctx.textAlign='center';ctx.fillText('m='+fmt(p.mass,1),blockX+blockW/2,groundY-blockH/2+6*devicePixelRatio);
      if(Math.abs(p.force)>0.01){const arrowLen=p.force*14*devicePixelRatio,arrowDir=Math.sign(p.force),arrowX=blockX+blockW/2;
        ctx.strokeStyle='#f59e0b';ctx.fillStyle='#f59e0b';ctx.lineWidth=3*devicePixelRatio;ctx.beginPath();ctx.moveTo(arrowX,groundY-blockH-20*devicePixelRatio);ctx.lineTo(arrowX+arrowDir*arrowLen,groundY-blockH-20*devicePixelRatio);ctx.stroke();
        ctx.beginPath();ctx.moveTo(arrowX+arrowDir*arrowLen,groundY-blockH-20*devicePixelRatio);ctx.lineTo(arrowX+arrowDir*(arrowLen-10*devicePixelRatio),groundY-blockH-26*devicePixelRatio);ctx.lineTo(arrowX+arrowDir*(arrowLen-10*devicePixelRatio),groundY-blockH-14*devicePixelRatio);ctx.closePath();ctx.fill();
        ctx.fillStyle='#f59e0b';ctx.font=(13*devicePixelRatio)+'px monospace';ctx.textAlign='center';ctx.fillText('F='+fmt(p.force,1)+'N',arrowX+arrowDir*arrowLen/2,groundY-blockH-28*devicePixelRatio);
      }
      ctx.fillStyle='#e5e7eb';ctx.font=(12*devicePixelRatio)+'px monospace';ctx.textAlign='left';ctx.fillText('v='+fmt(vel)+' m/s',startX,groundY+30*devicePixelRatio);
    }
    function params(){return{mass:Number(inputs.mass.value),force:Number(inputs.force.value),friction:Number(inputs.friction.value)};}
    function loop(now){if(!last)last=now;const dt=Math.min(.025,(now-last)/1000);last=now;if(running){t+=dt;vel+=accel*dt;pos+=vel*dt;pos=Math.max(-1.5,Math.min(8,pos));if(Math.abs(pos)>=7.9&&Math.abs(vel)<0.1)vel=0;}draw();raf=requestAnimationFrame(loop);}
    root.addEventListener('input',()=>draw());
    root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='play')running=!running;if(a==='reset'){t=0;pos=0;vel=0;draw();}});
    canvas.addEventListener('pointerdown',e=>{const r=canvas.getBoundingClientRect(),cx=(e.clientX-r.left)*devicePixelRatio/canvas.width;pos=Math.max(-1.5,Math.min(8,(cx-0.2)*8));vel=0;draw();});
    window.addEventListener('resize',resize);resize();raf=requestAnimationFrame(loop);
  })();
  </script>
</section>`;
}

function geometryRescueHtml(): string {
  return `
<section class="lfg-rescue" data-learnforge-widget="geometry-demo">
  <style>
    .lfg-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--amber:#f59e0b;--green:#86efac;--rose:#fb7185;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 20% 10%,rgba(34,211,238,.16),transparent 28%),linear-gradient(135deg,#07111f,#111827 58%,#06151c);border:0;padding:14px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfg-head{margin-bottom:8px}.lfg-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfg-head h2{margin:4px 0 4px;font-size:26px}.lfg-head p{margin:0;color:var(--muted);font-size:13px}
    .lfg-grid{display:grid;grid-template-columns:250px minmax(0,1fr);gap:10px;min-height:0}.lfg-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);padding:12px;overflow:auto}.lfg-control{display:grid;gap:4px;margin-bottom:8px}.lfg-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lfg-control input,.lfg-control select{width:100%;accent-color:var(--cyan)}.lfg-control select{height:34px;border:1px solid var(--line);border-radius:10px;background:#111827;color:var(--ink);font-weight:900;padding:0 10px}
    .lfg-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}.lfg-actions button{min-height:34px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lfg-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lfg-stage{min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}.lfg-canvas{display:block;width:100%;height:100%}
    .lfg-readouts{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}.lfg-metric{border:1px solid rgba(255,255,255,.11);border-radius:10px;background:rgba(255,255,255,.06);padding:8px}.lfg-metric small{display:block;color:var(--muted);font-size:11px}.lfg-metric strong{font-size:16px}
    @media(max-width:840px){.lfg-rescue{height:auto;overflow:visible}.lfg-grid{grid-template-columns:1fr}.lfg-canvas{height:380px}.lfg-stage{min-height:380px}}
  </style>
  <div class="lfg-head"><div class="lfg-kicker">Geometry Visual Lab</div><h2>几何图形交互演示</h2><p>调节参数实时观察三角形、圆形、多边形等几何形状的变化与性质。</p></div>
  <div class="lfg-grid">
    <aside class="lfg-panel"><h3>图形参数</h3><div class="lfg-control"><label>形状 <span data-value="shape">三角形</span></label><select data-param="shape"><option value="triangle">三角形</option><option value="circle">圆形</option><option value="square">正方形</option></select></div><div class="lfg-control"><label>参数A <span data-value="paramA">1.0</span></label><input data-param="paramA" type="range" min="0.3" max="2.5" step="0.05" value="1"></div><div class="lfg-control"><label>参数B <span data-value="paramB">0.7</span></label><input data-param="paramB" type="range" min="0.2" max="2" step="0.05" value="0.7"></div><div class="lfg-actions"><button type="button" data-action="play">旋转动画</button><button class="secondary" type="button" data-action="reset">重置</button></div><div class="lfg-readouts"><div class="lfg-metric"><small>面积</small><strong data-metric="area">0.00</strong></div><div class="lfg-metric"><small>周长</small><strong data-metric="perimeter">0.00</strong></div><div class="lfg-metric"><small>角度和</small><strong data-metric="angleSum">180°</strong></div><div class="lfg-metric"><small>旋转角</small><strong data-metric="rotation">0°</strong></div></div></aside>
    <div class="lfg-stage"><canvas class="lfg-canvas" data-role="canvas"></canvas></div>
  </div>
  <script>
    (()=>{const root=document.currentScript.closest('.lfg-rescue');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';
    const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
    const inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i]));
    const values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n]));
    const metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n]));
    let raf=0,t=0,last=0,rotating=false,rotation=0;
    const fmt=(n,d=2)=>Number(n).toFixed(d).replace(/-0\\.00|\\.00$/g,'0');
    function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(500,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(300,Math.floor(r.height*devicePixelRatio));draw();}
    function drawShape(cx,cy,scale,rot){
      const shape=inputs.shape.value,a=Number(inputs.paramA.value),b=Number(inputs.paramB.value);
      ctx.save();ctx.translate(cx,cy);ctx.rotate(rot);
      if(shape==='triangle'){const points=[{x:0,y:-scale*0.7*a},{x:-scale*0.6*b,y:scale*0.5*a},{x:scale*0.6*b,y:scale*0.5*a}];
        ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);points.forEach(p=>ctx.lineTo(p.x,p.y));ctx.closePath();ctx.fill();ctx.stroke();
        const area=(scale*a*scale*b*1.2*0.5)/(120*120);const perimeter=(Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y)+Math.hypot(points[1].x-points[2].x,points[1].y-points[2].y)+Math.hypot(points[2].x-points[0].x,points[2].y-points[0].y))/(120);
        return{area:fmt(area*300),perimeter:fmt(perimeter*300),angleSum:'180°'};}
      else if(shape==='circle'){ctx.beginPath();ctx.arc(0,0,scale*0.45*a,0,Math.PI*2);ctx.fill();ctx.stroke();return{area:fmt(Math.PI*a*a*0.2),perimeter:fmt(2*Math.PI*a*0.45),angleSum:'360°'};}
      else{const s=scale*0.45*a;ctx.beginPath();ctx.rect(-s,-s,s*2,s*2);ctx.fill();ctx.stroke();return{area:fmt(4*a*a*0.2),perimeter:fmt(8*a*0.45),angleSum:'360°'};}
    }
    function draw(){const w=canvas.width,h=canvas.height,cx=w/2,cy=h/2,scale=Math.min(w,h)*0.32;ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);
      ctx.strokeStyle='rgba(148,163,184,.10)';ctx.lineWidth=1*devicePixelRatio;const gs=50*devicePixelRatio;for(let x=gs;x<w;x+=gs){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}for(let y=gs;y<h;y+=gs){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
      ctx.fillStyle='rgba(34,211,238,.18)';ctx.strokeStyle='#22d3ee';ctx.lineWidth=3*devicePixelRatio;
      const result=drawShape(cx,cy,scale,rotation);ctx.restore();
      values.shape.textContent=inputs.shape.value==='triangle'?'三角形':inputs.shape.value==='circle'?'圆形':'正方形';
      values.paramA.textContent=fmt(Number(inputs.paramA.value));values.paramB.textContent=fmt(Number(inputs.paramB.value));
      metrics.area.textContent=result.area;metrics.perimeter.textContent=result.perimeter;metrics.angleSum.textContent=result.angleSum;metrics.rotation.textContent=fmt(rotation*180/Math.PI%360)+'°';
    }
    function loop(now){if(!last)last=now;const dt=Math.min(.025,(now-last)/1000);last=now;if(rotating)rotation+=(Number(inputs.paramA.value)*0.8)*dt;draw();raf=requestAnimationFrame(loop);}
    root.addEventListener('input',()=>draw());
    root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='play')rotating=!rotating;if(a==='reset'){rotation=0;rotating=false;draw();}});
    canvas.addEventListener('pointerdown',e=>{const r=canvas.getBoundingClientRect(),mx=(e.clientX-r.left)*devicePixelRatio/canvas.width;rotation=(mx-0.5)*Math.PI*2;draw();});
    window.addEventListener('resize',resize);resize();raf=requestAnimationFrame(loop);
  })();
  </script>
</section>`;
}

function probabilityRescueHtml(): string {
  return `
<section class="lfp-rescue" data-learnforge-widget="probability-demo">
  <style>
    .lfp-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--amber:#f59e0b;--green:#86efac;--rose:#fb7185;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 20% 10%,rgba(34,211,238,.16),transparent 28%),linear-gradient(135deg,#07111f,#111827 58%,#06151c);border:0;padding:14px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfp-head{margin-bottom:8px}.lfp-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfp-head h2{margin:4px 0 4px;font-size:26px}.lfp-head p{margin:0;color:var(--muted);font-size:13px}
    .lfp-grid{display:grid;grid-template-columns:250px minmax(0,1fr);gap:10px;min-height:0}.lfp-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);padding:12px;overflow:auto}.lfp-control{display:grid;gap:4px;margin-bottom:8px}.lfp-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lfp-control input{width:100%;accent-color:var(--cyan)}
    .lfp-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}.lfp-actions button{min-height:34px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lfp-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lfp-stage{min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}.lfp-canvas{display:block;width:100%;height:100%}
    .lfp-readouts{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}.lfp-metric{border:1px solid rgba(255,255,255,.11);border-radius:10px;background:rgba(255,255,255,.06);padding:8px}.lfp-metric small{display:block;color:var(--muted);font-size:11px}.lfp-metric strong{font-size:16px}
    @media(max-width:840px){.lfp-rescue{height:auto;overflow:visible}.lfp-grid{grid-template-columns:1fr}.lfp-canvas{height:380px}.lfp-stage{min-height:380px}}
  </style>
  <div class="lfp-head"><div class="lfp-kicker">Probability & Statistics Lab</div><h2>概率与统计交互演示</h2><p>模拟随机事件，观察概率分布和统计特征随样本量增加的变化。</p></div>
  <div class="lfp-grid">
    <aside class="lfp-panel"><h3>实验参数</h3><div class="lfp-control"><label>成功概率 p <span data-value="prob">0.50</span></label><input data-param="prob" type="range" min="0.05" max="0.95" step="0.01" value="0.5"></div><div class="lfp-control"><label>模拟速度 <span data-value="speed">中速</span></label><input data-param="speed" type="range" min="1" max="4" step="1" value="2"></div><div class="lfp-actions"><button type="button" data-action="play">暂停/播放</button><button class="secondary" type="button" data-action="reset">重置实验</button></div><div class="lfp-readouts"><div class="lfp-metric"><small>理论概率</small><strong data-metric="theory">0.500</strong></div><div class="lfp-metric"><small>实验频率</small><strong data-metric="empirical">0.000</strong></div><div class="lfp-metric"><small>试验次数</small><strong data-metric="trials">0</strong></div><div class="lfp-metric"><small>成功次数</small><strong data-metric="successes">0</strong></div></div></aside>
    <div class="lfp-stage"><canvas class="lfp-canvas" data-role="canvas"></canvas></div>
  </div>
  <script>
    (()=>{const root=document.currentScript.closest('.lfp-rescue');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';
    const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
    const inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i]));
    const values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n]));
    const metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n]));
    let raf=0,last=0,lastEmit=0,running=true,trials=0,successes=0,history=[];
    const fmt=(n,d=3)=>Number(n).toFixed(d).replace(/0+$/,'').replace(/\\.$/,'');
    function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(500,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(300,Math.floor(r.height*devicePixelRatio));draw();}
    function draw(){const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);
      const p=Number(inputs.prob.value);values.prob.textContent=fmt(p,2);values.speed.textContent=['慢速','中速','快速','高速'][Number(inputs.speed.value)-1];
      metrics.theory.textContent=fmt(p);metrics.empirical.textContent=fmt(trials>0?successes/trials:0);metrics.trials.textContent=trials;metrics.successes.textContent=successes;
      if(history.length>1){const maxH=Math.max(...history.map(h=>h.empirical),p*1.2),padX=60*devicePixelRatio,padY=40*devicePixelRatio,plotW=w-padX*2,plotH=h-padY*2;
        ctx.strokeStyle='rgba(148,163,184,.12)';ctx.lineWidth=1*devicePixelRatio;
        for(let i=0;i<=4;i++){const y=padY+plotH*(1-i/4);ctx.beginPath();ctx.moveTo(padX,y);ctx.lineTo(w-padX,y);ctx.stroke();}
        ctx.strokeStyle='rgba(34,211,238,.5)';ctx.setLineDash([6,8]);ctx.lineWidth=2*devicePixelRatio;const theoryY=padY+plotH*(1-p/maxH);ctx.beginPath();ctx.moveTo(padX,theoryY);ctx.lineTo(w-padX,theoryY);ctx.stroke();ctx.setLineDash([]);
        ctx.fillStyle='#22d3ee';ctx.font=(12*devicePixelRatio)+'px monospace';ctx.fillText('理论 p='+fmt(p),w-padX-80*devicePixelRatio,theoryY-6*devicePixelRatio);
        ctx.strokeStyle='#86efac';ctx.lineWidth=2.5*devicePixelRatio;ctx.beginPath();
        history.forEach((h,i)=>{const x=padX+(i/(history.length-1))*plotW,y=padY+plotH*(1-h.empirical/maxH);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.stroke();
        if(history.length>0){const lastH=history[history.length-1];const lx=padX+plotW,ly=padY+plotH*(1-lastH.empirical/maxH);ctx.fillStyle='#86efac';ctx.beginPath();ctx.arc(lx,ly,5*devicePixelRatio,0,Math.PI*2);ctx.fill();
          ctx.fillText('经验 '+(trials>0?fmt(successes/trials):'0'),lx-70*devicePixelRatio,ly-8*devicePixelRatio);}
        ctx.fillStyle='#aab6ca';ctx.font=(11*devicePixelRatio)+'px monospace';ctx.fillText('N='+trials,padX,padY-10*devicePixelRatio);
      }
    }
    function loop(now){if(!last)last=now;const dt=Math.min(.025,(now-last)/1000);last=now;if(running&&now-lastEmit>400/Math.pow(2,Number(inputs.speed.value))){lastEmit=now;const p=Number(inputs.prob.value);trials++;if(Math.random()<p)successes++;if(trials%3===0)history.push({empirical:successes/trials});if(history.length>200)history.shift();draw();}raf=requestAnimationFrame(loop);}
    root.addEventListener('input',()=>draw());
    root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='play')running=!running;if(a==='reset'){trials=0;successes=0;history=[];draw();}});
    window.addEventListener('resize',resize);resize();raf=requestAnimationFrame(loop);
  })();
  </script>
</section>`;
}

function calculusRescueHtml(): string {
  return `
<section class="lfc-rescue" data-learnforge-widget="calculus-demo">
  <style>
    .lfc-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--rose:#fb7185;--green:#86efac;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 20% 10%,rgba(34,211,238,.16),transparent 28%),linear-gradient(135deg,#07111f,#111827 58%,#06151c);border:0;padding:14px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfc-head{margin-bottom:8px}.lfc-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfc-head h2{margin:4px 0 4px;font-size:26px}.lfc-head p{margin:0;color:var(--muted);font-size:13px}
    .lfc-grid{display:grid;grid-template-columns:250px minmax(0,1fr);gap:10px;min-height:0}.lfc-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);padding:12px;overflow:auto}.lfc-control{display:grid;gap:4px;margin-bottom:8px}.lfc-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lfc-control input,.lfc-control select{width:100%;accent-color:var(--cyan)}.lfc-control select{height:34px;border:1px solid var(--line);border-radius:10px;background:#111827;color:var(--ink);font-weight:900;padding:0 10px}
    .lfc-actions{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}.lfc-actions button{min-height:34px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}.lfc-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lfc-stage{min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}.lfc-canvas{display:block;width:100%;height:100%}
    .lfc-readouts{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}.lfc-metric{border:1px solid rgba(255,255,255,.11);border-radius:10px;background:rgba(255,255,255,.06);padding:8px}.lfc-metric small{display:block;color:var(--muted);font-size:11px}.lfc-metric strong{font-size:16px}
    @media(max-width:840px){.lfc-rescue{height:auto;overflow:visible}.lfc-grid{grid-template-columns:1fr}.lfc-canvas{height:380px}.lfc-stage{min-height:380px}}
  </style>
  <div class="lfc-head"><div class="lfc-kicker">Calculus Visual Lab</div><h2>微积分可视化演示</h2><p>观察函数曲线、切线斜率和积分面积。拖拽观察点看导数如何随 x 变化。</p></div>
  <div class="lfc-grid">
    <aside class="lfc-panel"><h3>函数参数</h3><div class="lfc-control"><label>函数类型 <span data-value="fnType">x²</span></label><select data-param="fnType"><option value="x2">f(x) = x²</option><option value="x3">f(x) = x³/4</option><option value="sin">f(x) = sin(x)</option></select></div><div class="lfc-control"><label>观察点 x <span data-value="obsX">0.80</span></label><input data-param="obsX" type="range" min="-2.5" max="2.5" step="0.02" value="0.8"></div><div class="lfc-actions"><button type="button" data-action="play">自动移动</button><button class="secondary" type="button" data-action="reset">重置</button></div><div class="lfc-readouts"><div class="lfc-metric"><small>f(x)</small><strong data-metric="fx">0.00</strong></div><div class="lfc-metric"><small>f'(x)</small><strong data-metric="deriv">0.00</strong></div><div class="lfc-metric"><small>积分 [-1,x]</small><strong data-metric="integr">0.00</strong></div></div></aside>
    <div class="lfc-stage"><canvas class="lfc-canvas" data-role="canvas"></canvas></div>
  </div>
  <script>
    (()=>{const root=document.currentScript.closest('.lfc-rescue');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';
    const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
    const inputs=Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i=>[i.dataset.param,i]));
    const values=Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n=>[n.dataset.value,n]));
    const metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n]));
    let raf=0,t=0,last=0,autoPlay=false;
    const fmt=(n,d=2)=>Number(n).toFixed(d).replace(/-0\\.00|\\.00$/g,'0');
    function f(x,type){if(type==='x2')return x*x;if(type==='x3')return x*x*x/4;return Math.sin(x);}
    function df(x,type){const h=0.0001;return (f(x+h,type)-f(x-h,type))/(2*h);}
    function integral(a,b,type,steps=80){let sum=0;const dx=(b-a)/steps;for(let i=0;i<steps;i++){const x=a+i*dx;sum+=f(x,type)*dx;}return sum;}
    function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(500,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(300,Math.floor(r.height*devicePixelRatio));draw();}
    function draw(){const w=canvas.width,h=canvas.height,type=inputs.fnType.value,obsX=Number(inputs.obsX.value);
      values.fnType.textContent=type==='x2'?'x²':type==='x3'?'x³/4':'sin(x)';values.obsX.textContent=fmt(obsX);
      const fx=f(obsX,type),deriv=df(obsX,type),integr=integral(-1,Math.min(obsX,2.5),type);
      metrics.fx.textContent=fmt(fx);metrics.deriv.textContent=fmt(deriv);metrics.integr.textContent=fmt(integr);
      ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);
      const cx=w/2,cy=h/2,xScale=w/5.5,xMin=-2.8,xMax=2.8,toX=v=>cx+v*xScale,toY=v=>cy-v*(h*.15);
      ctx.strokeStyle='rgba(148,163,184,.12)';ctx.lineWidth=1*devicePixelRatio;
      for(let y=cy-h*.15*3;y<=cy+h*.15*3;y+=h*.15){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
      ctx.strokeStyle='rgba(226,232,240,.45)';ctx.lineWidth=2*devicePixelRatio;ctx.beginPath();ctx.moveTo(0,cy);ctx.lineTo(w,cy);ctx.stroke();ctx.beginPath();ctx.moveTo(cx,0);ctx.lineTo(cx,h);ctx.stroke();
      ctx.strokeStyle='#22d3ee';ctx.lineWidth=3*devicePixelRatio;ctx.beginPath();
      for(let i=0;i<=w;i+=2){const worldX=xMin+(i/w)*(xMax-xMin),fy=f(worldX,type);const y=toY(fy);if(i===0)ctx.moveTo(i,y);else ctx.lineTo(i,y);}ctx.stroke();
      const ox=toX(obsX),oy=toY(fx),tangentLen=80*devicePixelRatio;
      ctx.strokeStyle='#fb7185';ctx.lineWidth=2.5*devicePixelRatio;ctx.setLineDash([4,5]);
      ctx.beginPath();ctx.moveTo(ox-tangentLen,oy-deriv*tangentLen/xScale*h*.15);ctx.lineTo(ox+tangentLen,oy+deriv*tangentLen/xScale*h*.15);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#86efac';ctx.beginPath();ctx.arc(ox,oy,8*devicePixelRatio,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle='#86efac';ctx.lineWidth=1.5*devicePixelRatio;ctx.setLineDash([2,4]);ctx.beginPath();ctx.moveTo(ox,oy);ctx.lineTo(ox,cy);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#e5e7eb';ctx.font=(13*devicePixelRatio)+'px monospace';ctx.fillText('f\\'('+fmt(obsX)+')='+fmt(deriv),ox+10*devicePixelRatio,oy-12*devicePixelRatio);
    }
    function loop(now){if(!last)last=now;const dt=Math.min(.025,(now-last)/1000);last=now;if(autoPlay){inputs.obsX.value=fmt(1.5*Math.sin(t*.8));t+=dt*2;}draw();raf=requestAnimationFrame(loop);}
    root.addEventListener('input',()=>{autoPlay=false;draw();});
    root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='play'){autoPlay=!autoPlay;t=0;}if(a==='reset'){autoPlay=false;inputs.obsX.value=0.8;draw();}});
    canvas.addEventListener('pointerdown',e=>{autoPlay=false;const r=canvas.getBoundingClientRect();inputs.obsX.value=fmt(((e.clientX-r.left)*devicePixelRatio/canvas.width)*5.5-2.8);draw();});
    canvas.addEventListener('pointermove',e=>{if(e.buttons!==1)return;const r=canvas.getBoundingClientRect();inputs.obsX.value=fmt(((e.clientX-r.left)*devicePixelRatio/canvas.width)*5.5-2.8);draw();});
    window.addEventListener('resize',resize);resize();raf=requestAnimationFrame(loop);
  })();
  </script>
</section>`;
}

function hashRescueHtml(): string {
  return `
<section class="lfh-rescue" data-learnforge-widget="hash-demo">
  <style>
    .lfh-rescue{--ink:#f8fafc;--muted:#aab6ca;--line:rgba(255,255,255,.15);--cyan:#22d3ee;--amber:#f59e0b;--rose:#fb7185;--green:#86efac;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;height:100%;min-height:0;color:var(--ink);background:radial-gradient(circle at 20% 10%,rgba(34,211,238,.16),transparent 28%),linear-gradient(135deg,#07111f,#111827 58%,#06151c);border:0;padding:14px;box-sizing:border-box;overflow:auto;display:grid;grid-template-rows:auto minmax(0,1fr)}
    .lfh-head{margin-bottom:8px}.lfh-kicker{font-size:12px;color:var(--cyan);font-weight:950;letter-spacing:.12em;text-transform:uppercase}.lfh-head h2{margin:4px 0 4px;font-size:26px}.lfh-head p{margin:0;color:var(--muted);font-size:13px}
    .lfh-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:10px;min-height:0}.lfh-stage{min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}.lfh-canvas{display:block;width:100%;height:100%}
    .lfh-bar{display:flex;align-items:center;gap:10px;padding:8px 12px;border-bottom:1px solid var(--line)}.lfh-bar button{min-height:32px;border:1px solid var(--line);border-radius:8px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer;padding:0 12px}.lfh-bar button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lfh-bar select{height:34px;border:1px solid var(--line);border-radius:8px;background:#111827;color:var(--ink);font-weight:900;padding:0 10px}.lfh-bar span{color:var(--muted);font-size:12px;font-weight:900}
    @media(max-width:840px){.lfh-rescue{height:auto;overflow:visible}.lfh-canvas{height:380px}.lfh-stage{min-height:380px}}
  </style>
  <div class="lfh-head"><div class="lfh-kicker">Data Structures Lab</div><h2>哈希表冲突可视化</h2><p>观察不同 key 如何映射到 bucket，冲突如何发生以及链地址/线性探测如何解决冲突。</p></div>
  <div class="lfh-bar"><button type="button" data-action="add">插入 Key</button><button class="secondary" type="button" data-action="reset">重置</button><select data-param="strategy"><option value="chain">链地址法</option><option value="linear">线性探测</option></select><span>Bucket 数:</span><select data-param="buckets"><option value="4">4</option><option value="5" selected>5</option><option value="6">6</option><option value="7">7</option></select><span>冲突: <strong data-metric="collisions">0</strong></span><span>负载: <strong data-metric="load">0.00</strong></span></div>
  <div class="lfh-grid"><div class="lfh-stage"><canvas class="lfh-canvas" data-role="canvas"></canvas></div></div>
  <script>
    (()=>{const root=document.currentScript.closest('.lfh-rescue');if(!root||root.dataset.ready==='1')return;root.dataset.ready='1';
    const canvas=root.querySelector('[data-role="canvas"]'),ctx=canvas.getContext('2d');
    const metrics=Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n=>[n.dataset.metric,n]));
    const keys=['A12','K37','M25','Q41','B09','T18','R52','N14','P88','W20'];let inserted=0,bucketCount=5,strategy='chain';
    function hash(k){return Array.from(k).reduce((s,c)=>s+c.charCodeAt(0),0);}
    function state(){const buckets=Array.from({length:bucketCount},()=>[]);const occupied=Array(bucketCount).fill(false);let collisions=0;
      keys.slice(0,inserted).forEach(k=>{const home=hash(k)%bucketCount;let target=home,collided=buckets[home].length>0||occupied[home];
        if(strategy==='linear'){let p=0;while(occupied[target]&&p<bucketCount){target=(target+1)%bucketCount;p++;}}
        if(collided)collisions++;occupied[target]=true;buckets[target].push({key:k,home,collided});});
      return{buckets,collisions};}
    function resize(){const r=canvas.getBoundingClientRect();canvas.width=Math.max(500,Math.floor(r.width*devicePixelRatio));canvas.height=Math.max(300,Math.floor(r.height*devicePixelRatio));draw();}
    function draw(){const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#07111f';ctx.fillRect(0,0,w,h);
      const s=state(),padX=40*devicePixelRatio,padY=30*devicePixelRatio,bw=(w-padX*2)/s.buckets.length,gap=10*devicePixelRatio;
      metrics.collisions.textContent=s.collisions;metrics.load.textContent=(inserted/bucketCount).toFixed(2);
      s.buckets.forEach((items,i)=>{const x=padX+i*bw,y=padY,bh=h-padY*2;
        ctx.fillStyle=items.some(it=>it.collided)?'rgba(245,158,11,.12)':'rgba(148,163,184,.06)';ctx.fillRect(x+gap/2,y,bw-gap,bh);
        ctx.strokeStyle=items.some(it=>it.collided)?'#f59e0b':'rgba(148,163,184,.25)';ctx.lineWidth=2*devicePixelRatio;ctx.strokeRect(x+gap/2,y,bw-gap,bh);
        ctx.fillStyle='#e5e7eb';ctx.font=(14*devicePixelRatio)+'px sans-serif';ctx.textAlign='center';ctx.fillText('Bucket '+i,x+bw/2,y+22*devicePixelRatio);
        items.forEach((it,j)=>{const ix=x+gap/2+10*devicePixelRatio,iy=y+40*devicePixelRatio+j*32*devicePixelRatio;
          ctx.fillStyle=it.collided?'#fb7185':'#22d3ee';ctx.beginPath();const rx=8*devicePixelRatio;ctx.moveTo(ix+rx,iy);ctx.lineTo(ix+bw-gap-20*devicePixelRatio-rx,iy);ctx.arcTo(ix+bw-gap-20*devicePixelRatio,iy,ix+bw-gap-20*devicePixelRatio,iy+24*devicePixelRatio,rx);ctx.arcTo(ix+bw-gap-20*devicePixelRatio,iy+24*devicePixelRatio,ix,iy+24*devicePixelRatio,rx);ctx.arcTo(ix,iy+24*devicePixelRatio,ix,iy,rx);ctx.arcTo(ix,iy,ix+rx,iy,rx);ctx.closePath();ctx.fill();
          ctx.fillStyle='#04111d';ctx.font=(12*devicePixelRatio)+'px monospace';ctx.textAlign='center';ctx.fillText(it.key+(it.home!==i?' →'+i:''),ix+(bw-gap-20*devicePixelRatio)/2,iy+17*devicePixelRatio);});
      });
    }
    root.addEventListener('click',e=>{const a=e.target&&e.target.dataset?e.target.dataset.action:'';if(a==='add')inserted=Math.min(keys.length,inserted+1);if(a==='reset')inserted=0;draw();});
    root.addEventListener('change',e=>{const r=e.target&&e.target.dataset?e.target.dataset.param:'';if(r==='strategy')strategy=e.target.value;if(r==='buckets')bucketCount=Number(e.target.value);draw();});
    window.addEventListener('resize',resize);resize();
  })();
  </script>
</section>`;
}

// Detect a known topic from the demo's title + intro using ONLY unambiguous, domain-specific
// terms. We deliberately avoid words that cross topics — e.g. "抛物线/parabola" appears in BOTH
// quadratic-function AND projectile-motion (mechanics) demos, so it must NOT force the quadratic
// lab; "波/力/sort" likewise leak across contexts. When nothing matches with high confidence we
// return null and keep the model's own demo. Returns a curated lab builder, or null.
function pickCuratedLab(source: string): (() => string) | null {
  // Strip <style> and <script> bodies so we match ONLY on visible/structural text — this
  // catches a topic keyword buried after a large CSS block (e.g. a "冒泡排序" dropdown option),
  // and avoids false matches on code identifiers like "sort"/"bubble" inside script bodies.
  const scope = source
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .slice(0, 6000);
  if (/伯努利|文丘里|流体力学|流体压强|连续性方程|bernoulli|venturi/i.test(scope)) return fluidRescueHtml;
  if (/二次函数|判别式|顶点式|开口方向|配方法|quadratic function/i.test(scope)) return quadraticRescueHtml;
  if (/三角函数|正弦函数|余弦函数|正切函数|sine wave|cosine function|trigonometric/i.test(scope)) return trigRescueHtml;
  if (/排序算法|冒泡排序|插入排序|选择排序|快速排序|归并排序|堆排序|sorting algorithm|bubble sort|quick sort|insertion sort|selection sort|merge sort/i.test(scope)) return sortingRescueHtml;
  if (/动量守恒|弹性碰撞|非弹性碰撞|恢复系数|conservation of momentum|elastic collision/i.test(scope)) return momentumRescueHtml;
  if (/简谐运动|简谐振动|机械波|横波|纵波|simple harmonic motion/i.test(scope)) return wavesRescueHtml;
  if (/哈希表|散列表|hash table|哈希冲突|链地址法|线性探测/i.test(scope)) return hashRescueHtml;
  if (/受力分析|自由体受力|斜面摩擦|滑块受力|free body diagram/i.test(scope)) return forcesRescueHtml;
  if (/三角形面积公式|多边形内角和|圆的周长公式|圆的面积公式/i.test(scope)) return geometryRescueHtml;
  if (/概率分布|大数定律|二项分布|正态分布|probability distribution/i.test(scope)) return probabilityRescueHtml;
  if (/导数的定义|定积分|不定积分|黎曼和|riemann sum/i.test(scope)) return calculusRescueHtml;
  // Particle/thermal simulations map well onto the generic bouncing-particle physics lab.
  if (/分子扩散|布朗运动|气体扩散|热运动|熵增|粒子碰撞|molecular diffusion|brownian motion/i.test(scope)) {
    return () => genericInteractiveRescueHtml(source);
  }
  return null;
}

export function rescueCustomHtml(html: string): string {
  const source = String(html || "").trim();
  if (!source || !/<[a-z!][\s\S]*>/i.test(source)) {
    return "<section><h2>HTML artifact 无法渲染</h2><p>服务端返回的内容为空或不是有效 HTML。</p></section>";
  }
  if (/data-learnforge-widget=["'][^"']+["']/i.test(source)) {
    return source;
  }
  if (/three\.module\.js|new\s+THREE\.WebGLRenderer|WebGLRenderer|type=["']module["'][\s\S]*\bTHREE\b/i.test(source)) {
    return source;
  }
  const curated = pickCuratedLab(source);
  return curated ? curated() : source;
}

export function truncateOpenScript(html: string): string {
  const start = html.toLowerCase().lastIndexOf("<script");
  const end = html.toLowerCase().lastIndexOf("</script>");
  if (start > end) {
    return html.slice(0, start);
  }
  return html;
}

export function fingerprint(value: string): string {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash.toString(16);
}

export function getCachedHeight(key: string): number {
  return heightCache.get(key) ?? 240;
}

export function setCachedHeight(key: string, height: number): void {
  heightCache.set(key, Math.max(160, Math.min(720, height)));
}

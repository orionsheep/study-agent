from __future__ import annotations

import re
from html import escape

from app.skills.base import SkillInput, SkillOutput


class CustomHtmlAppSkill:
    skill_name = "custom_html_app_skill"
    blocked_tags = ("iframe", "form", "object", "embed", "base")
    blocked_script_patterns = ()

    def sorting_demo_widget(self, topic: str) -> str:
        title = escape(topic or "排序算法")
        template = """
<section class="lf-sort-demo" data-learnforge-widget="sorting-demo">
  <style>
    .lf-sort-demo{--ink:#111827;--muted:#5b6475;--line:#d8e0ec;--paper:#fffdf7;--blue:#2563eb;--cyan:#0891b2;--amber:#f59e0b;--green:#059669;--red:#dc2626;font-family:"Avenir Next","PingFang SC",ui-sans-serif,system-ui;color:var(--ink);background:linear-gradient(135deg,#f7fbff 0%,#fff8eb 56%,#f2fff7 100%);border:1px solid #dde7f4;border-radius:18px;padding:22px;min-height:510px;box-sizing:border-box;box-shadow:0 18px 46px rgba(38,66,115,.12)}
    .lf-sort-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:start;margin-bottom:14px}
    .lf-sort-title{margin:0;font-size:25px;line-height:1.18;letter-spacing:0}
    .lf-sort-copy{margin:8px 0 0;color:var(--muted);font-size:13px;line-height:1.65;max-width:760px}
    .lf-sort-chiprail{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
    .lf-sort-chip{font-size:12px;font-weight:800;border:1px solid #cbd5e1;border-radius:999px;padding:6px 10px;background:rgba(255,255,255,.72);white-space:nowrap}
    .lf-sort-toolbar{display:flex;flex-wrap:wrap;gap:9px;margin:16px 0}
    .lf-sort-toolbar button{border:0;border-radius:10px;padding:10px 13px;font-weight:850;color:#fff;background:var(--blue);cursor:pointer;box-shadow:0 10px 22px rgba(37,99,235,.16)}
    .lf-sort-toolbar button:nth-child(2){background:var(--green)}
    .lf-sort-toolbar button:nth-child(3){background:#7c3aed}
    .lf-sort-toolbar button:nth-child(4){background:#475569}
    .lf-sort-toolbar button:active{transform:translateY(1px)}
    .lf-sort-workbench{display:grid;grid-template-columns:minmax(0,1.38fr) minmax(270px,.72fr);gap:14px}
    .lf-sort-stage-wrap{border:1px solid var(--line);background:rgba(255,255,255,.78);border-radius:16px;padding:14px;box-sizing:border-box}
    .lf-sort-stage-label{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:10px;font-size:12px;color:#64748b;font-weight:800}
    .lf-sort-stage{height:282px;display:flex;align-items:flex-end;gap:9px;padding:18px;border:1px solid #dbeafe;background:linear-gradient(180deg,#ffffff,#eef7ff);border-radius:14px;box-sizing:border-box;overflow:hidden}
    .lf-bar{flex:1;min-width:18px;border-radius:10px 10px 5px 5px;background:linear-gradient(180deg,#67e8f9,#2563eb);display:flex;align-items:flex-start;justify-content:center;color:#fff;font-size:12px;font-weight:900;padding-top:8px;box-shadow:inset 0 1px 0 rgba(255,255,255,.45),0 10px 18px rgba(37,99,235,.14);transition:height .26s ease,background .18s ease,transform .18s ease}
    .lf-bar.compare{background:linear-gradient(180deg,#fde68a,#f97316);transform:translateY(-10px)}
    .lf-bar.moved{background:linear-gradient(180deg,#fecaca,#dc2626);transform:translateY(-4px)}
    .lf-bar.sorted{background:linear-gradient(180deg,#6ee7b7,#059669)}
    .lf-sort-side{border:1px solid var(--line);background:rgba(255,255,255,.8);border-radius:16px;padding:14px;box-sizing:border-box}
    .lf-sort-side h3{margin:0 0 8px;font-size:16px}
    .lf-sort-side p{margin:0;color:#475569;font-size:13px;line-height:1.58}
    .lf-sort-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
    .lf-sort-metric{border:1px solid #e2e8f0;border-radius:12px;padding:10px;background:#fff}
    .lf-sort-metric small{display:block;color:#64748b;margin-bottom:4px}
    .lf-sort-metric strong{font-size:22px;line-height:1}
    .lf-sort-code{margin:12px 0 0;border-radius:12px;background:#111827;color:#dbeafe;padding:12px;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:12px;line-height:1.55;white-space:pre-wrap}
    .lf-sort-log{margin-top:12px;min-height:46px;border-left:4px solid #2563eb;background:#eff6ff;border-radius:10px;padding:10px;color:#1e3a8a;font-weight:800;font-size:13px;line-height:1.5}
    .lf-sort-legend{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;color:#475569;font-size:12px}
    .lf-sort-legend span{display:inline-flex;align-items:center;gap:5px}
    .lf-sort-dot{width:10px;height:10px;border-radius:999px;background:#2563eb}.lf-sort-dot.compare{background:#f97316}.lf-sort-dot.sorted{background:#059669}
    @media(max-width:760px){.lf-sort-head,.lf-sort-workbench{grid-template-columns:1fr}.lf-sort-chiprail{justify-content:flex-start}.lf-sort-stage{height:230px;gap:6px}.lf-sort-toolbar button{flex:1;min-width:120px}}
  </style>
  <div class="lf-sort-head">
    <div>
      <h2 class="lf-sort-title">__TITLE__互动实验室</h2>
      <p class="lf-sort-copy">把排序从“背代码”拆成可观察的扫描、比较和移动。首屏已经给出数组柱状图，即使脚本延迟加载也不会出现空舞台。</p>
    </div>
    <div class="lf-sort-chiprail" aria-label="算法复杂度">
      <span class="lf-sort-chip">冒泡 O(n^2)</span>
      <span class="lf-sort-chip">插入 O(n^2)</span>
      <span class="lf-sort-chip">稳定排序</span>
    </div>
  </div>
  <div class="lf-sort-toolbar">
    <button type="button" data-action="bubble">冒泡排序</button>
    <button type="button" data-action="insertion">插入排序</button>
    <button type="button" data-action="step">单步执行</button>
    <button type="button" data-action="reset">随机重置</button>
  </div>
  <div class="lf-sort-workbench">
    <div class="lf-sort-stage-wrap">
      <div class="lf-sort-stage-label"><span>数组轨道</span><span>橙色=正在比较，绿色=已归位</span></div>
      <div class="lf-sort-stage" aria-label="排序数组可视化">
        <div class="lf-bar" style="height:132px">42</div>
        <div class="lf-bar" style="height:218px">76</div>
        <div class="lf-bar" style="height:94px">28</div>
        <div class="lf-bar" style="height:252px">91</div>
        <div class="lf-bar" style="height:160px">55</div>
        <div class="lf-bar" style="height:70px">18</div>
        <div class="lf-bar" style="height:186px">64</div>
        <div class="lf-bar" style="height:118px">37</div>
      </div>
      <div class="lf-sort-legend"><span><i class="lf-sort-dot"></i>未处理</span><span><i class="lf-sort-dot compare"></i>比较焦点</span><span><i class="lf-sort-dot sorted"></i>已排序区</span></div>
    </div>
    <aside class="lf-sort-side">
      <h3>当前策略</h3>
      <p class="lf-sort-desc">选择一种算法开始。冒泡排序把最大值逐轮推到右侧；插入排序维护左侧有序区，再把新元素插进去。</p>
      <div class="lf-sort-metrics">
        <div class="lf-sort-metric"><small>比较次数</small><strong data-metric="compare">0</strong></div>
        <div class="lf-sort-metric"><small>交换/移动</small><strong data-metric="swap">0</strong></div>
      </div>
      <div class="lf-sort-code" data-role="pseudo">选择算法后，这里会显示当前步骤的伪代码焦点。</div>
      <div class="lf-sort-log">点击算法按钮开始；也可以先点“单步执行”查看提示。</div>
    </aside>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-sort-demo');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const stage = root.querySelector('.lf-sort-stage');
      const log = root.querySelector('.lf-sort-log');
      const desc = root.querySelector('.lf-sort-desc');
      const pseudo = root.querySelector('[data-role="pseudo"]');
      const compareNode = root.querySelector('[data-metric="compare"]');
      const swapNode = root.querySelector('[data-metric="swap"]');
      let values = [42, 76, 28, 91, 55, 18, 64, 37];
      let compares = 0;
      let swaps = 0;
      let queue = [];
      let timer = null;
      const sleep = 520;

      function render(active = [], moved = [], sortedFrom = values.length) {
        stage.innerHTML = '';
        values.forEach((value, index) => {
          const bar = document.createElement('div');
          bar.className = 'lf-bar' + (active.includes(index) ? ' compare' : '') + (moved.includes(index) ? ' moved' : '') + (index >= sortedFrom ? ' sorted' : '');
          bar.style.height = Math.max(48, value * 2.55) + 'px';
          bar.textContent = value;
          stage.appendChild(bar);
        });
        compareNode.textContent = compares;
        swapNode.textContent = swaps;
      }

      function reset() {
        values = Array.from({ length: 8 }, () => 18 + Math.floor(Math.random() * 76));
        compares = 0;
        swaps = 0;
        queue = [];
        clearInterval(timer);
        timer = null;
        desc.textContent = '已生成新数组。选择算法后观察比较焦点、移动次数和已排序区域。';
        pseudo.textContent = '等待选择算法...';
        log.textContent = '新数组已就绪。';
        render();
      }

      function buildBubble() {
        const arr = values.slice();
        const steps = [];
        for (let end = arr.length - 1; end > 0; end -= 1) {
          for (let i = 0; i < end; i += 1) {
            steps.push({ type: 'compare', active: [i, i + 1], sortedFrom: end + 1, code: `if a[${i}] > a[${i + 1}]`, note: `比较 ${arr[i]} 和 ${arr[i + 1]}` });
            if (arr[i] > arr[i + 1]) {
              [arr[i], arr[i + 1]] = [arr[i + 1], arr[i]];
              steps.push({ type: 'swap', values: arr.slice(), active: [i, i + 1], moved: [i, i + 1], sortedFrom: end + 1, code: `swap(a[${i}], a[${i + 1}])`, note: '左边更大，交换相邻元素' });
            }
          }
          steps.push({ type: 'sorted', sortedFrom: end, code: `mark a[${end}] sorted`, note: `第 ${arr.length - end} 轮结束，右侧元素归位` });
        }
        steps.push({ type: 'done', sortedFrom: 0, code: 'done', note: '冒泡排序完成' });
        return steps;
      }

      function buildInsertion() {
        const arr = values.slice();
        const steps = [];
        for (let i = 1; i < arr.length; i += 1) {
          const key = arr[i];
          let j = i - 1;
          steps.push({ type: 'compare', active: [i, j], sortedFrom: values.length, code: `key = a[${i}]`, note: `取出 ${key}，准备插入左侧有序区` });
          while (j >= 0 && arr[j] > key) {
            arr[j + 1] = arr[j];
            steps.push({ type: 'swap', values: arr.slice(), active: [j, j + 1], moved: [j + 1], code: `a[${j + 1}] = a[${j}]`, note: `${arr[j]} 右移，为 ${key} 腾位置` });
            j -= 1;
          }
          arr[j + 1] = key;
          steps.push({ type: 'swap', values: arr.slice(), active: [j + 1], moved: [j + 1], code: `a[${j + 1}] = key`, note: `${key} 插入到正确位置` });
        }
        steps.push({ type: 'done', sortedFrom: 0, code: 'done', note: '插入排序完成' });
        return steps;
      }

      function applyStep(step) {
        if (!step) return;
        if (step.type === 'compare') compares += 1;
        if (step.type === 'swap') {
          swaps += 1;
          values = step.values.slice();
        }
        pseudo.textContent = step.code || '';
        log.textContent = step.note;
        render(step.active || [], step.moved || [], step.sortedFrom ?? values.length);
      }

      function stepOnce() {
        if (!queue.length) {
          log.textContent = '当前没有待执行步骤，请先选择冒泡排序或插入排序。';
          return;
        }
        applyStep(queue.shift());
      }

      function play(kind) {
        clearInterval(timer);
        compares = 0;
        swaps = 0;
        queue = kind === 'insertion' ? buildInsertion() : buildBubble();
        desc.textContent = kind === 'insertion'
          ? '插入排序：左侧始终保持有序，把当前 key 插入正确位置。'
          : '冒泡排序：一轮轮扫描相邻元素，把较大值推向右侧边界。';
        render();
        stepOnce();
        timer = setInterval(() => {
          if (!queue.length) {
            clearInterval(timer);
            timer = null;
            render([], [], 0);
            return;
          }
          stepOnce();
        }, sleep);
      }

      root.addEventListener('click', (event) => {
        const action = event.target && event.target.dataset ? event.target.dataset.action : '';
        if (action === 'bubble') play('bubble');
        if (action === 'insertion') play('insertion');
        if (action === 'step') stepOnce();
        if (action === 'reset') reset();
      });
      render();
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)

    def sorting_kinetic_lab_widget(self, topic: str) -> str:
        title = escape(topic or "经典排序算法")
        template = """
<section class="lf-sortx" data-learnforge-widget="sorting-demo">
  <style>
    .lf-sortx{--ink:#f8fafc;--muted:#a8b3c7;--line:rgba(255,255,255,.16);--panel:rgba(10,18,30,.72);--cyan:#2dd4bf;--blue:#38bdf8;--amber:#f59e0b;--red:#fb7185;--green:#86efac;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;color:var(--ink);min-height:760px;padding:0;background:#07111f;border:1px solid rgba(148,163,184,.28);box-sizing:border-box;overflow:hidden;position:relative}
    .lf-sortx:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 18% 16%,rgba(45,212,191,.22),transparent 28%),radial-gradient(circle at 78% 10%,rgba(56,189,248,.18),transparent 26%),linear-gradient(135deg,#07111f 0%,#101827 58%,#06151c 100%);pointer-events:none}
    .lf-sortx:after{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:26px 26px;mask-image:linear-gradient(180deg,#000,transparent 78%);pointer-events:none}
    .lf-sortx>*{position:relative;z-index:1}
    .lf-sortx-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:end;padding:28px 30px 16px;border-bottom:1px solid var(--line)}
    .lf-sortx-kicker{font-size:12px;font-weight:950;color:var(--cyan);letter-spacing:.12em;text-transform:uppercase}.lf-sortx h2{margin:6px 0 8px;font-size:36px;line-height:1.02;letter-spacing:0}.lf-sortx p{margin:0;color:var(--muted);font-size:13px;line-height:1.7;max-width:820px}
    .lf-sortx-status{display:grid;grid-template-columns:repeat(3,96px);gap:8px}.lf-sortx-stat{border:1px solid var(--line);background:rgba(255,255,255,.07);padding:10px;border-radius:12px}.lf-sortx-stat small{display:block;color:var(--muted);font-size:11px}.lf-sortx-stat strong{font-size:22px}
    .lf-sortx-main{display:grid;grid-template-columns:300px minmax(0,1fr) 310px;gap:14px;padding:16px}
    .lf-sortx-panel{border:1px solid var(--line);background:var(--panel);backdrop-filter:blur(12px);border-radius:14px;padding:14px;box-sizing:border-box}.lf-sortx-panel h3{margin:0 0 12px;font-size:15px}
    .lf-sortx-field{display:grid;gap:6px;margin-bottom:12px}.lf-sortx-field label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}.lf-sortx select,.lf-sortx input{width:100%;accent-color:var(--cyan)}.lf-sortx select{height:38px;border-radius:10px;border:1px solid var(--line);background:#111827;color:var(--ink);font-weight:900;padding:0 10px}
    .lf-sortx-buttons{display:grid;grid-template-columns:1fr 1fr;gap:8px}.lf-sortx button{min-height:40px;border:1px solid rgba(255,255,255,.16);border-radius:10px;background:linear-gradient(135deg,rgba(45,212,191,.95),rgba(56,189,248,.85));color:#04111d;font-weight:950;cursor:pointer}.lf-sortx button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}.lf-sortx button.warn{background:linear-gradient(135deg,#f59e0b,#fb7185);color:#1f0b10}
    .lf-sortx-stage{min-height:560px;border:1px solid rgba(45,212,191,.24);background:linear-gradient(180deg,rgba(8,13,24,.74),rgba(4,10,18,.92));border-radius:14px;overflow:hidden;position:relative}.lf-sortx-canvas{width:100%;height:560px;display:block}.lf-sortx-overlay{position:absolute;left:16px;right:16px;bottom:14px;display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:12px}.lf-sortx-pill{border:1px solid var(--line);background:rgba(0,0,0,.28);border-radius:999px;padding:7px 10px}
    .lf-sortx-code{min-height:186px;white-space:pre-wrap;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:12px;line-height:1.58;color:#c7d2fe;background:#060b13;border:1px solid rgba(148,163,184,.18);border-radius:12px;padding:12px}.lf-sortx-log{margin-top:10px;min-height:72px;color:#dbeafe;border-left:3px solid var(--cyan);background:rgba(56,189,248,.09);border-radius:10px;padding:10px;font-weight:850;line-height:1.55}
    .lf-sortx-legend{display:grid;gap:8px;margin-top:12px}.lf-sortx-legend span{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:12px}.lf-sortx-dot{width:12px;height:12px;border-radius:4px;background:var(--blue)}.lf-sortx-dot.compare{background:var(--amber)}.lf-sortx-dot.swap{background:var(--red)}.lf-sortx-dot.sorted{background:var(--green)}
    @media(max-width:980px){.lf-sortx-head,.lf-sortx-main{grid-template-columns:1fr}.lf-sortx-status{grid-template-columns:repeat(3,1fr)}.lf-sortx-canvas{height:460px}.lf-sortx-stage{min-height:460px}}
  </style>
  <div class="lf-sortx-head">
    <div><div class="lf-sortx-kicker">Algorithm Motion Lab</div><h2>__TITLE__动态可视化实验室</h2><p>实时观察比较、交换、分区和有序区扩张。这里不是模板预览，而是由 Canvas 和本地状态机驱动的排序动画。</p></div>
    <div class="lf-sortx-status"><div class="lf-sortx-stat"><small>比较</small><strong data-metric="compare">0</strong></div><div class="lf-sortx-stat"><small>交换</small><strong data-metric="swap">0</strong></div><div class="lf-sortx-stat"><small>步骤</small><strong data-metric="step">0</strong></div></div>
  </div>
  <div class="lf-sortx-main">
    <aside class="lf-sortx-panel">
      <h3>控制台</h3>
      <div class="lf-sortx-field"><label>算法 <span data-role="algo-label">冒泡排序</span></label><select data-role="algo"><option value="bubble">冒泡排序</option><option value="insertion">插入排序</option><option value="selection">选择排序</option><option value="quick">快速排序分区</option></select></div>
      <div class="lf-sortx-field"><label>数据规模 <span data-role="size-label">18</span></label><input data-role="size" type="range" min="8" max="36" value="18"></div>
      <div class="lf-sortx-field"><label>动画速度 <span data-role="speed-label">中速</span></label><input data-role="speed" type="range" min="1" max="5" value="3"></div>
      <div class="lf-sortx-buttons"><button type="button" data-action="play">开始执行</button><button class="secondary" type="button" data-action="step">单步</button><button class="secondary" type="button" data-action="shuffle">刷新数据</button><button class="warn" type="button" data-action="stop">中止</button></div>
      <div class="lf-sortx-legend"><span><i class="lf-sortx-dot"></i>待处理元素</span><span><i class="lf-sortx-dot compare"></i>比较焦点</span><span><i class="lf-sortx-dot swap"></i>交换/移动</span><span><i class="lf-sortx-dot sorted"></i>已确定区域</span></div>
    </aside>
    <div class="lf-sortx-stage"><canvas class="lf-sortx-canvas" data-role="canvas"></canvas><div class="lf-sortx-overlay"><span class="lf-sortx-pill" data-role="phase">等待执行</span><span class="lf-sortx-pill">点击“单步”可以逐帧拆解</span></div></div>
    <aside class="lf-sortx-panel"><h3>当前算法</h3><div class="lf-sortx-code" data-role="code">选择算法后开始执行。</div><div class="lf-sortx-log" data-role="log">已生成初始数据。排序过程会在中央舞台逐帧展开。</div></aside>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-sortx');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const canvas = root.querySelector('[data-role="canvas"]');
      const ctx = canvas.getContext('2d');
      const nodes = {
        algo: root.querySelector('[data-role="algo"]'), size: root.querySelector('[data-role="size"]'), speed: root.querySelector('[data-role="speed"]'),
        algoLabel: root.querySelector('[data-role="algo-label"]'), sizeLabel: root.querySelector('[data-role="size-label"]'), speedLabel: root.querySelector('[data-role="speed-label"]'),
        compare: root.querySelector('[data-metric="compare"]'), swap: root.querySelector('[data-metric="swap"]'), step: root.querySelector('[data-metric="step"]'),
        phase: root.querySelector('[data-role="phase"]'), code: root.querySelector('[data-role="code"]'), log: root.querySelector('[data-role="log"]')
      };
      const labels = { bubble: '冒泡排序', insertion: '插入排序', selection: '选择排序', quick: '快速排序分区' };
      const speedText = ['很慢','慢速','中速','快速','高速'];
      let values = [], steps = [], cursor = 0, playing = false, raf = 0, last = 0, metrics = { compare: 0, swap: 0, step: 0 }, current = {};
      function resize(){ const r = canvas.getBoundingClientRect(); canvas.width = Math.max(720, Math.floor(r.width * devicePixelRatio)); canvas.height = Math.floor(r.height * devicePixelRatio); draw(); }
      function shuffle(){ const n = Number(nodes.size.value); values = Array.from({length:n},(_,i)=>({ id:i, v:12 + Math.floor(Math.random()*88) })); metrics = { compare:0, swap:0, step:0 }; cursor = 0; steps = buildSteps(nodes.algo.value, values.map(x=>x.v)); current = { note:'新数据已就绪', active:[], moved:[], sorted:[] }; updateText(); draw(); }
      function buildSteps(kind, source){ return kind === 'insertion' ? insertion(source) : kind === 'selection' ? selection(source) : kind === 'quick' ? quick(source) : bubble(source); }
      function bubble(a){ const arr=a.slice(), out=[]; for(let end=arr.length-1; end>0; end--){ for(let i=0;i<end;i++){ out.push({t:'compare', active:[i,i+1], sorted:range(end+1,arr.length), code:`if a[${i}] > a[${i+1}]`, note:`比较相邻元素 ${arr[i]} 和 ${arr[i+1]}`}); if(arr[i]>arr[i+1]){ [arr[i],arr[i+1]]=[arr[i+1],arr[i]]; out.push({t:'swap', values:arr.slice(), active:[i,i+1], moved:[i,i+1], sorted:range(end+1,arr.length), code:`swap(a[${i}], a[${i+1}])`, note:'较大的元素向右冒泡'}); } } out.push({t:'mark', sorted:range(end,arr.length), code:`mark a[${end}] sorted`, note:'本轮最大值归位'}); } out.push({t:'done', sorted:range(0,arr.length), code:'done', note:'排序完成'}); return out; }
      function insertion(a){ const arr=a.slice(), out=[]; for(let i=1;i<arr.length;i++){ const key=arr[i]; let j=i-1; out.push({t:'compare', active:[i,j], sorted:range(0,i), code:`key = a[${i}]`, note:`取出 ${key}，插入左侧有序区`}); while(j>=0 && arr[j]>key){ arr[j+1]=arr[j]; out.push({t:'swap', values:arr.slice(), active:[j,j+1], moved:[j+1], sorted:range(0,i), code:`a[${j+1}] = a[${j}]`, note:`${arr[j]} 右移`}); j--; } arr[j+1]=key; out.push({t:'swap', values:arr.slice(), active:[j+1], moved:[j+1], sorted:range(0,i+1), code:`a[${j+1}] = key`, note:`${key} 插入完成`}); } out.push({t:'done', sorted:range(0,arr.length), code:'done', note:'排序完成'}); return out; }
      function selection(a){ const arr=a.slice(), out=[]; for(let i=0;i<arr.length-1;i++){ let min=i; for(let j=i+1;j<arr.length;j++){ out.push({t:'compare', active:[min,j], sorted:range(0,i), code:`min = argmin(a[${i}..])`, note:`比较当前最小值 ${arr[min]} 和候选 ${arr[j]}`}); if(arr[j]<arr[min]) min=j; } if(min!==i){ [arr[i],arr[min]]=[arr[min],arr[i]]; out.push({t:'swap', values:arr.slice(), active:[i,min], moved:[i,min], sorted:range(0,i+1), code:`swap(a[${i}], a[${min}])`, note:'把最小值放到当前边界'}); } } out.push({t:'done', sorted:range(0,arr.length), code:'done', note:'排序完成'}); return out; }
      function quick(a){ const arr=a.slice(), out=[]; function part(lo,hi){ if(lo>=hi) return; const pivot=arr[hi]; let i=lo; out.push({t:'mark', active:[hi], sorted:[], code:`pivot = a[${hi}]`, note:`选择 ${pivot} 作为基准`}); for(let j=lo;j<hi;j++){ out.push({t:'compare', active:[j,hi], moved:range(lo,i), code:`if a[${j}] < pivot`, note:'小于基准的元素被推进左侧分区'}); if(arr[j]<pivot){ [arr[i],arr[j]]=[arr[j],arr[i]]; out.push({t:'swap', values:arr.slice(), active:[i,j], moved:[i,j], code:`swap(a[${i}], a[${j}])`, note:'扩大小于基准的分区'}); i++; } } [arr[i],arr[hi]]=[arr[hi],arr[i]]; out.push({t:'swap', values:arr.slice(), active:[i,hi], sorted:[i], code:`swap(pivot, a[${i}])`, note:'基准落到最终位置'}); part(lo,i-1); part(i+1,hi); } part(0,arr.length-1); out.push({t:'done', sorted:range(0,arr.length), code:'done', note:'快速排序分区完成'}); return out; }
      function range(a,b){ return Array.from({length:Math.max(0,b-a)},(_,i)=>a+i); }
      function apply(step){ if(!step) return; current = step; if(step.values) values = step.values.map((v,i)=>values[i] ? {...values[i], v} : {id:i,v}); if(step.t==='compare') metrics.compare++; if(step.t==='swap') metrics.swap++; metrics.step++; updateText(); draw(); }
      function updateText(){ nodes.algoLabel.textContent=labels[nodes.algo.value]; nodes.sizeLabel.textContent=nodes.size.value; nodes.speedLabel.textContent=speedText[Number(nodes.speed.value)-1]; nodes.compare.textContent=metrics.compare; nodes.swap.textContent=metrics.swap; nodes.step.textContent=metrics.step; nodes.phase.textContent=current.note||'等待执行'; nodes.code.textContent=current.code||'选择算法后开始执行。'; nodes.log.textContent=current.note||'已生成初始数据。'; }
      function draw(){ const w=canvas.width,h=canvas.height; ctx.clearRect(0,0,w,h); const pad=44*devicePixelRatio, base=h-pad, max=Math.max(1,...values.map(x=>x.v)); const gap=4*devicePixelRatio, bw=(w-pad*2-gap*(values.length-1))/values.length; ctx.fillStyle='#07111f'; ctx.fillRect(0,0,w,h); ctx.strokeStyle='rgba(148,163,184,.16)'; for(let y=pad;y<base;y+=42*devicePixelRatio){ ctx.beginPath(); ctx.moveTo(pad,y); ctx.lineTo(w-pad,y); ctx.stroke(); } values.forEach((item,i)=>{ const x=pad+i*(bw+gap), bh=(item.v/max)*(h-pad*2); const active=(current.active||[]).includes(i), moved=(current.moved||[]).includes(i), sorted=(current.sorted||[]).includes(i); const grad=ctx.createLinearGradient(0,base-bh,0,base); grad.addColorStop(0, sorted?'#86efac':moved?'#fb7185':active?'#f59e0b':'#38bdf8'); grad.addColorStop(1, sorted?'#15803d':moved?'#be123c':active?'#b45309':'#1d4ed8'); ctx.fillStyle=grad; roundRect(ctx,x,base-bh,bw,bh,Math.min(14*devicePixelRatio,bw/3)); ctx.fill(); if(bw>18*devicePixelRatio){ ctx.fillStyle=sorted?'#052e16':'#eff6ff'; ctx.font=`${12*devicePixelRatio}px ui-monospace`; ctx.textAlign='center'; ctx.fillText(String(item.v),x+bw/2,base-bh+18*devicePixelRatio); } }); }
      function roundRect(c,x,y,w,h,r){ c.beginPath(); c.moveTo(x+r,y); c.arcTo(x+w,y,x+w,y+h,r); c.arcTo(x+w,y+h,x,y+h,r); c.arcTo(x,y+h,x,y,r); c.arcTo(x,y,x+w,y,r); c.closePath(); }
      function loop(t){ if(!playing) return; const delay=760-Number(nodes.speed.value)*115; if(t-last>delay){ last=t; if(cursor>=steps.length){ playing=false; return; } apply(steps[cursor++]); } raf=requestAnimationFrame(loop); }
      function play(){ if(playing) return; playing=true; last=0; raf=requestAnimationFrame(loop); }
      function stop(){ playing=false; cancelAnimationFrame(raf); }
      root.addEventListener('click',e=>{ const a=e.target&&e.target.dataset?e.target.dataset.action:''; if(a==='play') play(); if(a==='stop') stop(); if(a==='shuffle'){ stop(); shuffle(); } if(a==='step'){ stop(); if(cursor<steps.length) apply(steps[cursor++]); } });
      root.addEventListener('input',e=>{ if(e.target===nodes.size || e.target===nodes.algo){ stop(); shuffle(); } else updateText(); });
      window.addEventListener('resize', resize);
      resize(); shuffle();
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)

    def hash_collision_demo_widget(self, topic: str) -> str:
        title = escape(topic or "哈希表冲突")
        template = """
<section class="lf-hash-demo" data-learnforge-widget="hash-collision-demo">
  <style>
    .lf-hash-demo{--ink:#101827;--muted:#667085;--line:#d7e2ef;--blue:#2563eb;--teal:#0f766e;--amber:#f59e0b;--red:#dc2626;font-family:"Avenir Next","PingFang SC",ui-sans-serif,system-ui;color:var(--ink);background:linear-gradient(135deg,#f5fbff,#fff9eb 58%,#f2fff8);border:1px solid #dae6f3;border-radius:18px;padding:22px;min-height:500px;box-sizing:border-box;box-shadow:0 18px 46px rgba(37,71,113,.12)}
    .lf-hash-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:start}
    .lf-hash-head h2{margin:0;font-size:25px;line-height:1.18}
    .lf-hash-head p{margin:8px 0 0;color:var(--muted);font-size:13px;line-height:1.65;max-width:760px}
    .lf-hash-formula{font-family:"SFMono-Regular",ui-monospace,monospace;background:#111827;color:#d1fae5;border-radius:12px;padding:10px 12px;font-size:12px;white-space:nowrap}
    .lf-hash-toolbar{display:flex;gap:9px;flex-wrap:wrap;margin:16px 0}
    .lf-hash-toolbar button,.lf-hash-toolbar select{height:38px;border-radius:10px;border:1px solid #cbd5e1;background:#fff;color:#172033;font-weight:850;padding:0 12px}
    .lf-hash-toolbar button{border:0;background:#2563eb;color:#fff;box-shadow:0 10px 22px rgba(37,99,235,.15);cursor:pointer}
    .lf-hash-toolbar button:nth-child(2){background:#0f766e}
    .lf-hash-grid{display:grid;grid-template-columns:minmax(180px,.42fr) minmax(0,1fr) minmax(240px,.48fr);gap:14px}
    .lf-hash-panel{border:1px solid var(--line);background:rgba(255,255,255,.78);border-radius:16px;padding:14px;box-sizing:border-box}
    .lf-hash-panel h3{margin:0 0 10px;font-size:15px}
    .lf-key-list{display:grid;gap:8px}
    .lf-key{border:1px solid #dbeafe;background:#eff6ff;border-radius:12px;padding:9px 10px;font-family:"SFMono-Regular",ui-monospace,monospace;font-weight:900;color:#1d4ed8}
    .lf-key.pending{background:#fff;color:#64748b;border-style:dashed}
    .lf-bucket-grid{display:grid;gap:9px}
    .lf-bucket{display:grid;grid-template-columns:70px minmax(0,1fr);gap:9px;align-items:center;border:1px solid #e2e8f0;border-radius:13px;background:#fff;padding:9px}
    .lf-bucket.hot{border-color:#f59e0b;background:#fffbeb}
    .lf-bucket-index{font-weight:900;color:#0f172a}
    .lf-chain{display:flex;gap:6px;flex-wrap:wrap;min-height:32px;align-items:center}
    .lf-chip{display:inline-flex;align-items:center;gap:5px;border-radius:999px;background:#dbeafe;color:#1e3a8a;padding:6px 9px;font-size:12px;font-weight:900}
    .lf-chip.collision{background:#fee2e2;color:#991b1b}
    .lf-empty{color:#94a3b8;font-size:12px}
    .lf-hash-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .lf-hash-metric{border:1px solid #e2e8f0;border-radius:12px;background:#fff;padding:10px}
    .lf-hash-metric small{display:block;color:#64748b;margin-bottom:4px}
    .lf-hash-metric strong{font-size:21px;line-height:1}
    .lf-hash-log{margin-top:12px;border-left:4px solid #f59e0b;background:#fffbeb;color:#92400e;border-radius:10px;padding:10px;font-size:13px;line-height:1.55;font-weight:800}
    .lf-hash-note{margin-top:12px;color:#475569;font-size:13px;line-height:1.6}
    @media(max-width:860px){.lf-hash-head,.lf-hash-grid{grid-template-columns:1fr}.lf-hash-formula{white-space:normal}.lf-bucket{grid-template-columns:54px minmax(0,1fr)}}
  </style>
  <div class="lf-hash-head">
    <div>
      <h2>__TITLE__实验室</h2>
      <p>把 key 映射进有限 bucket：当不同 key 算出的下标相同，冲突就会真实出现。这里可以切换链地址和线性探测，看同一批 key 如何被安放。</p>
    </div>
    <div class="lf-hash-formula">hash(key) % bucket_count</div>
  </div>
  <div class="lf-hash-toolbar">
    <button type="button" data-action="next">插入下一个 key</button>
    <button type="button" data-action="reset">重置</button>
    <select data-role="strategy" aria-label="冲突处理策略"><option value="chain">链地址法</option><option value="linear">线性探测</option></select>
    <select data-role="buckets" aria-label="bucket 数量"><option value="4">4 个 bucket</option><option value="5">5 个 bucket</option><option value="6">6 个 bucket</option></select>
  </div>
  <div class="lf-hash-grid">
    <div class="lf-hash-panel">
      <h3>待插入 key</h3>
      <div class="lf-key-list" data-role="keys">
        <div class="lf-key">A12</div><div class="lf-key">K37</div><div class="lf-key">M25</div><div class="lf-key">Q41</div><div class="lf-key pending">B09</div><div class="lf-key pending">T18</div>
      </div>
    </div>
    <div class="lf-hash-panel">
      <h3>bucket 现场</h3>
      <div class="lf-bucket-grid" data-role="buckets-grid">
        <div class="lf-bucket"><span class="lf-bucket-index">bucket 0</span><div class="lf-chain"><span class="lf-chip">A12</span></div></div>
        <div class="lf-bucket hot"><span class="lf-bucket-index">bucket 1</span><div class="lf-chain"><span class="lf-chip">K37</span><span class="lf-chip collision">Q41</span></div></div>
        <div class="lf-bucket"><span class="lf-bucket-index">bucket 2</span><div class="lf-chain"><span class="lf-empty">空</span></div></div>
        <div class="lf-bucket"><span class="lf-bucket-index">bucket 3</span><div class="lf-chain"><span class="lf-chip">M25</span></div></div>
      </div>
    </div>
    <aside class="lf-hash-panel">
      <h3>冲突读数</h3>
      <div class="lf-hash-metrics">
        <div class="lf-hash-metric"><small>已插入</small><strong data-metric="inserted">4</strong></div>
        <div class="lf-hash-metric"><small>冲突次数</small><strong data-metric="collisions">1</strong></div>
        <div class="lf-hash-metric"><small>负载因子</small><strong data-metric="load">1.00</strong></div>
        <div class="lf-hash-metric"><small>当前策略</small><strong data-metric="strategy">链地址</strong></div>
      </div>
      <div class="lf-hash-log" data-role="log">Q41 和 K37 映射到同一个 bucket，冲突被高亮。</div>
      <p class="lf-hash-note">抽屉原理的影子在这里很直接：key 多、bucket 少时，至少会有 bucket 承担多个 key。</p>
    </aside>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-hash-demo');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const allKeys = ['A12', 'K37', 'M25', 'Q41', 'B09', 'T18', 'R52'];
      let inserted = 4;
      let bucketCount = 4;
      let strategy = 'chain';
      const keyList = root.querySelector('[data-role="keys"]');
      const grid = root.querySelector('[data-role="buckets-grid"]');
      const log = root.querySelector('[data-role="log"]');
      const insertedNode = root.querySelector('[data-metric="inserted"]');
      const collisionNode = root.querySelector('[data-metric="collisions"]');
      const loadNode = root.querySelector('[data-metric="load"]');
      const strategyNode = root.querySelector('[data-metric="strategy"]');

      function hashKey(key) {
        return Array.from(key).reduce((sum, ch) => sum + ch.charCodeAt(0), 0);
      }

      function buildBuckets() {
        const buckets = Array.from({ length: bucketCount }, () => []);
        const occupied = new Array(bucketCount).fill(false);
        let collisions = 0;
        allKeys.slice(0, inserted).forEach((key) => {
          const home = hashKey(key) % bucketCount;
          let target = home;
          let collided = buckets[home].length > 0 || occupied[home];
          if (strategy === 'linear') {
            let probe = 0;
            while (occupied[target] && probe < bucketCount) {
              target = (target + 1) % bucketCount;
              probe += 1;
            }
          }
          if (collided) collisions += 1;
          occupied[target] = true;
          buckets[target].push({ key, home, collided });
        });
        return { buckets, collisions };
      }

      function render() {
        const state = buildBuckets();
        keyList.innerHTML = allKeys.map((key, index) => `<div class="lf-key${index >= inserted ? ' pending' : ''}">${key}</div>`).join('');
        grid.innerHTML = state.buckets.map((items, index) => {
          const hot = items.some((item) => item.collided);
          const chain = items.length
            ? items.map((item) => `<span class="lf-chip${item.collided ? ' collision' : ''}">${item.key}${item.home !== index ? ` -> ${index}` : ''}</span>`).join('')
            : '<span class="lf-empty">空</span>';
          return `<div class="lf-bucket${hot ? ' hot' : ''}"><span class="lf-bucket-index">bucket ${index}</span><div class="lf-chain">${chain}</div></div>`;
        }).join('');
        insertedNode.textContent = inserted;
        collisionNode.textContent = state.collisions;
        loadNode.textContent = (inserted / bucketCount).toFixed(2);
        strategyNode.textContent = strategy === 'linear' ? '线性探测' : '链地址';
        log.textContent = state.collisions > 0
          ? `已经出现 ${state.collisions} 次冲突：不同 key 的 home bucket 相同，需要使用${strategy === 'linear' ? '探测序列寻找空位' : '链表挂在同一 bucket'}。`
          : '当前还没有冲突，继续插入会提高负载因子。';
      }

      root.addEventListener('click', (event) => {
        const action = event.target && event.target.dataset ? event.target.dataset.action : '';
        if (action === 'next') {
          inserted = Math.min(allKeys.length, inserted + 1);
          render();
        }
        if (action === 'reset') {
          inserted = 3;
          render();
        }
      });
      root.addEventListener('change', (event) => {
        const role = event.target && event.target.dataset ? event.target.dataset.role : '';
        if (role === 'strategy') strategy = event.target.value;
        if (role === 'buckets') bucketCount = Number(event.target.value);
        render();
      });
      render();
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)

    def pigeonhole_demo_widget(self, topic: str) -> str:
        title = escape(topic or "抽屉原理")
        template = """
<section class="lf-pigeon-demo" data-learnforge-widget="pigeonhole-demo">
  <style>
    .lf-pigeon-demo{--ink:#111827;--muted:#64748b;--line:#dbe4f0;--blue:#2563eb;--amber:#f59e0b;--green:#059669;font-family:"Avenir Next","PingFang SC",ui-sans-serif,system-ui;color:var(--ink);background:linear-gradient(135deg,#f7fbff,#fff8eb 60%,#f4fff7);border:1px solid #dce7f4;border-radius:18px;padding:22px;min-height:430px;box-sizing:border-box}
    .lf-pigeon-demo h2{margin:0;font-size:25px}.lf-pigeon-demo p{margin:8px 0 0;color:var(--muted);font-size:13px;line-height:1.6}
    .lf-pigeon-controls{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}.lf-pigeon-control{background:#fff;border:1px solid #dbe4f0;border-radius:12px;padding:10px;min-width:150px}.lf-pigeon-control label{display:block;font-size:12px;color:#64748b;font-weight:800;margin-bottom:6px}.lf-pigeon-control input{width:100%}
    .lf-drawer-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.lf-drawer{border:1px solid #e2e8f0;border-radius:14px;background:#fff;padding:10px;min-height:118px}.lf-drawer.hot{border-color:#f59e0b;background:#fffbeb}.lf-drawer strong{display:block;margin-bottom:8px}.lf-items{display:flex;flex-wrap:wrap;gap:6px}.lf-item{width:26px;height:26px;border-radius:8px;background:#dbeafe;color:#1e3a8a;display:grid;place-items:center;font-size:12px;font-weight:900}.lf-drawer.hot .lf-item{background:#fed7aa;color:#9a3412}
    .lf-pigeon-summary{margin-top:12px;border-left:4px solid #f59e0b;background:#fffbeb;color:#92400e;border-radius:10px;padding:10px;font-size:13px;font-weight:850;line-height:1.55}
    @media(max-width:760px){.lf-drawer-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
  </style>
  <h2>__TITLE__可视化</h2>
  <p>把 n 个对象放进 m 个抽屉，只要对象数量超过抽屉容量的平均分配上限，就必然出现某个抽屉拥挤。</p>
  <div class="lf-pigeon-controls">
    <div class="lf-pigeon-control"><label>对象数量 <span data-role="item-count">9</span></label><input data-role="items" type="range" min="5" max="14" value="9"></div>
    <div class="lf-pigeon-control"><label>抽屉数量 <span data-role="drawer-count">4</span></label><input data-role="drawers" type="range" min="2" max="6" value="4"></div>
  </div>
  <div class="lf-drawer-grid" data-role="drawer-grid">
    <div class="lf-drawer hot"><strong>抽屉 1</strong><div class="lf-items"><span class="lf-item">1</span><span class="lf-item">5</span><span class="lf-item">9</span></div></div>
    <div class="lf-drawer"><strong>抽屉 2</strong><div class="lf-items"><span class="lf-item">2</span><span class="lf-item">6</span></div></div>
    <div class="lf-drawer"><strong>抽屉 3</strong><div class="lf-items"><span class="lf-item">3</span><span class="lf-item">7</span></div></div>
    <div class="lf-drawer"><strong>抽屉 4</strong><div class="lf-items"><span class="lf-item">4</span><span class="lf-item">8</span></div></div>
  </div>
  <div class="lf-pigeon-summary" data-role="summary">9 个对象放进 4 个抽屉，至少有一个抽屉包含 3 个对象。</div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-pigeon-demo');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const grid = root.querySelector('[data-role="drawer-grid"]');
      const summary = root.querySelector('[data-role="summary"]');
      const itemLabel = root.querySelector('[data-role="item-count"]');
      const drawerLabel = root.querySelector('[data-role="drawer-count"]');
      const itemsInput = root.querySelector('[data-role="items"]');
      const drawersInput = root.querySelector('[data-role="drawers"]');
      function render() {
        const items = Number(itemsInput.value);
        const drawers = Number(drawersInput.value);
        const slots = Array.from({ length: drawers }, () => []);
        for (let i = 1; i <= items; i += 1) slots[(i - 1) % drawers].push(i);
        const max = Math.max(...slots.map((slot) => slot.length));
        const threshold = Math.floor((items - 1) / drawers) + 1;
        itemLabel.textContent = items;
        drawerLabel.textContent = drawers;
        grid.innerHTML = slots.map((slot, index) => `<div class="lf-drawer${slot.length === max ? ' hot' : ''}"><strong>抽屉 ${index + 1}</strong><div class="lf-items">${slot.map((item) => `<span class="lf-item">${item}</span>`).join('')}</div></div>`).join('');
        summary.textContent = `${items} 个对象放进 ${drawers} 个抽屉，至少有一个抽屉包含 ${threshold} 个对象；当前高亮抽屉就是这个必然拥挤的证据。`;
      }
      root.addEventListener('input', render);
      render();
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)

    def quadratic_demo_widget(self, topic: str) -> str:
        title = escape(topic or "二次函数")
        template = """
<section class="lf-quad-demo" data-learnforge-widget="quadratic-demo">
  <style>
    .lf-quad-demo{--bg:#10151d;--panel:#f7f1e3;--paper:#fffaf0;--ink:#171717;--muted:#6c6152;--line:#d8c8aa;--red:#c2412d;--blue:#1f6f8b;--green:#2f7d57;--gold:#d4912a;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;color:var(--ink);background:linear-gradient(135deg,#f8f1df,#e8f2ef 56%,#f5e7d3);border:1px solid #d8c8aa;border-radius:18px;padding:20px;min-height:680px;box-sizing:border-box;box-shadow:0 22px 58px rgba(49,38,22,.16)}
    .lf-quad-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:start;margin-bottom:14px}
    .lf-quad-kicker{font-size:12px;font-weight:900;color:var(--blue);letter-spacing:.08em;text-transform:uppercase}
    .lf-quad-title{margin:4px 0 6px;font-family:Georgia,"Songti SC",serif;font-size:34px;line-height:1.05;letter-spacing:0}
    .lf-quad-sub{margin:0;color:var(--muted);font-size:13px;line-height:1.7;max-width:740px}
    .lf-quad-equation{border:1px solid var(--line);border-radius:12px;background:rgba(255,250,240,.82);padding:12px 14px;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:18px;font-weight:900;white-space:nowrap;color:#15212b}
    .lf-quad-grid{display:grid;grid-template-columns:minmax(260px,.34fr) minmax(0,.66fr);gap:14px}
    .lf-quad-controls,.lf-quad-panel{border:1px solid var(--line);border-radius:16px;background:rgba(255,250,240,.76);padding:14px;box-sizing:border-box}
    .lf-quad-controls{display:grid;gap:12px;align-content:start}
    .lf-quad-control label{display:flex;justify-content:space-between;gap:10px;font-weight:900;font-size:13px;margin-bottom:6px;color:#2b241a}
    .lf-quad-control input{width:100%;accent-color:var(--red)}
    .lf-quad-buttons{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .lf-quad-buttons button{min-height:38px;border:0;border-radius:10px;background:#1f6f8b;color:#fff;font-weight:900;cursor:pointer}
    .lf-quad-buttons button:nth-child(2){background:#8b5a2b}.lf-quad-buttons button:nth-child(3){background:#2f7d57}.lf-quad-buttons button:nth-child(4){background:#52525b}
    .lf-quad-play{grid-column:1/-1!important;background:#c2412d!important}
    .lf-quad-readouts{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .lf-quad-metric{border:1px solid #e2d5bc;border-radius:12px;background:#fffaf0;padding:10px}
    .lf-quad-metric small{display:block;color:var(--muted);font-size:12px;margin-bottom:3px}.lf-quad-metric strong{font-size:19px;line-height:1}
    .lf-quad-stage{position:relative;min-height:500px;overflow:hidden;border:1px solid #cab997;border-radius:16px;background:linear-gradient(180deg,#fffaf0,#ecf3ef)}
    .lf-quad-svg{display:block;width:100%;height:500px}
    .lf-quad-axis{stroke:#8a7b65;stroke-width:1.2}.lf-quad-gridline{stroke:#d7c8aa;stroke-width:.8;opacity:.7}.lf-quad-curve{fill:none;stroke:#c2412d;stroke-width:4;stroke-linecap:round}.lf-quad-focus{fill:#1f6f8b;stroke:#fffaf0;stroke-width:4}.lf-quad-vertex{fill:#2f7d57;stroke:#fffaf0;stroke-width:4}.lf-quad-root{fill:#d4912a;stroke:#fffaf0;stroke-width:3}.lf-quad-guide{stroke:#2f7d57;stroke-dasharray:6 6;stroke-width:1.4}
    .lf-quad-label{font-family:"SFMono-Regular",ui-monospace,monospace;font-size:12px;fill:#34291f;font-weight:800}
    .lf-quad-callout{position:absolute;right:14px;top:14px;max-width:250px;border:1px solid rgba(31,111,139,.28);border-radius:14px;background:rgba(255,250,240,.9);padding:12px;color:#2b241a;box-shadow:0 14px 30px rgba(58,43,24,.1)}
    .lf-quad-callout strong{display:block;margin-bottom:5px}.lf-quad-callout p{margin:0;color:var(--muted);font-size:12px;line-height:1.55}
    .lf-quad-notes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:12px}
    .lf-quad-note{border:1px solid var(--line);border-radius:14px;background:rgba(255,250,240,.78);padding:12px;min-height:88px}.lf-quad-note strong{display:block;margin-bottom:6px}.lf-quad-note p{margin:0;color:var(--muted);font-size:12px;line-height:1.55}
    @media(max-width:860px){.lf-quad-head,.lf-quad-grid,.lf-quad-notes{grid-template-columns:1fr}.lf-quad-equation{white-space:normal}.lf-quad-stage{min-height:420px}.lf-quad-svg{height:420px}}
  </style>
  <div class="lf-quad-head">
    <div>
      <div class="lf-quad-kicker">LearnForge Function Studio</div>
      <h2 class="lf-quad-title">__TITLE__动态模型</h2>
      <p class="lf-quad-sub">拖动系数，直接观察开口、顶点、对称轴、根和函数值如何联动。这个模型只围绕二次函数本身，避免混入无关算法语境。</p>
    </div>
    <div class="lf-quad-equation" data-role="equation">y = 1.00x² + 0.00x + 0.00</div>
  </div>
  <div class="lf-quad-grid">
    <aside class="lf-quad-controls">
      <div class="lf-quad-control"><label>二次项 a <span data-value="a">1.00</span></label><input data-param="a" type="range" min="-3" max="3" step="0.05" value="1"></div>
      <div class="lf-quad-control"><label>一次项 b <span data-value="b">0.00</span></label><input data-param="b" type="range" min="-6" max="6" step="0.1" value="0"></div>
      <div class="lf-quad-control"><label>常数项 c <span data-value="c">0.00</span></label><input data-param="c" type="range" min="-8" max="8" step="0.1" value="0"></div>
      <div class="lf-quad-control"><label>观察点 x <span data-value="x">1.50</span></label><input data-param="x" type="range" min="-6" max="6" step="0.05" value="1.5"></div>
      <div class="lf-quad-buttons">
        <button class="lf-quad-play" type="button" data-action="play">播放系数变形动画</button>
        <button type="button" data-preset="standard">标准开口</button>
        <button type="button" data-preset="shift">顶点平移</button>
        <button type="button" data-preset="roots">双根示例</button>
        <button type="button" data-preset="flat">宽抛物线</button>
      </div>
      <div class="lf-quad-readouts">
        <div class="lf-quad-metric"><small>顶点</small><strong data-metric="vertex">(0, 0)</strong></div>
        <div class="lf-quad-metric"><small>对称轴</small><strong data-metric="axis">x = 0</strong></div>
        <div class="lf-quad-metric"><small>判别式</small><strong data-metric="disc">0</strong></div>
        <div class="lf-quad-metric"><small>当前 y</small><strong data-metric="y">2.25</strong></div>
      </div>
    </aside>
    <div class="lf-quad-panel">
      <div class="lf-quad-stage">
        <svg class="lf-quad-svg" data-role="svg" viewBox="0 0 760 500" role="img" aria-label="二次函数抛物线动态图像"></svg>
        <div class="lf-quad-callout"><strong data-role="state-title">开口向上，有最小值</strong><p data-role="state-copy">a 决定开口方向与宽窄；顶点给出函数的最小值或最大值。</p></div>
      </div>
    </div>
  </div>
  <div class="lf-quad-notes">
    <article class="lf-quad-note"><strong>看 a</strong><p>a &gt; 0 开口向上，a &lt; 0 开口向下；|a| 越大，曲线越窄。</p></article>
    <article class="lf-quad-note"><strong>看顶点</strong><p>顶点横坐标是 -b / 2a，对称轴穿过顶点。</p></article>
    <article class="lf-quad-note"><strong>看判别式</strong><p>b² - 4ac 大于 0 有两个实根，等于 0 有一个重根，小于 0 没有实根。</p></article>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-quad-demo');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const svg = root.querySelector('[data-role="svg"]');
      const inputs = Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map((input) => [input.dataset.param, input]));
      const valueNodes = Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map((node) => [node.dataset.value, node]));
      const metrics = Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map((node) => [node.dataset.metric, node]));
      const equation = root.querySelector('[data-role="equation"]');
      const stateTitle = root.querySelector('[data-role="state-title"]');
      const stateCopy = root.querySelector('[data-role="state-copy"]');
      const W = 760, H = 500, xMin = -6, xMax = 6, yMin = -10, yMax = 10;
      let animationFrame = 0;
      let animationStart = 0;
      let isDraggingPoint = false;
      const sx = (x) => ((x - xMin) / (xMax - xMin)) * W;
      const sy = (y) => H - ((y - yMin) / (yMax - yMin)) * H;
      const xFromClient = (clientX) => {
        const rect = svg.getBoundingClientRect();
        return Math.max(xMin, Math.min(xMax, xMin + ((clientX - rect.left) / rect.width) * (xMax - xMin)));
      };
      const fmt = (n, d = 2) => Number(n).toFixed(d).replace(/-0\\.00|^-0$/, '0');
      const f = (x, a, b, c) => a * x * x + b * x + c;
      function state() {
        const a = Number(inputs.a.value) || 0.01;
        return { a: Math.abs(a) < 0.05 ? 0.05 : a, b: Number(inputs.b.value), c: Number(inputs.c.value), x: Number(inputs.x.value) };
      }
      function roots(a, b, c) {
        const d = b * b - 4 * a * c;
        if (d < 0) return [];
        const s = Math.sqrt(d);
        return [(-b - s) / (2 * a), (-b + s) / (2 * a)].filter((x) => x >= xMin && x <= xMax);
      }
      function grid() {
        let out = '';
        for (let x = xMin; x <= xMax; x += 1) out += `<line class="lf-quad-gridline" x1="${sx(x)}" y1="0" x2="${sx(x)}" y2="${H}"></line>`;
        for (let y = yMin; y <= yMax; y += 2) out += `<line class="lf-quad-gridline" x1="0" y1="${sy(y)}" x2="${W}" y2="${sy(y)}"></line>`;
        out += `<line class="lf-quad-axis" x1="0" y1="${sy(0)}" x2="${W}" y2="${sy(0)}"></line><line class="lf-quad-axis" x1="${sx(0)}" y1="0" x2="${sx(0)}" y2="${H}"></line>`;
        return out;
      }
      function render() {
        const { a, b, c, x } = state();
        inputs.a.value = a;
        const vx = -b / (2 * a);
        const vy = f(vx, a, b, c);
        const y = f(x, a, b, c);
        const disc = b * b - 4 * a * c;
        const points = [];
        for (let i = 0; i <= 180; i += 1) {
          const px = xMin + (i / 180) * (xMax - xMin);
          const py = f(px, a, b, c);
          points.push(`${sx(px).toFixed(1)},${sy(Math.max(yMin, Math.min(yMax, py))).toFixed(1)}`);
        }
        valueNodes.a.textContent = fmt(a);
        valueNodes.b.textContent = fmt(b);
        valueNodes.c.textContent = fmt(c);
        valueNodes.x.textContent = fmt(x);
        equation.textContent = `y = ${fmt(a)}x² ${b >= 0 ? '+' : '-'} ${fmt(Math.abs(b))}x ${c >= 0 ? '+' : '-'} ${fmt(Math.abs(c))}`;
        metrics.vertex.textContent = `(${fmt(vx)}, ${fmt(vy)})`;
        metrics.axis.textContent = `x = ${fmt(vx)}`;
        metrics.disc.textContent = fmt(disc);
        metrics.y.textContent = fmt(y);
        stateTitle.textContent = a > 0 ? '开口向上，有最小值' : '开口向下，有最大值';
        stateCopy.textContent = disc > 0 ? '曲线与 x 轴有两个交点，两个实根都被标成金色。' : disc === 0 ? '曲线刚好贴住 x 轴，顶点就是重根。' : '曲线没有穿过 x 轴，因此没有实数根。';
        const rootMarks = roots(a, b, c).map((rx) => `<circle class="lf-quad-root" cx="${sx(rx)}" cy="${sy(0)}" r="7"></circle><text class="lf-quad-label" x="${sx(rx) + 8}" y="${sy(0) - 8}">根 ${fmt(rx)}</text>`).join('');
        svg.innerHTML = `${grid()}<line class="lf-quad-guide" x1="${sx(vx)}" y1="0" x2="${sx(vx)}" y2="${H}"></line><polyline class="lf-quad-curve" points="${points.join(' ')}"></polyline>${rootMarks}<circle class="lf-quad-vertex" cx="${sx(vx)}" cy="${sy(Math.max(yMin, Math.min(yMax, vy)))}" r="8"></circle><circle class="lf-quad-focus" data-drag-point="x" cx="${sx(x)}" cy="${sy(Math.max(yMin, Math.min(yMax, y)))}" r="10"></circle><line class="lf-quad-guide" x1="${sx(x)}" y1="${sy(0)}" x2="${sx(x)}" y2="${sy(Math.max(yMin, Math.min(yMax, y)))}"></line><text class="lf-quad-label" x="${sx(vx) + 10}" y="22">对称轴</text><text class="lf-quad-label" x="${sx(x) + 10}" y="${sy(Math.max(yMin, Math.min(yMax, y))) - 12}">拖拽观察点 (${fmt(x)}, ${fmt(y)})</text>`;
      }
      function stopAnimation() {
        if (animationFrame) cancelAnimationFrame(animationFrame);
        animationFrame = 0;
        animationStart = 0;
        const play = root.querySelector('[data-action="play"]');
        if (play) play.textContent = '播放系数变形动画';
      }
      function playAnimation(now = performance.now()) {
        if (!animationStart) animationStart = now;
        const t = (now - animationStart) / 1000;
        inputs.a.value = (1.45 * Math.sin(t * 0.72) + 0.25).toFixed(2);
        inputs.b.value = (4.2 * Math.sin(t * 0.48 + 1.3)).toFixed(2);
        inputs.c.value = (4.8 * Math.cos(t * 0.64)).toFixed(2);
        inputs.x.value = (5.2 * Math.sin(t * 0.95)).toFixed(2);
        render();
        animationFrame = requestAnimationFrame(playAnimation);
      }
      const presets = {
        standard: { a: 1, b: 0, c: 0, x: 1.5 },
        shift: { a: 0.8, b: -3.2, c: 1.4, x: 2.6 },
        roots: { a: 0.7, b: -1.4, c: -4.2, x: -2 },
        flat: { a: -0.28, b: 1.4, c: 4.6, x: 4 }
      };
      root.addEventListener('input', render);
      root.addEventListener('click', (event) => {
        if (event.target && event.target.dataset && event.target.dataset.action === 'play') {
          if (animationFrame) {
            stopAnimation();
          } else {
            event.target.textContent = '停止动画';
            animationFrame = requestAnimationFrame(playAnimation);
          }
          return;
        }
        const preset = event.target && event.target.dataset ? event.target.dataset.preset : '';
        if (!preset || !presets[preset]) return;
        stopAnimation();
        Object.entries(presets[preset]).forEach(([key, value]) => { inputs[key].value = value; });
        render();
      });
      svg.addEventListener('pointerdown', (event) => {
        stopAnimation();
        isDraggingPoint = true;
        inputs.x.value = xFromClient(event.clientX).toFixed(2);
        render();
        svg.setPointerCapture(event.pointerId);
      });
      svg.addEventListener('pointermove', (event) => {
        if (!isDraggingPoint) return;
        inputs.x.value = xFromClient(event.clientX).toFixed(2);
        render();
      });
      svg.addEventListener('pointerup', () => { isDraggingPoint = false; });
      svg.addEventListener('pointercancel', () => { isDraggingPoint = false; });
      render();
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)


    def momentum_collision_demo_widget(self, topic: str) -> str:
        title = escape(topic or "动量守恒")
        template = """
<section class="lf-momentum-demo" data-learnforge-widget="momentum-demo">
  <style>
    .lf-momentum-demo{--ink:#f8fafc;--muted:#a8b3c7;--line:rgba(255,255,255,.16);--cyan:#22d3ee;--amber:#f59e0b;--rose:#fb7185;--green:#86efac;font-family:"Avenir Next","PingFang SC",ui-sans-serif,system-ui;color:var(--ink);background:radial-gradient(circle at 18% 8%,rgba(34,211,238,.18),transparent 28%),radial-gradient(circle at 82% 10%,rgba(134,239,172,.12),transparent 24%),linear-gradient(135deg,#07111f,#111827 60%,#06151c);border:1px solid rgba(148,163,184,.25);padding:18px;box-sizing:border-box;min-height:0;overflow:auto}
    .lf-momentum-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:end;margin-bottom:12px}
    .lf-momentum-kicker{font-size:12px;font-weight:950;color:var(--cyan);letter-spacing:.12em;text-transform:uppercase}
    .lf-momentum-head h2{margin:5px 0 6px;font-size:28px;line-height:1.05}
    .lf-momentum-head p{margin:0;color:var(--muted);font-size:13px;line-height:1.6;max-width:760px}
    .lf-momentum-formula{border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.07);padding:10px 14px;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:15px;font-weight:900;white-space:nowrap}
    .lf-momentum-grid{display:grid;grid-template-columns:280px minmax(0,1fr) 250px;gap:14px;min-height:0}
    .lf-momentum-panel{border:1px solid var(--line);border-radius:14px;background:rgba(8,13,24,.72);backdrop-filter:blur(10px);padding:14px;box-sizing:border-box;overflow:auto}
    .lf-momentum-panel h3{margin:0 0 10px;font-size:15px}
    .lf-momentum-control{display:grid;gap:6px;margin-bottom:12px}
    .lf-momentum-control label{display:flex;justify-content:space-between;color:var(--muted);font-size:12px;font-weight:900}
    .lf-momentum-control input{width:100%;accent-color:var(--cyan)}
    .lf-momentum-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
    .lf-momentum-actions button{min-height:38px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,var(--cyan),#60a5fa);color:#04111d;font-weight:950;cursor:pointer}
    .lf-momentum-actions button.secondary{background:rgba(255,255,255,.10);color:var(--ink)}
    .lf-momentum-stage{position:relative;min-height:0;border:1px solid rgba(34,211,238,.22);border-radius:14px;background:linear-gradient(180deg,rgba(8,13,24,.70),rgba(3,7,18,.96));overflow:hidden}
    .lf-momentum-canvas{display:block;width:100%;height:100%}
    .lf-momentum-metrics{display:grid;grid-template-columns:1fr;gap:8px}
    .lf-momentum-metric{border:1px solid rgba(255,255,255,.11);border-radius:12px;background:rgba(255,255,255,.06);padding:10px}
    .lf-momentum-metric small{display:block;color:var(--muted);font-size:11px}
    .lf-momentum-metric strong{font-size:17px}
    .lf-momentum-note{margin-top:10px;border-left:3px solid var(--green);background:rgba(134,239,172,.08);border-radius:10px;padding:10px;color:#dbeafe;font-size:12px;line-height:1.55}
    @media(max-width:980px){.lf-momentum-grid{grid-template-columns:1fr}.lf-momentum-formula{white-space:normal}.lf-momentum-canvas{height:400px}.lf-momentum-stage{min-height:400px}}
  </style>
  <div class="lf-momentum-head">
    <div>
      <div class="lf-momentum-kicker">Collision Momentum Lab</div>
      <h2>__TITLE__ 碰撞与动量守恒实验室</h2>
      <p>调节两个方块的质量和速度，观察碰撞前后的速度变化、动量守恒和动能损失。Canvas 实时渲染碰撞动画。</p>
    </div>
    <div class="lf-momentum-formula" data-role="formula">p = m1v1 + m2v2 = 常量</div>
  </div>
  <div class="lf-momentum-grid">
    <aside class="lf-momentum-panel">
      <h3>物体参数</h3>
      <div class="lf-momentum-control"><label>A 质量 m1 <span data-value="m1">2.0</span></label><input data-param="m1" type="range" min="0.5" max="6" step="0.1" value="2"></div>
      <div class="lf-momentum-control"><label>A 初速度 v1 <span data-value="v1">4.0</span></label><input data-param="v1" type="range" min="-6" max="6" step="0.1" value="4"></div>
      <div class="lf-momentum-control"><label>B 质量 m2 <span data-value="m2">3.0</span></label><input data-param="m2" type="range" min="0.5" max="6" step="0.1" value="3"></div>
      <div class="lf-momentum-control"><label>B 初速度 v2 <span data-value="v2">-2.0</span></label><input data-param="v2" type="range" min="-6" max="6" step="0.1" value="-2"></div>
      <div class="lf-momentum-control"><label>恢复系数 e <span data-value="e">1.00</span></label><input data-param="e" type="range" min="0" max="1" step="0.05" value="1"></div>
      <div class="lf-momentum-actions"><button type="button" data-action="play">播放碰撞</button><button class="secondary" type="button" data-action="reset">重置场景</button></div>
    </aside>
    <div class="lf-momentum-stage"><canvas class="lf-momentum-canvas" data-role="canvas"></canvas></div>
    <aside class="lf-momentum-panel">
      <h3>守恒读数</h3>
      <div class="lf-momentum-metrics">
        <div class="lf-momentum-metric"><small>碰撞后速度</small><strong data-metric="after">v1'=0, v2'=0</strong></div>
        <div class="lf-momentum-metric"><small>总动量 (前/后)</small><strong data-metric="momentum">0 / 0</strong></div>
        <div class="lf-momentum-metric"><small>总动能 (前/后)</small><strong data-metric="energy">0 / 0</strong></div>
        <div class="lf-momentum-metric"><small>碰撞类型</small><strong data-metric="type">完全弹性</strong></div>
      </div>
      <div class="lf-momentum-note" data-role="note">拖动画布中的方块改变位置。e=1 时动能守恒，减小 e 动能会损失。</div>
    </aside>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-momentum-demo');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const canvas = root.querySelector('[data-role="canvas"]'), ctx = canvas.getContext('2d');
      const inputs = Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(i => [i.dataset.param, i]));
      const values = Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(n => [n.dataset.value, n]));
      const metrics = Object.fromEntries(Array.from(root.querySelectorAll('[data-metric]')).map(n => [n.dataset.metric, n]));
      const phase = root.querySelector('[data-role="formula"]');
      let raf = 0, last = 0, running = false, collided = false, drag = null;
      let boxA = { x: -3.4, v: 4 }, boxB = { x: 3.2, v: -2 };
      const fmt = (n, d = 2) => Number(n).toFixed(d).replace(/-0\\.00|\\.00$/g, '0');
      function params() { return { m1: Number(inputs.m1.value), v1: Number(inputs.v1.value), m2: Number(inputs.m2.value), v2: Number(inputs.v2.value), e: Number(inputs.e.value) }; }
      function post(p) {
        p = p || params();
        const v1 = (p.m1 * p.v1 + p.m2 * p.v2 - p.m2 * p.e * (p.v1 - p.v2)) / (p.m1 + p.m2);
        const v2 = (p.m1 * p.v1 + p.m2 * p.v2 + p.m1 * p.e * (p.v1 - p.v2)) / (p.m1 + p.m2);
        return { v1, v2 };
      }
      function energy(m, v) { return 0.5 * m * v * v; }
      function resetScene() { const p = params(); boxA = { x: -3.4, v: p.v1 }; boxB = { x: 3.2, v: p.v2 }; collided = false; update(); draw(); }
      function update() {
        const p = params(), q = post(p), p0 = p.m1 * p.v1 + p.m2 * p.v2, p1 = p.m1 * q.v1 + p.m2 * q.v2;
        const k0 = energy(p.m1, p.v1) + energy(p.m2, p.v2), k1 = energy(p.m1, q.v1) + energy(p.m2, q.v2);
        values.m1.textContent = fmt(p.m1, 1) + ' kg'; values.v1.textContent = fmt(p.v1, 1) + ' m/s';
        values.m2.textContent = fmt(p.m2, 1) + ' kg'; values.v2.textContent = fmt(p.v2, 1) + ' m/s'; values.e.textContent = fmt(p.e);
        metrics.after.textContent = "v1'=" + fmt(q.v1) + ", v2'=" + fmt(q.v2);
        metrics.momentum.textContent = fmt(p0) + ' / ' + fmt(p1) + ' kg\\u00b7m/s';
        metrics.energy.textContent = fmt(k0) + ' / ' + fmt(k1) + ' J';
        metrics.type.textContent = p.e === 1 ? '完全弹性' : p.e === 0 ? '完全非弹性' : '部分弹性';
        phase.textContent = 'p = ' + fmt(p0) + ' kg\\u00b7m/s \\u2192 碰撞后 p = ' + fmt(p1);
      }
      function resize() { const r = canvas.getBoundingClientRect(); canvas.width = Math.max(600, Math.floor(r.width * devicePixelRatio)); canvas.height = Math.max(360, Math.floor(r.height * devicePixelRatio)); draw(); }
      function toScreen(x) { const w = canvas.width, pad = 80 * devicePixelRatio; return pad + ((x + 6) / 12) * (w - pad * 2); }
      function fromScreen(px) { const r = canvas.getBoundingClientRect(); return ((px - r.left) / r.width) * 12 - 6; }
      function widths() { const p = params(); return { a: (54 + p.m1 * 11) * devicePixelRatio, b: (54 + p.m2 * 11) * devicePixelRatio }; }
      function draw() {
        const w = canvas.width, h = canvas.height, groundY = h * 0.58, wh = widths();
        ctx.clearRect(0, 0, w, h); ctx.fillStyle = '#07111f'; ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = 'rgba(148,163,184,.14)'; ctx.lineWidth = 1 * devicePixelRatio;
        for (let x = 60 * devicePixelRatio; x < w - 60 * devicePixelRatio; x += 50 * devicePixelRatio) { ctx.beginPath(); ctx.moveTo(x, 40 * devicePixelRatio); ctx.lineTo(x, h - 40 * devicePixelRatio); ctx.stroke(); }
        ctx.strokeStyle = 'rgba(226,232,240,.48)'; ctx.lineWidth = 2.5 * devicePixelRatio; ctx.beginPath(); ctx.moveTo(40 * devicePixelRatio, groundY + 62 * devicePixelRatio); ctx.lineTo(w - 40 * devicePixelRatio, groundY + 62 * devicePixelRatio); ctx.stroke();
        const ax = toScreen(boxA.x) - wh.a / 2, bx = toScreen(boxB.x) - wh.b / 2, bh = 64 * devicePixelRatio;
        const gradA = ctx.createLinearGradient(0, groundY - bh, 0, groundY); gradA.addColorStop(0, '#67e8f9'); gradA.addColorStop(1, '#2563eb');
        const gradB = ctx.createLinearGradient(0, groundY - bh, 0, groundY); gradB.addColorStop(0, '#86efac'); gradB.addColorStop(1, '#15803d');
        ctx.fillStyle = gradA; ctx.beginPath(); ctx.roundRect(ax, groundY - bh, wh.a, bh, 12 * devicePixelRatio); ctx.fill();
        ctx.fillStyle = gradB; ctx.beginPath(); ctx.roundRect(bx, groundY - bh, wh.b, bh, 12 * devicePixelRatio); ctx.fill();
        ctx.fillStyle = '#06111c'; ctx.font = (16 * devicePixelRatio) + 'px sans-serif'; ctx.textAlign = 'center'; ctx.fillText('A', ax + wh.a / 2, groundY - bh / 2 + 5 * devicePixelRatio); ctx.fillText('B', bx + wh.b / 2, groundY - bh / 2 + 5 * devicePixelRatio);
        const arrowFn = function(cx, cy, v, color) {
          const len = Math.max(18, Math.min(110, Math.abs(v) * 22)) * devicePixelRatio, dir = v >= 0 ? 1 : -1;
          ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 4 * devicePixelRatio;
          ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + dir * len, cy); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(cx + dir * len, cy); ctx.lineTo(cx + dir * (len - 12 * devicePixelRatio), cy - 7 * devicePixelRatio); ctx.lineTo(cx + dir * (len - 12 * devicePixelRatio), cy + 7 * devicePixelRatio); ctx.closePath(); ctx.fill();
        };
        arrowFn(ax + wh.a / 2, groundY - bh - 24 * devicePixelRatio, boxA.v, '#22d3ee');
        arrowFn(bx + wh.b / 2, groundY - bh - 24 * devicePixelRatio, boxB.v, '#86efac');
        if (collided) { ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 3 * devicePixelRatio; ctx.setLineDash([6, 4]); ctx.beginPath(); ctx.arc((ax + wh.a + bx) / 2, groundY - bh / 2, 38 * devicePixelRatio, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]); }
        ctx.fillStyle = 'rgba(226,232,240,.78)'; ctx.font = (13 * devicePixelRatio) + 'px monospace'; ctx.textAlign = 'center'; ctx.fillText('一维碰撞轨道 \\u00b7 拖拽方块改变位置', w / 2, h - 20 * devicePixelRatio);
      }
      function step(t) { if (!running) return; if (!last) last = t; var dt = Math.min(0.032, (t - last) / 1000); last = t; boxA.x += boxA.v * dt * 0.62; boxB.x += boxB.v * dt * 0.62; var wh = widths(), scale = 12 / (canvas.width - 140 * devicePixelRatio), gap = (wh.a / 2 + wh.b / 2) * scale; if (!collided && boxA.x + gap >= boxB.x && boxA.v > boxB.v) { var q = post(); boxA.v = q.v1; boxB.v = q.v2; boxA.x = boxB.x - gap; collided = true; update(); } draw(); raf = requestAnimationFrame(step); }
      function play() { if (running) { running = false; cancelAnimationFrame(raf); root.querySelector('[data-action="play"]').textContent = '播放碰撞'; return; } running = true; root.querySelector('[data-action="play"]').textContent = '暂停'; raf = requestAnimationFrame(step); }
      root.addEventListener('input', function() { running = false; if (raf) cancelAnimationFrame(raf); root.querySelector('[data-action="play"]').textContent = '播放碰撞'; resetScene(); });
      root.addEventListener('click', function(e) { var a = e.target && e.target.dataset ? e.target.dataset.action : ''; if (a === 'play') play(); if (a === 'reset') { running = false; if (raf) cancelAnimationFrame(raf); root.querySelector('[data-action="play"]').textContent = '播放碰撞'; resetScene(); } });
      canvas.addEventListener('pointerdown', function(e) { running = false; if (raf) cancelAnimationFrame(raf); var wh = widths(), r = canvas.getBoundingClientRect(), sy = canvas.height * 0.58 / devicePixelRatio - 64; var ax = toScreen(boxA.x) / devicePixelRatio - wh.a / devicePixelRatio / 2, bx = toScreen(boxB.x) / devicePixelRatio - wh.b / devicePixelRatio / 2; if (e.clientY - r.top > sy - 18 && e.clientY - r.top < sy + 92) { if (e.clientX - r.left > ax && e.clientX - r.left < ax + wh.a / devicePixelRatio) drag = 'a'; else if (e.clientX - r.left > bx && e.clientX - r.left < bx + wh.b / devicePixelRatio) drag = 'b'; } if (drag) canvas.setPointerCapture(e.pointerId); });
      canvas.addEventListener('pointermove', function(e) { if (!drag) return; var x = Math.max(-5.4, Math.min(5.4, fromScreen(e.clientX))); if (drag === 'a') boxA.x = Math.min(x, boxB.x - 0.55); else boxB.x = Math.max(x, boxA.x + 0.55); collided = false; update(); draw(); });
      canvas.addEventListener('pointerup', function() { drag = null; }); canvas.addEventListener('pointercancel', function() { drag = null; });
      window.addEventListener('resize', resize); resize(); resetScene();
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)

    def rubik_cube_demo_widget(self, topic: str) -> str:
        title = escape(topic or "三阶魔方还原")
        template = """
<section class="lf-rubik-demo" data-learnforge-widget="rubik-cube-demo">
  <style>
    .lf-rubik-demo{--ink:#111827;--muted:#586174;--line:#d8e0ec;--paper:#fffdf7;--panel:#f7fafc;--blue:#2563eb;--cyan:#0891b2;--red:#dc2626;--orange:#f97316;--green:#16a34a;--yellow:#eab308;font-family:"Avenir Next","PingFang SC",ui-sans-serif,system-ui;color:var(--ink);background:linear-gradient(135deg,#f8fbff 0%,#fff7e8 54%,#f1fff6 100%);border:1px solid #dbe6f3;border-radius:18px;box-sizing:border-box;min-height:680px;padding:18px;box-shadow:0 20px 50px rgba(31,58,104,.12)}
    .lf-rubik-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:start;margin-bottom:14px}
    .lf-rubik-kicker{font-size:12px;font-weight:900;color:#0f766e;letter-spacing:.08em;text-transform:uppercase}
    .lf-rubik-title{font-size:26px;line-height:1.18;margin:4px 0 6px;letter-spacing:0}
    .lf-rubik-sub{margin:0;color:var(--muted);font-size:13px;line-height:1.65;max-width:860px}
    .lf-rubik-badges{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
    .lf-rubik-badge{border:1px solid #cbd5e1;border-radius:999px;padding:6px 10px;background:rgba(255,255,255,.76);font-size:12px;font-weight:850;white-space:nowrap}
    .lf-rubik-app{display:grid;grid-template-columns:minmax(250px,320px) minmax(0,1fr);gap:14px;align-items:stretch}
    .lf-rubik-panel,.lf-rubik-stage-wrap{border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.82);box-sizing:border-box;box-shadow:0 12px 28px rgba(43,69,111,.08)}
    .lf-rubik-panel{padding:14px;display:flex;flex-direction:column;gap:14px}
    .lf-rubik-section{border-top:1px solid #e2e8f0;padding-top:12px}
    .lf-rubik-section:first-child{border-top:0;padding-top:0}
    .lf-rubik-section h3{margin:0 0 8px;font-size:14px;letter-spacing:0;color:#1f2937}
    .lf-rubik-move-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
    .lf-rubik-demo button{border:0;border-radius:10px;padding:9px 8px;font-weight:900;font-size:12px;line-height:1.1;color:#fff;background:#2563eb;cursor:pointer;box-shadow:0 8px 18px rgba(37,99,235,.16);transition:transform .14s ease,filter .14s ease}
    .lf-rubik-demo button:hover{filter:brightness(1.04)}
    .lf-rubik-demo button:active{transform:translateY(1px)}
    .lf-rubik-demo button.secondary{background:#475569}
    .lf-rubik-demo button.warn{background:#dc2626}
    .lf-rubik-demo button.good{background:#16a34a}
    .lf-rubik-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .lf-rubik-readouts{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .lf-rubik-readout{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:9px}
    .lf-rubik-readout small{display:block;color:#64748b;font-size:11px;margin-bottom:4px}
    .lf-rubik-readout strong{font-size:18px;line-height:1}
    .lf-rubik-control{display:grid;grid-template-columns:minmax(0,1fr) 48px;gap:9px;align-items:center;margin:8px 0}
    .lf-rubik-control label{grid-column:1 / -1;color:#475569;font-size:12px;font-weight:850;display:flex;justify-content:space-between}
    .lf-rubik-control input{width:100%;accent-color:#2563eb}
    .lf-rubik-queue{min-height:42px;border:1px dashed #cbd5e1;border-radius:12px;background:#f8fafc;padding:9px;color:#334155;font-size:12px;line-height:1.45;word-break:break-word}
    .lf-rubik-note{background:#f0f9ff;border-left:4px solid #0891b2;border-radius:12px;padding:10px;color:#155e75;font-size:12px;line-height:1.58}
    .lf-rubik-stage-wrap{position:relative;overflow:hidden;min-height:560px;background:radial-gradient(circle at 48% 38%,#ffffff 0%,#eef7ff 38%,#dcecff 100%)}
    .lf-rubik-stage{position:absolute;inset:0;display:grid;place-items:center;perspective:1100px;touch-action:none;cursor:grab}
    .lf-rubik-stage:active{cursor:grabbing}
    .lf-rubik-scene{position:relative;width:330px;height:330px;transform-style:preserve-3d;transition:transform .18s ease}
    .lf-rubik-cubie{position:absolute;left:50%;top:50%;width:82px;height:82px;margin:-41px 0 0 -41px;transform-style:preserve-3d;transition:transform .32s cubic-bezier(.2,.82,.22,1)}
    .lf-rubik-cubie.pulse .lf-rubik-face{filter:brightness(1.12);box-shadow:inset 0 0 0 4px rgba(255,255,255,.64),0 0 26px rgba(37,99,235,.18)}
    .lf-rubik-face{position:absolute;inset:0;border:3px solid #111827;border-radius:8px;background:#111827;box-sizing:border-box;box-shadow:inset 0 0 0 1px rgba(255,255,255,.34);backface-visibility:hidden}
    .lf-rubik-face[data-face="x+"]{transform:rotateY(90deg) translateZ(41px)}
    .lf-rubik-face[data-face="x-"]{transform:rotateY(-90deg) translateZ(41px)}
    .lf-rubik-face[data-face="y+"]{transform:rotateX(-90deg) translateZ(41px)}
    .lf-rubik-face[data-face="y-"]{transform:rotateX(90deg) translateZ(41px)}
    .lf-rubik-face[data-face="z+"]{transform:translateZ(41px)}
    .lf-rubik-face[data-face="z-"]{transform:rotateY(180deg) translateZ(41px)}
    .lf-rubik-shadow{position:absolute;width:360px;height:74px;border-radius:999px;background:radial-gradient(ellipse,rgba(15,23,42,.22),rgba(15,23,42,0) 66%);transform:translateY(205px) rotateX(70deg);filter:blur(1px)}
    .lf-rubik-hint{position:absolute;right:14px;bottom:12px;color:#475569;background:rgba(255,255,255,.78);border:1px solid #dbe4ef;border-radius:999px;padding:7px 10px;font-size:12px;font-weight:850}
    @media(max-width:880px){.lf-rubik-head,.lf-rubik-app{grid-template-columns:1fr}.lf-rubik-badges{justify-content:flex-start}.lf-rubik-stage-wrap{min-height:460px}.lf-rubik-scene{width:270px;height:270px}.lf-rubik-cubie{width:66px;height:66px;margin:-33px 0 0 -33px}.lf-rubik-face[data-face="x+"]{transform:rotateY(90deg) translateZ(33px)}.lf-rubik-face[data-face="x-"]{transform:rotateY(-90deg) translateZ(33px)}.lf-rubik-face[data-face="y+"]{transform:rotateX(-90deg) translateZ(33px)}.lf-rubik-face[data-face="y-"]{transform:rotateX(90deg) translateZ(33px)}.lf-rubik-face[data-face="z+"]{transform:translateZ(33px)}.lf-rubik-face[data-face="z-"]{transform:rotateY(180deg) translateZ(33px)}}
  </style>
  <div class="lf-rubik-head">
    <div>
      <div class="lf-rubik-kicker">Rubik Cube Interactive Lab</div>
      <h2 class="lf-rubik-title">__TITLE__</h2>
      <p class="lf-rubik-sub">用 27 个独立小方块构建三阶魔方。点击标准转动记号、拖拽观察视角、滚轮缩放，右侧舞台不会被控制面板遮挡。</p>
    </div>
    <div class="lf-rubik-badges"><span class="lf-rubik-badge">U/D/F/B/R/L</span><span class="lf-rubik-badge">队列播放</span><span class="lf-rubik-badge">可拖拽相机</span></div>
  </div>
  <div class="lf-rubik-app">
    <aside class="lf-rubik-panel">
      <div class="lf-rubik-section">
        <h3>层转动</h3>
        <div class="lf-rubik-move-grid" aria-label="魔方转动按钮">
          <button type="button" data-move="U">U</button><button type="button" data-move="Ui">U'</button><button type="button" data-move="D">D</button><button type="button" data-move="Di">D'</button>
          <button type="button" data-move="F">F</button><button type="button" data-move="Fi">F'</button><button type="button" data-move="B">B</button><button type="button" data-move="Bi">B'</button>
          <button type="button" data-move="R">R</button><button type="button" data-move="Ri">R'</button><button type="button" data-move="L">L</button><button type="button" data-move="Li">L'</button>
        </div>
      </div>
      <div class="lf-rubik-section">
        <h3>演示控制</h3>
        <div class="lf-rubik-actions">
          <button type="button" class="good" data-action="scramble">随机打乱</button>
          <button type="button" class="secondary" data-action="undo">撤销一步</button>
          <button type="button" data-action="demo">播放还原思路</button>
          <button type="button" class="warn" data-action="reset">复原</button>
        </div>
      </div>
      <div class="lf-rubik-section">
        <h3>相机</h3>
        <div class="lf-rubik-control"><label>水平旋转 <span data-value="rotY">-34</span></label><input type="range" min="-180" max="180" value="-34" data-camera="rotY"><strong>deg</strong></div>
        <div class="lf-rubik-control"><label>俯仰角 <span data-value="rotX">-24</span></label><input type="range" min="-70" max="40" value="-24" data-camera="rotX"><strong>deg</strong></div>
        <div class="lf-rubik-control"><label>缩放 <span data-value="zoom">1.00</span></label><input type="range" min="0.72" max="1.28" step="0.01" value="1" data-camera="zoom"><strong>x</strong></div>
      </div>
      <div class="lf-rubik-section">
        <h3>状态读数</h3>
        <div class="lf-rubik-readouts">
          <div class="lf-rubik-readout"><small>当前步</small><strong data-role="step">0</strong></div>
          <div class="lf-rubik-readout"><small>最近动作</small><strong data-role="last">复原</strong></div>
          <div class="lf-rubik-readout"><small>已打乱</small><strong data-role="scramble">0</strong></div>
          <div class="lf-rubik-readout"><small>队列</small><strong data-role="queueCount">0</strong></div>
        </div>
      </div>
      <div class="lf-rubik-section">
        <h3>待播放序列</h3>
        <div class="lf-rubik-queue" data-role="queue">暂无队列。点击“随机打乱”或直接选择层转动。</div>
      </div>
      <div class="lf-rubik-note">记号说明：U=上层顺时针，R=右层顺时针，F=前层顺时针；带撇号表示反向。此 Demo 侧重空间动作可视化，不用遮挡模型的浮层。</div>
    </aside>
    <div class="lf-rubik-stage-wrap">
      <div class="lf-rubik-stage" data-role="stage" aria-label="可拖拽三维魔方舞台">
        <div class="lf-rubik-shadow"></div>
        <div class="lf-rubik-scene" data-role="scene"></div>
      </div>
      <div class="lf-rubik-hint">拖拽旋转视角 · 滚轮缩放</div>
    </div>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-rubik-demo');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const scene = root.querySelector('[data-role="scene"]');
      const stage = root.querySelector('[data-role="stage"]');
      const read = Object.fromEntries(Array.from(root.querySelectorAll('[data-role]')).map(node => [node.dataset.role, node]));
      const cameraInputs = Object.fromEntries(Array.from(root.querySelectorAll('[data-camera]')).map(node => [node.dataset.camera, node]));
      const cameraValues = Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(node => [node.dataset.value, node]));
      const colors = {'x+':'#dc2626','x-':'#f97316','y+':'#f8fafc','y-':'#eab308','z+':'#16a34a','z-':'#2563eb'};
      const faceNames = ['x+','x-','y+','y-','z+','z-'];
      const unit = () => window.matchMedia('(max-width:880px)').matches ? 72 : 90;
      let cubies = [];
      let history = [];
      let queue = [];
      let timer = 0;
      let step = 0;
      let lastMove = '复原';
      let camera = { rotX: -24, rotY: -34, zoom: 1 };
      let drag = null;
      function solvedCubies() {
        const next = [];
        for (let x = -1; x <= 1; x += 1) {
          for (let y = -1; y <= 1; y += 1) {
            for (let z = -1; z <= 1; z += 1) {
              const faces = {};
              faceNames.forEach(f => faces[f] = '#111827');
              if (x === 1) faces['x+'] = colors['x+']; if (x === -1) faces['x-'] = colors['x-'];
              if (y === 1) faces['y+'] = colors['y+']; if (y === -1) faces['y-'] = colors['y-'];
              if (z === 1) faces['z+'] = colors['z+']; if (z === -1) faces['z-'] = colors['z-'];
              next.push({ id: `${x},${y},${z}`, x, y, z, faces });
            }
          }
        }
        return next;
      }
      function rotateVector(v, axis, dir) {
        const x = v.x, y = v.y, z = v.z;
        if (axis === 'x') return dir > 0 ? { x, y: -z, z: y } : { x, y: z, z: -y };
        if (axis === 'y') return dir > 0 ? { x: z, y, z: -x } : { x: -z, y, z: x };
        return dir > 0 ? { x: -y, y: x, z } : { x: y, y: -x, z };
      }
      function faceVector(name) {
        return name === 'x+' ? {x:1,y:0,z:0} : name === 'x-' ? {x:-1,y:0,z:0} : name === 'y+' ? {x:0,y:1,z:0} : name === 'y-' ? {x:0,y:-1,z:0} : name === 'z+' ? {x:0,y:0,z:1} : {x:0,y:0,z:-1};
      }
      function vectorFace(v) {
        if (v.x === 1) return 'x+'; if (v.x === -1) return 'x-';
        if (v.y === 1) return 'y+'; if (v.y === -1) return 'y-';
        if (v.z === 1) return 'z+'; return 'z-';
      }
      function moveSpec(move) {
        const prime = move.endsWith('i');
        const m = prime ? move.slice(0, -1) : move;
        const table = { U:['y',-1,1], D:['y',1,-1], F:['z',1,1], B:['z',-1,-1], R:['x',1,1], L:['x',-1,-1] };
        const spec = table[m] || table.U;
        return { axis: spec[0], layer: spec[1], dir: prime ? -spec[2] : spec[2], label: m + (prime ? "'" : '') };
      }
      function affected(c, spec) { return c[spec.axis] === spec.layer; }
      function applyMove(move, record = true) {
        const spec = moveSpec(move);
        cubies = cubies.map(c => {
          if (!affected(c, spec)) return c;
          const pos = rotateVector(c, spec.axis, spec.dir);
          const faces = {};
          Object.entries(c.faces).forEach(([face, color]) => {
            faces[vectorFace(rotateVector(faceVector(face), spec.axis, spec.dir))] = color;
          });
          return { ...c, ...pos, faces, pulse: true };
        });
        if (record) history.push(move);
        step += 1;
        lastMove = spec.label;
        render();
        window.setTimeout(() => { cubies = cubies.map(c => ({ ...c, pulse: false })); render(); }, 340);
      }
      function render() {
        scene.innerHTML = '';
        const gap = unit();
        scene.style.transform = `scale(${camera.zoom}) rotateX(${camera.rotX}deg) rotateY(${camera.rotY}deg)`;
        cubies.slice().sort((a,b) => (a.z - b.z) || (a.y - b.y)).forEach(c => {
          const node = document.createElement('div');
          node.className = 'lf-rubik-cubie' + (c.pulse ? ' pulse' : '');
          node.style.transform = `translate3d(${c.x * gap}px, ${c.y * gap}px, ${c.z * gap}px)`;
          faceNames.forEach(face => {
            const f = document.createElement('div');
            f.className = 'lf-rubik-face';
            f.dataset.face = face;
            f.style.background = c.faces[face] || '#111827';
            node.appendChild(f);
          });
          scene.appendChild(node);
        });
        read.step.textContent = String(step);
        read.last.textContent = lastMove;
        read.scramble.textContent = String(history.length);
        read.queueCount.textContent = String(queue.length);
        read.queue.textContent = queue.length ? queue.map(m => moveSpec(m).label).join('  ') : '暂无队列。点击“随机打乱”或直接选择层转动。';
        cameraValues.rotX.textContent = String(Math.round(camera.rotX));
        cameraValues.rotY.textContent = String(Math.round(camera.rotY));
        cameraValues.zoom.textContent = camera.zoom.toFixed(2);
      }
      function playQueue(list) {
        queue = list.slice();
        clearInterval(timer);
        timer = window.setInterval(() => {
          if (!queue.length) { clearInterval(timer); timer = 0; render(); return; }
          applyMove(queue.shift());
        }, 430);
        render();
      }
      function inverse(move) { return move.endsWith('i') ? move.slice(0, -1) : move + 'i'; }
      function reset() { clearInterval(timer); timer = 0; cubies = solvedCubies(); history = []; queue = []; step = 0; lastMove = '复原'; render(); }
      function scramble() {
        const pool = ['U','Ui','D','Di','F','Fi','B','Bi','R','Ri','L','Li'];
        const moves = Array.from({ length: 18 }, () => pool[Math.floor(Math.random() * pool.length)]);
        playQueue(moves);
      }
      function undo() {
        if (!history.length) return;
        const last = history.pop();
        applyMove(inverse(last), false);
        lastMove = '撤销 ' + moveSpec(last).label;
        render();
      }
      function demo() { playQueue(['R','U','Ri','Ui','F','R','U','Ri','Ui','Fi']); }
      root.addEventListener('click', event => {
        const button = event.target.closest('button');
        if (!button) return;
        if (button.dataset.move) applyMove(button.dataset.move);
        if (button.dataset.action === 'scramble') scramble();
        if (button.dataset.action === 'undo') undo();
        if (button.dataset.action === 'demo') demo();
        if (button.dataset.action === 'reset') reset();
      });
      root.addEventListener('input', event => {
        const key = event.target.dataset && event.target.dataset.camera;
        if (!key) return;
        camera[key] = Number(event.target.value);
        render();
      });
      stage.addEventListener('pointerdown', event => {
        drag = { x: event.clientX, y: event.clientY, rotX: camera.rotX, rotY: camera.rotY };
        stage.setPointerCapture(event.pointerId);
      });
      stage.addEventListener('pointermove', event => {
        if (!drag) return;
        camera.rotY = Math.max(-180, Math.min(180, drag.rotY + (event.clientX - drag.x) * 0.42));
        camera.rotX = Math.max(-70, Math.min(40, drag.rotX - (event.clientY - drag.y) * 0.32));
        cameraInputs.rotY.value = String(camera.rotY);
        cameraInputs.rotX.value = String(camera.rotX);
        render();
      });
      stage.addEventListener('pointerup', () => { drag = null; });
      stage.addEventListener('pointercancel', () => { drag = null; });
      stage.addEventListener('wheel', event => {
        event.preventDefault();
        camera.zoom = Math.max(0.72, Math.min(1.28, camera.zoom + (event.deltaY < 0 ? 0.04 : -0.04)));
        cameraInputs.zoom.value = String(camera.zoom);
        render();
      }, { passive: false });
      window.addEventListener('resize', render);
      reset();
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)

    def bernoulli_venturi_demo_widget(self, topic: str) -> str:
        title = escape(topic or "伯努利定律")
        template = """
<section class="lf-bern-demo" data-learnforge-widget="bernoulli-venturi-demo">
  <style>
    .lf-bern-demo{--ink:#15202b;--muted:#5c6876;--line:#d6dde7;--paper:#f7f3ea;--panel:#fffdf7;--charcoal:#17202b;--cyan:#05a8b8;--blue:#2468d8;--amber:#d98216;--red:#d84c3f;--green:#128a61;font-family:"Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;color:var(--ink);background:linear-gradient(135deg,#f8f4e8 0%,#f5fbff 44%,#eef7f2 100%);border:1px solid #d9e2ec;border-radius:18px;box-sizing:border-box;min-height:760px;padding:18px;box-shadow:0 22px 56px rgba(27,48,72,.14)}
    .lf-bern-demo *{box-sizing:border-box}
    .lf-bern-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:start;margin-bottom:14px}
    .lf-bern-kicker{font-size:12px;font-weight:950;color:#0b7f87;text-transform:uppercase;letter-spacing:.08em}
    .lf-bern-title{font-size:28px;line-height:1.12;margin:4px 0 7px;letter-spacing:0}
    .lf-bern-sub{margin:0;color:var(--muted);font-size:13px;line-height:1.64;max-width:900px}
    .lf-bern-badges{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
    .lf-bern-badge{border:1px solid #cad6e3;border-radius:999px;padding:6px 10px;background:rgba(255,255,255,.76);font-size:12px;font-weight:850;white-space:nowrap}
    .lf-bern-app{display:grid;grid-template-columns:minmax(290px,352px) minmax(0,1fr);gap:14px;align-items:stretch}
    .lf-bern-panel,.lf-bern-stage-wrap{border:1px solid var(--line);background:rgba(255,253,247,.9);box-shadow:0 14px 30px rgba(38,57,82,.09)}
    .lf-bern-panel{border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:13px}
    .lf-bern-section{border-top:1px solid #e2e8f0;padding-top:12px}
    .lf-bern-section:first-child{border-top:0;padding-top:0}
    .lf-bern-section h3{margin:0 0 9px;font-size:14px;letter-spacing:0}
    .lf-bern-control{display:grid;grid-template-columns:minmax(0,1fr) 58px;gap:9px;align-items:center;margin:9px 0}
    .lf-bern-control label{grid-column:1 / -1;color:#475569;font-size:12px;font-weight:850;display:flex;justify-content:space-between;gap:10px}
    .lf-bern-control input{width:100%;accent-color:#05a8b8}
    .lf-bern-control strong{font-size:12px;color:#0d7b79;text-align:right}
    .lf-bern-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .lf-bern-actions button{min-height:38px;border:1px solid rgba(15,23,42,.08);border-radius:9px;padding:9px 8px;color:#fff;background:#2468d8;font-weight:900;font-size:12px;cursor:pointer;box-shadow:0 9px 18px rgba(36,104,216,.15)}
    .lf-bern-actions button.secondary{background:#536274}.lf-bern-actions button.good{background:#128a61}.lf-bern-actions button.layer{background:#17202b}.lf-bern-actions button.is-off{background:#9aa5b1;color:#1f2937}
    .lf-bern-readouts{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .lf-bern-readout{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:9px;min-width:0}
    .lf-bern-readout small{display:block;color:#64748b;font-size:11px;margin-bottom:4px}
    .lf-bern-readout strong{font-size:17px;line-height:1.08;color:#0f172a;white-space:nowrap}
    .lf-bern-equation{background:#17202b;color:#d7f4f2;border-radius:12px;padding:11px;font-family:"SFMono-Regular",ui-monospace,monospace;font-size:12px;line-height:1.55}
    .lf-bern-note{background:#fff7ed;border-left:4px solid #d98216;border-radius:10px;padding:10px;color:#7c3f00;font-size:12px;line-height:1.58}
    .lf-bern-stage-wrap{position:relative;overflow:hidden;min-height:610px;border-radius:14px;background:#141b24}
    .lf-bern-canvas{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none;cursor:grab}
    .lf-bern-canvas:active{cursor:grabbing}
    .lf-bern-overlay{position:absolute;left:14px;right:14px;bottom:12px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;pointer-events:none}
    .lf-bern-card{border:1px solid rgba(255,255,255,.18);background:rgba(20,27,36,.72);color:#d9e9ee;backdrop-filter:blur(10px);border-radius:10px;padding:9px;font-size:11px}
    .lf-bern-card strong{display:block;font-size:15px;color:#fff;margin-top:3px;white-space:nowrap}
    @media(max-width:960px){.lf-bern-head,.lf-bern-app{grid-template-columns:1fr}.lf-bern-badges{justify-content:flex-start}.lf-bern-stage-wrap{min-height:520px}.lf-bern-overlay{grid-template-columns:1fr 1fr}.lf-bern-readouts{grid-template-columns:1fr 1fr}}
    @media(max-width:620px){.lf-bern-demo{padding:12px}.lf-bern-title{font-size:23px}.lf-bern-readouts,.lf-bern-actions,.lf-bern-overlay{grid-template-columns:1fr}.lf-bern-stage-wrap{min-height:460px}}
  </style>
  <div class="lf-bern-head">
    <div>
      <div class="lf-bern-kicker">Bernoulli Venturi Lab</div>
      <h2 class="lf-bern-title">__TITLE__ 3D 可交互演示模型</h2>
      <p class="lf-bern-sub">拖拽舞台改变视角，滚轮或缩放滑块推进相机。调节入口速度、喉管截面积、密度和高度差后，压力场、流线、粒子尾迹、压强计与能量项会同步更新。</p>
    </div>
    <div class="lf-bern-badges"><span class="lf-bern-badge">压力场图层</span><span class="lf-bern-badge">粒子尾迹</span><span class="lf-bern-badge">流线/速度箭头</span><span class="lf-bern-badge">能量守恒读数</span></div>
  </div>
  <div class="lf-bern-app">
    <aside class="lf-bern-panel">
      <div class="lf-bern-section">
        <h3>流体参数</h3>
        <div class="lf-bern-control"><label>入口流速 v1 <span data-value="v1">4.0</span></label><input type="range" min="1.5" max="9" step="0.1" value="4" data-param="v1"><strong>m/s</strong></div>
        <div class="lf-bern-control"><label>喉管截面积比 A2/A1 <span data-value="ratio">0.55</span></label><input type="range" min="0.32" max="0.9" step="0.01" value="0.55" data-param="ratio"><strong>ratio</strong></div>
        <div class="lf-bern-control"><label>流体密度 rho <span data-value="rho">1000</span></label><input type="range" min="700" max="1300" step="10" value="1000" data-param="rho"><strong>kg/m3</strong></div>
        <div class="lf-bern-control"><label>高度差 Δh <span data-value="height">0.0</span></label><input type="range" min="-1.5" max="1.5" step="0.1" value="0" data-param="height"><strong>m</strong></div>
      </div>
      <div class="lf-bern-section">
        <h3>相机与图层</h3>
        <div class="lf-bern-control"><label>水平视角 yaw <span data-value="yaw">26</span></label><input type="range" min="-58" max="58" step="1" value="26" data-param="yaw"><strong>deg</strong></div>
        <div class="lf-bern-control"><label>俯仰视角 pitch <span data-value="pitch">-10</span></label><input type="range" min="-28" max="24" step="1" value="-10" data-param="pitch"><strong>deg</strong></div>
        <div class="lf-bern-control"><label>相机缩放 zoom <span data-value="zoom">1.00</span></label><input type="range" min="0.78" max="1.34" step="0.01" value="1" data-param="zoom"><strong>x</strong></div>
      </div>
      <div class="lf-bern-section">
        <h3>演示控制</h3>
        <div class="lf-bern-actions">
          <button type="button" class="good" data-action="toggle-running">暂停粒子</button>
          <button type="button" class="layer" data-action="toggle-streamlines">隐藏流线</button>
          <button type="button" class="layer" data-action="toggle-field">隐藏压力场</button>
          <button type="button" class="layer" data-action="toggle-labels">隐藏标注</button>
          <button type="button" class="secondary" data-action="reset-camera">重置相机</button>
          <button type="button" class="secondary" data-action="reset">重置参数</button>
        </div>
      </div>
      <div class="lf-bern-section">
        <h3>实时读数</h3>
        <div class="lf-bern-readouts">
          <div class="lf-bern-readout"><small>入口速度 v1</small><strong data-role="out-v1">4.0</strong></div>
          <div class="lf-bern-readout"><small>喉管速度 v2</small><strong data-role="out-v2">7.3</strong></div>
          <div class="lf-bern-readout"><small>入口压强 P1</small><strong data-role="out-p1">101.3</strong></div>
          <div class="lf-bern-readout"><small>喉管压强 P2</small><strong data-role="out-p2">82.7</strong></div>
          <div class="lf-bern-readout"><small>压强差 ΔP</small><strong data-role="out-dp">18.6</strong></div>
          <div class="lf-bern-readout"><small>连续性</small><strong data-role="out-cont">A1v1=A2v2</strong></div>
          <div class="lf-bern-readout"><small>总能量偏差</small><strong data-role="out-energy">0.0</strong></div>
        </div>
      </div>
      <div class="lf-bern-equation">P + 1/2 rho v^2 + rho g h = 常量<br>A1 v1 = A2 v2</div>
      <div class="lf-bern-note">观察重点：截面积变小，连续性方程迫使速度增大；动压项上升时，静压项下降。高度差会把 rho g h 加入能量分配。</div>
    </aside>
    <div class="lf-bern-stage-wrap">
      <canvas class="lf-bern-canvas" data-role="canvas" aria-label="伯努利定律三维文丘里管交互舞台"></canvas>
      <div class="lf-bern-overlay">
        <div class="lf-bern-card">宽管区域<strong data-role="badge-left">高静压 / 低流速</strong></div>
        <div class="lf-bern-card">喉管区域<strong data-role="badge-mid">低静压 / 高流速</strong></div>
        <div class="lf-bern-card">能量交换<strong data-role="badge-energy">静压 -> 动压</strong></div>
        <div class="lf-bern-card">视角控制<strong data-role="badge-view">yaw 26°</strong></div>
      </div>
    </div>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-bern-demo');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const canvas = root.querySelector('[data-role="canvas"]');
      const ctx = canvas.getContext('2d');
      const params = Object.fromEntries(Array.from(root.querySelectorAll('[data-param]')).map(node => [node.dataset.param, node]));
      const values = Object.fromEntries(Array.from(root.querySelectorAll('[data-value]')).map(node => [node.dataset.value, node]));
      const out = Object.fromEntries(Array.from(root.querySelectorAll('[data-role]')).map(node => [node.dataset.role, node]));
      let dpr = Math.max(1, window.devicePixelRatio || 1);
      let particles = [];
      const layers = { streamlines: true, field: true, labels: true };
      let running = true;
      let last = 0;
      let drag = null;
      function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
      function setControl(name, value) {
        if (params[name]) params[name].value = String(value);
      }
      function readParams() {
        const v1 = Number(params.v1.value);
        const ratio = Number(params.ratio.value);
        const rho = Number(params.rho.value);
        const height = Number(params.height.value);
        const yaw = Number(params.yaw.value);
        const pitch = Number(params.pitch.value);
        const zoom = Number(params.zoom.value);
        const v2 = v1 / Math.max(0.24, ratio);
        const p1 = 101.3;
        const dpSigned = (0.5 * rho * (v2 * v2 - v1 * v1) + rho * 9.81 * height) / 1000;
        const p2 = clamp(p1 - dpSigned, 4, 165);
        const dyn1 = 0.5 * rho * v1 * v1 / 1000;
        const dyn2 = 0.5 * rho * v2 * v2 / 1000;
        const total1 = p1 + dyn1;
        const total2 = p2 + dyn2 + rho * 9.81 * height / 1000;
        return { v1, ratio, rho, height, yaw, pitch, zoom, v2, p1, p2, dp: p1 - p2, dyn1, dyn2, total1, total2 };
      }
      function resize() {
        const r = canvas.getBoundingClientRect();
        dpr = Math.max(1, window.devicePixelRatio || 1);
        canvas.width = Math.max(720, Math.floor(r.width * dpr));
        canvas.height = Math.max(500, Math.floor(r.height * dpr));
        draw();
      }
      function seedParticles() {
        particles = Array.from({ length: 176 }, (_, i) => ({
          x: (i / 176) * 1.16 - 0.08,
          lane: Math.random() * 2 - 1,
          phase: Math.random() * Math.PI * 2,
          shade: Math.random(),
          drift: Math.random() * 0.55 + 0.65
        }));
      }
      function radiusAt(t, ratio) {
        const throat = Math.exp(-Math.pow((t - 0.5) / 0.18, 2));
        const area = 1 - throat * (1 - ratio);
        return 0.19 + 0.21 * Math.sqrt(Math.max(0.22, area));
      }
      function relativeAreaAt(t, ratio) {
        const r = radiusAt(t, ratio);
        const r0 = radiusAt(0.08, ratio);
        return Math.max(0.2, (r * r) / (r0 * r0));
      }
      function areaSpeedAt(t, p) {
        return p.v1 / relativeAreaAt(t, p.ratio);
      }
      function pressureAt(t, p) {
        const speed = areaSpeedAt(t, p);
        const heightTerm = p.rho * 9.81 * p.height * t / 1000;
        return clamp(p.p1 - (0.5 * p.rho * (speed * speed - p.v1 * p.v1)) / 1000 - heightTerm, 4, 165);
      }
      function project(x, y, z) {
        const W = canvas.width, H = canvas.height;
        const p = readParams();
        const cy = Math.cos(p.yaw * Math.PI / 180), sy = Math.sin(p.yaw * Math.PI / 180);
        const cp = Math.cos(p.pitch * Math.PI / 180), sp = Math.sin(p.pitch * Math.PI / 180);
        const x1 = x * cy + z * sy;
        const z1 = z * cy - x * sy;
        const y1 = y * cp - z1 * sp;
        const z2 = y * sp + z1 * cp;
        const depth = 2.35 + z2 * 0.34;
        const scale = Math.min(W / 2.05, H / 1.18) * p.zoom / depth;
        return { x: W * 0.51 + x1 * scale, y: H * 0.51 + y1 * scale, s: scale, depth };
      }
      function pipePoint(t, side, p) {
        const x = (t - 0.5) * 1.52;
        const r = radiusAt(t, p.ratio);
        const heightCurve = p.height * (t - 0.5) * 0.075;
        return project(x, side * r + heightCurve, 0);
      }
      function pressureColor(t, p, alpha) {
        const pressure = pressureAt(t, p);
        const ratio = clamp((p.p1 - pressure) / 42, 0, 1);
        const r = Math.round(19 + ratio * 225);
        const g = Math.round(153 - ratio * 66);
        const b = Math.round(170 - ratio * 126);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
      }
      function drawBackdrop() {
        const W = canvas.width, H = canvas.height;
        const sky = ctx.createLinearGradient(0, 0, 0, H);
        sky.addColorStop(0, '#111923');
        sky.addColorStop(0.48, '#172430');
        sky.addColorStop(1, '#efe6d1');
        ctx.fillStyle = sky;
        ctx.fillRect(0, 0, W, H);
        ctx.strokeStyle = 'rgba(255,255,255,.055)';
        ctx.lineWidth = 1 * dpr;
        for (let x = -W; x < W * 2; x += 42 * dpr) {
          ctx.beginPath();
          ctx.moveTo(x, H * 0.63);
          ctx.lineTo(x + W * 0.28, H);
          ctx.stroke();
        }
        for (let y = H * 0.63; y < H; y += 36 * dpr) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(W, y);
          ctx.stroke();
        }
        ctx.fillStyle = 'rgba(255,255,255,.045)';
        ctx.font = (12 * dpr) + 'px "SFMono-Regular", monospace';
        ctx.textAlign = 'left';
        ctx.fillText('continuity field / pressure map / live particle traces', 22 * dpr, 28 * dpr);
      }
      function drawPipe(p) {
        const top = [], bottom = [];
        for (let i = 0; i <= 120; i += 1) {
          const t = i / 120;
          top.push(pipePoint(t, -1, p));
          bottom.push(pipePoint(t, 1, p));
        }
        if (layers.field) {
          for (let i = 0; i < top.length - 1; i += 1) {
            const t = i / (top.length - 1);
            ctx.beginPath();
            ctx.moveTo(top[i].x, top[i].y);
            ctx.lineTo(top[i + 1].x, top[i + 1].y);
            ctx.lineTo(bottom[i + 1].x, bottom[i + 1].y);
            ctx.lineTo(bottom[i].x, bottom[i].y);
            ctx.closePath();
            ctx.fillStyle = pressureColor(t, p, 0.68);
            ctx.fill();
          }
        } else {
          const grad = ctx.createLinearGradient(canvas.width * 0.18, 0, canvas.width * 0.82, 0);
          grad.addColorStop(0, 'rgba(38,205,210,.48)');
          grad.addColorStop(0.5, 'rgba(245,158,11,.40)');
          grad.addColorStop(1, 'rgba(27,185,139,.44)');
          ctx.beginPath();
          top.forEach((pt, i) => i ? ctx.lineTo(pt.x, pt.y) : ctx.moveTo(pt.x, pt.y));
          bottom.slice().reverse().forEach(pt => ctx.lineTo(pt.x, pt.y));
          ctx.closePath();
          ctx.fillStyle = grad;
          ctx.fill();
        }
        ctx.save();
        ctx.shadowColor = 'rgba(0,0,0,.35)';
        ctx.shadowBlur = 18 * dpr;
        ctx.lineWidth = 8 * dpr;
        ctx.strokeStyle = 'rgba(6,10,16,.72)';
        ctx.beginPath();
        top.forEach((pt, i) => i ? ctx.lineTo(pt.x, pt.y) : ctx.moveTo(pt.x, pt.y));
        bottom.slice().reverse().forEach(pt => ctx.lineTo(pt.x, pt.y));
        ctx.closePath();
        ctx.stroke();
        ctx.restore();
        ctx.lineWidth = 2 * dpr;
        ctx.strokeStyle = 'rgba(255,255,255,.48)';
        ctx.beginPath(); top.forEach((pt, i) => i ? ctx.lineTo(pt.x, pt.y) : ctx.moveTo(pt.x, pt.y)); ctx.stroke();
        ctx.strokeStyle = 'rgba(15,23,42,.42)';
        ctx.beginPath(); bottom.forEach((pt, i) => i ? ctx.lineTo(pt.x, pt.y) : ctx.moveTo(pt.x, pt.y)); ctx.stroke();
        [0.08, 0.5, 0.92].forEach((t, idx) => {
          const c = project((t - 0.5) * 1.52, p.height * (t - 0.5) * 0.075, 0);
          const r = radiusAt(t, p.ratio) * c.s;
          ctx.beginPath();
          ctx.ellipse(c.x, c.y, Math.max(14, r * 0.42), Math.max(20, r), p.yaw * Math.PI / 180, 0, Math.PI * 2);
          ctx.strokeStyle = idx === 1 ? 'rgba(249,180,58,.95)' : 'rgba(255,255,255,.46)';
          ctx.lineWidth = (idx === 1 ? 3 : 2) * dpr;
          ctx.stroke();
        });
      }
      function drawStreamlines(p) {
        if (!layers.streamlines) return;
        const lanes = [-0.72, -0.42, -0.16, 0.16, 0.42, 0.72];
        lanes.forEach((lane, idx) => {
          ctx.beginPath();
          for (let i = 0; i <= 96; i += 1) {
            const t = i / 96;
            const r = radiusAt(t, p.ratio);
            const y = lane * r + Math.sin(t * Math.PI * 2 + idx) * r * 0.025 + p.height * (t - 0.5) * 0.075;
            const pt = project((t - 0.5) * 1.52, y, 0.036);
            if (i === 0) ctx.moveTo(pt.x, pt.y); else ctx.lineTo(pt.x, pt.y);
          }
          ctx.strokeStyle = idx % 2 ? 'rgba(255,255,255,.48)' : 'rgba(132,230,224,.58)';
          ctx.lineWidth = 1.5 * dpr;
          ctx.stroke();
        });
      }
      function drawGauge(t, label, pressure, p, color) {
        const base = project((t - 0.5) * 1.52, -0.54, 0);
        const h = clamp(pressure * 1.18, 28, 150) * dpr;
        const x = base.x, y = base.y - 8 * dpr;
        ctx.strokeStyle = 'rgba(236,244,247,.72)';
        ctx.lineWidth = 2 * dpr;
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - 164 * dpr); ctx.stroke();
        ctx.strokeRect(x - 9 * dpr, y - 164 * dpr, 18 * dpr, 164 * dpr);
        const grad = ctx.createLinearGradient(x, y, x, y - h);
        grad.addColorStop(0, color);
        grad.addColorStop(1, 'rgba(255,255,255,.94)');
        ctx.fillStyle = grad;
        ctx.fillRect(x - 8 * dpr, y - h, 16 * dpr, h);
        ctx.fillStyle = 'rgba(10,14,20,.72)';
        ctx.fillRect(x - 48 * dpr, y - 196 * dpr, 96 * dpr, 36 * dpr);
        ctx.strokeStyle = 'rgba(255,255,255,.18)';
        ctx.strokeRect(x - 48 * dpr, y - 196 * dpr, 96 * dpr, 36 * dpr);
        ctx.fillStyle = '#f8fafc';
        ctx.font = (11 * dpr) + 'px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(label + ' ' + pressure.toFixed(1) + ' kPa', x, y - 174 * dpr);
      }
      function drawParticles(p) {
        particles.forEach(pt => {
          const t = clamp(pt.x, 0, 1);
          const r = radiusAt(t, p.ratio);
          const y = pt.lane * r * 0.72 + Math.sin(pt.phase) * r * 0.07 + p.height * (t - 0.5) * 0.075;
          const pos = project((t - 0.5) * 1.52, y, 0.05);
          const speed = areaSpeedAt(t, p);
          const tailT = clamp(t - 0.015 - speed * 0.006, 0, 1);
          const tailR = radiusAt(tailT, p.ratio);
          const tail = project((tailT - 0.5) * 1.52, pt.lane * tailR * 0.72 + p.height * (tailT - 0.5) * 0.075, 0.04);
          ctx.strokeStyle = speed > p.v1 * 1.45 ? 'rgba(255,190,76,.55)' : 'rgba(96,220,232,.38)';
          ctx.lineWidth = (1.3 + Math.min(2.2, speed * 0.12)) * dpr;
          ctx.beginPath();
          ctx.moveTo(tail.x, tail.y);
          ctx.lineTo(pos.x, pos.y);
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, (1.7 + Math.min(3.3, speed * 0.19)) * dpr, 0, Math.PI * 2);
          ctx.fillStyle = pt.shade > 0.58 ? 'rgba(255,255,255,.95)' : (speed > p.v1 * 1.45 ? 'rgba(255,186,73,.9)' : 'rgba(39,213,221,.88)');
          ctx.fill();
        });
      }
      function drawArrows(p) {
        [[0.16, areaSpeedAt(0.16, p), '#35d0d4'], [0.5, areaSpeedAt(0.5, p), '#f5a524'], [0.84, areaSpeedAt(0.84, p), '#3dd486']].forEach(([t, speed, color]) => {
          const a = project((t - 0.5) * 1.52 - 0.075, 0, 0.09);
          const b = project((t - 0.5) * 1.52 + Math.min(0.23, Number(speed) / 48), 0, 0.09);
          ctx.strokeStyle = String(color);
          ctx.fillStyle = String(color);
          ctx.lineWidth = 4 * dpr;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x - 12 * dpr, b.y - 7 * dpr); ctx.lineTo(b.x - 12 * dpr, b.y + 7 * dpr); ctx.closePath(); ctx.fill();
        });
      }
      function drawEnergyPanel(p) {
        const x = canvas.width - 190 * dpr;
        const y = 58 * dpr;
        const w = 156 * dpr;
        const rows = [
          ['静压 P1', p.p1, '#35d0d4'],
          ['动压 q1', p.dyn1, '#7dd3fc'],
          ['静压 P2', p.p2, '#f5a524'],
          ['动压 q2', p.dyn2, '#fb7185']
        ];
        ctx.fillStyle = 'rgba(10,14,20,.66)';
        ctx.fillRect(x - 14 * dpr, y - 24 * dpr, w + 28 * dpr, 150 * dpr);
        ctx.strokeStyle = 'rgba(255,255,255,.16)';
        ctx.strokeRect(x - 14 * dpr, y - 24 * dpr, w + 28 * dpr, 150 * dpr);
        ctx.fillStyle = '#f8fafc';
        ctx.font = (12 * dpr) + 'px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('能量项 kPa', x, y - 8 * dpr);
        rows.forEach((row, i) => {
          const by = y + (18 + i * 27) * dpr;
          const bw = clamp(row[1] / 115, 0.04, 1) * w;
          ctx.fillStyle = 'rgba(255,255,255,.12)';
          ctx.fillRect(x, by, w, 9 * dpr);
          ctx.fillStyle = row[2];
          ctx.fillRect(x, by, bw, 9 * dpr);
          ctx.fillStyle = '#dbeafe';
          ctx.fillText(row[0] + ' ' + row[1].toFixed(1), x, by - 4 * dpr);
        });
      }
      function drawLabels(p) {
        if (!layers.labels) return;
        const labels = [
          [0.1, -0.47, '入口截面 A1：速度较低，静压较高'],
          [0.5, 0.47, '喉管 A2：连续性迫使 v2 增大'],
          [0.77, -0.42, '压力恢复区：流速回落，静压回升']
        ];
        ctx.font = (12 * dpr) + 'px sans-serif';
        ctx.textAlign = 'center';
        labels.forEach(([t, offset, text]) => {
          const anchor = project((t - 0.5) * 1.52, 0, 0.08);
          const pos = project((t - 0.5) * 1.52, offset, 0.22);
          ctx.strokeStyle = 'rgba(255,255,255,.32)';
          ctx.beginPath(); ctx.moveTo(anchor.x, anchor.y); ctx.lineTo(pos.x, pos.y); ctx.stroke();
          const metrics = ctx.measureText(text);
          ctx.fillStyle = 'rgba(12,16,22,.78)';
          ctx.fillRect(pos.x - metrics.width / 2 - 10 * dpr, pos.y - 18 * dpr, metrics.width + 20 * dpr, 25 * dpr);
          ctx.fillStyle = '#f8fafc';
          ctx.fillText(text, pos.x, pos.y);
        });
      }
      function updateText(p) {
        values.v1.textContent = p.v1.toFixed(1);
        values.ratio.textContent = p.ratio.toFixed(2);
        values.rho.textContent = String(Math.round(p.rho));
        values.height.textContent = p.height.toFixed(1);
        values.yaw.textContent = String(Math.round(p.yaw));
        values.pitch.textContent = String(Math.round(p.pitch));
        values.zoom.textContent = p.zoom.toFixed(2);
        out['out-v1'].textContent = p.v1.toFixed(1) + ' m/s';
        out['out-v2'].textContent = p.v2.toFixed(1) + ' m/s';
        out['out-p1'].textContent = p.p1.toFixed(1) + ' kPa';
        out['out-p2'].textContent = p.p2.toFixed(1) + ' kPa';
        out['out-dp'].textContent = p.dp.toFixed(1) + ' kPa';
        out['out-cont'].textContent = 'v2 = v1 / ' + p.ratio.toFixed(2);
        out['out-energy'].textContent = Math.abs(p.total1 - p.total2).toFixed(1) + ' kPa';
        out['badge-mid'].textContent = p.dp > 0 ? '低静压 / 高流速' : '高度项主导';
        out['badge-energy'].textContent = '动压 +' + Math.max(0, p.dyn2 - p.dyn1).toFixed(1) + ' kPa';
        out['badge-view'].textContent = 'yaw ' + Math.round(p.yaw) + '°';
      }
      function draw() {
        if (!ctx) return;
        const p = readParams();
        updateText(p);
        drawBackdrop();
        drawPipe(p);
        drawStreamlines(p);
        drawParticles(p);
        drawArrows(p);
        drawGauge(0.18, 'P1', p.p1, p, 'rgba(8,145,178,.75)');
        drawGauge(0.5, 'P2', p.p2, p, 'rgba(217,119,6,.78)');
        drawEnergyPanel(p);
        drawLabels(p);
      }
      function tick(t) {
        const p = readParams();
        const dt = Math.min(0.034, last ? (t - last) / 1000 : 0.016);
        last = t;
        if (running) {
          particles.forEach(pt => {
            const speed = areaSpeedAt(Math.max(0, Math.min(1, pt.x)), p);
            pt.x += dt * (0.105 + speed * 0.021) * pt.drift;
            pt.phase += dt * (3.2 + speed * 0.12);
            if (pt.x > 1.08) { pt.x = -0.08; pt.lane = Math.random() * 2 - 1; pt.shade = Math.random(); }
          });
        }
        draw();
        requestAnimationFrame(tick);
      }
      root.addEventListener('input', draw);
      root.addEventListener('click', event => {
        const action = event.target && event.target.dataset ? event.target.dataset.action : '';
        if (action === 'toggle-running') {
          running = !running;
          event.target.textContent = running ? '暂停粒子' : '继续粒子';
        }
        if (action === 'toggle-streamlines') {
          layers.streamlines = !layers.streamlines;
          event.target.textContent = layers.streamlines ? '隐藏流线' : '显示流线';
          event.target.classList.toggle('is-off', !layers.streamlines);
          draw();
        }
        if (action === 'toggle-field') {
          layers.field = !layers.field;
          event.target.textContent = layers.field ? '隐藏压力场' : '显示压力场';
          event.target.classList.toggle('is-off', !layers.field);
          draw();
        }
        if (action === 'toggle-labels') {
          layers.labels = !layers.labels;
          event.target.textContent = layers.labels ? '隐藏标注' : '显示标注';
          event.target.classList.toggle('is-off', !layers.labels);
          draw();
        }
        if (action === 'reset-camera') {
          setControl('yaw', 26); setControl('pitch', -10); setControl('zoom', 1);
          draw();
        }
        if (action === 'reset') {
          setControl('v1', 4); setControl('ratio', 0.55); setControl('rho', 1000); setControl('height', 0);
          setControl('yaw', 26); setControl('pitch', -10); setControl('zoom', 1);
          running = true;
          layers.streamlines = true; layers.field = true; layers.labels = true;
          root.querySelector('[data-action="toggle-running"]').textContent = '暂停粒子';
          root.querySelector('[data-action="toggle-streamlines"]').textContent = '隐藏流线';
          root.querySelector('[data-action="toggle-field"]').textContent = '隐藏压力场';
          root.querySelector('[data-action="toggle-labels"]').textContent = '隐藏标注';
          root.querySelectorAll('[data-action^="toggle-"]').forEach(btn => btn.classList.remove('is-off'));
          seedParticles(); draw();
        }
      });
      canvas.addEventListener('pointerdown', event => {
        drag = { x: event.clientX, y: event.clientY, yaw: Number(params.yaw.value), pitch: Number(params.pitch.value) };
        canvas.setPointerCapture?.(event.pointerId);
      });
      canvas.addEventListener('pointermove', event => {
        if (!drag) return;
        setControl('yaw', Math.round(clamp(drag.yaw + (event.clientX - drag.x) * 0.18, -58, 58)));
        setControl('pitch', Math.round(clamp(drag.pitch + (event.clientY - drag.y) * 0.12, -28, 24)));
        draw();
      });
      canvas.addEventListener('pointerup', () => { drag = null; });
      canvas.addEventListener('pointercancel', () => { drag = null; });
      canvas.addEventListener('wheel', event => {
        event.preventDefault();
        const next = clamp(Number(params.zoom.value) + (event.deltaY < 0 ? 0.04 : -0.04), 0.78, 1.34);
        setControl('zoom', next.toFixed(2));
        draw();
      }, { passive: false });
      window.addEventListener('resize', resize);
      resize();
      seedParticles();
      requestAnimationFrame(tick);
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)


    def concept_demo_widget(self, topic: str) -> str:
        title = escape(topic or "互动学习")
        template = """
<section class="lfx-lab lf-concept-demo" data-learnforge-widget="concept-demo">
  <style>
    .lf-concept-demo .lf-concept-map{min-height:300px;display:grid;place-items:center;position:relative;overflow:hidden}
    .lf-concept-demo .lf-orbit{position:absolute;border:1px solid rgba(100,216,255,.18);border-radius:999px;animation:lfSpin 18s linear infinite}
    .lf-concept-demo .lf-orbit.one{width:260px;height:260px}
    .lf-concept-demo .lf-orbit.two{width:190px;height:190px;animation-duration:13s;animation-direction:reverse}
    .lf-concept-demo .lf-orbit.three{width:120px;height:120px;animation-duration:9s}
    .lf-concept-demo .lf-core{position:relative;z-index:2;width:min(240px,70%);aspect-ratio:1;border-radius:999px;display:grid;place-items:center;text-align:center;padding:24px;background:radial-gradient(circle at 35% 25%,rgba(126,240,178,.44),rgba(100,216,255,.18) 42%,rgba(155,140,255,.16));border:1px solid rgba(255,255,255,.22);box-shadow:0 0 70px rgba(100,216,255,.16)}
    .lf-concept-demo .lf-core strong{font-size:22px;line-height:1.16}
    .lf-concept-demo .lf-readout{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:12px}
    .lf-concept-demo .lf-readout div{border:1px solid rgba(255,255,255,.14);border-radius:14px;padding:10px;background:rgba(255,255,255,.07)}
    .lf-concept-demo .lf-readout small{display:block;color:#aab3ca;margin-bottom:4px}
    .lf-concept-demo .lf-readout strong{font-size:20px}
    .lf-concept-demo .lf-control-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;margin-top:10px}
    .lf-concept-demo input[type=range]{width:100%;accent-color:#64d8ff}
    @keyframes lfSpin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
    @media(max-width:760px){.lf-concept-demo .lf-readout,.lf-concept-demo .lf-control-row{grid-template-columns:1fr}.lf-concept-demo .lf-concept-map{min-height:240px}}
  </style>
  <div class="lfx-hero">
    <div>
      <div class="lfx-kicker">LearnForge Lab · 互动微应用</div>
      <h2 class="lfx-title">__TITLE__</h2>
      <p class="lfx-sub">这是降级路径下的高保真安全组件：它仍然提供可视化主体、状态读数、滑块控制、标签页讲解和即时自测。</p>
      <div class="lfx-tabs">
        <button type="button" data-lf-tab="intuition">核心直觉</button>
        <button type="button" data-lf-tab="variables">关键变量</button>
        <button type="button" data-lf-tab="practice">自测迁移</button>
      </div>
    </div>
    <div class="lfx-card">
      <strong>互动强度</strong>
      <div class="lf-control-row">
        <input type="range" min="20" max="95" value="54" data-role="intensity" aria-label="互动强度">
        <strong><span data-role="intensity-value">54</span>%</strong>
      </div>
      <div class="lf-readout">
        <div><small>直觉清晰度</small><strong data-role="clarity">68</strong></div>
        <div><small>步骤稳定性</small><strong data-role="stability">61</strong></div>
        <div><small>迁移准备</small><strong data-role="transfer">49</strong></div>
      </div>
    </div>
  </div>
  <div class="lfx-grid">
    <div class="lfx-stage lfx-span-7">
      <div class="lf-concept-map" aria-label="概念可视化主体">
        <div class="lf-orbit one"></div>
        <div class="lf-orbit two"></div>
        <div class="lf-orbit three"></div>
        <div class="lf-core"><strong>__TITLE__</strong><span>输入 · 动作 · 输出</span></div>
      </div>
    </div>
    <div class="lfx-card lfx-span-5">
      <strong>理解曲线</strong>
      <div class="lfx-bar-stage" data-role="bars" data-lf-bars='[{"label":"输入","value":68},{"label":"动作","value":61},{"label":"输出","value":49},{"label":"迁移","value":37}]'></div>
    </div>
    <article class="lfx-card lfx-span-4" data-lf-panel="intuition">
      <strong>核心直觉</strong>
      <p>把“__TITLE__”先拆成可观察的状态、变化和结果，避免只背结论。</p>
    </article>
    <article class="lfx-card lfx-span-4" data-lf-panel="variables">
      <strong>关键变量</strong>
      <p>记录输入、约束、变化方向和输出，用它们解释每一步为什么发生。</p>
    </article>
    <article class="lfx-card lfx-span-4" data-lf-panel="practice">
      <strong>检查理解</strong>
      <div data-lf-quiz>
        <p>学习一个新概念时，哪一步最能防止“看懂但不会用”？</p>
        <div class="lfx-toolbar">
          <button type="button" data-lf-answer="false">先背定义</button>
          <button type="button" data-lf-answer="true">预测变化并用例子校验</button>
        </div>
        <p data-lf-feedback>选择一个答案。</p>
      </div>
    </article>
  </div>
  <script>
    (() => {
      const root = document.currentScript.closest('.lf-concept-demo');
      if (!root || root.dataset.ready === '1') return;
      root.dataset.ready = '1';
      const input = root.querySelector('[data-role="intensity"]');
      const valueNode = root.querySelector('[data-role="intensity-value"]');
      const clarity = root.querySelector('[data-role="clarity"]');
      const stability = root.querySelector('[data-role="stability"]');
      const transfer = root.querySelector('[data-role="transfer"]');
      const bars = root.querySelector('[data-role="bars"]');
      function render() {
        const value = Number(input.value || 54);
        const nextClarity = Math.min(96, value + 14);
        const nextStability = Math.min(94, Math.round(value * 0.9 + 12));
        const nextTransfer = Math.min(92, Math.round(value * 0.72 + 10));
        valueNode.textContent = value;
        clarity.textContent = nextClarity;
        stability.textContent = nextStability;
        transfer.textContent = nextTransfer;
        if (window.LF && typeof window.LF.bars === 'function') {
          window.LF.bars(bars, [
            { label: '输入', value: nextClarity },
            { label: '动作', value: nextStability },
            { label: '输出', value: nextTransfer },
            { label: '迁移', value: Math.max(28, nextTransfer - 12) }
          ], { active: [Math.floor(value / 25) % 4] });
        }
      }
      input.addEventListener('input', render);
      render();
    })();
  </script>
</section>
"""
        return template.replace("__TITLE__", title)

    def sanitize_widget(self, html: str) -> str:
        cleaned = str(html or "")
        cleaned = re.sub(r"<!--[\s\S]*?-->", "", cleaned)
        tag_group = "|".join(self.blocked_tags)
        cleaned = re.sub(rf"<\s*({tag_group})\b[^>]*>[\s\S]*?<\s*/\s*\1\s*>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(rf"<\s*/?\s*({tag_group})\b[^>]*>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<\s*script\b[^>]*\bsrc\s*=\s*['\"](?!https://|http://|data:|blob:)[^'\"]*['\"][^>]*>[\s\S]*?<\s*/\s*script\s*>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<\s*script\b(?=[^>]*\btype\s*=)(?![^>]*\btype\s*=\s*['\"]?(?:text/javascript|application/javascript|module|importmap)['\"]?)[^>]*>[\s\S]*?<\s*/\s*script\s*>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s(href|src)\s*=\s*(['\"]?)\s*javascript:[^'\"\s>]*\2", r' \1="#"', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"url\(\s*(['\"]?)javascript:[^)]+\)", "none", cleaned, flags=re.IGNORECASE)
        cleaned = self.sanitize_scripts(cleaned)
        if not cleaned.strip():
            cleaned = "<section><h2>学习卡片</h2><p>原始 HTML 包含不安全内容，已降级为安全预览。</p></section>"
        return cleaned

    def sanitize_scripts(self, html: str) -> str:
        def replace_script(match: re.Match[str]) -> str:
            tag = match.group(0)
            script_body = match.group(1) or ""
            if any(re.search(pattern, script_body, flags=re.IGNORECASE) for pattern in self.blocked_script_patterns):
                return "<script>console.warn('LearnForge blocked unsafe widget script.');</script>"
            return tag

        return re.sub(r"<\s*script\b[^>]*>([\s\S]*?)<\s*/\s*script\s*>", replace_script, html, flags=re.IGNORECASE)

    def short_widget_title(self, topic: str, default: str) -> str:
        """Collapse a possibly-huge topic (e.g. a whole assistant reply pulled from context)
        into a clean short title so it never renders as a wall of text inside a widget."""
        text = str(topic or "")
        text = re.sub(r"<[^>]+>", " ", text)            # strip html tags
        text = re.sub(r"[*#`_>\[\]()$\\]", "", text)     # strip markdown/latex noise
        text = re.sub(r"\s+", " ", text).strip()
        # Take the first natural segment before punctuation.
        segment = re.split(r"[，。！？!?,;；:：\n]", text)[0].strip()
        candidate = segment or text
        if not candidate or len(candidate) > 40:
            candidate = (candidate or "")[:24].strip()
        return candidate or default

    # Topic detectors are STRICT and meant to run on the concise topic string — not on the
    # full generated HTML (whose script bodies often contain words like "sort"). Use specific
    # domain terms so a long mixed text can't accidentally trigger the wrong curated widget.
    def is_sorting_topic(self, combined: str) -> bool:
        return re.search(r"排序|冒泡排序|插入排序|选择排序|快速排序|归并排序|堆排序|bubble sort|quick sort|insertion sort|selection sort|merge sort|sorting algorithm", combined, flags=re.IGNORECASE) is not None

    def is_hash_collision_topic(self, combined: str) -> bool:
        return re.search(r"哈希表|散列表|hash table|哈希冲突|哈希函数|链地址|线性探测|开放寻址", combined, flags=re.IGNORECASE) is not None

    def is_pigeonhole_topic(self, combined: str) -> bool:
        return re.search(r"抽屉原理|鸽巢原理|pigeonhole", combined, flags=re.IGNORECASE) is not None

    def is_quadratic_topic(self, combined: str) -> bool:
        return re.search(r"二次函数|抛物线|顶点式|判别式|开口方向|quadratic function|parabola", combined, flags=re.IGNORECASE) is not None

    def is_momentum_topic(self, combined: str) -> bool:
        return re.search(r"动量守恒|动量|弹性碰撞|非弹性碰撞|恢复系数|conservation of momentum|elastic collision|碰撞", combined, flags=re.IGNORECASE) is not None

    def is_bernoulli_topic(self, combined: str) -> bool:
        return re.search(r"伯努利|文丘里|流体|流速|压强|压力差|管道收缩|venturi|bernoulli|fluid pressure", combined, flags=re.IGNORECASE) is not None

    def is_rubik_cube_topic(self, combined: str) -> bool:
        return re.search(r"魔方|三阶魔方|鲁比克|Rubik|Rubik's Cube|Rubiks Cube|cube restoration|层转动|还原演示", combined, flags=re.IGNORECASE) is not None

    def has_empty_visual_shell(self, html: str) -> bool:
        blocked_script = "blocked unsafe widget script" in html
        placeholder = re.search(r"请点击上方按钮|开始动画|等待生成|观察不同算法|empty stage|blank|\{\{[^}]+\}\}", html, flags=re.IGNORECASE)
        return blocked_script or placeholder is not None

    def has_inert_controls(self, html: str) -> bool:
        button_count = len(re.findall(r"<\s*button\b", html, flags=re.IGNORECASE))
        if button_count == 0:
            return False
        has_binding = re.search(r"addEventListener\s*\(|\bon[a-z]+\s*=|data-(?:action|move)\s*=", html, flags=re.IGNORECASE) is not None
        return button_count >= 2 and not has_binding

    def needs_interactive_fallback(self, topic: str, raw_html: str, html: str) -> bool:
        combined = f"{topic}\n{raw_html}\n{html}"
        has_curated_sorting = 'data-learnforge-widget="sorting-demo"' in html
        has_curated_hash = 'data-learnforge-widget="hash-collision-demo"' in html
        has_curated_pigeonhole = 'data-learnforge-widget="pigeonhole-demo"' in html
        has_curated_quadratic = 'data-learnforge-widget="quadratic-demo"' in html
        has_curated_rubik = 'data-learnforge-widget="rubik-cube-demo"' in html
        topic_text = str(topic or "")
        # A demo is genuinely usable only if it has a real Canvas/SVG scene with a script
        # and no template leaks. Never replace a working AI demo purely because the topic matches.
        has_real_scene = (
            re.search(r"<\s*(canvas|svg)\b", html, flags=re.IGNORECASE) is not None
            and re.search(r"<\s*script\b", html, flags=re.IGNORECASE) is not None
        )
        has_template_leak = re.search(r"\{\{[^}]+\}\}", html, flags=re.IGNORECASE) is not None
        has_inert_controls = self.has_inert_controls(html)
        demo_is_broken = (not has_real_scene) or has_template_leak or has_inert_controls
        if self.is_rubik_cube_topic(topic_text) and not has_curated_rubik and demo_is_broken:
            return True
        if self.is_quadratic_topic(topic_text) and not has_curated_quadratic and demo_is_broken:
            return True
        if self.is_hash_collision_topic(topic_text) and not has_curated_hash and demo_is_broken:
            return True
        if self.is_pigeonhole_topic(topic_text) and not has_curated_pigeonhole and demo_is_broken:
            return True
        if self.is_sorting_topic(topic_text) and not has_curated_sorting and demo_is_broken:
            return True
        if self.is_momentum_topic(topic_text) and demo_is_broken:
            return True
        if self.is_bernoulli_topic(topic_text) and demo_is_broken:
            return True
        # NOTE: we intentionally do NOT route on `combined` (topic + raw_html + html) here.
        # The generated HTML/script body can contain words like "sort" and would mis-trigger
        # a curated replacement for an unrelated topic. Topic detection above uses topic_text only.
        if re.search(r"\{\{[^}]+\}\}", html, flags=re.IGNORECASE):
            return True
        if re.search(r"\{\{[^}]+\}\}|学习率|梯度下降|gradient descent|learning rate", html, flags=re.IGNORECASE) and self.is_quadratic_topic(topic_text):
            return True
        has_controls = re.search(r"<\s*(button|input)\b", html, flags=re.IGNORECASE) is not None
        has_script = re.search(r"<\s*script\b", html, flags=re.IGNORECASE) is not None
        asks_interactive = re.search(r"互动|演示|动画|可视化|点击|按钮|滑块|interactive|demo|animation", combined, flags=re.IGNORECASE) is not None
        has_blank_stage = self.has_empty_visual_shell(html)
        return has_controls and asks_interactive and (not has_script or has_blank_stage)

    def fallback_widget(self, topic: str, raw_html: str, html: str) -> str:
        # Route ONLY on the concise topic string. Never scan the generated HTML body, whose
        # script can contain words like "sort"/"bubble" and mis-route an unrelated demo into
        # the sorting widget. Titles are cleaned so a long topic never becomes a wall of text.
        topic_text = str(topic or "")
        if self.is_quadratic_topic(topic_text):
            return self.quadratic_demo_widget(self.short_widget_title(topic_text, "二次函数"))
        if self.is_hash_collision_topic(topic_text):
            return self.hash_collision_demo_widget(self.short_widget_title(topic_text, "哈希表冲突"))
        if self.is_pigeonhole_topic(topic_text):
            return self.pigeonhole_demo_widget(self.short_widget_title(topic_text, "抽屉原理"))
        if self.is_rubik_cube_topic(topic_text):
            return self.rubik_cube_demo_widget(self.short_widget_title(topic_text, "三阶魔方还原"))
        if self.is_sorting_topic(topic_text):
            return self.sorting_kinetic_lab_widget(self.short_widget_title(topic_text, "经典排序算法"))
        if self.is_momentum_topic(topic_text):
            return self.momentum_collision_demo_widget(self.short_widget_title(topic_text, "动量守恒"))
        if self.is_bernoulli_topic(topic_text):
            return self.bernoulli_venturi_demo_widget(self.short_widget_title(topic_text, "伯努利定律"))
        return self.concept_demo_widget(self.short_widget_title(topic_text, "互动学习"))

    def validate_widget(self, html: str) -> bool:
        lowered = html.lower()
        blocked = ["javascript:", "<iframe", "<form", "<object", "<embed"]
        if any(item in lowered for item in blocked):
            return False
        return True

    def run(self, data: SkillInput) -> SkillOutput:
        raw_html = data.payload.get("html", "<section><h2>学习卡片</h2><p>安全沙箱预览。</p></section>")
        html = self.sanitize_widget(str(raw_html))
        valid = self.validate_widget(html)
        return SkillOutput(
            skill_name=self.skill_name,
            payload={
                "html": html,
                "valid": valid,
                "sanitized": html != str(raw_html),
                "fallback_used": False,
                "sandbox": "allow-scripts",
            },
            trace=["parsed_show_widget", "kept_generated_widget", "checked_sandbox_policy"],
        )

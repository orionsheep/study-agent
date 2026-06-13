import { describe, expect, it } from "vitest";
import { fingerprint, getCachedHeight, parseShowWidget, rescueCustomHtml, sanitizePreview, setCachedHeight, truncateOpenScript } from "../src/features/custom-html-app/widgetParser";

describe("CustomHtmlApp parser and sandbox helpers", () => {
  it("preserves text before partial show-widget fence", () => {
    const parsed = parseShowWidget('先看这段说明\n```show-widget\n{"widget_code":"<b>Hi');
    expect(parsed.textBefore).toContain("先看这段说明");
    expect(parsed.widgetCode).toContain("<b>Hi");
    expect(parsed.isClosed).toBe(false);
  });

  it("strips scripts and event handlers in preview", () => {
    const html = '<p onclick="x()" onmouseover=y()>ok</p><img src=x onerror=alert(1)><a href="javascript:alert(1)">bad</a><script>alert(1)</script>';
    expect(sanitizePreview(html)).toBe('<p>ok</p><img src=x><a href="#">bad</a>');
    expect(truncateOpenScript("<section>ok<script>const x = 1")).toBe("<section>ok");
  });

  it("caches iframe height by fingerprint", () => {
    const key = fingerprint("<p>height</p>");
    setCachedHeight(key, 333);
    expect(getCachedHeight(key)).toBe(333);
  });

  it("rescues plain quadratic parameter documents into an interactive SVG lab", () => {
    const html = `
      <section>
        <h1>参数与几何实验室</h1>
        <p>滑动下方参数，观察二次函数解析式与抛物线特征。</p>
        <label>参数 a <input type="range"></label>
        <h2>关键特征分析</h2>
      </section>
    `;
    const rescued = rescueCustomHtml(html);

    expect(rescued).toContain('data-learnforge-widget="quadratic-demo"');
    expect(rescued).toContain('data-role="svg"');
    expect(rescued).toContain('data-action="play"');
    expect(rescued).toContain("pointerdown");
    expect(rescued).not.toContain("参数与几何实验室</h1>");
  });

  it("rescues weak sorting shells into an animated canvas lab", () => {
    const html = `
      <section>
        <h1>高级排序算法交互沙盒</h1>
        <p>观察数据在内存中的跳动轨迹</p>
        <div>未排序 正在扫描/比较 交换/基准(Pivot) 排序完成</div>
        <label>选择算法 <select><option>冒泡排序 (Bubble Sort)</option></select></label>
        <label>数据规模 50 <input type="range"></label>
        <label>执行速度 中等 <input type="range"></label>
        <button>开始排序动画</button>
      </section>
    `;
    const rescued = rescueCustomHtml(html);

    expect(rescued).toContain('data-learnforge-widget="sorting-demo"');
    expect(rescued).toContain('data-role="canvas"');
    expect(rescued).toContain("Algorithm Motion Lab");
    expect(rescued).toContain("requestAnimationFrame");
    expect(rescued).not.toContain("高级排序算法交互沙盒</h1>");
  });

  it("renders a fluid demo via the curated fluid lab, never the trig lab (no false swap)", () => {
    const html = `
      <section class="bernoulli">
        <h1>伯努利定律文丘里管流体动态模拟</h1>
        <canvas id="stage"></canvas>
        <button>播放</button>
        <script>
          const ctx = document.getElementById('stage').getContext('2d');
          function draw(){ ctx.clearRect(0,0,300,150); ctx.fillRect(Math.sin(t)*10, Math.cos(t)*10, 5, 5); }
          requestAnimationFrame(function loop(){ draw(); requestAnimationFrame(loop); });
        </script>
      </section>
    `;
    const rescued = rescueCustomHtml(html);
    // A Bernoulli/fluid topic must render the fluid lab (reliable), and NEVER the trig lab.
    expect(rescued).toContain('data-learnforge-widget="fluid-demo"');
    expect(rescued).not.toContain('data-learnforge-widget="trig-demo"');
  });

  it("detects a sorting topic even when the keyword is buried after a big CSS block", () => {
    const bigCss = "<style>" + ".x{color:red}".repeat(200) + "</style>"; // pushes keyword past 800 chars
    const html = `
      <section>${bigCss}
        <h2>八大经典排序算法可视化交互模型</h2>
        <select><option>冒泡排序 (Bubble O(n^2))</option></select>
        <canvas></canvas><button>开始</button>
      </section>
    `;
    const rescued = rescueCustomHtml(html);
    expect(rescued).toContain('data-learnforge-widget="sorting-demo"');
  });

  it("routes a molecular-diffusion demo to the generic particle lab", () => {
    const html = `
      <section>
        <h2>分子扩散物理模拟</h2>
        <p>观察基于布朗运动的微观粒子热运动演化宏观混合分布（熵增）的过程。</p>
        <input type="range"><button>重置</button>
      </section>
    `;
    const rescued = rescueCustomHtml(html);
    expect(rescued).toContain('data-learnforge-widget="generic-dynamic-demo"');
    expect(rescued).toContain("getContext");
  });

  it("keeps an authored Three.js/WebGL module demo instead of replacing it", () => {
    const html = `
      <!doctype html><html><head>
        <title>3D 模型测试</title>
        <script type="module">
          import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js';
          const renderer = new THREE.WebGLRenderer();
          function tick(){ requestAnimationFrame(tick); renderer.render(scene, camera); }
        </script>
      </head><body>
        <div id="stage"><canvas></canvas></div>
      </body></html>
    `;
    const rescued = rescueCustomHtml(html);
    expect(rescued).toContain("three.module.js");
    expect(rescued).toContain("WebGLRenderer");
    expect(rescued).not.toContain('data-learnforge-widget="generic-dynamic-demo"');
  });

  it("keeps an already-curated fluid widget as-is (no double wrap)", () => {
    const curated = rescueCustomHtml('<section><h1>伯努利文丘里管</h1><canvas></canvas><script>getContext()</script></section>');
    // Feeding a curated widget back through rescue must return it unchanged (single fluid-demo).
    const again = rescueCustomHtml(curated);
    expect((again.match(/data-learnforge-widget="fluid-demo"/g) ?? []).length).toBe(1);
  });

  it("rescues a form-only fluid demo (no real canvas drawing) into the fluid lab", () => {
    const html = `
      <section>
        <h1>伯努利流体沙盒</h1>
        <label>流体密度 ρ <input type="range"></label>
        <label>入口流速 v1 <input type="range"></label>
        <div>压强 P1 101.30 kPa</div>
        <script>function update(){ /* only updates readouts, no canvas */ }</script>
      </section>
    `;
    const rescued = rescueCustomHtml(html);
    expect(rescued).toContain('data-learnforge-widget="fluid-demo"');
    expect(rescued).toContain('data-role="canvas"');
    expect(rescued).toContain("getContext");
    expect(rescued).not.toContain("伯努利流体沙盒</h1>");
  });

  it("routes the server app_type-correction shell into the fluid lab", () => {
    // Shape emitted by enforce_interactive_demo_app_types when the model wrongly returns a
    // native work_energy_demo for a Bernoulli request.
    const html =
      '<section data-needs-rescue="1"><h2>流体压差做功与动能变化模拟</h2>' +
      '<p>伯努利定律的演示动画 互动演示</p>' +
      '<label>参数 <input type="range"></label><button type="button">播放</button></section>';
    const rescued = rescueCustomHtml(html);
    expect(rescued).toContain('data-learnforge-widget="fluid-demo"');
    expect(rescued).toContain("getContext");
    expect(rescued).not.toContain("流体压差做功与动能变化模拟</h2>");
  });

  it("rescues trigonometric template shells into a fitted SVG wave lab", () => {
    const html = `
      <section>
        <h1>三角函数实验室</h1>
        <label>函数类型 {{ type }}</label>
        <label>振幅 A {{ A.toFixed(1) }}</label>
        <label>角频率 ω {{ omega.toFixed(1) }}</label>
        <label>初相位 φ {{ phi.toFixed(2) }}</label>
        <div>当前数学模型 y = {{ A.toFixed(1) }} {{ funcType }}</div>
      </section>
    `;
    const rescued = rescueCustomHtml(html);

    expect(rescued).toContain('data-learnforge-widget="trig-demo"');
    expect(rescued).toContain('data-role="svg"');
    expect(rescued).toContain('data-action="play"');
    expect(rescued).toContain("Wave Motion Studio");
    expect(rescued).not.toContain("{{");
    expect(rescued).not.toContain("三角函数实验室</h1>");
  });
});

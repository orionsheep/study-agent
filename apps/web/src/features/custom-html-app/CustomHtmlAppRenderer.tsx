import { useEffect, useMemo, useRef, useState } from "react";
import { fingerprint, getCachedHeight, setCachedHeight } from "./widgetParser";

type Props = {
  code: string;
  theme: "light" | "dark";
  mode?: "canvas" | "inline";
  forceDeckBridge?: boolean;
};

const MIN_WIDGET_HEIGHT = 220;
const MAX_WIDGET_HEIGHT = 1100;

function clampWidgetHeight(height: number) {
  return Math.max(MIN_WIDGET_HEIGHT, Math.min(MAX_WIDGET_HEIGHT, Math.round(height)));
}

function learnForgeBridgeScript(widgetId: string, enableDeckBridge: boolean) {
  const encodedWidgetId = JSON.stringify(widgetId);
  const encodedDeckBridge = JSON.stringify(enableDeckBridge);
  return `
<script>
(() => {
  const WIDGET_ID = ${encodedWidgetId};
  const ENABLE_DECK_BRIDGE = ${encodedDeckBridge};
  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  function send(message) {
    parent.postMessage({ ...message, widgetId: WIDGET_ID }, '*');
  }
  function reportHeight() {
    const height = Math.max(
      document.documentElement ? document.documentElement.scrollHeight : 0,
      document.body ? document.body.scrollHeight : 0,
      document.documentElement ? Math.ceil(document.documentElement.getBoundingClientRect().height) : 0,
      document.body ? Math.ceil(document.body.getBoundingClientRect().height) : 0
    );
    send({ type: 'widget:height', height });
  }
  function installLearnForgeRuntime() {
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const toNumber = (value, fallback = 0) => {
      const next = Number(value);
      return Number.isFinite(next) ? next : fallback;
    };
    const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
    const runtime = {
      version: 'learnforge-lab-runtime@1',
      qs,
      qsa,
      clamp,
      fmt(value, digits = 2) {
        const number = Number(value);
        return Number.isFinite(number) ? number.toFixed(digits).replace(/\\.0+$/, '') : String(value ?? '');
      },
      store(initial, render) {
        let state = { ...(initial || {}) };
        const api = {
          get: () => ({ ...state }),
          set(patch) {
            state = { ...state, ...(typeof patch === 'function' ? patch(state) : patch || {}) };
            if (typeof render === 'function') render(state, api);
            reportHeight();
            return state;
          }
        };
        if (typeof render === 'function') requestAnimationFrame(() => render(state, api));
        return api;
      },
      bars(target, values, options = {}) {
        const root = typeof target === 'string' ? qs(target) : target;
        if (!root) return;
        const items = Array.isArray(values) ? values : [];
        const max = Math.max(1, ...items.map((item) => Math.abs(toNumber(typeof item === 'object' ? item.value : item, 0))));
        root.innerHTML = items.map((item, index) => {
          const value = toNumber(typeof item === 'object' ? item.value : item, 0);
          const label = typeof item === 'object' ? item.label ?? value : value;
          const pct = clamp(Math.abs(value) / max, 0.04, 1) * 100;
          const active = Array.isArray(options.active) && options.active.includes(index);
          return '<div class="lfx-bar ' + (active ? 'is-active' : '') + '" style="--h:' + pct + '%"><span>' + escapeHtml(label) + '</span></div>';
        }).join('');
      },
      sparkline(target, values, options = {}) {
        const root = typeof target === 'string' ? qs(target) : target;
        const items = (Array.isArray(values) ? values : []).map((value) => toNumber(value, 0));
        if (!root || items.length < 2) return;
        const w = toNumber(options.width, 560);
        const h = toNumber(options.height, 160);
        const min = Math.min(...items);
        const max = Math.max(...items);
        const span = max - min || 1;
        const points = items.map((value, index) => {
          const x = (index / (items.length - 1)) * w;
          const y = h - ((value - min) / span) * (h - 18) - 9;
          return x.toFixed(1) + ',' + y.toFixed(1);
        }).join(' ');
        root.innerHTML = '<svg class="lfx-spark" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="趋势线"><defs><linearGradient id="lfx-line-' + WIDGET_ID + '" x1="0" x2="1"><stop stop-color="#64d8ff"/><stop offset="1" stop-color="#7ef0b2"/></linearGradient></defs><polyline points="' + points + '" fill="none" stroke="url(#lfx-line-' + WIDGET_ID + ')" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>' + items.map((value, index) => { const p = points.split(' ')[index]; return '<circle cx="' + p.split(',')[0] + '" cy="' + p.split(',')[1] + '" r="4" />'; }).join('') + '</svg>';
      },
      tabs(root = document) {
        const buttons = qsa('[data-lf-tab]', root);
        if (!buttons.length) return;
        const activate = (name) => {
          buttons.forEach((button) => button.classList.toggle('is-active', button.getAttribute('data-lf-tab') === name));
          qsa('[data-lf-panel]', root).forEach((panel) => panel.classList.toggle('is-active', panel.getAttribute('data-lf-panel') === name));
          reportHeight();
        };
        buttons.forEach((button) => button.addEventListener('click', () => activate(button.getAttribute('data-lf-tab'))));
        activate(buttons[0].getAttribute('data-lf-tab'));
      },
      ranges(root = document) {
        qsa('input[type="range"][data-lf-output]', root).forEach((input) => {
          const output = qs(input.getAttribute('data-lf-output'), root);
          const update = () => { if (output) output.textContent = input.value; };
          input.addEventListener('input', update);
          update();
        });
      },
      quiz(root = document) {
        qsa('[data-lf-answer]', root).forEach((button) => {
          button.addEventListener('click', () => {
            const group = button.closest('[data-lf-quiz]') || root;
            qsa('[data-lf-answer]', group).forEach((item) => item.classList.remove('is-correct', 'is-wrong'));
            button.classList.add(button.getAttribute('data-lf-answer') === 'true' ? 'is-correct' : 'is-wrong');
            const feedback = qs('[data-lf-feedback]', group);
            if (feedback) feedback.textContent = button.getAttribute('data-lf-answer') === 'true' ? '判断正确，可以进入下一步。' : '这个选项不稳，再看一眼关键条件。';
            reportHeight();
          });
        });
      },
      auto(root = document) {
        runtime.tabs(root);
        runtime.ranges(root);
        runtime.quiz(root);
        qsa('[data-lf-bars]', root).forEach((node) => {
          try { runtime.bars(node, JSON.parse(node.getAttribute('data-lf-bars') || '[]')); } catch (_) {}
        });
        qsa('[data-lf-sparkline]', root).forEach((node) => {
          try { runtime.sparkline(node, JSON.parse(node.getAttribute('data-lf-sparkline') || '[]')); } catch (_) {}
        });
      }
    };
    window.LF = runtime;
  }
  window.addEventListener('error', (event) => {
    send({ type: 'widget:error', message: String(event.message || 'script error') });
  });
  window.addEventListener('unhandledrejection', (event) => {
    send({ type: 'widget:error', message: String(event.reason && event.reason.message || event.reason || 'unhandled rejection') });
  });
  installLearnForgeRuntime();
  let deckInstallAttempts = 0;
  let deckInstalled = false;
  function installDeckRuntime() {
    if (!ENABLE_DECK_BRIDGE || deckInstalled) return;
    deckInstallAttempts += 1;
    const slideSelectors = [
      'section.slide',
      '.slide',
      '[data-slide]',
      '[data-layout]',
      '.deck > section',
      'main > section'
    ];
    const slides = Array.from(new Set(slideSelectors.flatMap((selector) => qsa(selector))))
      .filter((node) => node && node.getBoundingClientRect && node.getBoundingClientRect().width > 0);
    if (slides.length < 2) {
      if (deckInstallAttempts < 12) setTimeout(installDeckRuntime, 120);
      return;
    }
    deckInstalled = true;
    const deck = qs('.deck') || qs('[data-deck]') || qs('main') || document.scrollingElement || document.documentElement;
    [document.documentElement, document.body, deck].forEach((node) => {
      if (node && node.setAttribute && !node.hasAttribute('tabindex')) node.setAttribute('tabindex', '0');
    });
    let index = Math.max(0, slides.findIndex((slide) => {
      const rect = slide.getBoundingClientRect();
      return rect.left >= -20 && rect.left < window.innerWidth * 0.6;
    }));
    if (index < 0) index = 0;
    function scrollDeckTo(left) {
      if (deck && typeof deck.scrollTo === 'function') {
        try { deck.scrollTo({ left, top: 0, behavior: 'smooth' }); return; } catch (_) {}
        try { deck.scrollLeft = left; return; } catch (_) {}
      }
      try { window.scrollTo({ left, top: 0, behavior: 'smooth' }); } catch (_) { window.scrollTo(left, 0); }
    }
    function goto(nextIndex) {
      index = Math.max(0, Math.min(slides.length - 1, nextIndex));
      const slide = slides[index];
      if (!slide) return;
      try {
        slide.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
      } catch (_) {
        const rect = slide.getBoundingClientRect();
        scrollDeckTo((deck.scrollLeft || window.scrollX || 0) + rect.left);
      }
      document.documentElement.dataset.lfDeckIndex = String(index + 1);
      document.documentElement.dataset.lfDeckTotal = String(slides.length);
      send({ type: 'deck:navigate', index: index + 1, total: slides.length });
    }
    function syncIndex() {
      const viewportWidth = Math.max(1, window.innerWidth);
      const next = slides.reduce((best, slide, slideIndex) => {
        const distance = Math.abs(slide.getBoundingClientRect().left);
        return distance < best.distance ? { index: slideIndex, distance } : best;
      }, { index, distance: viewportWidth * 2 }).index;
      index = Math.max(0, Math.min(slides.length - 1, next));
    }
    window.LFDeck = {
      slides,
      get index() { return index; },
      get total() { return slides.length; },
      next: () => goto(index + 1),
      prev: () => goto(index - 1),
      goto
    };
    window.addEventListener('keydown', (event) => {
      const tag = String(event.target && event.target.tagName || '').toLowerCase();
      if (['input', 'textarea', 'select', 'button'].includes(tag)) return;
      if (['ArrowRight', 'PageDown', ' ', 'Spacebar'].includes(event.key)) {
        event.preventDefault();
        syncIndex();
        goto(index + 1);
      }
      if (['ArrowLeft', 'PageUp'].includes(event.key)) {
        event.preventDefault();
        syncIndex();
        goto(index - 1);
      }
      if (event.key === 'Home') { event.preventDefault(); goto(0); }
      if (event.key === 'End') { event.preventDefault(); goto(slides.length - 1); }
    }, { capture: true });
    let wheelLock = 0;
    window.addEventListener('wheel', (event) => {
      if (Date.now() < wheelLock) return;
      const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
      if (Math.abs(delta) < 18) return;
      event.preventDefault();
      syncIndex();
      goto(index + (delta > 0 ? 1 : -1));
      wheelLock = Date.now() + 520;
    }, { passive: false, capture: true });
    let touchStartX = 0;
    let touchStartY = 0;
    window.addEventListener('touchstart', (event) => {
      const touch = event.touches && event.touches[0];
      if (!touch) return;
      touchStartX = touch.clientX;
      touchStartY = touch.clientY;
    }, { passive: true });
    window.addEventListener('touchend', (event) => {
      const touch = event.changedTouches && event.changedTouches[0];
      if (!touch) return;
      const dx = touch.clientX - touchStartX;
      const dy = touch.clientY - touchStartY;
      if (Math.abs(dx) < 42 || Math.abs(dx) < Math.abs(dy)) return;
      syncIndex();
      goto(index + (dx < 0 ? 1 : -1));
    }, { passive: true });
    setTimeout(() => {
      try { (deck || document.body).focus({ preventScroll: true }); } catch (_) { try { document.body.focus(); } catch (_) {} }
      goto(index);
    }, 60);
  }
  function queueDeckRuntime() {
    if (!ENABLE_DECK_BRIDGE) return;
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', installDeckRuntime, { once: true });
    }
    requestAnimationFrame(installDeckRuntime);
    setTimeout(installDeckRuntime, 120);
    setTimeout(installDeckRuntime, 420);
  }
  queueDeckRuntime();
  send({ type: 'widget:ready' });
  window.addEventListener('load', reportHeight);
  window.addEventListener('resize', reportHeight);
  let nudgeQueued = false;
  let nudgeCount = 0;
  function resetCanvasTransforms() {
    qsa('canvas').forEach((canvas) => {
      try {
        const ctx = canvas.getContext && canvas.getContext('2d');
        if (ctx && typeof ctx.setTransform === 'function') {
          ctx.setTransform(1, 0, 0, 1, 0, 0);
        }
      } catch (_) {}
    });
  }
  function nudgeVisuals() {
    try {
      nudgeCount += 1;
      qsa('canvas').forEach((canvas) => {
        const parent = canvas.parentElement;
        const rect = parent ? parent.getBoundingClientRect() : canvas.getBoundingClientRect();
        if ((!canvas.width || !canvas.height) && rect.width > 20 && rect.height > 20) {
          const dpr = window.devicePixelRatio || 1;
          canvas.width = Math.max(1, Math.floor(rect.width * dpr));
          canvas.height = Math.max(1, Math.floor(rect.height * dpr));
          canvas.style.width = rect.width + 'px';
          canvas.style.height = rect.height + 'px';
        }
      });
      resetCanvasTransforms();
      window.dispatchEvent(new Event('resize'));
      reportHeight();
    } catch (_) {}
  }
  function queueNudge() {
    if (nudgeQueued || nudgeCount > 8) return;
    nudgeQueued = true;
    requestAnimationFrame(function () {
      nudgeQueued = false;
      nudgeVisuals();
    });
  }
  if (typeof MutationObserver !== 'undefined') {
    new MutationObserver(function () { queueNudge(); }).observe(document.documentElement, { childList: true, subtree: true, attributes: true });
  }
  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(function () { queueNudge(); }).observe(document.documentElement);
    if (document.body) new ResizeObserver(function () { queueNudge(); }).observe(document.body);
  }
  queueNudge();
  setTimeout(nudgeVisuals, 80);
  setTimeout(nudgeVisuals, 300);
  setTimeout(nudgeVisuals, 900);
})();
</script>`;
}

function learnForgeFullDocumentRescueStyle() {
  return `<style data-learnforge-rescue>
html,body{width:100%;height:100%;min-height:100%;margin:0}
body{min-height:100vh}
canvas,svg{max-width:100%}
:where(.layout-container,.stage-panel,.canvas-wrapper,[class*="stage"],[id*="canvas"]){min-width:0;min-height:0}
:where(.canvas-wrapper,[id*="canvas"]){overflow:hidden}
</style>`;
}

function sourceLooksLikeDeck(html: string) {
  return /deck_kind|guizang|web\s*ppt|horizontal[- ]swipe|slide deck|data-layout=|class=["'][^"']*\bdeck\b|class=["'][^"']*\bslide\b|<section\b[^>]*\bslide\b/i.test(html);
}

function sourceLooksLikeFullDocument(html: string) {
  return /<\s*(?:!doctype|html|head|body)\b/i.test(html);
}

function injectBridgeIntoDocument(html: string, widgetId: string, enableDeckBridge: boolean) {
  const bridge = learnForgeBridgeScript(widgetId, enableDeckBridge);
  const rescueStyle = learnForgeFullDocumentRescueStyle();
  if (/<\/head\s*>/i.test(html)) {
    return html.replace(/<\/head\s*>/i, `${rescueStyle}${bridge}</head>`);
  }
  if (/<\/body\s*>/i.test(html)) {
    return html.replace(/<\/body\s*>/i, `${rescueStyle}${bridge}</body>`);
  }
  if (/<\/html\s*>/i.test(html)) {
    return html.replace(/<\/html\s*>/i, `${rescueStyle}${bridge}</html>`);
  }
  return `${html}${rescueStyle}${bridge}`;
}

function receiverPage(theme: "light" | "dark", widgetId: string, html: string, forceDeckBridge = false) {
  const source = String(html || "");
  const enableDeckBridge = forceDeckBridge || sourceLooksLikeDeck(source);
  if (sourceLooksLikeFullDocument(source)) {
    return injectBridgeIntoDocument(source, widgetId, enableDeckBridge);
  }
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
  :root{color-scheme:${theme};--bg:${theme === "dark" ? "#080914" : "#f8fafc"};--panel:rgba(255,255,255,.08);--panel2:rgba(255,255,255,.13);--line:rgba(202,211,255,.18);--fg:#f6f7fb;--muted:#aab3ca;--cyan:#64d8ff;--green:#7ef0b2;--amber:#ffd166;--rose:#ff7aa8;--violet:#9b8cff}
  *{box-sizing:border-box}
  html,body{width:100%;min-height:100%;height:100%;margin:0;color:var(--fg);font:14px/1.55 "Avenir Next","PingFang SC","Microsoft YaHei",ui-sans-serif,system-ui;letter-spacing:0;background:transparent}
  body{padding:0;overflow:auto}
  a{color:var(--cyan)}
  button,input,select{font:inherit}
  #widget-root{width:100%;min-height:100%;height:100%;padding:0}
  #widget-root>section,#widget-root>article,#widget-root>div:first-child{min-height:420px}
  .lfx-lab,.lf-concept-demo,.lf-sort-demo,.lf-hash-demo,.lf-pigeon-demo,.lf-card{position:relative;overflow:hidden;border:1px solid var(--line)!important;border-radius:0!important;background:linear-gradient(135deg,rgba(255,255,255,.10),rgba(255,255,255,.045))!important;color:var(--fg)!important;box-shadow:none!important;min-height:520px!important;padding:24px!important}
  .lfx-lab::before,.lf-concept-demo::before,.lf-sort-demo::before,.lf-hash-demo::before,.lf-pigeon-demo::before,.lf-card::before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.055) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.055) 1px,transparent 1px);background-size:28px 28px;mask-image:linear-gradient(180deg,rgba(0,0,0,.75),transparent 78%);pointer-events:none}
  .lfx-lab>* , .lf-concept-demo>* , .lf-sort-demo>* , .lf-hash-demo>* , .lf-pigeon-demo>* , .lf-card>*{position:relative}
  .lfx-hero{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(260px,.9fr);gap:18px;align-items:stretch;margin-bottom:16px}
  .lfx-kicker{display:inline-flex;align-items:center;gap:8px;color:var(--green);font-size:12px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}
  .lfx-title{margin:8px 0 10px;font-size:clamp(24px,4vw,44px);line-height:1.02;font-weight:900}
  .lfx-sub{max-width:780px;margin:0;color:var(--muted);font-size:14px;line-height:1.75}
  .lfx-card,.lfx-panel{border:1px solid var(--line);background:var(--panel);backdrop-filter:blur(14px);border-radius:14px;padding:14px}
  .lfx-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:12px}
  .lfx-span-4{grid-column:span 4}.lfx-span-5{grid-column:span 5}.lfx-span-6{grid-column:span 6}.lfx-span-7{grid-column:span 7}.lfx-span-8{grid-column:span 8}.lfx-span-12{grid-column:span 12}
  .lfx-stage{min-height:280px;border:1px solid rgba(100,216,255,.24);border-radius:18px;padding:18px;background:radial-gradient(circle at 50% 0,rgba(100,216,255,.14),transparent 42%),rgba(1,8,20,.44)}
  .lfx-toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
  .lfx-toolbar button,.lfx-button,.lfx-tabs button{min-height:36px;border:1px solid rgba(255,255,255,.16);border-radius:10px;background:linear-gradient(135deg,rgba(100,216,255,.20),rgba(155,140,255,.18));color:var(--fg);font-weight:850;padding:0 12px;cursor:pointer}
  .lfx-toolbar button:hover,.lfx-button:hover,.lfx-tabs button:hover{border-color:rgba(100,216,255,.55);transform:translateY(-1px)}
  .lfx-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.lfx-tabs button.is-active{background:linear-gradient(135deg,var(--cyan),var(--green));color:#06111c}
  [data-lf-panel]{display:none}[data-lf-panel].is-active{display:block;animation:lfxIn .24s ease}
  .lfx-bar-stage{height:260px;display:flex;align-items:flex-end;gap:8px;padding:14px;border-radius:16px;background:rgba(0,0,0,.24)}
  .lfx-bar{flex:1;min-width:14px;height:var(--h);border-radius:10px 10px 4px 4px;background:linear-gradient(180deg,var(--cyan),#476dff);display:grid;place-items:start center;color:#06111c;font-weight:900;padding-top:7px;transition:height .28s ease,transform .2s ease,background .2s ease}.lfx-bar.is-active{background:linear-gradient(180deg,var(--amber),var(--rose));transform:translateY(-8px)}
  .lfx-spark{width:100%;height:auto;overflow:visible}.lfx-spark circle{fill:var(--green);stroke:#07111f;stroke-width:2}
  [data-lf-answer].is-correct{background:linear-gradient(135deg,var(--green),var(--cyan));color:#06111c}[data-lf-answer].is-wrong{background:linear-gradient(135deg,var(--rose),#ffb86b);color:#17070f}
  @keyframes lfxIn{from{opacity:.4;transform:translateY(8px)}to{opacity:1;transform:none}}
  @media(max-width:760px){.lfx-hero,.lfx-grid{grid-template-columns:1fr}.lfx-span-4,.lfx-span-5,.lfx-span-6,.lfx-span-7,.lfx-span-8,.lfx-span-12{grid-column:auto}.lfx-lab,.lf-concept-demo,.lf-sort-demo,.lf-hash-demo,.lf-pigeon-demo,.lf-card{padding:16px!important}}
  </style>${learnForgeBridgeScript(widgetId, enableDeckBridge)}</head><body><div id="widget-root">${source}</div></body></html>`;
}

export function CustomHtmlAppRenderer({ code, theme, mode = "inline", forceDeckBridge = false }: Props) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const renderedCode = useMemo(() => String(code || ""), [code]);
  const key = useMemo(() => fingerprint(renderedCode), [renderedCode]);
  const widgetId = useMemo(() => `lf-${key}`, [key]);
  const [height, setHeight] = useState(getCachedHeight(key));
  const srcDoc = useMemo(() => receiverPage(theme, widgetId, renderedCode, forceDeckBridge), [theme, widgetId, renderedCode, forceDeckBridge]);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const message = event.data || {};
      if (event.source !== iframeRef.current?.contentWindow || message.widgetId !== widgetId) return;
      if (message.type === "widget:height" && typeof message.height === "number") {
        const nextHeight = clampWidgetHeight(message.height);
        setHeight(nextHeight);
        setCachedHeight(key, nextHeight);
      }
      if (message.type === "widget:error") {
        setHeight((current) => Math.max(current, 220));
      }
    };
    window.addEventListener("message", handler);
    return () => {
      window.removeEventListener("message", handler);
    };
  }, [widgetId]);

  return (
    <iframe
      ref={iframeRef}
      key={key}
      className={`custom-html-frame ${mode === "canvas" ? "custom-html-frame-canvas" : ""}`}
      title="CustomHtmlApp 沙箱"
      sandbox="allow-scripts allow-pointer-lock allow-presentation allow-popups allow-downloads"
      allow="fullscreen; autoplay; encrypted-media; xr-spatial-tracking; gyroscope; accelerometer"
      allowFullScreen
      srcDoc={srcDoc}
      style={mode === "canvas" ? { height: "100%", minHeight: 0 } : { height }}
      data-testid="custom-html-renderer"
    />
  );
}

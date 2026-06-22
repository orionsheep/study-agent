import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/app/styles.css"
with open(file_path, "r") as f:
    content = f.read()

# Remove EVERYTHING below the "PRO LIGHT MODE" or "ULTIMATE" comments that broke the UI
content = re.sub(r'/\* =====================================================================\s+PRO LIGHT MODE.*', '', content, flags=re.DOTALL)
content = re.sub(r'/\* =====================================================================\s+THE ULTIMATE LIGHT MODE REWRITE.*', '', content, flags=re.DOTALL)
content = re.sub(r'/\* =====================================================================\s+Global Glass Integration.*', '', content, flags=re.DOTALL)
content = re.sub(r'/\* =====================================================================\s+GLOBAL LIQUID GLASS SETTINGS.*', '', content, flags=re.DOTALL)

# Now, we inject the perfect, minimalist Light Mode overrides that DO NOT break anything.
new_css = """

/* =====================================================================
   CLEAN LIGHT MODE FOR ENGLISH WORKSPACE
   No inverts, no bad grays. Just pristine reading contrast.
   ===================================================================== */

/* 1. Global Backgrounds for English Workspace */
html:not(.dark) .english-workspace {
  background: var(--bg-1) !important;
  color: var(--text-1) !important;
}

/* 2. Specific Panels */
/* Left WordList and Middle WordDetail backgrounds */
html:not(.dark) .english-workspace [style*="background: #0a0a0a"],
html:not(.dark) .english-workspace [style*="background: '#0a0a0a'"],
html:not(.dark) .english-workspace [style*="background: #000"],
html:not(.dark) .english-workspace [style*="background: '#000'"],
html:not(.dark) .english-workspace [style*="background: #000000"] {
  background: var(--bg-0) !important;
}

/* Secondary dark backgrounds (headers, active states) */
html:not(.dark) .english-workspace [style*="background: #171717"],
html:not(.dark) .english-workspace [style*="background: rgba(23, 23, 23"] {
  background: var(--bg-2) !important;
}

/* Hover states */
html:not(.dark) .english-workspace [style*="background: rgba(255, 255, 255, 0.05)"] {
  background: var(--glass-border) !important;
}

/* 3. Text Colors (Extreme clarity) */
html:not(.dark) .english-workspace [style*="color: #fff"],
html:not(.dark) .english-workspace [style*="color: #ffffff"],
html:not(.dark) .english-workspace h1,
html:not(.dark) .english-workspace h2,
html:not(.dark) .english-workspace h3,
html:not(.dark) .english-workspace strong {
  color: #18181b !important;
}

html:not(.dark) .english-workspace [style*="color: #d4d4d4"],
html:not(.dark) .english-workspace [style*="color: #a3a3a3"] {
  color: #52525b !important;
}

html:not(.dark) .english-workspace [style*="color: #737373"],
html:not(.dark) .english-workspace p,
html:not(.dark) .english-workspace small {
  color: #71717a !important;
}

/* 4. Semantic Accents (Blue, Orange, Purple, etc.) */
html:not(.dark) .english-workspace [style*="color: #3b82f6"],
html:not(.dark) .english-workspace [style*="color: #60a5fa"] {
  color: #2563eb !important; /* Deeper blue for white bg */
}

html:not(.dark) .english-workspace [style*="color: #eab308"],
html:not(.dark) .english-workspace [style*="color: #fef08a"] {
  color: #d97706 !important; /* Deeper yellow/orange */
}

html:not(.dark) .english-workspace [style*="color: #a855f7"],
html:not(.dark) .english-workspace [style*="color: #c084fc"] {
  color: #7e22ce !important; /* Deeper purple */
}

html:not(.dark) .english-workspace [style*="background: rgba(37, 99, 235, 0.2)"] {
  background: rgba(37, 99, 235, 0.1) !important; /* Light blue bg */
}

/* 5. Borders */
html:not(.dark) .english-workspace [style*="border-color: #262626"],
html:not(.dark) .english-workspace [style*="border-bottom: 1px solid #262626"],
html:not(.dark) .english-workspace [style*="border-right: 1px solid #262626"],
html:not(.dark) .english-workspace [style*="border-top: 1px solid #171717"] {
  border-color: var(--border) !important;
}

/* 6. The FissionGraph Star Map */
/* We invert JUST the canvas, not the tooltips or buttons around it */
html:not(.dark) .fission-graph-container {
  background: #ffffff !important;
  border-left: 1px solid var(--border) !important;
}

html:not(.dark) .fission-graph-container canvas {
  filter: invert(1) hue-rotate(180deg) brightness(1.1) contrast(0.9);
}

/* Ensure the floating buttons and legend inside the graph don't get inverted or stay black */
html:not(.dark) .fission-graph-container > div:not(.force-graph-container) {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid var(--border) !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
}

html:not(.dark) .fission-graph-container > div:not(.force-graph-container) * {
  color: #18181b !important;
}
html:not(.dark) .fission-graph-container > div:not(.force-graph-container) [style*="color: #a3a3a3"] {
  color: #52525b !important;
}

/* 7. Markdown content readability */
html:not(.dark) .english-workspace .markdown-body code {
  background: var(--bg-2) !important;
  color: #2563eb !important;
}
html:not(.dark) .english-workspace .markdown-body pre {
  background: var(--bg-2) !important;
  border: 1px solid var(--border) !important;
}
html:not(.dark) .english-workspace .markdown-body pre code {
  color: #52525b !important;
}


/* =====================================================================
   GLOBAL GLASS TOGGLE SUPPORT (Controlled by Droplet icon)
   ===================================================================== */
html.enable-glass .notebooklm-workspace,
html.enable-glass .native-app-body-custom,
html.enable-glass .native-app-body-workspace {
  background: transparent !important;
}

/* Only make the English workspace transparent if we are in dark mode,
   because a transparent white workspace looks too washed out. */
html.enable-glass.dark .english-workspace [style*="background: #0a0a0a"],
html.enable-glass.dark .english-workspace [style*="background: '#0a0a0a'"] {
  background: transparent !important;
}

html.enable-glass .nblm-source-rail {
  background: rgba(128, 128, 128, 0.1) !important;
}

/* Fullscreen disables all glass */
.canvas-app.fullscreen, .appwin.fullscreen {
  background: var(--bg-0) !important;
  backdrop-filter: none !important;
}

"""

with open(file_path, "w") as f:
    f.write(content + new_css)
print("CSS patched securely")

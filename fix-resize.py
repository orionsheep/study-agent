import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Make polling permanent and robust
old_poll = """    let stableCount = 0;
    let lastW = 0, lastH = 0;
    const pollInterval = setInterval(() => {
      if (!containerRef.current) return;
      // Same offsetWidth/offsetHeight fix as updateDimensions — see comment there.
      const width = containerRef.current.offsetWidth;
      const height = containerRef.current.offsetHeight;
      if (width > 0 && height > 0) {
        if (Math.round(width) !== lastW || Math.round(height) !== lastH) {
          lastW = Math.round(width); lastH = Math.round(height);
          setDimensions({ width, height });
          stableCount = 0;
        } else {
          stableCount++;
          if (stableCount > 8) clearInterval(pollInterval); // stable for ~1.6s, stop
        }
      }
    }, 200);"""

new_poll = """    let lastW = 0, lastH = 0;
    const pollInterval = setInterval(() => {
      if (!containerRef.current) return;
      const width = containerRef.current.offsetWidth;
      const height = containerRef.current.offsetHeight;
      if (width > 0 && height > 0) {
        if (Math.round(width) !== lastW || Math.round(height) !== lastH) {
          lastW = Math.round(width); lastH = Math.round(height);
          setDimensions({ width, height });
        }
      }
    }, 150);"""

content = content.replace(old_poll, new_poll)

with open(file_path, "w") as f:
    f.write(content)
